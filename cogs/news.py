import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import json
import os
import datetime
import html
import re
import deepl
from deepl import QuotaExceededException

# Load glossary terms
GLOSSARY_FILE = "data/glossary.json"

def load_glossary_terms():
    if os.path.exists(GLOSSARY_FILE):
        try:
            with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading glossary: {e}")
    return []

class SteamNews(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.news_channel_id = self.bot.config.get_channel_id("news")

        self.app_id = os.getenv("ARC_RAIDERS_APP_ID")
        self.state_file = "data/news_state.json"
        self.last_posted_id = self.load_state()
        
        self.deepl_api_key = os.getenv("DEEPL_API_KEY")
        self.translator = None
        self.glossary = None
        
        if self.deepl_api_key:
            try:
                self.translator = deepl.Translator(self.deepl_api_key)
                print("DeepL Übersetzer initialisiert.")
                self.init_glossary()
            except Exception as e:
                print(f"Fehler beim Initialisieren von DeepL: {e}")

        if self.app_id and self.news_channel_id:
            self.check_news.start()
        else:
            print("Steam News: Fehlende Konfiguration (App ID oder Channel ID). Task nicht gestartet.")


    def init_glossary(self):
        if not self.translator: return
        
        terms = load_glossary_terms()
        if not terms:
            print("No glossary terms found.")
            return

        # Prepare Glossary Entries (Source = Target for DNT)
        entries = {term: term for term in terms}
        glossary_name = "ArcRaiders_Glossary"
        
        try:
            # 1. List existing glossaries
            existing_glossaries = self.translator.list_glossaries()
            
            # 2. Check if our glossary already exists
            existing_glossary = None
            for g in existing_glossaries:
                if g.name == glossary_name:
                    existing_glossary = g
                    break
            
            if existing_glossary:
                print(f"DeepL Glossary found: {existing_glossary.name} ({existing_glossary.entry_count} entries). REMOVING and RECREATING to update terms.")
                # We MUST delete and recreate to update terms locally
                try:
                    self.translator.delete_glossary(existing_glossary)
                    print("Altes Glossar gelöscht.")
                except Exception as e:
                    print(f"Fehler beim Löschen des alten Glossars (Limit erreicht?): {e}")
                    # If we can't delete, we might as well try to use it? 
                    # But if we use it, we miss new terms.
                    # If we are quota limited, we might be forced to use it.
                    self.glossary = existing_glossary
                    return

            # 3. Create new glossary
            try:
                self.glossary = self.translator.create_glossary(
                    glossary_name,
                    source_lang="EN",
                    target_lang="DE",
                    entries=entries
                )
                print(f"DeepL Glossar erstellt: {self.glossary.name} ({self.glossary.entry_count} Einträge)")
            except deepl.QuotaExceededException:
                 print("Kritisch: DeepL Quota bei Erstellung überschritten. Falle zurück auf KEIN Glossar oder existierendes.")
                 # If we failed to create but had one (that we deleted? oops), we are in trouble.
                 # If we failed to create because we didn't delete the old one, we should have found it above.
                 
            except Exception as e:
                print(f"Fehler beim Erstellen des Glossars: {e}")
            
        except Exception as e:
            print(f"Fehler beim Verwalten des DeepL Glossars: {e}")

    async def translate_text(self, text):
        if not self.translator: return text
        if not text or len(text.strip()) == 0: return text
        
        def _translate_sync():
            try:
                # Use HTML tag handling which is often smarter for web content
                result = self.translator.translate_text(
                    text,
                    target_lang="DE",
                    glossary=self.glossary if self.glossary else None,
                    tag_handling="html"
                )
                return result.text
            except Exception as e:
                print(f"Translation failed: {e}")
                return text

        return await self.bot.loop.run_in_executor(None, _translate_sync)

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    return data.get("last_posted_id")
            except Exception as e:
                print(f"Error loading news state: {e}")
        return None

    def save_state(self, news_id):
        self.last_posted_id = news_id
        try:
            with open(self.state_file, "w") as f:
                json.dump({"last_posted_id": news_id}, f)
        except Exception as e:
            print(f"Error saving news state: {e}")

    def cog_unload(self):
        self.check_news.cancel()

    def clean_html(self, raw_text):
        # 1. Extract Images
        image_urls = []
        img_matches = re.findall(r'\[img src="([^"]+)"\]', raw_text)
        for img_path in img_matches:
            clean_url = img_path.replace("{STEAM_CLAN_IMAGE}", "https://clan.cloudflare.steamstatic.com/images")
            image_urls.append(clean_url)

        # 2. ESCAPE CONTENT FIRST
        text = html.escape(raw_text)
        
        # 3. Apply Structure Tags
        
        # Lists
        text = text.replace("[list]", "<ul>").replace("[/list]", "</ul>")
        text = text.replace("[*]", "<li>")
        text = text.replace("[/*]", "</li>")
        
        # Headers
        text = re.sub(r'\[h1\](.*?)\[/h1\]', r'<h1>\1</h1>', text)
        text = re.sub(r'\[h2\](.*?)\[/h2\]', r'<h2>\1</h2>', text)
        text = re.sub(r'\[h3\](.*?)\[/h3\]', r'<h3>\1</h3>', text)
        
        # Basic Formatting
        text = re.sub(r'\[b\](.*?)\[/b\]', r'<b>\1</b>', text)
        text = re.sub(r'\[i\](.*?)\[/i\]', r'<i>\1</i>', text)
        text = re.sub(r'\[u\](.*?)\[/u\]', r'<u>\1</u>', text)
        
        # Urls -> <a href="...">...</a>
        # Fix: Remove quotes from the URL capture group if they exist
        # [url="http..."] -> \1="http..." -> we want http...
        def fix_url(match):
            url = match.group(1).replace('&quot;', '').replace('"', '').strip()
            content = match.group(2)
            return f'<a href="{url}">{content}</a>'
            
        text = re.sub(r'\[url=([^\]]+)\](.*?)\[/url\]', fix_url, text)
        
        # Cleanups
        text = re.sub(r'\[img.*?\[/img\]', '', text)
        text = re.sub(r'\[.*?\]', '', text) 
        text = re.sub(r'\[/?p\]', '\n', text)
        text = re.sub(r'\[/?br\]', '\n', text)
        
        return text.strip(), image_urls

    def html_to_discord_markdown(self, text):
        """Converts the translated HTML back to Discord Markdown."""
        
        # 1. Remove structure tags and replace with Markdown
        
        # Headers
        text = text.replace("<h1>", "\n\n# ").replace("</h1>", "\n\n")
        text = text.replace("<h2>", "\n\n## ").replace("</h2>", "\n\n")
        text = text.replace("<h3>", "\n\n### ").replace("</h3>", "\n\n")
        
        # Lists
        text = text.replace("<ul>", "").replace("</ul>", "")
        text = text.replace("<li>", "\n- ").replace("</li>", "")
        
        # Formatting
        text = text.replace("<b>", "**").replace("</b>", "**")
        text = text.replace("<i>", "*").replace("</i>", "*")
        text = text.replace("<u>", "__").replace("</u>", "__")
        
        # Links
        # We process links BEFORE unescaping to avoid breaking the HTML structure if the text contained tags
        text = re.sub(r'<a href="([^"]+)">(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)
        
        # 2. Unescape content
        text = html.unescape(text)
        
        # Cleanup extra newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

    async def fetch_latest_news(self, count=5):
        """Holt die neuesten offiziellen News über die Steam Events API.
        Gibt bei count=1 ein einzelnes Dict zurück, bei count>1 eine Liste.
        Dict-Format: {gid, title, contents, url}
        """
        events_url = (
            f"https://store.steampowered.com/events/ajaxgetpartnereventspageable/"
            f"?clan_accountid=0&appid={self.app_id}&offset=0&count={count}&l=english"
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(events_url) as response:
                    if response.status != 200:
                        print(f"Steam Events API gab Status zurück: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    if not data.get("success"):
                        print("Steam Events API: Anfrage nicht erfolgreich.")
                        return None
                    
                    events = data.get("events", [])
                    if not events:
                        print("Keine Events in der Steam Events API gefunden.")
                        return None
                    
                    results = []
                    for event in events:
                        ann = event.get("announcement_body", {})
                        gid = str(ann.get("gid", ""))
                        title = ann.get("headline", "Neuigkeiten zu Arc Raiders")
                        body = ann.get("body", "")
                        news_url = f"https://store.steampowered.com/news/app/{self.app_id}/view/{gid}"
                        results.append({
                            "gid": gid,
                            "title": title,
                            "contents": body,
                            "url": news_url,
                        })
                    
                    # Rückwärtskompatibel: bei count<=1 einzelnes Dict
                    if count <= 1:
                        return results[0] if results else None
                    return results
                    
        except Exception as e:
            print(f"Fehler beim Abrufen der Steam Events: {e}")
            return None

    @tasks.loop(minutes=15)
    async def check_news(self):
        latest_news = await self.fetch_latest_news(count=1)
        
        if not latest_news:
            return
        
        news_id = latest_news.get("gid")
        
        # Nur posten wenn es eine neue News ist
        if news_id != self.last_posted_id:
            # AUTOMATISCHER POST -> PING ROLE = TRUE
            await self.post_news(latest_news, ping_role=True)
            self.save_state(news_id)

    async def post_news(self, news_item, ping_role=False):
        channel = self.bot.get_channel(self.news_channel_id)
        if not channel:
            print(f"News Channel {self.news_channel_id} nicht gefunden.")
            return

        # Translate Title
        translated_title = await self.translate_text(news_item.get("title", "Neuigkeiten zu Arc Raiders"))

        # Parse content and extract images
        contents, image_urls = self.clean_html(news_item.get("contents", ""))
        
        # Translate Content (Text is HTML here)
        translated_html = await self.translate_text(contents)
        translated_contents = self.html_to_discord_markdown(translated_html)
        
        # Get URL
        url = news_item.get("url")
        
        # Header Message
        header = ""
        if ping_role:
             header += "<@&1466986718229041204>\n\n"
             
        header += f"**{translated_title}**\n\n"
        
        # Split content into chunks of 1900 chars
        full_text = header + translated_contents
        chunks = []
        
        try:
            # 1. Download and Prepare Images as Files
            files_to_send = []
            if image_urls:
                async with aiohttp.ClientSession() as session:
                    # Limit to 10 images (Discord attachment limit)
                    for i, img_url in enumerate(image_urls[:10]):
                        try:
                            async with session.get(img_url) as resp:
                                if resp.status == 200:
                                    data = await resp.read()
                                    from io import BytesIO
                                    file_obj = discord.File(BytesIO(data), filename=f"image_{i}.jpg")
                                    files_to_send.append(file_obj)
                        except Exception as e:
                            print(f"Fehler beim Herunterladen des Bildes {img_url}: {e}")

            # 2. Split Text
            while full_text:
                if len(full_text) <= 1900:
                    chunks.append(full_text)
                    break
                else:
                    split_index = full_text.rfind('\n', 0, 1900)
                    if split_index == -1: split_index = full_text.rfind(' ', 0, 1900)
                    if split_index == -1: split_index = 1900
                    chunks.append(full_text[:split_index])
                    full_text = full_text[split_index:].lstrip()

            # Add Source Link and Disclaimer to the last chunk
            footer = ""
            if url:
                 footer += f"\n\n[Original Artikel auf Steam](<{url}>)"
            
            footer += "\n_(Automatisch übersetzt mit DeepL)_"
            
            chunks[-1] += footer

            # 3. Send Chunks
            # Send all chunks except the last one comfortably
            for chunk in chunks[:-1]:
                await channel.send(content=chunk)
            
            # Send the last chunk WITH the files (images)
            if chunks:
                await channel.send(content=chunks[-1], files=files_to_send)
            
            print(f"Neue News gepostet: {translated_title}")

        except discord.HTTPException as e:
            print(f"Fehler beim Posten der News: {e}")
        except Exception as e:
             print(f"Unerwarteter Fehler in post_news: {e}")

    @check_news.before_loop
    async def before_check_news(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="force_news", description="Erzwingt das Posten der neuesten Steam News (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def force_news(self, interaction: discord.Interaction):
        # Check permissions manually using IDs from config
        allowed_roles = ["admin", "supervisor", "moderator"]
        user_role_ids = [role.id for role in interaction.user.roles]
        
        has_permission = False
        for role_key in allowed_roles:
            role_id = self.bot.config.get_role_id(role_key)
            if role_id and role_id in user_role_ids:
                has_permission = True
                break
        
        if not has_permission:
            await interaction.response.send_message("⛔ **Zugriff verweigert!** Du hast nicht die nötigen Rechte.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        


        try:
            latest_news = await self.fetch_latest_news(count=1)
            
            if not latest_news:
                await interaction.followup.send("Keine offiziellen News gefunden.", ephemeral=True)
                return

            # MANUELLER POST -> PING ROLE = FALSE
            await self.post_news(latest_news, ping_role=False)
            # State aktualisieren damit nicht doppelt gepostet wird
            self.save_state(latest_news.get("gid"))
            
            await interaction.followup.send(
                f"✅ Neueste News wurde gepostet: **{latest_news.get('title')}**", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"Fehler: {e}", ephemeral=True)

    # ── /patchnotes Command ──────────────────────────────────────

    @app_commands.command(name="patchnotes", description="Zeigt die letzten Patch Notes von Steam an")
    async def patchnotes(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            news_list = await self.fetch_latest_news(count=5)
            
            if not news_list:
                await interaction.followup.send("❌ Keine Patch Notes gefunden.", ephemeral=True)
                return
            
            # Select Menu erstellen
            view = PatchNotesView(news_list, self)
            
            embed = discord.Embed(
                title="📋 Patch Notes",
                description="Wähle eine News aus dem Dropdown-Menü:",
                color=discord.Color.blue()
            )
            
            for i, news in enumerate(news_list):
                title = news.get('title', 'Unbekannt')
                if len(title) > 60:
                    title = title[:57] + "..."
                embed.add_field(
                    name=f"{i+1}. {title}",
                    value=f"[Auf Steam lesen]({news.get('url', '#')})",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler: {e}", ephemeral=True)


class PatchNotesSelect(discord.ui.Select):
    def __init__(self, news_list, cog):
        self.news_list = news_list
        self.cog = cog
        
        options = []
        for i, news in enumerate(news_list):
            title = news.get('title', 'Unbekannt')
            if len(title) > 95:
                title = title[:92] + "..."
            options.append(discord.SelectOption(
                label=title,
                value=str(i),
                description=f"News #{i+1}"
            ))
        
        super().__init__(
            placeholder="📰 Wähle eine News...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        index = int(self.values[0])
        news = self.news_list[index]
        
        title = news.get('title', 'Patch Notes')
        body = news.get('contents', '')
        url = news.get('url', '')
        
        # BBCode zu lesbarem Text konvertieren (ohne Übersetzung)
        cleaned, _ = self.cog.clean_html(body)
        content = self.cog.html_to_discord_markdown(cleaned)
        
        # Auf 4000 Zeichen begrenzen (Embed-Limit)
        if len(content) > 4000:
            content = content[:3997] + "..."
        
        embed = discord.Embed(
            title=f"📰 {title}",
            description=content,
            color=discord.Color.blue(),
            url=url
        )
        embed.set_footer(text="Quelle: Steam | Originalsprache (Englisch)")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class PatchNotesView(discord.ui.View):
    def __init__(self, news_list, cog):
        super().__init__(timeout=300)
        self.add_item(PatchNotesSelect(news_list, cog))

async def setup(bot):
    await bot.add_cog(SteamNews(bot))
