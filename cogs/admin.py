import discord
from discord import app_commands
from discord.ext import commands

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

    @commands.command(name="sync", hidden=True)
    @commands.has_permissions(administrator=True)
    async def sync(self, ctx):
        """Manually syncs slash commands to the current guild."""
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"✅ {len(synced)} Befehle global synchronisiert.")
        except Exception as e:
            await ctx.send(f"❌ Synchronisation fehlgeschlagen: {e}")



async def setup(bot):
    await bot.add_cog(Admin(bot))
