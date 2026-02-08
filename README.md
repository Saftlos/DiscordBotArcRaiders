# Arc Raiders Discord Bot

Ein maßgeschneiderter Discord-Bot für die Arc Raiders Community mit automatischer News-Übersetzung und spielspezifischen Funktionen.

## Funktionen

- **Steam News Integration**: Ruft automatisch die neuesten Nachrichten von Steam ab.
- **DeepL Übersetzung**: Übersetzt Titel und Inhalt der Nachrichten von Englisch nach Deutsch.
- **Intelligentes Glossar**: Verwendet ein benutzerdefiniertes Glossar (`data/glossary.json`), um die Übersetzung spezifischer Spielbegriffe (z.B. "Arc Raiders", "Stash", "Speranza") zu verhindern.
- **Formatierungs-Korrekturen**: Wandelt Steam-BBCode in sauberes Markdown für Discord um.
- **Rollen- & Kanal-Verwaltung**: Konfigurierbar über `config.json`.

## Einrichtung

1.  **Python 3.10+ installieren**
2.  **Abhängigkeiten installieren**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Umgebung konfigurieren**:
    Erstelle eine `.env` Datei im Hauptverzeichnis:
    ```env
    DISCORD_TOKEN=dein_discord_bot_token
    STEAM_API_KEY=dein_steam_api_key
    ARC_RAIDERS_APP_ID=deine_app_id
    DEEPL_API_KEY=dein_deepl_api_key
    ```
4.  **Bot starten**:
    ```bash
    python main.py
    ```

## Projektstruktur

- `cogs/`: Bot-Erweiterungen (News, Moderation, etc.)
- `data/`: JSON-Daten (Glossar, Config, usw.)
- `main.py`: Startpunkt

## Hinweise

- Der Bot verwaltet DeepL-Glossare beim Start automatisch, um Quota-Limits zu vermeiden.
- Bearbeite `data/glossary.json`, um neue Begriffe hinzuzufügen, die nicht übersetzt werden sollen.
