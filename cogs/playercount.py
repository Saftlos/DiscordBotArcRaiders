import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import os


class PlayerCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app_id = os.getenv("ARC_RAIDERS_APP_ID")

    @app_commands.command(name="spielerzahl", description="Zeigt die aktuelle Spielerzahl von Arc Raiders auf Steam")
    async def spielerzahl(self, interaction: discord.Interaction):
        """Zeigt die aktuelle Anzahl der Spieler auf Steam."""
        await interaction.response.defer(ephemeral=True)

        if not self.app_id:
            await interaction.followup.send("❌ App-ID nicht konfiguriert.", ephemeral=True)
            return

        try:
            url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={self.app_id}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        await interaction.followup.send("❌ Steam API nicht erreichbar.", ephemeral=True)
                        return

                    data = await response.json()
                    result = data.get("response", {})
                    
                    if result.get("result") != 1:
                        await interaction.followup.send("❌ Keine Daten verfügbar.", ephemeral=True)
                        return

                    player_count = result.get("player_count", 0)

            # Spielerzahl formatieren
            count_str = f"{player_count:,}".replace(",", ".")

            # Dynamische Farbe basierend auf Spielerzahl
            if player_count >= 10000:
                color = discord.Color.green()
                status = "🟢 Sehr aktiv"
            elif player_count >= 5000:
                color = discord.Color.gold()
                status = "🟡 Aktiv"
            elif player_count >= 1000:
                color = discord.Color.orange()
                status = "🟠 Moderat"
            else:
                color = discord.Color.red()
                status = "🔴 Ruhig"

            embed = discord.Embed(
                title="🎮 Arc Raiders — Spielerzahl",
                color=color
            )

            embed.add_field(
                name="👥 Aktuell Online",
                value=f"**{count_str}** Spieler",
                inline=True
            )
            embed.add_field(
                name="📊 Status",
                value=status,
                inline=True
            )

            embed.set_footer(text="Quelle: Steam API | Nur Steam-Spieler")

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PlayerCount(bot))
