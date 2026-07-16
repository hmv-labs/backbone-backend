from pathlib import Path

import environ

env = environ.Env()

_loaded = None


def read_env(p: Path | None = None):
    global _loaded

    if _loaded:
        return

    path = p or Path(__file__).resolve().parent.parent / ".env"

    environ.Env.read_env(path)

    _loaded = path
    print(f"[env] loaded from {_loaded}")


def get_asgi_application():
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.security.websocket import AllowedHostsOriginValidator
    from django.core.asgi import get_asgi_application as _get_asgi_application

    def get_websocket_app():
        import backbone.channels.routing

        return AllowedHostsOriginValidator(
            AuthMiddlewareStack(
                URLRouter(backbone.channels.routing.websocket_urlpatterns)
            )
        )

    return ProtocolTypeRouter(
        {
            "http": _get_asgi_application(),
            "websocket": get_websocket_app(),
        }
    )
