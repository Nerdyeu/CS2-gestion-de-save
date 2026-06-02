import os
import json
from pathlib import Path


class ConfigManager:
    """Gère la configuration locale de CitySync (%APPDATA%\\CitySync\\config.json)."""

    # %APPDATA% existe sur Windows. Fallback sur le home si absent (dev/tests).
    CONFIG_DIR = Path(os.getenv("APPDATA") or Path.home()) / "CitySync"
    CONFIG_FILE = CONFIG_DIR / "config.json"

    def __init__(self):
        self.config = {}
        self._ensure_config_dir()
        self._load_config()

    def _ensure_config_dir(self):
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, OSError):
                # Config corrompue : on repart d'une config vide plutôt que de planter.
                self.config = {}

    def save(self):
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    def is_configured(self):
        """Vrai si les champs indispensables sont renseignés."""
        required = ['player_name', 'save_name', 'github_repo', 'saves_folder']
        return all(self.config.get(k) for k in required)
