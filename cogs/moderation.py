import discord
from discord import app_commands
from discord.ext import commands, tasks
import datetime
import json
import os
import asyncio
import time

MUTES_FILE = "data/mutes.json"
HISTORY_FILE = "data/history.json"

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_mutes = self.load_data(MUTES_FILE)
        self.history = self.load_data(HISTORY_FILE)
        self.check_mutes.start()

    def load_data(self, filepath):
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Fehler beim Laden von {filepath}: {e}")
            return {}

    def save_data(self, filepath, data):
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"❌ Fehler beim Speichern von {filepath}: {e}")

    def add_history_entry(self, user_id: int, moderator_id: int, action: str, reason: str, duration: str = None):
        """Adds an entry to the user's history."""
        user_key = str(user_id)
        if user_key not in self.history:
            self.history[user_key] = []
            
        entry = {
            "action": action,
            "moderator": moderator_id,
            "reason": reason,
            "timestamp": int(time.time()),
            "duration": duration,
            "case_id": len(self.history[user_key]) + 1
        }
        self.history[user_key].append(entry)
        self.save_data(HISTORY_FILE, self.history)

    def parse_duration(self, duration: str) -> int:
        """Parses duration string (30s, 10m, 1h, 1d) into seconds."""
        duration = duration.strip().lower()
        multiplier = 1
        if duration.endswith("s"):
            multiplier = 1
            value = int(duration[:-1])
        elif duration.endswith("m"):
            multiplier = 60
            value = int(duration[:-1])
        elif duration.endswith("h"):
            multiplier = 3600
            value = int(duration[:-1])
        elif duration.endswith("d"):
            multiplier = 86400
            value = int(duration[:-1])
        else:
            raise ValueError("Ungültiges Format")
        return value * multiplier

    def has_permission(self, user: discord.Member, permission_key: str) -> bool:
        if user.id == user.guild.owner_id:
            return True
        allowed_ids = self.bot.config.get_role_ids_list(permission_key)
        return any(role.id in allowed_ids for role in user.roles)
    
    def is_staff(self, user: discord.Member) -> bool:
        return self.has_permission(user, "mute_allowed")

    async def log_strafakte(self, interaction: discord.Interaction, target: discord.Member, action: str, reason: str, duration: str = None, ban_recommendation: bool = False):
        """Creates the Strafakte Embed."""
        channel_id = self.bot.config.get_channel_id("strafakte")
        channel = self.bot.get_channel(channel_id)
        
        if not channel:
            if interaction:
                 await interaction.followup.send("❌ Fehler: Strafakte-Kanal nicht gefunden.", ephemeral=True)
            return None

        embed = discord.Embed(title=f"⚖️ Strafakte: {action.upper()}", color=discord.Color.dark_red())
        embed.add_field(name="👤 Täter", value=f"{target.mention} (`{target.id}`)", inline=True)
        
        moderator = interaction.user.mention if interaction else "🤖 Auto-System"
        embed.add_field(name="👮 Moderator", value=moderator, inline=True)
        
        if duration:
            embed.add_field(name="⏱️ Dauer", value=duration, inline=True)
        
        embed.add_field(name="📝 Grund", value=reason, inline=False)
        
        if ban_recommendation:
             embed.add_field(name="🛑 BANN EMPFEHLUNG", value="⚠️ Strafe ist ≥ 14 Tage. Ein Supervisor muss dies prüfen und ggf. bannen.", inline=False)

        footer_text = f"Fall-ID: {interaction.id if interaction else 'AUTO'}"
        if interaction:
            footer_text += " | Antworte mit: notiz:, grund:, dauer: oder Bildern."
            
        embed.set_footer(text=footer_text)
        embed.timestamp = datetime.datetime.now()

        msg = await channel.send(embed=embed)
        return msg

    @tasks.loop(minutes=1)
    async def check_mutes(self):
        """Checks regularly for expired mutes."""
        current_time = time.time()
        to_remove = []

        for user_id_str, data in self.active_mutes.items():
            end_time = data.get("end_time")
            if end_time and current_time >= end_time:
                guild_id = data.get("guild_id")
                role_id = data.get("role_id")
                
                guild = self.bot.get_guild(guild_id)
                if guild:
                    member = guild.get_member(int(user_id_str))
                    role = guild.get_role(role_id)
                    
                    if member and role and role in member.roles:
                        try:
                            await member.remove_roles(role, reason="Mute abgelaufen (Auto-System)")
                            # Log Unmute
                            channel_id = self.bot.config.get_channel_id("strafakte")
                            channel = self.bot.get_channel(channel_id)
                            if channel:
                                embed = discord.Embed(title="⚖️ Strafakte: AUTO-UNMUTE", color=discord.Color.green())
                                embed.add_field(name="👤 Nutzer", value=f"{member.mention}", inline=True)
                                embed.add_field(name="👮 Moderator", value="🤖 Auto-System", inline=True)
                                embed.add_field(name="📝 Grund", value="Zeit abgelaufen", inline=False)
                                embed.timestamp = datetime.datetime.now()
                                await channel.send(embed=embed)
                                
                            # History Entry
                            self.add_history_entry(int(user_id_str), self.bot.user.id, "UNMUTE (AUTO)", "Zeit abgelaufen")

                        except Exception as e:
                            print(f"Fehler beim Auto-Unmute von User {user_id_str}: {e}")
                
                to_remove.append(user_id_str)
        
        for uid in to_remove:
            del self.active_mutes[uid]
        
        if to_remove:
            self.save_data(MUTES_FILE, self.active_mutes)

    @check_mutes.before_loop
    async def before_check_mutes(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.check_mutes.cancel()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handles evidence uploads and Case edits via reply."""
        if message.author.bot:
            return
            
        strafakte_id = self.bot.config.get_channel_id("strafakte")
        if message.channel.id != strafakte_id:
            return

        if not message.reference:
            return
            
        if not self.is_staff(message.author):
            return

        try:
            ref_msg = await message.channel.fetch_message(message.reference.message_id)
            if ref_msg.author.id != self.bot.user.id or not ref_msg.embeds:
                return

            original_embeds = list(ref_msg.embeds)
            main_embed = original_embeds[0]
            changes_made = False
            cleanup_message = True

            content = message.content.strip()
            content_lower = content.lower()
            
            if content_lower.startswith("notiz:"):
                # ... (Logic identical to previous, just logging history maybe not needed for notes) ...
                note_text = content[6:].strip()
                if note_text:
                    note_field_index = -1
                    for idx, field in enumerate(main_embed.fields):
                        if field.name == "📝 Notiz":
                            note_field_index = idx
                            break
                    if note_field_index >= 0:
                        old_val = main_embed.fields[note_field_index].value
                        main_embed.set_field_at(note_field_index, name="📝 Notiz", value=f"{old_val}\n- {note_text}", inline=False)
                    else:
                        main_embed.add_field(name="📝 Notiz", value=f"- {note_text}", inline=False)
                    changes_made = True

            elif content_lower.startswith("grund:"):
                reason_text = content[6:].strip()
                if reason_text:
                    for idx, field in enumerate(main_embed.fields):
                        if field.name == "📝 Grund":
                            main_embed.set_field_at(idx, name="📝 Grund", value=reason_text, inline=False)
                            changes_made = True
                            break

            elif content_lower.startswith("dauer:"):
                duration_str = content[6:].strip()
                try:
                    time_seconds = self.parse_duration(duration_str)
                    for idx, field in enumerate(main_embed.fields):
                        if field.name == "⏱️ Dauer":
                            main_embed.set_field_at(idx, name="⏱️ Dauer", value=duration_str, inline=True)
                            changes_made = True
                            break
                    
                    footer = main_embed.footer.text or ""
                    if "Dauer geändert" not in footer:
                        main_embed.set_footer(text=f"{footer} | ⚠️ Dauer geändert auf {duration_str}")

                    target_user_id = None
                    for uid, data in self.active_mutes.items():
                        if data.get("log_message_id") == ref_msg.id:
                            target_user_id = uid
                            break
                    
                    if target_user_id:
                        new_end_time = time.time() + time_seconds
                        self.active_mutes[target_user_id]["end_time"] = new_end_time
                        self.save_data(MUTES_FILE, self.active_mutes)
                        await message.add_reaction("✅")
                        
                        # History update? Maybe too specific, skipped for brevity.
                    
                except ValueError:
                    await message.add_reaction("❓")
                    cleanup_message = False

            if message.attachments:
                new_embeds_list = [main_embed]
                if len(original_embeds) > 1:
                    new_embeds_list = original_embeds
                
                for attachment in message.attachments:
                    if not attachment.content_type or not attachment.content_type.startswith("image/"):
                        continue
                    if len(new_embeds_list) >= 10:
                        await message.add_reaction("⚠️")
                        break

                    if not new_embeds_list[0].image.url:
                        new_embeds_list[0].set_image(url=attachment.url)
                    else:
                        gal_embed = discord.Embed(url=new_embeds_list[0].url)
                        gal_embed.set_image(url=attachment.url)
                        if new_embeds_list[0].color:
                            gal_embed.color = new_embeds_list[0].color
                        new_embeds_list.append(gal_embed)
                    changes_made = True
                main_embed = new_embeds_list[0]
                original_embeds = new_embeds_list

            if changes_made:
                await ref_msg.edit(embeds=original_embeds)
                if cleanup_message:
                    await message.delete()

        except Exception as e:
            print(f"Fehler bei der Reply-Interaktion: {e}")

    @app_commands.command(name="mute", description="Muted einen User (Nutze: 30s, 10m, 1h, 1d)")
    @app_commands.describe(member="Der User", duration="Dauer (z.B. 1h)", reason="Grund")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str):
        if not self.has_permission(interaction.user, "mute_allowed"):
            await interaction.response.send_message("⛔ Keine Berechtigung!", ephemeral=True)
            return
            
        role_id = self.bot.config.get_role_id("muted")
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("❌ Muted-Rolle nicht gefunden.", ephemeral=True)
            return

        if role in member.roles:
             if not self.has_permission(interaction.user, "unmute_allowed"):
                  await interaction.response.send_message("⛔ User bereits gemuted.", ephemeral=True)
                  return

        await interaction.response.defer(ephemeral=True)
        
        try:
            time_seconds = self.parse_duration(duration)
        except ValueError:
             await interaction.followup.send("❌ Ungültiges Zeitformat.", ephemeral=True)
             return

        recommend_ban = False
        if time_seconds >= 1209600:
            recommend_ban = True

        try:
            await member.add_roles(role, reason=reason)
            
            # Log & Persistence & History
            log_msg = await self.log_strafakte(interaction, member, "MUTE", reason, duration, ban_recommendation=recommend_ban)
            log_id = log_msg.id if log_msg else None
            
            self.active_mutes[str(member.id)] = {
                "guild_id": interaction.guild.id,
                "role_id": role.id,
                "end_time": time.time() + time_seconds,
                "reason": reason,
                "log_message_id": log_id,
                "log_channel_id": log_msg.channel.id if log_msg else None
            }
            self.save_data(MUTES_FILE, self.active_mutes)
            
            self.add_history_entry(member.id, interaction.user.id, "MUTE", reason, duration)
            
            msg = f"✅ {member.mention} wurde für {duration} gemuted."
            if recommend_ban:
                msg += "\n⚠️ **Zeitraum ≥ 14 Tage**: Bann-Empfehlung vermerkt."
            await interaction.followup.send(msg)
        except Exception as e:
             await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)

    @app_commands.command(name="unmute", description="Entfernt Mute von einem User")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Manuell entfernt"):
        if not self.has_permission(interaction.user, "unmute_allowed"):
            await interaction.response.send_message("⛔ Keine Berechtigung!", ephemeral=True)
            return

        role_id = self.bot.config.get_role_id("muted")
        role = interaction.guild.get_role(role_id)
        if not role:
             await interaction.response.send_message("❌ Muted-Rolle nicht gefunden.", ephemeral=True)
             return

        await interaction.response.defer(ephemeral=True)
        try:
            await member.remove_roles(role, reason=reason)
            
            if str(member.id) in self.active_mutes:
                del self.active_mutes[str(member.id)]
                self.save_data(MUTES_FILE, self.active_mutes)

            await self.log_strafakte(interaction, member, "UNMUTE", reason)
            self.add_history_entry(member.id, interaction.user.id, "UNMUTE", reason)
            
            await interaction.followup.send(f"✅ {member.mention} wurde entmuted.")
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)

    @app_commands.command(name="kick", description="Kickt einen User aus dem Server")
    @app_commands.default_permissions(moderate_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if not self.has_permission(interaction.user, "kick_allowed"):
            await interaction.response.send_message("⛔ Keine Berechtigung!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await member.kick(reason=reason)
            await self.log_strafakte(interaction, member, "KICK", reason)
            self.add_history_entry(member.id, interaction.user.id, "KICK", reason)
            await interaction.followup.send(f"✅ {member.mention} wurde gekickt.")
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="Bannt einen User vom Server")
    @app_commands.default_permissions(moderate_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if not self.has_permission(interaction.user, "ban_allowed"):
            await interaction.response.send_message("⛔ Keine Berechtigung!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await member.ban(reason=reason)
            await self.log_strafakte(interaction, member, "BAN", reason)
            self.add_history_entry(member.id, interaction.user.id, "BAN", reason)
            await interaction.followup.send(f"✅ {member.mention} wurde gebannt.")
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)
            
    @app_commands.command(name="modlogs", description="Zeigt die Moderations-Historie eines Users")
    @app_commands.describe(member="Der User, dessen Akte du sehen willst")
    @app_commands.default_permissions(moderate_members=True)
    async def modlogs(self, interaction: discord.Interaction, member: discord.User): # Use User instead of Member to support left users if cache allows
        if not self.has_permission(interaction.user, "mute_allowed"):
             await interaction.response.send_message("⛔ Keine Berechtigung!", ephemeral=True)
             return
             
        user_key = str(member.id)
        if user_key not in self.history or not self.history[user_key]:
            await interaction.response.send_message(f"📜 Keine Einträge für {member.mention} gefunden.", ephemeral=True)
            return
            
        entries = self.history[user_key]
        entries.sort(key=lambda x: x['timestamp'], reverse=True) # Newest first
        
        embed = discord.Embed(title=f"📜 Akte: {member.name} ({member.id})", color=discord.Color.gold())
        
        text = ""
        for i, e in enumerate(entries[:10]): # Last 10
            ts = e.get("timestamp", 0)
            action = e.get("action", "UNKNOWN")
            mod_id = e.get("moderator")
            reason = e.get("reason", "Kein Grund")
            dur = f" ({e['duration']})" if e.get("duration") else ""
            
            text += f"**{i+1}. {action}{dur}** <t:{ts}:d>\n"
            text += f"> *{reason}* (Mod: <@{mod_id}>)\n\n"
            
        if len(entries) > 10:
            text += f"*...und {len(entries)-10} weitere ältere Einträge.*"
            
        embed.description = text
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="modhelp", description="Zeigt Hilfe für Moderatoren (Befehle & Tricks)")
    @app_commands.default_permissions(moderate_members=True)
    async def modhelp(self, interaction: discord.Interaction):
        if not self.has_permission(interaction.user, "mute_allowed"):
             await interaction.response.send_message("⛔ Nur für Teammitglieder.", ephemeral=True)
             return
             
        embed = discord.Embed(title="🛡️ Moderations-Handbuch", color=discord.Color.blue())
        
        embed.add_field(name="🆕 Befehle", value=(
            "`/mute @User [Dauer] [Grund]` - Mute (z.B. 30s, 10m, 2h)\n"
            "`/unmute @User` - Aufheben\n"
            "`/kick`, `/ban` - Standard\n"
            "`/modlogs @User` - Zeigt Vorstrafen"
        ), inline=False)
        
        embed.add_field(name="📂 Akten bearbeiten (Reply)", value=(
            "Antworte auf eine Nachricht im Strafakte-Kanal:\n"
            "• **Bild hochladen**: Einfach Bild anhängen (fügt zur Galerie hinzu)\n"
            "• `notiz: Text` - Fügt eine Notiz hinzu\n"
            "• `grund: Text` - Ändert den Grund\n"
            "• `dauer: 1h` - Ändert laufenden Mute (!)"
        ), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
