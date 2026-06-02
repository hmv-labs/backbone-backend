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
