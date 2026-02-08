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
        self.steam_api_key = os.getenv("STEAM_API_KEY")
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

        if self.steam_api_key and self.app_id and self.news_channel_id:
            self.check_news.start()
        else:
            print("Steam News: Fehlende Konfiguration (API Key, App ID oder Channel ID). Task nicht gestartet.")

    def init_glossary(self):
        if not self.translator: return
        
        terms = load_glossary_terms()
        if not terms:
            print("Keine Glossar-Begriffe gefunden.")
            return

        # Prepare Glossary Entries (Source = Target for DNT)
        entries = {term: term for term in terms}
        
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

    @tasks.loop(minutes=15)
    async def check_news(self):
        url = f"http://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={self.app_id}&count=5&maxlength=0&format=json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        news_items = data.get("appnews", {}).get("newsitems", [])
                        
                        if not news_items:
                            return

                        # Find the newest OFFICIAL news item
                        latest_news = None
                        for item in news_items:
                            if item.get("feedname") == "steam_community_announcements":
                                latest_news = item
                                break
                        
                        if not latest_news:
                            print("Keine offiziellen News im letzten Abruf gefunden.")
                            return
                        news_id = latest_news.get("gid")
                        
                        # If it's a new post
                        if news_id != self.last_posted_id:
                            await self.post_news(latest_news)
                            self.save_state(news_id)
                    else:
                        print(f"Steam News API gab Status zurück: {response.status}")
        except Exception as e:
            print(f"Fehler beim Prüfen der Steam News: {e}")

    async def post_news(self, news_item):
        channel = self.bot.get_channel(self.news_channel_id)
        if not channel:
            print(f"News Channel {self.news_channel_id} nicht gefunden.")
            return

        # Translate Title
        # Translate Title
        translated_title = await self.translate_text(news_item.get("title", "Neuigkeiten zu Arc Raiders"))

        # Parse content and extract images
        contents, image_urls = self.clean_html(news_item.get("contents", ""))
        
        # Translate Content
        # Translate Content (Text is HTML here)
        translated_html = await self.translate_text(contents)
        translated_contents = self.html_to_discord_markdown(translated_html)
        
        # Get URL
        url = news_item.get("url")
        
        # Header Message
        date_timestamp = news_item.get("date")
        # date_str = ""
        # if date_timestamp:
        #      date_str = f"<t:{date_timestamp}:D>" 
        
        header = f"**{translated_title}**\n\n"
        
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
        
        # Fetch more items (e.g., 5) and unlimited length
        url = f"http://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={self.app_id}&count=5&maxlength=0&format=json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        news_items = data.get("appnews", {}).get("newsitems", [])
                        
                        if not news_items:
                            await interaction.followup.send("Keine News gefunden.", ephemeral=True)
                            return

                        # Find the newest OFFICIAL news item
                        latest_news = None
                        for item in news_items:
                            if item.get("feedname") == "steam_community_announcements":
                                latest_news = item
                                break
                        
                        if not latest_news:
                            await interaction.followup.send("Keine offiziellen News gefunden.", ephemeral=True)
                            return

                        await self.post_news(latest_news)
                        # Update state so we don't double post next check (optional, but good practice)
                        self.save_state(latest_news.get("gid"))
                        
                        await interaction.followup.send("Neueste News wurde gepostet!", ephemeral=True)
                    else:
                        await interaction.followup.send(f"Fehler bei der Steam API: {response.status}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Fehler: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SteamNews(bot))
