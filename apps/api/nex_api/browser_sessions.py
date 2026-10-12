"""Opaque, bounded, encrypted Redis sessions. No in-process production fallback."""
import hashlib
import json
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, cast

from cryptography.fernet import Fernet
from redis.asyncio import Redis

SESSION_COOKIE = "__Secure-nex_session"
FLOW_COOKIE = "__Secure-nex_oidc"
COOKIE_PATH = "/api"


@dataclass
class Record:
    data: dict[str, Any]
    sealed: bytes


class BrowserSessions:
    def __init__(self, redis: Redis, key: str) -> None:
        self.redis = redis
        self.cipher = Fernet(key.encode())

    def key(self, kind: str, opaque: str) -> str:
        if not 20 <= len(opaque) <= 128:
            raise ValueError("Invalid opaque identifier")
        return "nex:m1:" + kind + ":" + hashlib.sha256(opaque.encode()).hexdigest()

    def seal(self, data: dict[str, Any]) -> bytes:
        return self.cipher.encrypt(json.dumps(data, separators=(",", ":")).encode())

    async def create(self, kind: str, opaque: str, data: dict[str, Any], ttl: int) -> None:
        if not await self.redis.set(self.key(kind, opaque), self.seal(data), ex=ttl, nx=True):
            raise RuntimeError("Session identifier collision")

    async def load(self, kind: str, opaque: str) -> Record | None:
        if not 20 <= len(opaque) <= 128:
            return None
        sealed = await self.redis.get(self.key(kind, opaque))
        if not sealed:
            return None
        raw = sealed.encode() if isinstance(sealed, str) else bytes(sealed)
        return Record(cast(dict[str, Any], json.loads(self.cipher.decrypt(raw))), raw)

    async def take(self, kind: str, opaque: str, expected: Record | None = None) -> Record | None:
        if not 20 <= len(opaque) <= 128:
            return None
        if expected is not None:
            result = await cast(Awaitable[Any], self.redis.eval(
                "if redis.call('GET',KEYS[1]) == ARGV[1] then "
                "return redis.call('GETDEL',KEYS[1]) else return false end",
                1, self.key(kind, opaque), expected.sealed.decode(),
            ))
        else:
            result = await self.redis.getdel(self.key(kind, opaque))
        if not result:
            return None
        raw = result.encode() if isinstance(result, str) else bytes(result)
        return Record(cast(dict[str, Any], json.loads(self.cipher.decrypt(raw))), raw)

    async def replace(self, opaque: str, old: Record, data: dict[str, Any], ttl: int) -> bool:
        # A concurrent logout wins: refresh cannot re-create a deleted session.
        return bool(await cast(Awaitable[Any], self.redis.eval(
            "if redis.call('GET',KEYS[1]) == ARGV[1] then "
            "redis.call('SET',KEYS[1],ARGV[2],'EX',ARGV[3]); return 1 else return 0 end",
            1, self.key("session", opaque), old.sealed.decode(),
            self.seal(data).decode(), str(max(1, ttl)),
        )))