from pathlib import Path
from backbone.settings.base import *  # pyright: ignore

# Update BASE_DIR
BASE_DIR = Path(__file__).resolve().parent.parent

# Reset required settings
ROOT_URLCONF = "demo.urls"

WSGI_APPLICATION = "demo.wsgi.application"
ASGI_APPLICATION = "demo.asgi.application"

MEDIA_ROOT = BASE_DIR / ".." / "media" / "uploads"
STATIC_ROOT = BASE_DIR / ".." / "media" / "static"
