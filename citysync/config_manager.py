import os
import json
import shutil
from pathlib import Path


class ConfigManager:
    """Gère la configuration locale de CitySync."""

    CONFIG_DIR = Path(os.getenv("APPDATA")) / "CitySync"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def __init__(self):
        self.config = {}
        self._ensure_config_dir()
        self._load_config()

    def _ensure_config_dir(self):
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        if self.CONFIG_FILE.exists():
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

    def save(self):
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def is_configured(self):
        required = ['player_name', 'save_name', 'github_repo', 'saves_folder']
        return all(self.config.get(k) for k in required)
