import discord
from discord import app_commands
from discord.ext import commands
from utils.api_client import ArcRaidersAPI

class Quests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="quest", description="Suche nach einer Quest (Details, Requirements)")
    @app_commands.describe(name="Name der Quest")
    async def quest_search(self, interaction: discord.Interaction, name: str):
        """Zeigt Quest-Details an."""
        await interaction.response.defer()
        
        api: ArcRaidersAPI = self.bot.api
        data = await api.get_quests(search=name, page=1)
        quests = data.get("data", [])
        
        if not quests:
            await interaction.followup.send(f"❌ Keine Quest gefunden für: `{name}`", ephemeral=True)
            return

        # Best Match
        quest = quests[0]
        
        embed = discord.Embed(title=f"📜 Quest: {quest.get('name', 'Unbekannt')}", color=discord.Color.gold())
        embed.description = quest.get("description", "Keine Beschreibung.")
        
        # Requirements
        reqs = quest.get("required_items", [])
        if reqs:
            req_text = ""
            for r in reqs:
                # Assuming structure: { "item": { "name": "..." }, "quantity": 5 }
                # Or flat: { "itemName": "...", "count": 5 }
                # Based on typical API:
                item_name = r.get("item", {}).get("name") or r.get("itemName", "Item")
                count = r.get("quantity") or r.get("count", 1)
                req_text += f"• {count}x **{item_name}**\n"
            embed.add_field(name="📋 Benötigt", value=req_text, inline=False)
            
        # Rewards
        rewards = quest.get("rewards", [])
        if rewards:
            rew_text = ""
            for r in rewards:
                type_name = r.get("type", "Item")
                val = r.get("value") or r.get("quantity", 1)
                name = r.get("name", "")
                rew_text += f"• {val}x {name} ({type_name})\n"
            embed.add_field(name="🎁 Belohnung", value=rew_text, inline=False)
            
        if "trader" in quest:
             embed.set_footer(text=f"Trader: {quest['trader']}")

        await interaction.followup.send(embed=embed)

    @quest_search.autocomplete('name')
    async def quest_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        api: ArcRaidersAPI = self.bot.api
        data = await api.get_quests(search=current, page=1)
        quests = data.get("data", [])
        return [
            app_commands.Choice(name=q["name"], value=q["name"])
            for q in quests[:25]
        ]

async def setup(bot):
    await bot.add_cog(Quests(bot))
