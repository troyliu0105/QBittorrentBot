import logging
from typing import Any, Optional

from .emulator import RedisEmulator

try:
    import redis.asyncio as redis
except ImportError:
    redis = None


class RedisWrapper:
    def __init__(self, url: Optional[str] = None):
        self._url = url
        self._client = None
        self._emulator = RedisEmulator()

    async def connect(self):
        if not self._url or not redis:
            logging.warning("Redis disabled. using in-memory storage")
            logging.warning("Redis emulator is intended for development use only, configure redis to avoid data loss")
            self._client = self._emulator
            return

        try:
            client = redis.from_url(str(self._url), decode_responses=True)
            await client.ping()
            self._client = client
            logging.info("Connected to Redis")
        except Exception as e:
            logging.warning(f"Redis unavailable ({e}), using in-memory storage")
            self._client = self._emulator

    # Unified API
    async def get(self, key: str) -> Optional[Any]:
        value = await self._client.get(key)
        # Empty string is the on-disk form of a "cleared" value (set(key, None));
        # surface it as None so both backends behave identically.
        return None if value == "" else value

    async def set(self, key: str, value: Any, ex: int | None = None):
        if value is None:
            # Callers use set(key, None) to clear; delete so get/exists agree.
            await self._client.delete(key)
            return
        # Normalize payloads so both backends store/return identical forms:
        # redis-py rejects bool and stringifies nothing, the emulator does both.
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, (str, bytes)):
            value = str(value)
        await self._client.set(key, value, ex=ex)

    async def delete(self, key: str):
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))
