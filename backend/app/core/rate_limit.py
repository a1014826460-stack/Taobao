from time import time

from fastapi import HTTPException, status
from redis import Redis

from backend.app.core.config import get_settings


def enforce_rate_limit(token_key: str, formal: bool, client: Redis | None = None) -> None:
    settings = get_settings()
    limit = settings.formal_rate_limit if formal else settings.trial_rate_limit
    now = int(time())
    key = f"crawler-api:rate:{token_key}:{now // 60}"
    redis = client or Redis.from_url(settings.redis_url, decode_responses=True)
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, 65)
    if count > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="RATE_LIMITED")
