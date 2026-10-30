# Arc Raiders Discord Bot

Ein deutscher Community-Bot für Arc Raiders: Spiel-Infos per Slash-Command, Live-Event-Timer pro Map,
automatisch übersetzte Steam-News und ein Moderationssystem mit Strafakten.

## Funktionen

**Spiel-Infos**
- `/arcs`: Gegner-Datenbank mit deutschen Namen, Schwachstellen, Taktiken und Live-Loot
- `/item`, `/quest`, `/trader`, `/map`: Items, Quests, Händler-Inventar und Map-Punkte aus der [MetaForge API](https://metaforge.app)
- `/spielerzahl`: aktuelle Spielerzahl über die Steam API
- `/help`: Übersicht aller Befehle

**Automatisch**
- **Event-Timer**: ein Kanal pro Map, alle 30 Minuten aktualisiert. Das Emoji des laufenden Events steht im Kanalnamen (`🟥◽dam`)
- **Steam-News**: neue offizielle Ankündigungen werden erkannt, von Steam-BBCode in Discord-Markdown umgewandelt und mit DeepL übersetzt. Ein Glossar (`data/glossary.json`) verhindert, dass Spielbegriffe wie „Stash“ übersetzt werden

**Moderation**
- `/mute` (mit Dauer wie `30m`, `2d`), `/unmute`, `/kick`, `/ban`, `/modlogs`, `/modhelp`
- Jede Strafe erzeugt eine **Strafakte** im Log-Kanal. Per Antwort darauf lassen sich Notizen, Beweisbilder, Grund und Dauer nachtragen
- Rechte pro Aktion über Rollen in `config.json`. Niemand kann Mitglieder mit gleicher oder höherer Rolle bestrafen
- Mutes laufen automatisch ab, auch nach einem Neustart

**Admin**
- `/update`: holt die neueste Version von GitHub und startet über systemd neu
- `/refresh_boards`, `/sync`, `/rules`, `/force_news`

## Einrichtung

1. **Python 3.10+** installieren
2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```
3. `.env.example` nach `.env` kopieren und ausfüllen (`DISCORD_TOKEN` ist Pflicht, `DEEPL_API_KEY` optional)
4. In `config.json` die Kanal- und Rollen-IDs des eigenen Servers eintragen
5. Im [Discord Developer Portal](https://discord.com/developers/applications) den **Message Content Intent** aktivieren (wird für die Strafakten-Antworten gebraucht)
6. Starten:
   ```bash
   python main.py
   ```

### Dauerbetrieb auf dem Raspberry Pi

`start.sh` legt beim ersten Start ein venv an. Für den Autostart liegt `arcraiders.service` bei:

```bash
sudo cp arcraiders.service /etc/systemd/system/
sudo systemctl enable --now arcraiders
```

Pfad und Benutzer in der Service-Datei vorher anpassen.

## Konfiguration (`config.json`)

| Bereich | Inhalt |
|---|---|
| `channels` | `strafakte`, `news`, `rules`, `event_category` |
| `event_channels` | Map-Name → Kanal-ID der Event-Timer. Fehlt eine Map, legt der Bot den Kanal selbst an |
| `roles` | `muted`, `news_ping` und die Team-Rollen |
| `permissions` | welche Rollen `mute`, `unmute`, `kick`, `ban` und `force_news` dürfen |

## Projektstruktur

```
main.py              Startpunkt, lädt alle Cogs
cogs/                ein Modul pro Themenbereich (general, news, moderation, ...)
utils/api_client.py  MetaForge-API-Client mit gemeinsamer HTTP-Session
utils/arc_data.py    deutsche ARC-Texte und Taktiken
utils/config.py      Zugriff auf config.json
data/glossary.json   Begriffe, die DeepL nicht übersetzen soll
assets/              Map- und ARC-Bilder, Logo
```

Moderationsdaten (`data/mutes.json`, `data/history.json`) enthalten Nutzerdaten und sind von Git ausgeschlossen.
