import logging
from backbone.bootstrap import env


class RelativePathnameFilter(logging.Filter):
    def filter(self, record):
        if "backbone/backend/" in record.pathname:
            bit = record.pathname.split("backend/")[1]
        elif "site-packages/" in record.pathname:
            bit = record.pathname.split("site-packages/")[1]
        else:
            bit = record.pathname

        record.relative_pathname = bit

        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "relative_pathname": {
            "()": "backbone.settings.logging.RelativePathnameFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} [{asctime}] {relative_pathname} {funcName}:{lineno} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "stream": {
            "level": env("LOG_LEVEL"),
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["relative_pathname"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["stream"],
            "propagate": False,
            "level": "INFO",
        },
        "backbone": {
            "handlers": ["stream"],
            "propagate": False,
            "level": env("LOG_LEVEL"),
        },
    },
}
