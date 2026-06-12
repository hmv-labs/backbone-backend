from backbone.settings.caches import REDIS_HOST


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "channels",
    ]

    settings["CHANNEL_LAYERS"] = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(REDIS_HOST, 6379)],
            },
        },
    }

    # dotted path to a function hook that could implement any logic when the user
    # disconnects from the websocket server
    # eg: consumer projects could update a last_seen timestamp on User.profile
    settings["BACKBONE_CHANNELS_POST_DISCONNECT_FUNC"] = (
        "backbone.channels.utils.post_disconnect_func"
    )
