from backbone.bootstrap import env
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

FRONTEND_HOST = env.str("FRONTEND_HOST", default="127.0.0.1")
FRONTEND_PORT = env.str("FRONTEND_PORT", default="3000")
FRONTEND_PUBLIC_SCHEME = env.str("FRONTEND_PUBLIC_SCHEME", default="http")
FRONTEND_PUBLIC_DOMAIN = env.str("FRONTEND_PUBLIC_DOMAIN", default="127.0.0.1:3000")
FRONTEND_PUBLIC_URL = f"{FRONTEND_PUBLIC_SCHEME}://{FRONTEND_PUBLIC_DOMAIN}"  # noqa

BACKEND_HOST = env.str("BACKEND_HOST", default="127.0.0.1")
BACKEND_PORT = env.str("BACKEND_PORT", default="8000")
BACKEND_PUBLIC_SCHEME = env.str("BACKEND_PUBLIC_SCHEME", default="http")
BACKEND_PUBLIC_DOMAIN = env.str("BACKEND_PUBLIC_DOMAIN", default="127.0.0.1:8000")
BACKEND_PUBLIC_URL = f"{BACKEND_PUBLIC_SCHEME}://{BACKEND_PUBLIC_DOMAIN}"  # noqa
