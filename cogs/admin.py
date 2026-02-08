import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="refresh_boards", description="Aktualisiert sofort alle Event-Boards (Owner Only)")
    @app_commands.default_permissions(administrator=True)
    async def refresh_boards(self, interaction: discord.Interaction):
        """Erzwingt ein Update der Event-Boards."""
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("⛔ **Zugriff verweigert!**", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        general_cog = self.bot.get_cog("General")
        if general_cog:
            try:
                # Direct update call without loop restart
                await general_cog.update_boards()
                await interaction.followup.send("✅ **Event-Boards werden aktualisiert!**", ephemeral=True)
            except Exception as e:
                 await interaction.followup.send(f"❌ Fehler beim Aktualisieren: {e}", ephemeral=True)
        else:
            await interaction.followup.send("❌ 'General' Modul nicht geladen.", ephemeral=True)



    @app_commands.command(name="sync", description="Synchronisiert Befehle (Owner Only)")
    @app_commands.default_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        """Synchronisiert die Slash-Befehle global."""
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("⛔ **Nur der Server-Owner darf das.**", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"✅ **{len(synced)} Befehle synchronisiert.**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Synchronisation fehlgeschlagen: {e}", ephemeral=True)

    @app_commands.command(name="update", description="Zieht Updates von Git und startet neu (Owner Only)")
    @app_commands.default_permissions(administrator=True)
    async def update_bot(self, interaction: discord.Interaction):
        """Führt git pull aus und startet den Bot neu (via Systemd)."""
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("⛔ **Nur der Server-Owner darf das.**", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Git Pull ausführen
            process = await asyncio.create_subprocess_shell(
                "git pull",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            output = stdout.decode().strip()
            error = stderr.decode().strip()

            if process.returncode != 0:
                await interaction.followup.send(f"❌ **Git Fehler:**\n```{error}```", ephemeral=True)
                return

            if "Already up to date" in output:
                await interaction.followup.send("✅ **Bereits aktuell.** Keine Änderungen geladen.", ephemeral=True)
                return

            # 2. Beenden für Neustart
            await interaction.followup.send(f"✅ **Update erfolgreich!**\n```{output}```\n♻️ **Bot wird neu gestartet...**", ephemeral=True)
            
            # Bot sauber beenden - Systemd (Restart=always) übernimmt den Neustart
            await self.bot.close()

        except Exception as e:
            await interaction.followup.send(f"❌ **Fehler beim Update:** {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
