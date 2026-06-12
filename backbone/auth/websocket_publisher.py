from backbone.channels.publishers import publisher as Publisher
from backbone.channels.utils import Group

publisher = Publisher("auth")


@publisher
def user_update(user: dict):
    return Group.user(user["id"]), user


@publisher
def user_logout(user_id: int):
    return Group.user(user_id), None


@publisher
def usersession_end(user_id: int, session_id: int):
    return Group.user(user_id), {"id": session_id}


@publisher
def usersession_init(user_id: int, session_id: int):
    return Group.user(user_id), {"id": session_id}
