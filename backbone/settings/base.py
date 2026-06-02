from backbone.env import env
from importlib import import_module

from .auth import AUTH_PASSWORD_VALIDATORS
from .caches import REDIS_URL_CACHE, REDIS_URL_BROKER, CACHES
from .common import FRONTEND_PUBLIC_DOMAIN, FRONTEND_PUBLIC_URL, BASE_DIR
from .email import (
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_HOST_USER,
    EMAIL_HOST_PASSWORD,
    EMAIL_USE_TLS,
    EMAIL_SUBJECT_PREFIX,
    EMAIL_HOST_USER_NOREPLY,
    SERVER_EMAIL,
)
from .logging import LOGGING
from .middleware import MIDDLEWARE
from .templates import TEMPLATES


ADMINS = env.list("DJANGO_ADMINS")
MANAGERS = env.list("DJANGO_MANAGERS")

ALLOWED_HOSTS = [FRONTEND_PUBLIC_DOMAIN, "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = [FRONTEND_PUBLIC_URL]

DEBUG = env.bool("APP_DEBUG", default=False)

LANGUAGE_CODE = "en-us"

ROOT_URLCONF = "backbone.urls"

SECRET_KEY = env("DJANGO_SECRET_KEY")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

WSGI_APPLICATION = "backbone.wsgi.application"
ASGI_APPLICATION = "backbone.asgi.application"

ADMIN_MEDIA_PREFIX = "/static/admin/"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
MEDIA_ROOT = BASE_DIR / ".." / "media" / "uploads"
MEDIA_URL = "/uploads/"
STATIC_ROOT = BASE_DIR / ".." / "media" / "static"
STATIC_URL = "/static/"

DATABASES = {"default": env.db_url()}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

BACKBONE_APPS = [
    "backbone.auth",
    "backbone.celery",
    "backbone.channels",
    "backbone.cors",
    "backbone.drf",
    "backbone.minio",
    "backbone.sentry",
]

for app in BACKBONE_APPS:
    app_settings = import_module(f"{app}.settings")
    app_settings.configure(globals())
