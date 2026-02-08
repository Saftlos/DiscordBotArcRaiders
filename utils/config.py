import json
import os

CONFIG_FILE = "config.json"

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return {} # Should not happen as we created it
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving config: {e}")

    def get_role_id(self, role_key: str):
        return self.config.get("roles", {}).get(role_key)

    def get_channel_id(self, channel_key: str):
        return self.config.get("channels", {}).get(channel_key)
    
    def get_role_ids_list(self, permission_key: str):
        """Returns a list of role IDs allowed for a specific action"""
        # 1. Get list of role keys (e.g. ["admin", "supervisor"])
        allowed_keys = self.config.get("permissions", {}).get(permission_key, [])
        # 2. Map keys to IDs
        ids = []
        roles = self.config.get("roles", {})
        for key in allowed_keys:
            if key in roles:
                ids.append(roles[key])
        return ids
