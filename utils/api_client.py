"""
Thin async client for the community MetaForge API (https://metaforge.app).
Every method returns the parsed JSON, or {"error": ...} on failure, so callers
can always use .get("data") without extra try/except around the HTTP layer.
"""

import os
from typing import Any, Dict, Optional

import aiohttp

DEFAULT_BASE_URL = "https://metaforge.app/api/arc-raiders"
MAP_DATA_URL = "https://metaforge.app/api/game-map-data"
TIMEOUT = aiohttp.ClientTimeout(total=15)


class ArcRaidersAPI:
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", DEFAULT_BASE_URL)
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=TIMEOUT)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _get_url(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        session = await self.get_session()
        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return {"error": f"HTTP Error {response.status}", "status": response.status}
                return await response.json()
        except aiohttp.ContentTypeError:
            return {"error": "Invalid JSON response"}
        except Exception as e:
            return {"error": str(e)}

    async def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        return await self._get_url(f"{self.base_url}{endpoint}", params)

    async def get_items(self, search: str = None, page: int = 1, limit: int = 25) -> Dict[str, Any]:
        params = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        return await self._get("/items", params)

    async def get_arcs(self, search: str = None, page: int = 1, include_loot: bool = False) -> Dict[str, Any]:
        params = {"page": page}
        if search:
            params["search"] = search
        if include_loot:
            params["includeLoot"] = "true"
        return await self._get("/arcs", params)

    async def get_quests(self, search: str = None, page: int = 1) -> Dict[str, Any]:
        params = {"page": page}
        if search:
            params["search"] = search
        return await self._get("/quests", params)

    async def get_events(self) -> Dict[str, Any]:
        return await self._get("/events-schedule")

    async def get_traders(self) -> Dict[str, Any]:
        return await self._get("/traders")

    async def get_map_data(self, map_id: str) -> Dict[str, Any]:
        # Map markers live outside the /arc-raiders base path
        return await self._get_url(MAP_DATA_URL, {"tableID": "arc_map_data", "mapID": map_id})
