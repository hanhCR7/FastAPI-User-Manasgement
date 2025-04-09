from fastapi import Request, HTTPException, status, Depends
from redis import Redis

RATE_LIMITER = 5
RATE_LIMIT_TTL = 60

def rate_limiters(redis_client: Redis, key_prefix: str = "rate_limit"):
    async def limiter(request: Request):
        #Ưu tiên user_id nếu có, fallback về IP
        user = request.scope.get("user")
        identity = user.get("user") if user else request.client.host
        key = f"rate_limit:{key_prefix}:{identity}"
        count = redis_client.get(key)
        try:
            if count and int(count) >= RATE_LIMITER:
                raise HTTPException(
                    status_code=429, 
                    detail="Bạn gửi yêu cầu quá nhanh. Vui lòng thử lại sau ít phút.",
                    headers={"Retry-After": str(RATE_LIMIT_TTL)}
                )
            pipe = redis_client.pipeline()
            pipe.incr(key, 1)
            if not count:
                pipe.expire(key, RATE_LIMIT_TTL)
            pipe.execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi rate limit: {str(e)}")
    return limiter
