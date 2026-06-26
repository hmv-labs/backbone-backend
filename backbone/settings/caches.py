from backbone.bootstrap import env

REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env("REDIS_PORT")

REDIS_URL_BASE = f"redis://{REDIS_HOST}:{REDIS_PORT}"

REDIS_URL_CACHE = f"{REDIS_URL_BASE}/0"
REDIS_URL_BROKER = f"{REDIS_URL_BASE}/1"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL_CACHE,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.DefaultParser",
            "CONNECTION_POOL_KWARGS": {
                "retry_on_timeout": True,
            },
        },
    },
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "TIMEOUT": None,  # never expire by default
    },
}
