import asyncio
import os
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.arc_data import ARC_DATA

EVENT_CATEGORY_NAME = "📅 EVENT TIMERS"
DEFAULT_COLOR = discord.Color.from_rgb(44, 47, 51)
LOGO_PATH = os.path.join("assets", "logo.png")

# Emoji per event, also used as prefix in the channel name ("🟥◽dam")
EVENT_EMOJI = {
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
}

EVENT_COLOR = {
    "Night Raid": discord.Color.red(),
    "Electromagnetic Storm": discord.Color.blue(),
    "Bird City": discord.Color.purple(),
    "Lush Blooms": discord.Color.gold(),
    "Cold Snap": discord.Color.teal(),
    "Matriarch": discord.Color.orange(),
    "Harvester": discord.Color.dark_orange(),
    "Prospecting Probes": discord.Color.light_grey(),
    "Uncovered Caches": discord.Color.green(),
    "Launch Tower Loot": discord.Color.from_rgb(139, 69, 19),
    "Locked Gate": discord.Color.from_rgb(0, 128, 0),
}

ARC_CATEGORIES = {
    "🛸 Lufteinheiten": ["snitch", "spotter", "wasp", "hornet", "rocketeer"],
    "🪖 Bodentruppen": ["pop", "tick", "fireball", "shredder", "leaper"],
    "🏰 Stationär & Taktisch": ["turret", "sentinel"],
    "💀 Elite & Bosse": ["bombardier", "bastion", "queen", "matriarch"],
    "📦 Loot": ["surveyor"],
}

HELP_TEXT = {
    "🔎 Infos": (
        "`/arcs` – Gegner, Schwachstellen & Taktiken\n"
        "`/item` – Item-Werte & Herstellung\n"
        "`/quest` – Quest-Ziele & Belohnungen\n"
        "`/trader` – Händler-Inventar\n"
        "`/map` – Spawns, Extracts & POIs\n"
        "`/spielerzahl` – Aktuelle Spieler auf Steam"
    ),
    "📅 Automatisch": (
        "Event-Timer pro Map (alle 30 Min.)\n"
        "Steam-News, übersetzt ins Deutsche"
    ),
}


def map_slug(map_name: str) -> str:
    """'Buried City' -> 'buried-city' (used for channel names and image files)."""
    return map_name.lower().replace(" ", "-").replace("'", "").strip()


