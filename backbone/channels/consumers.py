import uuid

import logging

from django.contrib.auth.models import User
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels_redis.core import RedisChannelLayer

from .utils import post_disconnect, Group
from . import presence, publishers

logger = logging.getLogger(__name__)


class WebsocketConsumer(AsyncJsonWebsocketConsumer):
    channel_layer: RedisChannelLayer  # pyright: ignore

    async def add_user_to_group(self, group: str):
        if group not in self.groups:
            self.groups.append(group)
            logger.debug(f'Adding group "{group}" to channel "{self.channel_name}"')
            await self.channel_layer.group_add(group, self.channel_name)

    async def connect(self):
        await self.accept()

        self.connection_id = str(uuid.uuid4())

        # add to dedicated group for all users
        await self.add_user_to_group(Group.ALL)

        user: User = self.scope["user"]  # pyright: ignore
        if user.is_authenticated:
            # add to dedicated groups
            await self.add_user_to_group(Group.user(user.pk))
            await self.add_user_to_group(Group.AUTH)

            # mark user active
            await presence.mark_user_active(user.pk, self.connection_id)

            # broadcast the full list of connected users only to this user
            active_user_ids = await presence.get_all_active_user_ids()

            # send the active user ids snapshot to this user
            await publishers.snapshot(user.pk, active_user_ids)

            # inform others this user got active
            await publishers.diff(user.pk, True)
        else:
            # add to dedicated groups
            await self.add_user_to_group(Group.GUESTS)

    async def disconnect(self, code):
        user: User = self.scope["user"]  # pyright: ignore
        if user.is_authenticated:
            await presence.unmark_user_active(user.pk, self.connection_id)

            remaining = await presence.get_user_connection_count(user.pk)
            if not remaining:
                await publishers.diff(user.pk, False)
                await post_disconnect(user)

        # discard all registered groups above on connect
        for group in self.groups:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kws):
        """Handles ping events, subscribes and unsubscribes"""
        event_name = content.get("name")

        if event_name == "ping":
            await self.send_json({"data": {"name": "pong"}})

            user: User = self.scope["user"]  # pyright: ignore
            if user.is_authenticated:
                await presence.mark_user_active(user.pk, self.connection_id)

    async def send_json(self, event, close=False):
        try:
            content = event["data"]
            await super().send(text_data=await self.encode_json(content), close=close)
        except Exception as exc:
            logger.error(exc)
