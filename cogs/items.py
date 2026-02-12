import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.api_client import ArcRaidersAPI
import asyncio

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.all_items = []
        self.refresh_cache.start()

    def cog_unload(self):
        self.refresh_cache.cancel()

    @tasks.loop(hours=6)
    async def refresh_cache(self):
        """Fetches all items from API to cache locally."""
        print("🔄 Caching Items...")
        api: ArcRaidersAPI = self.bot.api
        page = 1
        new_cache = []
        
        while True:
            try:
                data = await api.get_items(page=page, limit=100) # Max limit to speed up
                items = data.get("data", [])
                
                if not items:
                    break
                    
                new_cache.extend(items)
                
                # Safety break if too many pages (avoid infinite loop)
                if len(items) < 100: 
                    break
                    
                page += 1
                await asyncio.sleep(0.5) # Be nice to API
            except Exception as e:
                print(f"❌ Fehler beim Cachen der Items Seite {page}: {e}")
                break
        
        if new_cache:
            self.all_items = new_cache
            print(f"✅ {len(self.all_items)} Items gecacht.")
        else:
            print("⚠️ Item-Cache Update fehlgeschlagen oder leer.")

    @refresh_cache.before_loop
    async def before_refresh_cache(self):
        await self.bot.wait_until_ready()

    def get_rarity_color(self, rarity: str) -> discord.Color:
        rarity = rarity.lower()
        if "common" in rarity:
            return discord.Color.light_grey()
        elif "uncommon" in rarity:
            return discord.Color.green()
        elif "rare" in rarity:
            return discord.Color.blue()
        elif "epic" in rarity:
            return discord.Color.purple()
        elif "legendary" in rarity:
            return discord.Color.gold()
        return discord.Color.default()

    @app_commands.command(name="item", description="Suche nach einem Item in Arc Raiders")
    @app_commands.describe(name="Der Name des Items")
    async def item_search(self, interaction: discord.Interaction, name: str):
        """Suche nach einem Item und zeige dessen Stats an."""
        await interaction.response.defer(ephemeral=True)
        
        # Search in local cache first
        target_item = None
        for item in self.all_items:
            if item.get("name") == name:
                target_item = item
                break
        
        # Fallback to API if not in cache (fresh item?)
        if not target_item:
            api: ArcRaidersAPI = self.bot.api
            data = await api.get_items(search=name, limit=1)
            items = data.get("data", [])
            if items:
                target_item = items[0]

        if not target_item:
            await interaction.followup.send(f"❌ Keine Items gefunden für: `{name}`", ephemeral=True)
            return

        # Build Embed
        embed = discord.Embed(
            title=target_item.get("name", "Unbekanntes Item"),
            description=target_item.get("description", "Keine Beschreibung verfügbar."),
            color=self.get_rarity_color(target_item.get("rarity", ""))
        )
        
        if "icon" in target_item:
             embed.set_thumbnail(url=target_item["icon"])
        elif "image" in target_item:
             embed.set_thumbnail(url=target_item["image"])

        # Stats Fields
        try:
            if "type" in target_item:
                embed.add_field(name="Typ", value=target_item["type"], inline=True)
            if "rarity" in target_item:
                embed.add_field(name="Seltenheit", value=target_item["rarity"], inline=True)
            if "weight" in target_item:
                embed.add_field(name="Gewicht", value=f"{target_item['weight']} kg", inline=True)
                
            stats = target_item.get("stats", {})
            if stats and isinstance(stats, dict):
                stats_str = ""
                for k, v in stats.items():
                    stats_str += f"**{k.capitalize()}:** {v}\n"
                if stats_str:
                    embed.add_field(name="Werte", value=stats_str, inline=False)
                
            if "crafting_cost" in target_item:
                 embed.add_field(name="Herstellungskosten", value=str(target_item["crafting_cost"]), inline=False)
        except Exception as e:
            print(f"Fehler beim Erstellen der Embed-Felder: {e}")
            embed.set_footer(text="Fehler beim Laden einiger Details.")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @item_search.autocomplete('name')
    async def item_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current = current.lower()
        # Filter local list
        matches = [
            item for item in self.all_items 
            if current in item.get("name", "").lower()
        ]
        
        # Limit to 25 choices (Discord limit)
        return [
            app_commands.Choice(name=item["name"], value=item["name"])
            for item in matches[:25]
        ]

async def setup(bot):
    await bot.add_cog(Items(bot))
