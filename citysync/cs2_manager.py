import os
import subprocess
import tempfile
import shutil
import zipfile
from pathlib import Path
from datetime import datetime


class CS2Manager:
    """Gère les sauvegardes Cities Skylines 2."""

    BASE_SAVES_PATH = Path(os.getenv("USERPROFILE")) / "AppData" / "LocalLow" / "Colossal Order" / "Cities Skylines II" / "Saves"

    @staticmethod
    def get_steam_id():
        """Détecte automatiquement le SteamID (sous-dossier numérique)."""
        if not CS2Manager.BASE_SAVES_PATH.exists():
            return None

        steam_dirs = [d for d in CS2Manager.BASE_SAVES_PATH.iterdir() if d.is_dir() and d.name.isdigit()]

        if not steam_dirs:
            return None

        if len(steam_dirs) == 1:
            return steam_dirs[0].name

        # Si plusieurs, prendre le plus récemment modifié
        most_recent = max(steam_dirs, key=lambda x: x.stat().st_mtime)
        return most_recent.name

    @staticmethod
    def get_saves_folder():
        """Retourne le chemin du dossier des sauvegardes."""
        steam_id = CS2Manager.get_steam_id()
        if steam_id:
            return str(CS2Manager.BASE_SAVES_PATH / steam_id)
        return None

    @staticmethod
    def find_save_files(saves_folder, save_name):
        """Trouve tous les fichiers correspondant au nom de save."""
        if not Path(saves_folder).exists():
            return []

        matching = []
        for f in Path(saves_folder).iterdir():
            if f.name.startswith(save_name):
                matching.append(f)

        return matching

    @staticmethod
    def backup_save(saves_folder, save_name):
        """Crée une sauvegarde de sécurité locale."""
        backup_dir = Path(saves_folder) / ".citysync_backup"
        backup_dir.mkdir(exist_ok=True)

        save_files = CS2Manager.find_save_files(saves_folder, save_name)
        for f in save_files:
            shutil.copy2(f, backup_dir / f.name)

        return str(backup_dir)

    @staticmethod
    def zip_save(saves_folder, save_name):
        """Zippe la sauvegarde."""
        save_files = CS2Manager.find_save_files(saves_folder, save_name)

        if not save_files:
            raise FileNotFoundError(f"Aucune save trouvée : {save_name}")

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                for f in save_files:
                    zf.write(f, arcname=f.name)
            return tmp.name

    @staticmethod
    def unzip_save(zip_path, saves_folder):
        """Dézippe une sauvegarde."""
        Path(saves_folder).mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(saves_folder)

    @staticmethod
    def is_game_running():
        """Vérifie si Cities2.exe est en cours."""
        try:
            result = subprocess.run(
                ['tasklist'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return 'Cities2.exe' in result.stdout
        except:
            return False
