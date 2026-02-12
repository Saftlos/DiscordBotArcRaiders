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
        
        print(f"📖 Glossar: {len(terms)} Begriffe aus glossary.json geladen.")

        # Prepare Glossary Entries (Source = Target for DNT)
        # DeepL glossary is CASE-SENSITIVE, so we need multiple variants
        entries = {}
        for term in terms:
            entries[term] = term                 # Original: "Shared Watch" -> "Shared Watch"
            entries[term.upper()] = term         # UPPERCASE: "SHARED WATCH" -> "Shared Watch"
            entries[term.lower()] = term         # lowercase: "shared watch" -> "Shared Watch"
        
        print(f"📖 Glossar: {len(entries)} Einträge (mit Case-Varianten) vorbereitet.")
        glossary_name = "ArcRaiders_Glossary"
        
        try:
            # 1. List existing glossaries
            existing_glossaries = self.translator.list_glossaries()
            print(f"📖 Glossar: {len(existing_glossaries)} existierende Glossare gefunden.")
            
            # 2. Delete ALL existing glossaries (DeepL Free only allows 1!)
            for g in existing_glossaries:
                print(f"  - Lösche Glossar: {g.name} ({g.entry_count} Einträge, ID: {g.glossary_id})")
                try:
                    self.translator.delete_glossary(g)
                    print(f"    ✅ Gelöscht.")
                except Exception as e:
                    print(f"    ❌ Fehler beim Löschen: {e}")

            # 3. Create new glossary
            try:
                self.glossary = self.translator.create_glossary(
                    glossary_name,
                    source_lang="EN",
                    target_lang="DE",
                    entries=entries
                )
                print(f"✅ DeepL Glossar erstellt: {self.glossary.name} ({self.glossary.entry_count} Einträge, ID: {self.glossary.glossary_id})")
            except Exception as e:
                print(f"❌ Fehler beim Erstellen des Glossars: {type(e).__name__}: {e}")
            
        except Exception as e:
            print(f"❌ Fehler beim Verwalten des DeepL Glossars: {type(e).__name__}: {e}")

    async def translate_text(self, text):
        if not self.translator: return text
        if not text or len(text.strip()) == 0: return text
        
        def _translate_sync():
            try:
                # Split into lines and translate each non-empty line separately
                # This preserves ALL line breaks perfectly (they never enter DeepL)
                lines = text.split('\n')
                # Skip empty lines AND image placeholders ({{IMG:N}}) — they must not be sent to DeepL
                non_empty = [(i, line) for i, line in enumerate(lines) 
                             if line.strip() and not re.match(r'^\{\{IMG:\d+\}\}$', line.strip())]
                
                if not non_empty:
                    return text
                
                # Strip markdown formatting before translation so glossary can match
                texts_to_translate = []
                line_formats = []  # (prefix, suffix) to re-apply after translation
                for _, line in non_empty:
                    stripped = line
                    prefix = ''
                    suffix = ''
                    
                    # Pattern: • **bold text** (bullet + bold header)
                    if stripped.startswith('• **') and stripped.endswith('**'):
                        prefix = '• **'
                        suffix = '**'
                        stripped = stripped[4:-2]
                    # Pattern: **bold text** (standalone header)
                    elif stripped.startswith('**') and stripped.endswith('**'):
                        prefix = '**'
                        suffix = '**'
                        stripped = stripped[2:-2]
                    # Pattern: • text (plain bullet)
                    elif stripped.startswith('• '):
                        prefix = '• '
                        stripped = stripped[2:]
                    
                    texts_to_translate.append(stripped)
                    line_formats.append((prefix, suffix))
                
                # DeepL accepts a list — one API call for all lines
                glossary_to_use = self.glossary if self.glossary else None
                if glossary_to_use:
                    print(f"📖 Übersetze {len(texts_to_translate)} Zeilen MIT Glossar (ID: {glossary_to_use.glossary_id})")
                else:
                    print(f"⚠️ Übersetze {len(texts_to_translate)} Zeilen OHNE Glossar (self.glossary is None!)")
                
                results = self.translator.translate_text(
                    texts_to_translate,
                    source_lang="EN",
                    target_lang="DE",
                    glossary=glossary_to_use
                )
                
                # Reassemble with formatting and translations in the correct positions
                translated_lines = list(lines)
                for (idx, _), result, (prefix, suffix) in zip(non_empty, results, line_formats):
                    translated_lines[idx] = f'{prefix}{result.text}{suffix}'
                
                return '\n'.join(translated_lines)
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

    async def cog_unload(self):
        self.check_news.cancel()
        if hasattr(self, '_session') and self._session and not self._session.closed:
            await self._session.close()

    def bbcode_to_markdown(self, raw_text):
        """Converts Steam BBCode directly to Discord Markdown. No HTML intermediate."""
        text = raw_text
        
        # 1. Replace image tags with inline placeholders {{IMG:N}}
        image_urls = []
        def img_placeholder(match):
            # Extract URL from whichever group matched
            url = match.group(1) if match.group(1) else ''
            url = url.replace("{STEAM_CLAN_IMAGE}", "https://clan.cloudflare.steamstatic.com/images")
            if url:
                idx = len(image_urls)
                image_urls.append(url)
                return f'\n{{{{IMG:{idx}}}}}\n'
            return ''
        
        # Match all image patterns and replace with placeholders
        text = re.sub(r'\[img\]\{STEAM_CLAN_IMAGE\}([^\[]+)\[/img\]', img_placeholder, text)
        text = re.sub(r'\[img\](https?://[^\[]+)\[/img\]', img_placeholder, text)
        text = re.sub(r'\[img src="([^"]+)"\]', img_placeholder, text)
        # Remove any remaining unmatched image tags
        text = re.sub(r'\[img[^\]]*\].*?\[/img\]', '', text, flags=re.DOTALL)
        text = re.sub(r'\[previewyoutube[^\]]*\].*?\[/previewyoutube\]', '', text, flags=re.DOTALL)
        
        # 3. URLs -> markdown links (before we strip other tags)
        def fix_url(match):
            url = match.group(1).replace('"', '').strip()
            content = match.group(2).strip()
            return f'[{content}]({url})'
        text = re.sub(r'\[url=([^\]]+)\](.*?)\[/url\]', fix_url, text, flags=re.DOTALL)
        
        # 4. Headers -> **bold** with newlines
        for tag in ['h1', 'h2', 'h3']:
            def header_replace(match, t=tag):
                content = match.group(1).strip()
                return f'\n\n**{content}**\n'
            text = re.sub(rf'\[{tag}\](.*?)\[/{tag}\]', header_replace, text, flags=re.DOTALL)
        
        # 5. Bold / Italic / Underline
        text = re.sub(r'\[b\](.*?)\[/b\]', r'**\1**', text, flags=re.DOTALL)
        text = re.sub(r'\[i\](.*?)\[/i\]', r'*\1*', text, flags=re.DOTALL)
        text = re.sub(r'\[u\](.*?)\[/u\]', r'__\1__', text, flags=re.DOTALL)
        
        # 6. Lists -> bullet points
        # Remove list container tags
        text = re.sub(r'\[/?list\]', '', text)
        text = re.sub(r'\[/?olist\]', '', text)
        
        # Remove optional closing [/*] tags
        text = text.replace('[/*]', '')
        
        # Convert [*] to bullet character
        # Each [*] starts a new bullet — content follows until next [*] or structure
        text = re.sub(r'\[\*\]\s*', '\n• ', text)
        
        # 7. Paragraph and line breaks
        text = re.sub(r'\[/?p\]', '\n', text)
        text = re.sub(r'\[/?br\]', '\n', text)
        
        # 8. Remove any remaining BBCode tags
        text = re.sub(r'\[/?[a-zA-Z][^\]]*\]', '', text)
        
        # 9. Unescape HTML entities from raw text
        text = html.unescape(text)
        
        # 10. Cleanup whitespace
        text = re.sub(r'[ \t]+\n', '\n', text)       # Trailing whitespace on lines
        text = re.sub(r'\n[ \t]+\n', '\n\n', text)   # Lines with only whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)        # Max 2 consecutive newlines
        # Fix bullets that have extra newlines before the text
        text = re.sub(r'•\s*\n\s*', '• ', text)       # Bullet followed by newline -> single line
        
        return text.strip(), image_urls

    async def get_session(self):
        """Returns a cached aiohttp session, creating one if needed."""
        if not hasattr(self, '_session') or self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_latest_news(self, count=5):
        """Holt die neuesten offiziellen News über die Steam Events API.
        Gibt bei count=1 ein einzelnes Dict zurück, bei count>1 eine Liste.
        Dict-Format: {gid, title, contents, url, header_image}
        """
        events_url = (
            f"https://store.steampowered.com/events/ajaxgetpartnereventspageable/"
            f"?clan_accountid=0&appid={self.app_id}&offset=0&count={count}&l=english"
        )
        
        try:
            session = await self.get_session()
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
                    clan_id = ann.get("clanid", "")
                    news_url = f"https://store.steampowered.com/news/app/{self.app_id}/view/{gid}"
                    
                    # Extract header/banner image from jsondata
                    header_image = None
                    try:
                        jsondata = json.loads(event.get("jsondata", "{}"))
                        title_images = jsondata.get("localized_title_image", [])
                        if isinstance(title_images, list) and title_images:
                            # Index 0 = english
                            img_hash = title_images[0]
                            if img_hash and clan_id:
                                header_image = f"https://clan.cloudflare.steamstatic.com/images/{clan_id}/{img_hash}"
                    except Exception:
                        pass
                    
                    results.append({
                        "gid": gid,
                        "title": title,
                        "contents": body,
                        "url": news_url,
                        "header_image": header_image,
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

        # Parse content and extract images (with inline {{IMG:N}} placeholders)
        contents, image_urls = self.bbcode_to_markdown(news_item.get("contents", ""))
        
        # Translate Content (already in Discord Markdown)
        translated_contents = await self.translate_text(contents)
        
        # Get URL and header image
        url = news_item.get("url")
        header_image_url = news_item.get("header_image")
        
        # Header
        header = ""
        if ping_role:
             header += "<@&1466986718229041204>\n\n"
        header += f"**{translated_title}**\n\n"
        
        full_text = header + translated_contents
        
        # Footer
        footer = ""
        if url:
            footer += f"\n\n[Original Artikel auf Steam](<{url}>)"
        footer += "\n_(Automatisch übersetzt mit DeepL)_"
        full_text += footer
        
        try:
            session = await self.get_session()
            
            # 1. Download header banner image
            header_file = None
            if header_image_url:
                try:
                    async with session.get(header_image_url) as resp:
                        if resp.status == 200:
                            from io import BytesIO
                            header_data = await resp.read()
                            header_file = discord.File(BytesIO(header_data), filename="header.jpg")
                except Exception as e:
                    print(f"Fehler beim Herunterladen des Header-Banners: {e}")
            
            # 2. Download ALL inline images upfront
            downloaded_images = {}
            for i, img_url in enumerate(image_urls[:10]):
                try:
                    async with session.get(img_url) as resp:
                        if resp.status == 200:
                            downloaded_images[i] = await resp.read()
                except Exception as e:
                    print(f"Fehler beim Herunterladen des Bildes {img_url}: {e}")

            # 3. Send header banner first (if available)
            if header_file:
                await channel.send(file=header_file)

            # 4. Split text at image placeholders into segments
            segments = []
            parts = re.split(r'\{\{IMG:(\d+)\}\}', full_text)
            for j, part in enumerate(parts):
                if j % 2 == 0:
                    cleaned = part.strip()
                    if cleaned:
                        segments.append(('text', cleaned))
                else:
                    segments.append(('image', int(part)))
            
            # 5. Send segments in order
            for seg_type, seg_content in segments:
                if seg_type == 'text':
                    text_remaining = seg_content
                    while text_remaining:
                        if len(text_remaining) <= 1900:
                            await channel.send(content=text_remaining)
                            break
                        else:
                            split_idx = text_remaining.rfind('\n', 0, 1900)
                            if split_idx == -1: split_idx = text_remaining.rfind(' ', 0, 1900)
                            if split_idx == -1: split_idx = 1900
                            await channel.send(content=text_remaining[:split_idx])
                            text_remaining = text_remaining[split_idx:].lstrip()
                elif seg_type == 'image':
                    img_idx = seg_content
                    if img_idx in downloaded_images:
                        from io import BytesIO
                        file_obj = discord.File(BytesIO(downloaded_images[img_idx]), filename=f"image_{img_idx}.jpg")
                        await channel.send(file=file_obj)
            
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


async def setup(bot):
    await bot.add_cog(SteamNews(bot))
