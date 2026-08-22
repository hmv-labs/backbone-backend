from backbone.channels.publishers import publisher as Publisher
from backbone.channels.utils import Group

publisher = Publisher("chat")


@publisher
def conversation_create(user_id: int, conversation: dict):
    return Group.user(user_id), conversation


@publisher
def conversation_update(user_id: int, conversation: dict):
    return Group.user(user_id), conversation


@publisher
def conversation_delete(user_id: int, public_id: str):
    return Group.user(user_id), {"public_id": public_id}


@publisher
def message_create(user_id: int, message: dict):
    return Group.user(user_id), message


@publisher
def message_update(user_id: int, message: dict):
    return Group.user(user_id), message


@publisher
def message_reaction(
    user_id: int,
    *,
    actor_id: int,
    actor_reacted: bool,
    count: int,
    cpid: str,
    emoji: str,
    mpid: str,
):
    """
    actor_id: request user id - user that performed the reaction
    actor_reacted: whether that actor has created/removed the reaction after the operation
    count: authoritative total count for that emoji after the operation
    emoji: affected emoji
    """
    return Group.user(user_id), {
        "actor_id": actor_id,
        "actor_reacted": actor_reacted,
        "count": count,
        "cpid": cpid,
        "emoji": emoji,
        "mpid": mpid,
    }
