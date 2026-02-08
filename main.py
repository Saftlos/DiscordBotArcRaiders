import discord
from discord import app_commands
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from utils.api_client import ArcRaidersAPI
from utils.config import ConfigManager

# Load environment variables
load_dotenv()

# Setup Intents
intents = discord.Intents.default()
intents.message_content = True

class ArcRaidersBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            activity=discord.Game(name="Arc Raiders | /help")
        )
        self.api = ArcRaidersAPI()
        self.config = ConfigManager()

    async def setup_hook(self):
        # Load extensions (cogs)
        initial_extensions = [
            "cogs.items",
            "cogs.general",
            "cogs.maps",
            "cogs.admin",
            "cogs.moderation",
            "cogs.news"
        ]
        
        for ext in initial_extensions:
            try:
                await self.load_extension(ext)
                print(f"Erweiterung geladen: {ext}")
            except Exception as e:
                print(f"Fehler beim Laden der Erweiterung {ext}: {e}")

        # Sync commands with Discord
        print("Synchronisiere Befehle global...")
        await self.tree.sync()
        print("Befehle synchronisiert!")

    async def close(self):
        await self.api.close()
        await super().close()

    async def on_ready(self):
        print(f"Eingeloggt als {self.user} (ID: {self.user.id})")
        print("------")

bot = ArcRaidersBot()

# Global Error Handler for Interaction (Slash) Commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Cooldown! Versuch es in {error.retry_after:.2f}s nochmal.", ephemeral=True)
    else:
        print(f"❌ COMMAND ERROR: {error}")
        # Check if interaction is potentially expired or already responded to
        try:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Ein Fehler ist aufgetreten: {error}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Ein Fehler ist aufgetreten: {error}", ephemeral=True)
        except Exception as e:
            print(f"Konnte Fehlernachricht nicht an Nutzer senden: {e}")

async def main():
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    if not os.getenv("DISCORD_TOKEN"):
        print("Fehler: DISCORD_TOKEN nicht in .env gefunden")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            pass
