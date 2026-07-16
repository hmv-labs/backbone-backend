from importlib import import_module

from backbone.bootstrap import env

from .auth import AUTH_PASSWORD_VALIDATORS  # noqa
from .caches import CACHES, REDIS_URL_BROKER, REDIS_URL_CACHE  # noqa
from .common import BACKEND_PUBLIC_URL  # noqa
from .common import (
    BACKEND_PUBLIC_DOMAIN,
    BASE_DIR,
    FRONTEND_PUBLIC_DOMAIN,
    FRONTEND_PUBLIC_URL,
)
from .email import (  # noqa
    EMAIL_HOST,
    EMAIL_HOST_PASSWORD,
    EMAIL_HOST_USER,
    EMAIL_HOST_USER_NOREPLY,
    EMAIL_PORT,
    EMAIL_SUBJECT_PREFIX,
    EMAIL_USE_TLS,
    SERVER_EMAIL,
)
from .logging import LOGGING  # noqa
from .middleware import MIDDLEWARE  # noqa
from .templates import TEMPLATES  # noqa

ADMINS = env.list("DJANGO_ADMINS")
MANAGERS = env.list("DJANGO_MANAGERS")

ALLOWED_HOSTS = [
    "127.0.0.1",
    BACKEND_PUBLIC_DOMAIN,
    FRONTEND_PUBLIC_DOMAIN,
]
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
    "django_extensions",
]

BACKBONE_APPS = [
    "backbone.auth",
    "backbone.celery",
    "backbone.channels",
    "backbone.cors",
    "backbone.drf",
    "backbone.emails",
    "backbone.internals",
    "backbone.minio",
    "backbone.sentry",
]

for app in BACKBONE_APPS:
    app_settings = import_module(f"{app}.settings")
    app_settings.configure(globals())
