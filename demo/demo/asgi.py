from backbone.bootstrap import get_asgi_application, read_env
from pathlib import Path

read_env(Path(__file__).resolve().parent.parent / ".env")
application = get_asgi_application()
