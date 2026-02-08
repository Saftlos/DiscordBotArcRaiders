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

    @app_commands.command(name="rules", description="Postet das Regelwerk in den Rules-Channel (Admin Only)")
    @app_commands.default_permissions(administrator=True)
    async def post_rules(self, interaction: discord.Interaction):
        """Postet die Server-Regeln im Embed-Format."""
        # 1. Permission Check
        if not interaction.user.guild_permissions.administrator:
             await interaction.response.send_message("⛔ Nur Admins dürfen das.", ephemeral=True)
             return

        # 2. Target Channel
        channel_id = 1466942484943868088
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message(f"❌ Ziel-Kanal {channel_id} nicht gefunden!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # 3. Create Embeds (One per Rule for the "Block Style")
        
        # Header
        embed_header = discord.Embed(title="🚧  SERVER REGELWERK  🚧", description="Bitte lies dir die folgenden Regeln aufmerksam durch.", color=discord.Color.dark_red())
        embed_header.set_image(url="https://media.discordapp.net/attachments/1335016624897855562/1336067727181676645/Arc_Raiders_Header.png?ex=67a8677a&is=67a715fa&hm=a85237703511111111") # Placeholder / Arc Image if available

        # Rules Data
        rules = [
            {"title": "§1 Respektvoller Umgang", "desc": "Behandle alle Mitglieder mit Respekt. Beleidigungen, Mobbing, Rassismus, Sexismus, Hassrede oder Diskriminierung jeglicher Art werden nicht toleriert und führen zum sofortigen Bann/Mute.", "color": 0xFF0000}, # Red
            {"title": "§2 Kein Spam & Keine Werbung", "desc": "Spamming ist untersagt. Eigenwerbung bitte nur in den dafür vorgesehenen Kanälen posten. Werbung per DM ist streng verboten.", "color": 0xFFA500}, # Orange
            {"title": "§3 Keine NSFW-Inhalte", "desc": "Pornografische, extrem gewalttätige oder verstörende Inhalte sind streng verboten.", "color": 0xFFFF00}, # Yellow
            {"title": "§4 Privatsphäre & Datenschutz", "desc": "Verbreite niemals private Daten (Namen, Adressen, Nummern) von dir oder anderen.", "color": 0x00FF00}, # Green
            {"title": "§5 Channel-Nutzung", "desc": "Nutze bitte die passenden Kanäle für deine Themen (z. B. Spielersuche nur im Spielersuche-Channel).", "color": 0x00FFFF}, # Cyan
            {"title": "§6 Discord Richtlinien", "desc": "Es gelten die offiziellen [Discord Terms of Service](https://discord.com/terms) und [Community Guidelines](https://discord.com/guidelines).", "color": 0x800080}  # Purple
        ]

        try:
            # Purge old messages (optional, maybe dangerous? let's just post)
            # await channel.purge(limit=10) 
            
            await channel.send(embed=embed_header)

            for rule in rules:
                embed = discord.Embed(title=rule["title"], description=rule["desc"], color=rule["color"])
                await channel.send(embed=embed)

            await interaction.followup.send("✅ **Regelwerk erfolgreich gepostet!**", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Posten der Regeln: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
