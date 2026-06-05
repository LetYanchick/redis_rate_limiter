from functools import lru_cache
from typing import Annotated
from contextlib import asynccontextmanager
from redis.asyncio import Redis
from time import time
import random 
from fastapi import Body, Depends, FastAPI, HTTPException, status, Request

@lru_cache
def get_redis() ->Redis:
    return Redis(host="localhost", port=6379)

@lru_cache
def get_rate_limiter() ->RateLimiter:
    return RateLimiter(get_redis())

class RateLimiter:
    def __init__(self, redis:Redis):
        self._redis = redis

    async def is_limited(self, ip_address: str, endpoint: str, max_reqs: int, window_seconds: int) -> bool:
        key = f"rate_limiter{endpoint}:{ip_address}"
        current_time = time() * 1000
        window_start = current_time - window_seconds * 1000
        current_request = f"{current_time}-{random.randint(0, 100_000)}"
        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.zremrangebyscore(key, 0, window_start)
            await pipe.zcard(key)
            await pipe.zadd(key, {current_request: current_time})
            await pipe.expire(key, window_seconds)
            res = await pipe.execute()
        _, current_count, _, _ = res
        return current_count >= max_reqs

@asynccontextmanager
async def lifespan(app:FastAPI):
    redis = get_redis()
    await redis.ping()
    print("Redis работает")
    yield
    await redis.aclose()
    print("Redis всё")


def rate_limiter_factory(endpoint: str, max_reqs: int, window_seconds: int):
    async def dependency(request: Request, rate_limiter:Annotated[RateLimiter, Depends(get_rate_limiter)]):
        ip_address = request.client.host
        limited = await rate_limiter.is_limited(ip_address, endpoint, max_reqs, window_seconds)
        if limited:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Превышено количество запросов")
    return dependency


rate_limiter_sql=rate_limiter_factory("sql_code", 5, 5)
rate_limiter_python=rate_limiter_factory("python_code", 3, 10)

app = FastAPI(lifespan=lifespan)

@app.post("/sql_code", dependencies=[Depends(rate_limiter_sql)])
async def send_sql_code(code: str = Body(embed=True)):

    return {"Ok": True}

@app.post("/python_code", dependencies=[Depends(rate_limiter_python)])
async def send_python_code(code: str = Body(embed=True)):

    return {"Ok": True}

