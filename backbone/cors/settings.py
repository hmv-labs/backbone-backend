from backbone.settings.common import FRONTEND_PUBLIC_URL


def configure(settings):
    settings["INSTALLED_APPS"] += [
        "corsheaders",
    ]
    settings["MIDDLEWARE"] += [
        "corsheaders.middleware.CorsMiddleware",
    ]

    settings["CORS_ALLOW_CREDENTIALS"] = True
    settings["CORS_ORIGIN_WHITELIST"] = [FRONTEND_PUBLIC_URL]
