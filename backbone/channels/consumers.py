import uuid

import logging
import redis.asyncio as redis
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from channels_redis.core import RedisChannelLayer
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class WebsocketConsumer(AsyncJsonWebsocketConsumer):
    channel_layer: RedisChannelLayer

    GROUP_ALL = "all"
    GROUP_ALL_LOGGED_IN = "all-logged-in"

    @staticmethod
    def get_group_name(*args):
        return "-".join(map(str.lower, map(str, args)))

    async def connect(self):
        await self.accept()

        self.connection_id = str(uuid.uuid4())

        # add to dedicated group for all users
        group = self.GROUP_ALL
        if group not in self.groups:  # pyright: ignore
            self.groups.append(group)  # pyright: ignore
            await self.channel_layer.group_add(group, self.channel_name)

        user = self.scope["user"]
        if user.is_authenticated:
            # add to dedicated group for this user
            group = self.get_group_name("user", user.id)
            if group not in self.groups:  # pyright: ignore
                self.groups.append(group)  # pyright: ignore
                await self.channel_layer.group_add(group, self.channel_name)

            # add to dedicated group for logged in users
            group = self.GROUP_ALL_LOGGED_IN
            if group not in self.groups:  # pyright: ignore
                self.groups.append(group)  # pyright: ignore
                await self.channel_layer.group_add(group, self.channel_name)

            # mark user active
            await mark_user_active(user.id, self.connection_id)

            # broadcast the full list of connected users only to this user
            active_user_ids = await get_all_active_user_ids()

            await self.send_json(
                {
                    "data": {
                        "type": "presence_snapshot",
                        "data": active_user_ids,
                    }
                }
            )

            # send diff to everyone else
            await broadcast_presence_diff(user.id)

    async def disconnect(self, code):
        user = self.scope["user"]
        if user.is_authenticated:
            await unmark_user_active(user.id, self.connection_id)
            remaining = await get_user_connection_count(user.id)
            if not remaining:
                await broadcast_presence_diff(user.id, connected=False)
                await set_last_seen(user)

        # discard all registered groups above on connect
        for group in self.groups:  # pyright: ignore
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kws):
        """Handles ping events, subscribes and unsubscribes"""
        event_type = content.get("type")

        if event_type == "ping":
            await self.send_json({"data": {"type": "pong"}})
            user = self.scope["user"]
            if user.is_authenticated:
                await mark_user_active(user.id, self.connection_id)

        # subscribe to various groups on client demand
        groups = content.get("groups")

        if event_type == "subscribe":
            for group in groups:
                if group not in self.groups:
                    self.groups.append(group)  # pyright: ignore
                    await self.channel_layer.group_add(group, self.channel_name)

        if event_type == "unsubscribe":
            for group in groups:
                if group in self.groups:
                    self.groups.remove(group)  # pyright: ignore
                    await self.channel_layer.group_discard(group, self.channel_name)

    async def send_json(self, event, close=False):
        try:
            content = event["data"]
            await super().send(text_data=await self.encode_json(content), close=close)
        except Exception as exc:
            logger.error(exc)


channel_layer = get_channel_layer()


# presence related stuff
"""
- we store user connections in redis (see def mark_user_active)
- on ws connect
    - we mark the user active (per connection)
    - we send to this user the entire presence snapshot (all user ids from redis)
    - we broadcast this user has joined

- on ws ping
    - we mark the user active (hence keeping it alive in redis)

- on ws disconnect
    - we mark the user connection inactive
    - we check for other connections this user might have
    - if none remaining
        - we broadcast this user has left
        - we update user.profile.last_seen
"""
PRESENCE_TTL = 30  # in seconds - should be slightly higer than ws heartbeat interval
PRESENCE_KEY = "ws:presence"

r = redis.from_url(settings.REDIS_URL_CACHE, decode_responses=True)


@database_sync_to_async
def set_last_seen(user):
    # TODO update this
    user.profile.last_seen = now()
    user.profile.save(update_fields=["last_seen"])


async def mark_user_active(user_id: int, conn_id: str):
    await r.setex(f"{PRESENCE_KEY}:{user_id}:{conn_id}", PRESENCE_TTL, "1")


async def unmark_user_active(user_id: int, conn_id: str):
    await r.delete(f"{PRESENCE_KEY}:{user_id}:{conn_id}")


async def get_all_active_user_ids():
    keys = await r.keys(f"{PRESENCE_KEY}:*")
    user_ids = {int(k.split(":")[-2]) for k in keys}
    return list(user_ids)


async def get_user_connection_count(user_id):
    remaining = await r.keys(f"{PRESENCE_KEY}:{user_id}:*")
    return remaining


async def broadcast_presence_diff(user_id, connected=True):
    await channel_layer.group_send(  # pyright: ignore
        WebsocketConsumer.GROUP_ALL,
        {
            "type": "send_json",
            "data": {
                "type": "presence_diff",
                "data": {
                    "user_id": user_id,
                    "connected": connected,
                },
            },
        },
    )


# end presence related stuff


@async_to_sync
async def push_to_all(data_type, data):
    await channel_layer.group_send(  # pyright: ignore
        WebsocketConsumer.GROUP_ALL,
        {
            "type": "send_json",
            "data": {
                "type": data_type,
                "data": data,
            },
        },
    )


@async_to_sync
async def push_to_user(user_id, data_type, data):
    group_name = WebsocketConsumer.get_group_name("user", user_id)
    await channel_layer.group_send(  # pyright: ignore
        group_name,
        {
            "type": "send_json",
            "data": {
                "type": data_type,
                "data": data,
            },
        },
    )


def push_to_user_many(user_ids, data_type, data):
    """Light wrapper to accomodate the push to more users"""
    for user_id in user_ids:
        push_to_user(user_id, data_type, data)
