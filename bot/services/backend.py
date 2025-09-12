import httpx
from typing import Optional

class BackendClient:
    """Простой async-клиент для нашего Django-бэка с X-Bot-Key."""
    def __init__(self, base_url: str, bot_key: str, timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.bot_key = bot_key
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _cli(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout, headers={"X-Bot-Key": self.bot_key})
        return self._client

    async def ping(self) -> bool:
        try:
            cli = await self._cli()
            r = await cli.get(f"{self.base_url}/api/nutrition/ping/")
            return r.status_code == 200
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
