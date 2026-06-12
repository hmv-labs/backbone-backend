from . import utils
import logging
from functools import wraps
from typing import Callable, ParamSpec, TypeVar, Tuple, Any, Dict

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")
Payload = Dict[str, Any] | None


class publisher:
    """Decorator to be used for pushing websocket events.

    Decorated functions must return a two item tuple:

        group_name, payload_to_be_sent

    The websocket event name is derived from the prefix provided during init
    and the name of the decorated function.

    ---

    Eg:

    from backbone.channels.publishers import publisher as Publisher
    from backbone.channels.utils import Group

    publisher = Publisher('prefix')

    @publisher
    def test_name(*a, **kw):
        # do stuff with a and kw to build the payload
        payload = {"some": "stuff", "in": "here"}
        return Group.ALL, payload

    ---

    The above will push a websocket event like:

    {"name": "prefix.test_name", "data": {"some": "stuff", "in": "here"}}
    """

    def __init__(self, prefix: str):
        self.prefix = prefix

    def __call__(
        self,
        func: Callable[P, Tuple[str, Payload]],
    ) -> Callable[P, Any]:

        event_name = f"{self.prefix}.{func.__name__}"

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            group_name, payload = func(*args, **kwargs)
            logger.debug(f"[publisher] {group_name}.{event_name} {payload}")
            return utils.push_sync(group_name, event_name, payload)

        return wrapper


class async_publisher:
    def __init__(self, prefix: str):
        self.prefix = prefix

    def __call__(self, func):
        event_name = f"{self.prefix}.{func.__name__}"

        @wraps(func)
        async def wrapper(*args, **kwargs):
            group_name, payload = func(*args, **kwargs)
            logger.debug(f"[async_publisher] {group_name}.{event_name} {payload}")
            return await utils.push(group_name, event_name, payload)

        return wrapper


@async_publisher("presence")
def diff(user_id: int, connected: bool):
    return utils.Group.ALL, {"user_id": user_id, "connected": connected}


@async_publisher("presence")
def snapshot(user_id: int, active_user_ids: list[int]):
    return utils.Group.user(user_id), {"active_user_ids": active_user_ids}
