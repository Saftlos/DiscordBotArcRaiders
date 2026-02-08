import discord
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands
from utils.api_client import ArcRaidersAPI

class MapView(View):
    def __init__(self, map_data):
        super().__init__(timeout=None) # Persistent view logic not needed for ephemeral interactions usually, but good practice
        self.map_data = map_data

    def get_list(self, filter_type: str) -> str:
        lines = []
        for item in self.map_data:
            sub = item.get("subcategory", "unknown")
            cat = item.get("category", "unknown")
            
            lat = item.get("lat")
            lng = item.get("lng")
            coords = f"({int(lat)}, {int(lng)})" if lat and lng else ""
            
            if filter_type == "spawns" and sub == "player_spawn":
                lines.append(f"📍 {coords}")
            elif filter_type == "extracts" and (sub == "extraction_point" or cat == "extraction"):
                lines.append(f"🚁 {coords}")
            elif filter_type == "pois" and (cat in ["locations", "arc"] and sub not in ["player_spawn"]):
                 name = item.get("instanceName") or sub.replace("_", " ").title()
                 lines.append(f"• **{name}** {coords}")
        
        if not lines:
            return "❌ Keine Daten gefunden."
            
        # Chunking if too long
        full_text = "\n".join(lines)
        if len(full_text) > 1900:
            return full_text[:1900] + "\n... (Liste gekürzt)"
        return full_text

    @discord.ui.button(label="Zeige Spawns", style=discord.ButtonStyle.green, emoji="📍")
    async def spawns_button(self, interaction: discord.Interaction, button: Button):
        content = "**Startpunkte (Spawns):**\n" + self.get_list("spawns")
        await interaction.response.send_message(content, ephemeral=True)

    @discord.ui.button(label="Zeige Extracts", style=discord.ButtonStyle.blurple, emoji="🚁")
    async def extracts_button(self, interaction: discord.Interaction, button: Button):
        content = "**Extraktionspunkte:**\n" + self.get_list("extracts")
        await interaction.response.send_message(content, ephemeral=True)

    @discord.ui.button(label="Zeige POIs", style=discord.ButtonStyle.grey, emoji="🏙️")
    async def pois_button(self, interaction: discord.Interaction, button: Button):
        content = "**Wichtige Orte (POIs):**\n" + self.get_list("pois")
        await interaction.response.send_message(content, ephemeral=True)

class Maps(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="map", description="Informationen zu einer Map")
    @app_commands.describe(map_name="Name der Map (dam, spaceport, buried-city, blue-gate, stella-montis)")
    @app_commands.choices(map_name=[
        app_commands.Choice(name="Dam", value="dam"),
        app_commands.Choice(name="Spaceport", value="spaceport"),
        app_commands.Choice(name="Buried City", value="buried-city"),
        app_commands.Choice(name="Blue Gate", value="blue-gate"),
        app_commands.Choice(name="Stella Montis", value="stella-montis")
    ])
    async def map_info(self, interaction: discord.Interaction, map_name: str):
        """Zeige Details zu einer spezifischen Map."""
        await interaction.response.defer()
        
        api: ArcRaidersAPI = self.bot.api
        data = await api.get_map_data(map_id=map_name)
        
        map_data = data.get("allData", [])
        
        if not map_data:
            await interaction.followup.send(f"Keine Daten für Map `{map_name}` gefunden.", ephemeral=True)
            return

        embed = discord.Embed(title=f"🗺️ Karte: {map_name.replace('-', ' ').title()}", color=discord.Color.green())
        
        # Categorize for Summary
        spawns_count = 0
        extractions_count = 0
        pois = []
        
        for item in map_data:
            sub = item.get("subcategory", "unknown")
            cat = item.get("category", "unknown")
            
            if sub == "player_spawn":
                spawns_count += 1
            elif sub == "extraction_point" or cat == "extraction":
                 extractions_count += 1
            elif cat in ["locations", "arc"] and sub not in ["player_spawn"]:
                name = item.get("instanceName") or sub.replace("_", " ").title()
                if name not in pois: 
                    pois.append(name)

        embed.add_field(name="🚀 Startpunkte", value=f"📍 {spawns_count} verfügbar", inline=True)
        embed.add_field(name="🚁 Extraktionspunkte", value=f"📍 {extractions_count} verfügbar", inline=True)
        
        if pois:
            embed.add_field(name="🏙️ POIs (Auszug)", value=", ".join(pois[:5]) + "...", inline=False)

        if spawns_count == 0 and not pois:
            embed.description = "Keine interessanten Punkte gefunden."
            
        view = MapView(map_data)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Maps(bot))
