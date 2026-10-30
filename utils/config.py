"""
Server-specific settings (channel IDs, role IDs, permissions) from config.json.
Secrets live in .env instead, so this file can be versioned.
"""

import json
import os

CONFIG_FILE = "config.json"


class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> dict:
        if not os.path.exists(CONFIG_FILE):
            print(f"⚠️ {CONFIG_FILE} nicht gefunden, starte ohne Kanal-/Rollen-Konfiguration.")
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving config: {e}")

    def get_role_id(self, role_key: str):
        return self.config.get("roles", {}).get(role_key)

    def get_channel_id(self, channel_key: str):
        return self.config.get("channels", {}).get(channel_key)

    def get_event_channels(self) -> dict:
        """Map name -> text channel ID for the event timer boards."""
        return self.config.get("event_channels", {})

    def get_role_ids_list(self, permission_key: str) -> list[int]:
        """Role IDs allowed for an action, e.g. 'mute_allowed' -> [id of support, id of admin, ...]."""
        allowed_keys = self.config.get("permissions", {}).get(permission_key, [])
        roles = self.config.get("roles", {})
        return [roles[key] for key in allowed_keys if key in roles]
