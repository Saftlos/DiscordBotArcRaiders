import asyncio
import os
import aiohttp
import json
from dotenv import load_dotenv

load_dotenv()

async def test_quests():
    base_url = os.getenv("API_BASE_URL", "https://metaforge.app/api/arc-raiders")
    print(f"Using Base URL: {base_url}")
    
    async with aiohttp.ClientSession() as session:
        url = f"{base_url}/quests"
        async with session.get(url) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                if "data" in data:
                    quests = data["data"]
                    print(f"Found {len(quests)} quests.")
                    if quests:
                        q = quests[0]
                        with open("quest_debug.json", "w") as f:
                            json.dump(q, f, indent=2)
                        print("Wrote first quest to quest_debug.json")
                else:
                    print("No 'data' key in response.")
            else:
                print(await response.text())

if __name__ == "__main__":
    asyncio.run(test_quests())
