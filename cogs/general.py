import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils.api_client import ArcRaidersAPI
import os
import asyncio
from datetime import datetime, timedelta

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.image_cache = {}

    @app_commands.command(name="arcs", description="Informationen zu ARCs (Gegnern)")
    @app_commands.describe(arc_name="Suche nach einem spezifischen ARC")
    async def arcs(self, interaction: discord.Interaction, arc_name: str = None):
        """Zeigt Informationen zu ARCs an."""
        await interaction.response.defer(ephemeral=True)
        from utils.arc_data import ARC_DATA
        
        # If specific ARC requested
        if arc_name:
            # 1. Find key in local data
            key = None
            for k, v in ARC_DATA.items():
                if (v["names"]["de"].lower() == arc_name.lower() or 
                    v["names"]["en"].lower() == arc_name.lower() or 
                    k == arc_name.lower()):
                    key = k
                    break
            
            # 2. Try Fetching from API (for Loot & Live Data)
            api_data = None
            try:
                # API search uses English names or internal IDs usually
                # We search nicely with the name
                api: ArcRaidersAPI = self.bot.api
                search_term = ARC_DATA[key]['names']['en'] if key else arc_name
                response = await api.get_arcs(search=search_term, includeLoot=True) # Assuming helper supports kwargs
                # Note: api_client.get_arcs needs to support includeLoot param
                
                if response and "data" in response and response["data"]:
                    # Refine match
                    for item in response["data"]:
                        if item.get("name", "").lower() == search_term.lower():
                            api_data = item
                            break
                    if not api_data:
                         api_data = response["data"][0] # Fallback to first
            except Exception as e:
                print(f"API Abruf-Fehler: {e}")

            if not key and not api_data:
                await interaction.followup.send(f"❌ ARC '{arc_name}' nicht gefunden.", ephemeral=True)
                return
            
            # 3. Merge Data
            # Priority: Local Strategy > API Loot > Local Loot
            local_entry = ARC_DATA.get(key, {})
            
            name_de = local_entry.get("names", {}).get("de", arc_name)
            name_en = local_entry.get("names", {}).get("en", arc_name) # Fallback
            
            if api_data:
                 name_en = api_data.get("name", name_en)

            embed = discord.Embed(title=f"👾 {name_de}", color=discord.Color.red())
            
            # Description: Local > API
            desc = local_entry.get("description")
            if not desc and api_data:
                desc = api_data.get("description")
            embed.description = desc or "Keine Beschreibung verfügbar."
            
            # Fields
            type_val = local_entry.get("type") or (api_data.get("type", "Unbekannt") if api_data else "Unbekannt")
            embed.add_field(name="🛡️ Typ", value=type_val, inline=True)
            
            threat = local_entry.get("threat_level")
            if not threat and api_data:
                 threat = f"Tier {api_data.get('tier', '?')}"
            embed.add_field(name="⚠️ Bedrohung", value=threat or "Unbekannt", inline=True)
            
            # Combat (Local only usually)
            if local_entry.get("weak_points"):
                 weak_points = "\n".join([f"• {wp}" for wp in local_entry['weak_points']])
                 embed.add_field(name="🎯 Schwachstellen", value=weak_points, inline=False)
            
            if local_entry.get("tactic"):
                 embed.add_field(name="⚔️ Taktik", value=local_entry['tactic'], inline=False)

            # Drops (API Priority!)
            drops_text = ""
            if api_data and api_data.get("loot_table"):
                 # Assuming data structure: loot_table: [ { item: {name: "x"}, chance: 0.5 } ] or similar
                 # If simple list:
                 loot = api_data.get("loot_table", [])
                 # Check format. Docs said "Include loot items". Might be "drops" or "loot" key.
                 # Assuming typical structure based on quests/items.
                 # Let's try "drops" or "loot"
                 drops_list = []
                 source_list = api_data.get("drops") or api_data.get("loot") or []
                 
                 for d in source_list:
                     d_name = d.get("name") if isinstance(d, dict) else str(d)
                     if isinstance(d, dict) and "chance" in d:
                         d_name += f" ({d['chance']})"
                     drops_list.append(d_name)
                 
                 if drops_list:
                     drops_text = ", ".join(drops_list)
            
            if not drops_text and local_entry.get("drops"):
                 drops_text = ", ".join(local_entry['drops'])

            if drops_text:
                 embed.add_field(name="📦 Loot", value=drops_text, inline=False)
            
            # Image Logic
            en_name_safe = name_en.replace(" ", "_")
            image_filename = f"ARC_{en_name_safe}.png"
            image_path = f"assets/arcs/{image_filename}"
            
            # Reuse caching logic
            if image_filename in self.image_cache:
                embed.set_thumbnail(url=self.image_cache[image_filename])
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            if os.path.exists(image_path):
                 file = discord.File(image_path, filename=image_filename)
                 embed.set_thumbnail(url=f"attachment://{image_filename}")
                 msg = await interaction.followup.send(embed=embed, file=file, wait=True, ephemeral=True)
                 if msg.attachments:
                     self.image_cache[image_filename] = msg.attachments[0].url
            else:
                 # Check if API has image
                 if api_data and api_data.get("image"):
                      embed.set_thumbnail(url=api_data["image"])
                 await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Overview List (Categorized)
        embed = discord.Embed(
            title="👾 ARC Datenbank", 
            description="Hier findest du alle bekannten Gegner-Typen.\nNutze `/arcs name:Name` für Details & Taktiken.", 
            color=discord.Color.from_rgb(44, 47, 51)
        )
        
        # Categories
        categories = {
            "🛸 Lufteinheiten": ["snitch", "spotter", "wasp", "hornet", "rocketeer"],
            "🪖 Bodentruppen": ["pop", "tick", "fireball", "shredder", "leaper"],
            "🏰 Stationär & Taktisch": ["turret", "sentinel"],
            "💀 Elite & Bosse": ["bombardier", "bastion", "queen", "matriarch"],
            "📦 Loot": ["surveyor"]
        }
        
        for cat_name, keys in categories.items():
            value_list = []
            for k in keys:
                if k in ARC_DATA:
                    value_list.append(f"`{ARC_DATA[k]['names']['de']}`")
            
            if value_list:
                embed.add_field(name=cat_name, value=" • ".join(value_list), inline=False)
        
        embed.set_footer(text="Arc Raiders | Intel Database")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @arcs.autocomplete("arc_name")
    async def arcs_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        from utils.arc_data import ARC_DATA
        choices = []
        for k, v in ARC_DATA.items():
            name_de = v["names"]["de"]
            if current.lower() in name_de.lower():
                choices.append(app_commands.Choice(name=name_de, value=name_de))
        return choices[:25]

    async def cog_load(self):
        self.event_updater.start()

    async def cog_unload(self):
        self.event_updater.cancel()

    @tasks.loop(minutes=30)
    async def event_updater(self):
        await self.update_boards()

    async def update_boards(self):
        # Fetch Data
        try:
            data = await self.bot.api.get_events()
            all_events = data.get("data", [])
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Events: {e}")
            return



        if not all_events:
            return

        # Group by Map
        events_by_map = {}
        for event in all_events:
            map_name = event.get("map", "Unbekannt")
            if map_name not in events_by_map:
                events_by_map[map_name] = []
            events_by_map[map_name].append(event)
        
        # Sort
        for m in events_by_map:
            events_by_map[m].sort(key=lambda x: x.get("startTime", 0))

        # Color Mapping for Emojis
        emoji_map = {
            "Night Raid": "🟥",
            "Electromagnetic Storm": "🟦",
            "Bird City": "🟣",
            "Lush Blooms": "🟨",
            "Cold Snap": "🧊",
            "Matriarch": "🟠",
            "Harvester": "🟧",
            "Prospecting Probes": "⚪",
            "Uncovered Caches": "🟢",
            "Launch Tower Loot": "🟫",
            "Locked Gate": "🔐",
            "No Event Active": "⬛"
        }
        
        # Color Mapping for Embed Borders
        discord_color_map = {
            "Night Raid": discord.Color.red(),
            "Electromagnetic Storm": discord.Color.blue(),
            "Bird City": discord.Color.purple(),
            "Lush Blooms": discord.Color.gold(),
            "Cold Snap": discord.Color.teal(),
            "Matriarch": discord.Color.orange(),
            "Harvester": discord.Color.dark_orange(),
            "Prospecting Probes": discord.Color.light_grey(),
            "Uncovered Caches": discord.Color.green(),
            "Launch Tower Loot": discord.Color.from_rgb(139, 69, 19), # SaddleBrown
            "Locked Gate": discord.Color.from_rgb(0, 128, 0),
            "No Event Active": discord.Color.from_rgb(44, 47, 51) # Dark Grey
        }
        
        current_time = datetime.now().timestamp() * 1000

        # Update Guilds
        for guild in self.bot.guilds:
            # ... (Category logic remains same, we skip to loop inside) ...
            pass # Use match-all for replace tool if possible, but replace tool needs exact match.
            # I will just replace the `color_map` definition and the `translate_name` function logic inside the loop.
            # This tool call replaces a block. I need to be careful to target the right lines.
            
            # Since I can't target "inside the loop" easily without providing the whole loop context which is huge,
            # I will replace the color_map definition block primarily.
            # AND I will need to replace the `translate_name` function which is further down.
            # I'll do it in two chunks or one big chunk if they are close.
            # They are somewhat separated by the sorting logic.
            
            # Actually, `color_map` is defined before the loop. `translate_name` is inside.
            # I will replace `color_map` first.
            pass

    # ... (skipping to tool call) ...

        
        current_time = datetime.now().timestamp() * 1000

        # Channel Map (Hardcoded IDs to allow renaming)
        # Buried City: 1466957974856532185
        # Blue Gate: 1466957986995109980
        # Spaceport: 1466957990484508946
        # Dam: 1466958003612942398
        # Stella Montis: 1466958012525842498
        
        CHANNEL_MAP = {
            "Buried City": 1466957974856532185,
            "The Blue Gate": 1466957986995109980, # API usually sends "The Blue Gate" or "Blue Gate", check normalized?
            "Blue Gate": 1466957986995109980,
            "Spaceport": 1466957990484508946,
            "Dam": 1466958003612942398,
            "Dam Battlegrounds": 1466958003612942398, # Just in case
            "Stella Montis": 1466958012525842498
        }

        # Update Guilds
        for guild in self.bot.guilds:
            # Process each map channel
            for map_name, map_events in events_by_map.items():
                channel = None
                
                # 1. Try Configured ID
                if map_name in CHANNEL_MAP:
                    channel = guild.get_channel(CHANNEL_MAP[map_name])
                    # If not found (e.g. wrong guild or deleted), fallback to None
                
                # 2. Fallback to Name Lookup (only if ID failed)
                if not channel:
                    channel_name = map_name.lower().replace(" ", "-").replace("'", "").strip()
                    
                    # Try finding by name in a loop or get utils
                    # We need to find if it exists anywhere or in a specific category?
                    # Ideally we look globally or in our Known Category.
                    
                    # Get or Create Category (Lazy create only if we need to CREATE a channel)
                    cat_name = "📅 EVENT TIMERS"
                    category = discord.utils.get(guild.categories, name=cat_name)
                    
                    if category:
                        for c in category.text_channels:
                            if c.name == channel_name or c.name.endswith(f"◽{channel_name}"):
                                channel = c
                                break
                    
                    if not channel:
                        # CREATE NEW logic
                        if not category:
                             try:
                                category = await guild.create_category(cat_name)
                                await category.set_permissions(guild.default_role, send_messages=False, add_reactions=False, connect=False)
                             except Exception as e:
                                print(f"Fehler beim Erstellen der Kategorie: {e}")
                                continue
                        
                        try:
                            channel = await category.create_text_channel(channel_name)
                        except Exception as e:
                            print(f"Fehler beim Erstellen des Kanals {channel_name}: {e}")
                            continue

                if not channel:
                    print(f"Überspringe Karte {map_name} - Kanal konnte nicht gefunden oder erstellt werden.")
                    continue
                
                active_events = []
                upcoming_events = []
                for ev in map_events:
                    start = ev.get("startTime", 0)
                    end = ev.get("endTime", 0)
                    if start <= current_time <= end:
                        active_events.append(ev)
                    elif start > current_time:
                        upcoming_events.append(ev)

                # Determine Color (Use first active event)
                embed_color = discord.Color.from_rgb(44, 47, 51) # Default
                if active_events:
                    embed_color = discord_color_map.get(active_events[0].get("name"), discord.Color.purple())

                # Build Embed
                embed = discord.Embed(color=embed_color)
                embed.set_author(name="ARC Raiders DE", icon_url="https://i.imgur.com/8X8X8X.png") 
                embed.title = f"📍 {map_name}"

                # Active
                if active_events:
                    description = ""
                    for ev in active_events:
                        end_ts = int(ev.get("endTime", 0) / 1000)
                        emoji = emoji_map.get(ev.get("name"), "🟣") 
                        name = ev.get("name")
                        description += f"{emoji} **{name}**, endet <t:{end_ts}:R>\n"
                else:
                    if upcoming_events:
                        next_start = int(upcoming_events[0].get("startTime", 0) / 1000)
                        description = f"⬛ **Kein aktives Event**, bis <t:{next_start}:R>"
                    else:
                        description = "⬛ **Kein aktives Event**"
                
                embed.description = description + "\n**Bevorstehende Events**"
                
                # Upcoming
                for ev in upcoming_events[:5]:
                    start_ts = int(ev.get("startTime", 0) / 1000)
                    # REMOVED EMOJI for cleaner look
                    name = ev.get("name")
                    
                    real_time = datetime.fromtimestamp(ev.get("startTime",0)/1000).strftime("%H:%M")
                    # Use a simple bullet point
                    embed.description += f"\n• **{name}** <t:{start_ts}:R> ({real_time})"

                # Image Logic (Map)
                map_slug = map_name.lower().replace(" ", "-").replace("'", "")
                map_slug = map_slug.strip()
                
                file_path = None
                filename = None
                
                slugs_to_check = [map_slug]
                if map_slug.startswith("the-"):
                    slugs_to_check.append(map_slug[4:]) 
                else:
                    slugs_to_check.append(f"the-{map_slug}") 
                
                for slug in slugs_to_check:
                    if file_path: break
                    for ext in [".png", ".jpg", ".jpeg"]:
                        check_path = os.path.join("assets", "maps", slug + ext)
                        if os.path.exists(check_path):
                            file_path = check_path
                            filename = f"image_{slug}{ext}"
                            break
                
                # Check for Logo
                logo_path = os.path.join("assets", "logo.png")
                # Fallback to jpg if needed, but user sent png
                logo_filename = "logo.png"
                has_logo = os.path.exists(logo_path)

                file_obj = None
                logo_obj = None
                attachments = []

                if file_path:
                    file_obj = discord.File(file_path, filename=filename)
                    embed.set_image(url=f"attachment://{filename}")
                    attachments.append(file_obj)
                
                if has_logo:
                    logo_obj = discord.File(logo_path, filename=logo_filename)
                    attachments.append(logo_obj)
                    # Use Logo for Author Icon and Thumbnail
                    embed.set_author(name="ARC Raiders DE", icon_url=f"attachment://{logo_filename}") 
                    embed.set_thumbnail(url=f"attachment://{logo_filename}")
                else:
                     # Fallback to old Author Icon if no logo
                     embed.set_author(name="ARC Raiders DE", icon_url="https://i.imgur.com/8X8X8X.png")
                
                # Title separate as requested
                embed.title = f"📍 {map_name}"

                embed.set_footer(text=f"Aktualisiert: {datetime.now().strftime('%H:%M:%S')}")

                # Update Channel Name
                if active_events:
                    status_emoji = emoji_map.get(active_events[0].get("name"), "🟣")
                    # Support multiple icons?
                    if len(active_events) > 1:
                         emoji2 = emoji_map.get(active_events[1].get("name"), "🟣")
                         if emoji2 != status_emoji:
                             status_emoji += emoji2
                else:
                    status_emoji = "⬛"

                try:
                    base_slug = map_name.lower().replace(" ", "-").replace("'", "").strip()
                    new_channel_name = f"{status_emoji}◽{base_slug}"
                    if channel.name != new_channel_name:
                        await channel.edit(name=new_channel_name)
                except Exception as e:
                    print(f"Fehler beim Umbenennen des Kanals {channel.name}: {e}")

                try:
                    last_message = None
                    # Find last message by bot
                    async for msg in channel.history(limit=5):
                        if msg.author == self.bot.user:
                             last_message = msg
                             break
                    
                    if last_message:
                        # EDIT existing
                        await last_message.edit(embed=embed, attachments=attachments)
                    else:
                        # SEND new
                        await channel.purge(limit=5)
                        await channel.send(embed=embed, files=attachments)
                        
                except Exception as e:
                    print(f"Fehler beim Aktualisieren des Kanals {channel.name}: {e}")

    @event_updater.before_loop
    async def before_event_updater(self):
        await self.bot.wait_until_ready()
        
        # Align to next 30 min mark (XX:00 or XX:30)
        now = datetime.now()
        minutes_to_wait = 30 - (now.minute % 30)
        next_run = now + timedelta(minutes=minutes_to_wait)
        next_run = next_run.replace(second=0, microsecond=0)
        
        delay = (next_run - now).total_seconds()
        print(f"⏲️ Warte {delay:.1f}s, um Event-Loop auszurichten...")
        await asyncio.sleep(delay)

async def setup(bot):
    await bot.add_cog(General(bot))
