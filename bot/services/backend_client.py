import json, os
from typing import List, Optional
import httpx
from .models import MenuItem

class BackendClient:
    def __init__(self, base: str, user: str | None, password: str | None):
        self.base = base.rstrip("/")
        self.user = user
        self.password = password
        self._access: Optional[str] = None
        self._refresh: Optional[str] = None

    async def _auth(self, client: httpx.AsyncClient):
        if not (self.user and self.password): 
            return
        if self._access:
            return
        resp = await client.post(f"{self.base}/users/auth/token/", json={"username": self.user, "password": self.password})
        resp.raise_for_status()
        data = resp.json()
        self._access = data["access"]; self._refresh = data["refresh"]

    async def fetch_items(self) -> List[MenuItem]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await self._auth(client)
            headers = {"Authorization": f"Bearer {self._access}"} if self._access else {}
            resp = await client.get(f"{self.base}/catalog/items/", headers=headers)
            if resp.status_code == 200:
                arr = resp.json()
                items: List[MenuItem] = []
                for r in arr:
                    items.append(MenuItem(
                        id=r["id"],
                        title=r["title"],
                        price=r.get("price",0),
                        tags=r.get("tags",[]),
                        allergens=r.get("allergens",[]),
                        exclusions=r.get("exclusions",[]),
                        nutrients={
                            "calories": r["nutrients"]["calories"],
                            "protein": r["nutrients"]["protein"],
                            "fat": r["nutrients"]["fat"],
                            "carbs": r["nutrients"]["carbs"],
                            "fiber": r["nutrients"].get("fiber",0),
                            "sodium": r["nutrients"].get("sodium",0),
                        }
                    ))
                return items
            raise RuntimeError(f"backend catalog/items status={resp.status_code}")

    @staticmethod
    def load_local(path: str) -> List[MenuItem]:
        p = os.path.join(os.path.dirname(__file__), "..", path)
        p = os.path.normpath(p)
        with open(p, "r", encoding="utf-8") as f:
            arr = json.load(f)
        items: List[MenuItem] = []
        for r in arr:
            items.append(MenuItem(
                id=int(r.get("id") or r["source_id"]),
                title=r["title"], price=r.get("price",0),
                tags=r.get("tags",[]), allergens=r.get("allergens",[]), exclusions=r.get("exclusions",[]),
                nutrients=r["nutrients"]
            ))
        return items
