import asyncio

import discord
from discord import app_commands
from discord.ext import commands

RULES = [
    ("§1 Respektvoller Umgang", 0xFF0000,
     "Behandle alle Mitglieder mit Respekt. Beleidigungen, Mobbing, Rassismus, Sexismus, Hassrede oder "
     "Diskriminierung jeglicher Art werden nicht toleriert und führen zum sofortigen Bann/Mute."),
    ("§2 Kein Spam & Keine Werbung", 0xFFA500,
     "Spamming ist untersagt. Eigenwerbung bitte nur in den dafür vorgesehenen Kanälen posten. "
     "Werbung per DM ist streng verboten."),
    ("§3 Keine NSFW-Inhalte", 0xFFFF00,
     "Pornografische, extrem gewalttätige oder verstörende Inhalte sind streng verboten."),
    ("§4 Privatsphäre & Datenschutz", 0x00FF00,
     "Verbreite niemals private Daten (Namen, Adressen, Nummern) von dir oder anderen."),
    ("§5 Channel-Nutzung", 0x00FFFF,
     "Nutze bitte die passenden Kanäle für deine Themen (z. B. Spielersuche nur im Spielersuche-Channel)."),
    ("§6 Discord Richtlinien", 0x800080,
     "Es gelten die offiziellen [Discord Terms of Service](https://discord.com/terms) und "
     "[Community Guidelines](https://discord.com/guidelines)."),
]


async def run_git(*args: str) -> tuple[int, str]:
    """Runs a git command in the bot directory and returns (exit code, combined output)."""
    process = await asyncio.create_subprocess_exec(
        "git", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await process.communicate()
    return process.returncode, stdout.decode(errors="replace").strip()


class Admin(commands.Cog):
    """Owner/admin tools: board refresh, command sync, self-update and rules post."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def deny_unless_owner(interaction: discord.Interaction) -> bool:
        if interaction.user.id == interaction.guild.owner_id:
            return False
        await interaction.response.send_message("⛔ **Nur der Server-Owner darf das.**", ephemeral=True)
        return True

    @app_commands.command(name="refresh_boards", description="Aktualisiert sofort alle Event-Boards (Owner Only)")
    @app_commands.default_permissions(administrator=True)
    async def refresh_boards(self, interaction: discord.Interaction):
        if await self.deny_unless_owner(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        general_cog = self.bot.get_cog("General")
        if not general_cog:
            await interaction.followup.send("❌ 'General' Modul nicht geladen.", ephemeral=True)
            return
        try:
            await general_cog.update_boards()
            await interaction.followup.send("✅ **Event-Boards wurden aktualisiert!**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Aktualisieren: {e}", ephemeral=True)

    @app_commands.command(name="sync", description="Synchronisiert Befehle (Owner Only)")
    @app_commands.default_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        if await self.deny_unless_owner(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"✅ **{len(synced)} Befehle synchronisiert.**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Synchronisation fehlgeschlagen: {e}", ephemeral=True)

    @app_commands.command(name="update", description="Zieht Updates von GitHub und startet neu (Owner Only)")
    @app_commands.default_permissions(administrator=True)
    async def update_bot(self, interaction: discord.Interaction):
        """Syncs with origin/main and restarts via systemd (Restart=always)."""
        if await self.deny_unless_owner(interaction):
            return
        await interaction.response.defer(ephemeral=True)

        try:
            _, before = await run_git("rev-parse", "HEAD")
            # Fetch + hard reset: always takes the GitHub version, never ends in merge conflicts
            for args in (("fetch", "origin"), ("reset", "--hard", "origin/main")):
                code, output = await run_git(*args)
                if code != 0:
                    await interaction.followup.send(f"❌ **Git Fehler:**\n```{output[:1800]}```", ephemeral=True)
                    return
            _, after = await run_git("rev-parse", "HEAD")

            if before == after:
                await interaction.followup.send("✅ **Bereits aktuell.** Keine Änderungen geladen.", ephemeral=True)
                return

            _, log = await run_git("log", "--oneline", f"{before}..{after}")
            await interaction.followup.send(
                f"✅ **Update erfolgreich!**\n```{log[:1500]}```\n♻️ **Bot wird neu gestartet...**", ephemeral=True
            )
            await self.bot.close()
        except Exception as e:
            await interaction.followup.send(f"❌ **Fehler beim Update:** {e}", ephemeral=True)

    @app_commands.command(name="rules", description="Postet das Regelwerk in den Rules-Channel (Admin Only)")
    @app_commands.default_permissions(administrator=True)
    async def post_rules(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⛔ Nur Admins dürfen das.", ephemeral=True)
            return

        channel_id = self.bot.config.get_channel_id("rules")
        channel = self.bot.get_channel(channel_id) if channel_id else None
        if not channel:
            await interaction.response.send_message(
                "❌ Rules-Kanal nicht gefunden. Trage `channels.rules` in der config.json ein.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        header = discord.Embed(
            title="🚧  SERVER REGELWERK  🚧",
            description="Bitte lies dir die folgenden Regeln aufmerksam durch.",
            color=discord.Color.dark_red(),
        )
        header.set_image(url="attachment://logo.png")

        try:
            await channel.send(embed=header, file=discord.File("assets/logo.png", filename="logo.png"))
            # One embed per rule gives the colored "block" look
            for title, color, text in RULES:
                await channel.send(embed=discord.Embed(title=title, description=text, color=color))
            await interaction.followup.send("✅ **Regelwerk erfolgreich gepostet!**", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Posten der Regeln: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Admin(bot))
