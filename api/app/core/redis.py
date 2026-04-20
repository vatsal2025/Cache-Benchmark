import redis
from rq import Queue
from app.core.config import settings

_redis_conn: redis.Redis = None


def get_redis() -> redis.Redis:
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = redis.from_url(settings.REDIS_URL, decode_responses=False)
    return _redis_conn


def get_queue(name: str = "default") -> Queue:
    return Queue(name, connection=get_redis())


def get_cache() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
