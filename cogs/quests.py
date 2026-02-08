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
        
        # Parse Quest Data
        q_name = quest.get("name", "Unbekannt")
        q_trader = quest.get("trader_name", "Unbekannt")
        q_img = quest.get("image")
        
        # Description / Objectives
        # Some quests have 'objectives' list, some might have 'description' (though debug showed objectives)
        objectives = quest.get("objectives", [])
        desc_text = "\n".join([f"• {obj}" for obj in objectives]) if objectives else "Keine Beschreibung verfügbar."
        
        embed = discord.Embed(title=f"📜 Quest: {q_name}", description=desc_text, color=discord.Color.gold())
        
        if q_img:
            embed.set_thumbnail(url=q_img)
            
        embed.add_field(name="👤 Auftraggeber", value=q_trader, inline=True)
        
        # Requirements
        # Note: API usually returns 'required_items' similar to rewards
        reqs = quest.get("required_items", [])
        if reqs:
            req_text = ""
            for r in reqs:
                # Structure assumption based on rewards: { "item": { "name": "..." }, "quantity": "..." }
                item_obj = r.get("item", {})
                item_name = item_obj.get("name") or r.get("item_id", "Item")
                count = r.get("quantity", "1")
                req_text += f"• {count}x **{item_name}**\n"
            
            if req_text:
                embed.add_field(name="📋 Benötigt", value=req_text, inline=False)
            
        # Rewards
        rewards = quest.get("rewards", [])
        if rewards:
            rew_text = ""
            for r in rewards:
                item_obj = r.get("item", {})
                name = item_obj.get("name") or r.get("item_id", "Unknown")
                count = r.get("quantity", "1")
                rarity = item_obj.get("rarity", "")
                
                # Format: 5x Metal Parts (Common)
                entry = f"• {count}x {name}"
                if rarity:
                    entry += f" *({rarity})*"
                rew_text += entry + "\n"
                
            if rew_text:
                embed.add_field(name="🎁 Belohnung", value=rew_text, inline=False)

        # Guide Links
        links = quest.get("guide_links", [])
        if links:
            link_text = " | ".join([f"[{l.get('label', 'Guide')}]({l.get('url')})" for l in links])
            embed.add_field(name="🔗 Guides", value=link_text, inline=False)

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
