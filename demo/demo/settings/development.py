from .base import *

DEBUG = True

INSTALLED_APPS = ["daphne"] + INSTALLED_APPS

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"].append(  # pyright: ignore
    "rest_framework.renderers.BrowsableAPIRenderer"
)

# DEBUG TOOLBAR
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    "SHOW_COLLAPSED": True,
}
