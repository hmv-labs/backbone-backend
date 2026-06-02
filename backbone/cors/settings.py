from backbone.env import env
from corsheaders.defaults import default_headers
from backbone.settings.common import FRONTEND_PUBLIC_URL


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "corsheaders",
    ]
    settings["MIDDLEWARE"] += [
        "corsheaders.middleware.CorsMiddleware",
    ]

    settings["CORS_ALLOW_CREDENTIALS"] = True
    settings["CORS_ALLOW_HEADERS"] = [
        "x-challenge-token",
        "x-request-source",
        *default_headers,
    ]
    settings["CORS_ORIGIN_WHITELIST"] = [FRONTEND_PUBLIC_URL]

    settings["X_CHALLENGE_ENABLED"] = env.bool("X_CHALLENGE_ENABLED", False)
    settings["X_CHALLENGE_TOKEN_MAX_AGE"] = env.int("X_CHALLENGE_TOKEN_MAX_AGE", 60)
