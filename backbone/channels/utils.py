import logging

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.module_loading import import_string

channel_layer = get_channel_layer()
logger = logging.getLogger(__name__)


class Group:
    ALL = "all"
    AUTH = "auth"
    GUESTS = "guests"

    @staticmethod
    def get_name(*args):
        return "-".join(map(str.lower, map(str, args)))

    @staticmethod
    def user(id: int):
        return Group.get_name("user", id)


_post_disconnect_func = None


@database_sync_to_async
def post_disconnect(user: User):
    global _post_disconnect_func

    if _post_disconnect_func is None:
        if settings.BACKBONE_CHANNELS_POST_DISCONNECT_FUNC is False:
            _post_disconnect_func = False
        else:
            _post_disconnect_func = import_string(
                settings.BACKBONE_CHANNELS_POST_DISCONNECT_FUNC
            )

    if callable(_post_disconnect_func):
        _post_disconnect_func(user)


def post_disconnect_func(user: User):
    logger.warning(
        "Update settings.BACKBONE_CHANNELS_POST_DISCONNECT_FUNC "
        "to either a function (dotted path) or False to bypass "
        "the hook"
    )


async def push(group_name: str, event_name: str, data: dict | None):
    await channel_layer.group_send(  # pyright: ignore
        group_name,
        {
            "type": "send_json",
            "data": {
                "name": event_name,
                "data": data,
            },
        },
    )


def push_sync(group_name: str, event_name: str, data: dict | None):
    return async_to_sync(push)(group_name, event_name, data)
