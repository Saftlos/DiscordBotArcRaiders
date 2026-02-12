import discord
from discord import app_commands
from discord.ext import commands
from utils.api_client import ArcRaidersAPI

# Rarity Farben
RARITY_COLORS = {
    "Common": discord.Color.light_grey(),
    "Uncommon": discord.Color.green(),
    "Rare": discord.Color.blue(),
    "Epic": discord.Color.purple(),
    "Legendary": discord.Color.gold(),
}

RARITY_EMOJI = {
    "Common": "⬜",
    "Uncommon": "🟩",
    "Rare": "🟦",
    "Epic": "🟪",
    "Legendary": "🟨",
}

# Trader Beschreibungen
TRADER_INFO = {
    "Apollo": {"emoji": "🔧", "desc": "Taktische Ausrüstung & Granaten"},
    "Celeste": {"emoji": "📦", "desc": "Materialien & Crafting-Ressourcen"},
    "Lance": {"emoji": "🛡️", "desc": "Medizin, Schilde & Augmente"},
    "Shani": {"emoji": "🔑", "desc": "Gadgets & Schlüssel"},
    "TianWen": {"emoji": "🔫", "desc": "Waffen, Munition & Modifikationen"},
}


class Traders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trader", description="Zeigt das Inventar eines Händlers an")
    @app_commands.describe(name="Wähle einen Händler")
    @app_commands.choices(name=[
        app_commands.Choice(name="🔧 Apollo – Taktische Ausrüstung", value="Apollo"),
        app_commands.Choice(name="📦 Celeste – Materialien", value="Celeste"),
        app_commands.Choice(name="🛡️ Lance – Medizin & Schilde", value="Lance"),
        app_commands.Choice(name="🔑 Shani – Gadgets & Schlüssel", value="Shani"),
        app_commands.Choice(name="🔫 TianWen – Waffen & Mods", value="TianWen"),
    ])
    async def trader(self, interaction: discord.Interaction, name: str):
        """Zeigt das komplette Inventar eines Händlers."""
        await interaction.response.defer(ephemeral=True)
        
        api: ArcRaidersAPI = self.bot.api
        data = await api.get_traders()
        
        if not data or not data.get("success"):
            await interaction.followup.send("❌ Händler-Daten konnten nicht geladen werden.", ephemeral=True)
            return
        
        traders = data.get("data", {})
        items = traders.get(name)
        
        if not items:
            await interaction.followup.send(f"❌ Keine Items für Händler `{name}` gefunden.", ephemeral=True)
            return
        
        # Nach Rarity gruppieren
        by_rarity = {}
        for item in items:
            rarity = item.get("rarity", "Common")
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(item)
        
        # Rarity-Reihenfolge
        rarity_order = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]
        
        info = TRADER_INFO.get(name, {"emoji": "🏪", "desc": "Händler"})
        
        embed = discord.Embed(
            title=f"{info['emoji']} Händler: {name}",
            description=f"*{info['desc']}*\n**{len(items)} Items** im Sortiment",
            color=RARITY_COLORS.get("Rare", discord.Color.blue())
        )
        
        for rarity in rarity_order:
            group = by_rarity.get(rarity, [])
            if not group:
                continue
            
            emoji = RARITY_EMOJI.get(rarity, "⬜")
            
            # Items als kompakte Liste
            lines = []
            for item in group:
                price = item.get("trader_price", 0)
                price_str = f"{price:,}".replace(",", ".")
                item_type = item.get("item_type", "")
                lines.append(f"{emoji} **{item['name']}** — {price_str} ₩ *({item_type})*")
            
            # Embed-Feld (max 1024 Zeichen)
            value = "\n".join(lines)
            if len(value) > 1024:
                value = value[:1020] + "\n..."
            
            embed.add_field(
                name=f"─── {rarity} ({len(group)}) ───",
                value=value,
                inline=False
            )
        
        embed.set_footer(text="Arc Raiders | Metaforge API")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Traders(bot))