def find_map_image(map_name: str):
    """Looks for assets/maps/<slug>.png|jpg, with and without a leading 'the-'."""
    slug = map_slug(map_name)
    candidates = [slug, slug[4:]] if slug.startswith("the-") else [slug, f"the-{slug}"]
    for candidate in candidates:
        for ext in (".png", ".jpg", ".jpeg"):
            path = os.path.join("assets", "maps", candidate + ext)
            if os.path.exists(path):
                return path, f"image_{candidate}{ext}"
    return None, None


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Discord CDN URLs of already uploaded ARC images, so each file is only uploaded once
        self.image_cache: dict[str, str] = {}

    async def cog_load(self):
        self.event_updater.start()

    async def cog_unload(self):
        self.event_updater.cancel()

    # --- /help --------------------------------------------------------------

    @app_commands.command(name="help", description="Zeigt alle Befehle des Bots")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🤖 Arc Raiders Bot", color=discord.Color.blurple())
        for name, value in HELP_TEXT.items():
            embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text="Team-Befehle: /modhelp")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- /arcs --------------------------------------------------------------

    @app_commands.command(name="arcs", description="Informationen zu ARCs (Gegnern)")
    @app_commands.describe(arc_name="Suche nach einem spezifischen ARC")
    async def arcs(self, interaction: discord.Interaction, arc_name: str = None):
        await interaction.response.defer(ephemeral=True)
        if arc_name:
            await self.send_arc_details(interaction, arc_name)
        else:
            await interaction.followup.send(embed=self.build_arc_overview(), ephemeral=True)

    def build_arc_overview(self) -> discord.Embed:
        embed = discord.Embed(
            title="👾 ARC Datenbank",
            description="Hier findest du alle bekannten Gegner-Typen.\nNutze `/arcs name:Name` für Details & Taktiken.",
            color=DEFAULT_COLOR,
        )
        for category, keys in ARC_CATEGORIES.items():
            names = [f"`{ARC_DATA[k]['names']['de']}`" for k in keys if k in ARC_DATA]
            if names:
                embed.add_field(name=category, value=" • ".join(names), inline=False)
        embed.set_footer(text="Arc Raiders | Intel Database")
        return embed

    async def fetch_arc_from_api(self, search_term: str):
        """Live data incl. loot from the MetaForge API, or None."""
        try:
            response = await self.bot.api.get_arcs(search=search_term, include_loot=True)
        except Exception as e:
            print(f"API Abruf-Fehler: {e}")
            return None
        results = response.get("data") or []
        exact = [a for a in results if a.get("name", "").lower() == search_term.lower()]
        return (exact or results or [None])[0]

    async def send_arc_details(self, interaction: discord.Interaction, arc_name: str):
        # Local data holds the German texts and tactics, the API adds loot and images
        key = next(
            (k for k, v in ARC_DATA.items()
             if arc_name.lower() in (v["names"]["de"].lower(), v["names"]["en"].lower(), k)),
            None,
        )
        local = ARC_DATA.get(key, {})
        api_data = await self.fetch_arc_from_api(local["names"]["en"] if key else arc_name)

        if not key and not api_data:
            await interaction.followup.send(f"❌ ARC '{arc_name}' nicht gefunden.", ephemeral=True)
            return

        name_de = local.get("names", {}).get("de", arc_name)
        name_en = (api_data or {}).get("name") or local.get("names", {}).get("en", arc_name)

        embed = discord.Embed(title=f"👾 {name_de}", color=discord.Color.red())
        embed.description = local.get("description") or (api_data or {}).get("description") or "Keine Beschreibung verfügbar."
        embed.add_field(name="🛡️ Typ", value=local.get("type") or "Unbekannt", inline=True)
        embed.add_field(name="⚠️ Bedrohung", value=local.get("threat_level") or "Unbekannt", inline=True)

        if local.get("weak_points"):
            embed.add_field(name="🎯 Schwachstellen", value="\n".join(f"• {wp}" for wp in local["weak_points"]), inline=False)
        if local.get("tactic"):
            embed.add_field(name="⚔️ Taktik", value=local["tactic"], inline=False)

        # Loot: live from the API (list of {"item": {"name": ...}}), local list as fallback
        api_loot = [entry.get("item", {}).get("name") for entry in (api_data or {}).get("loot") or []]
        loot = [name for name in api_loot if name] or local.get("drops", [])
        if loot:
            embed.add_field(name="📦 Loot", value=", ".join(loot)[:1024], inline=False)

        await self.send_with_arc_image(interaction, embed, name_en, api_data)

    async def send_with_arc_image(self, interaction, embed, name_en, api_data):
        filename = f"ARC_{name_en.replace(' ', '_')}.png"
        path = os.path.join("assets", "arcs", filename)

        if filename in self.image_cache:
            embed.set_thumbnail(url=self.image_cache[filename])
            await interaction.followup.send(embed=embed, ephemeral=True)
        elif os.path.exists(path):
            embed.set_thumbnail(url=f"attachment://{filename}")
            msg = await interaction.followup.send(
                embed=embed, file=discord.File(path, filename=filename), wait=True, ephemeral=True
            )
            if msg.attachments:
                self.image_cache[filename] = msg.attachments[0].url
        else:
            if api_data and api_data.get("image"):
                embed.set_thumbnail(url=api_data["image"])
            await interaction.followup.send(embed=embed, ephemeral=True)

    @arcs.autocomplete("arc_name")
    async def arcs_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        names = [v["names"]["de"] for v in ARC_DATA.values() if current.lower() in v["names"]["de"].lower()]
        return [app_commands.Choice(name=n, value=n) for n in names[:25]]

    # --- Event timer boards -------------------------------------------------

    @tasks.loop(minutes=30)
    async def event_updater(self):
        await self.update_boards()

    @event_updater.before_loop
    async def before_event_updater(self):
        await self.bot.wait_until_ready()
        # Align to the next full or half hour, when the event rotation changes
        now = datetime.now()
        next_run = (now + timedelta(minutes=30 - now.minute % 30)).replace(second=0, microsecond=0)
        delay = (next_run - now).total_seconds()
        print(f"⏲️ Warte {delay:.1f}s, um Event-Loop auszurichten...")
        await asyncio.sleep(delay)

    async def update_boards(self):
        """Posts or edits one embed per map and puts the active event's emoji into the channel name."""
        try:
            data = await self.bot.api.get_events()
        except Exception as e:
            print(f"Fehler beim Aktualisieren der Events: {e}")
            return
        events = data.get("data") or []
        if not events:
            return

        events_by_map: dict[str, list] = {}
        for event in events:
            events_by_map.setdefault(event.get("map", "Unbekannt"), []).append(event)
        for map_events in events_by_map.values():
            map_events.sort(key=lambda e: e.get("startTime", 0))

        now_ms = datetime.now().timestamp() * 1000
        for guild in self.bot.guilds:
            for map_name, map_events in events_by_map.items():
                channel = await self.get_or_create_board_channel(guild, map_name)
                if not channel:
                    print(f"Überspringe Karte {map_name} - Kanal konnte nicht gefunden oder erstellt werden.")
                    continue
                active = [e for e in map_events if e.get("startTime", 0) <= now_ms <= e.get("endTime", 0)]
                upcoming = [e for e in map_events if e.get("startTime", 0) > now_ms]
                await self.rename_board_channel(channel, map_name, active)
                await self.post_board(channel, map_name, active, upcoming)

    async def get_or_create_board_channel(self, guild: discord.Guild, map_name: str):
        # 1. Configured channel ID (survives renames)
        channel_id = self.bot.config.get_event_channels().get(map_name)
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel:
            return channel

        # 2. Search by name inside the event category, 3. create it
        category_id = self.bot.config.get_channel_id("event_category")
        category = guild.get_channel(category_id) if category_id else None
        category = category or discord.utils.get(guild.categories, name=EVENT_CATEGORY_NAME)

        slug = map_slug(map_name)
        if category:
            for c in category.text_channels:
                if c.name == slug or c.name.endswith(f"◽{slug}"):
                    return c

        try:
            if not category:
                category = await guild.create_category(EVENT_CATEGORY_NAME)
                await category.set_permissions(guild.default_role, send_messages=False, add_reactions=False)
            return await category.create_text_channel(slug)
        except Exception as e:
            print(f"Fehler beim Erstellen des Kanals {slug}: {e}")
            return None

    async def rename_board_channel(self, channel, map_name, active):
        # Up to two different emojis for overlapping events
        emojis = []
        for event in active[:2]:
            emoji = EVENT_EMOJI.get(event.get("name"), "🟣")
            if emoji not in emojis:
                emojis.append(emoji)
        new_name = f"{''.join(emojis) or '⬛'}◽{map_slug(map_name)}"
        if channel.name == new_name:
            return
        try:
            # Discord only allows 2 channel renames per 10 minutes, the 30 min loop stays below that
            await channel.edit(name=new_name)
        except Exception as e:
            print(f"Fehler beim Umbenennen des Kanals {channel.name}: {e}")

    async def post_board(self, channel, map_name, active, upcoming):
        color = EVENT_COLOR.get(active[0].get("name"), discord.Color.purple()) if active else DEFAULT_COLOR
        embed = discord.Embed(title=f"📍 {map_name}", color=color)

        if active:
            lines = [
                f"{EVENT_EMOJI.get(e.get('name'), '🟣')} **{e.get('name')}**, endet <t:{int(e.get('endTime', 0) / 1000)}:R>"
                for e in active
            ]
            description = "\n".join(lines)
        elif upcoming:
            description = f"⬛ **Kein aktives Event**, bis <t:{int(upcoming[0].get('startTime', 0) / 1000)}:R>"
        else:
            description = "⬛ **Kein aktives Event**"

        description += "\n\n**Bevorstehende Events**"
        for e in upcoming[:5]:
            start = int(e.get("startTime", 0) / 1000)
            # <t:...:t> renders in each viewer's own time zone
            description += f"\n• **{e.get('name')}** <t:{start}:R> (<t:{start}:t>)"
        embed.description = description

        files = []
        image_path, image_name = find_map_image(map_name)
        if image_path:
            files.append(discord.File(image_path, filename=image_name))
            embed.set_image(url=f"attachment://{image_name}")
        if os.path.exists(LOGO_PATH):
            files.append(discord.File(LOGO_PATH, filename="logo.png"))
            embed.set_author(name="ARC Raiders DE", icon_url="attachment://logo.png")
            embed.set_thumbnail(url="attachment://logo.png")
        else:
            embed.set_author(name="ARC Raiders DE")
        embed.set_footer(text="Aktualisiert")
        embed.timestamp = datetime.now()

        try:
            # Edit the bot's last board message instead of spamming new ones
            last_message = None
            async for msg in channel.history(limit=5):
                if msg.author == self.bot.user:
                    last_message = msg
                    break
            if last_message:
                await last_message.edit(embed=embed, attachments=files)
            else:
                await channel.send(embed=embed, files=files)
        except Exception as e:
            print(f"Fehler beim Aktualisieren des Kanals {channel.name}: {e}")


async def setup(bot):
    await bot.add_cog(General(bot))
