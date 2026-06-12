import redis.asyncio as redis
from django.conf import settings

"""
- we store user connections in redis (see def mark_user_active)
- on ws connect
    - we mark the user active (per connection)
    - we send to this user the entire presence snapshot (all user ids from redis)
    - we broadcast this user has joined

- on ws ping
    - we mark the user active (hence keeping it alive in redis)

- on ws disconnect
    - we mark the user connection inactive
    - we check for other connections this user might have
    - if none remaining
        - we broadcast this user has left
        - we update user.profile.last_seen
"""
PRESENCE_TTL = 30  # in seconds - should be slightly higer than ws heartbeat interval
PRESENCE_KEY = "ws:presence"

r = redis.from_url(settings.REDIS_URL_CACHE, decode_responses=True)


async def mark_user_active(user_id: int, conn_id: str):
    await r.setex(f"{PRESENCE_KEY}:{user_id}:{conn_id}", PRESENCE_TTL, "1")


async def unmark_user_active(user_id: int, conn_id: str):
    await r.delete(f"{PRESENCE_KEY}:{user_id}:{conn_id}")


async def get_all_active_user_ids():
    # TODO look into SCAN or Redis sets
    # Redis KEYS is O(N)
    keys = await r.keys(f"{PRESENCE_KEY}:*")
    user_ids = {int(k.split(":")[-2]) for k in keys}
    return list(user_ids)


async def get_user_connection_count(user_id):
    remaining = await r.keys(f"{PRESENCE_KEY}:{user_id}:*")
    return remaining
