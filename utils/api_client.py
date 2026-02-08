import aiohttp
import os
from typing import Optional, Dict, Any, List

class ArcRaidersAPI:
    def __init__(self):
        self.base_url = os.getenv("API_BASE_URL", "https://metaforge.app/api/arc-raiders")
        self.session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        session = await self.get_session()
        url = f"{self.base_url}{endpoint}"
        async with session.get(url, params=params) as response:
            if response.status == 200:
                try:
                    return await response.json()
                except Exception:
                    # Fallback for non-JSON responses or empty responses if checking status
                    return {"error": "Invalid JSON response"}
            else:
                return {"error": f"HTTP Error {response.status}", "status": response.status}

    async def get_items(self, search: str = None, page: int = 1, limit: int = 25) -> Dict[str, Any]:
        params = {"page": page, "limit": limit}
        if search:
            params["search"] = search
        # The documentation says /items is under /api/arc-raiders/items
        # But base_url already includes /api/arc-raiders based on my .env plan.
        # Let's adjust. If base_url is https://metaforge.app/api/arc-raiders
        # Then endpoint should be just "/items"
        
        # Checking logic:
        # Docs say: GET /api/arc-raiders/items
        # user said base url: https://metaforge.app/api/arc-raiders
        # So request is base_url + "/items" -> https://metaforge.app/api/arc-raiders/items. Correct.
        return await self._get("/items", params)

    async def get_arcs(self, search: str = None, page: int = 1, includeLoot: bool = False) -> Dict[str, Any]:
        params = {"page": page}
        if search:
            params["search"] = search
        if includeLoot:
            params["includeLoot"] = "true"
        return await self._get("/arcs", params)

    async def get_quests(self, search: str = None, page: int = 1) -> Dict[str, Any]:
        params = {"page": page}
        if search:
            params["search"] = search
        return await self._get("/quests", params)

    async def get_events(self) -> Dict[str, Any]:
        # Docs mention /events-schedule and /event-timers (deprecated)
        return await self._get("/events-schedule")

    async def get_map_data(self, map_id: str) -> Dict[str, Any]:
        # This one is tricky. Docs say: /api/game-map-data
        # This is outside the /api/arc-raiders scope if base_url includes arc-raiders.
        # I need to handle this special case.
        
        # New base for map: https://metaforge.app/api/game-map-data
        # I will override the URL construction here manually.
        pass
        
        # Actually, let's look at the params: tableID=arc_map_data, mapID=...
        # Url: https://metaforge.app/api/game-map-data
        
        session = await self.get_session()
        url = "https://metaforge.app/api/game-map-data"
        params = {
            "tableID": "arc_map_data",
            "mapID": map_id
        }
        async with session.get(url, params=params) as response:
             if response.status == 200:
                try:
                    return await response.json()
                except:
                     return {"error": "Invalid JSON"}
             return {"error": f"HTTP {response.status}"}

