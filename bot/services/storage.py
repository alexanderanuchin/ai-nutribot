import json
from typing import Optional
from .models import Profile

try:
    from redis import asyncio as aioredis
except Exception:
    aioredis = None

class Storage:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn
        self._mem: dict[int, Profile] = {}
        self._r = None

    async def connect(self):
        if self.dsn and aioredis:
            self._r = aioredis.from_url(self.dsn, encoding="utf-8", decode_responses=True)
        return self

    async def get_profile(self, tg_id: int) -> Optional[Profile]:
        if self._r:
            s = await self._r.get(f"profile:{tg_id}")
            return Profile(**json.loads(s)) if s else None
        return self._mem.get(tg_id)

    async def set_profile(self, tg_id: int, p: Profile):
        if self._r:
            await self._r.set(f"profile:{tg_id}", json.dumps(p.__dict__, ensure_ascii=False))
        else:
            self._mem[tg_id] = p
