from .base import *

INSTALLED_APPS = ["daphne"] + INSTALLED_APPS

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(  # pyright: ignore
    "rest_framework.renderers.BrowsableAPIRenderer"
)

DJDT = False
DJDT = True

if DJDT:
    INSTALLED_APPS += [
        "debug_toolbar",
    ]

    MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ] + MIDDLEWARE

    DEBUG_TOOLBAR_CONFIG = {
        # "SHOW_TOOLBAR_CALLBACK": True,
        "SHOW_COLLAPSED": True,
    }

    INTERNAL_IPS = ["127.0.0.1"]
