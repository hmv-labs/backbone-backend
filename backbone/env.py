from pathlib import Path
import environ

env = environ.Env()

_loaded = None

def read_env(p: Path | None = None):
    global _loaded

    if _loaded:
        print(f"[env] already loaded from {_loaded}")
        return

    path = p or Path(__file__).resolve().parent.parent / ".env"

    environ.Env.read_env(path)

    _loaded = path

    print(f"[env] loaded from {_loaded}")
