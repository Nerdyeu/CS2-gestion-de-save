import os
import subprocess
import tempfile
import shutil
import zipfile
from pathlib import Path
from datetime import datetime


# Drapeau Windows pour ne PAS faire clignoter de console quand on lance tasklist
# depuis un .exe compilé en mode --windowed.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class CS2Manager:
    """Gère les sauvegardes Cities Skylines 2 sur le disque local."""

    # %USERPROFILE% existe sur Windows. Fallback home pour les tests hors Windows.
    BASE_SAVES_PATH = (
        Path(os.getenv("USERPROFILE") or Path.home())
        / "AppData" / "LocalLow" / "Colossal Order" / "Cities Skylines II" / "Saves"
    )

    # Dossier de backup interne ignoré par la détection de saves.
    BACKUP_DIR_NAME = ".citysync_backup"

    @staticmethod
    def get_steam_id():
        """Détecte automatiquement le SteamID (sous-dossier numérique le plus récent)."""
        if not CS2Manager.BASE_SAVES_PATH.exists():
            return None

        steam_dirs = [
            d for d in CS2Manager.BASE_SAVES_PATH.iterdir()
            if d.is_dir() and d.name.isdigit()
        ]

        if not steam_dirs:
            return None

        if len(steam_dirs) == 1:
            return steam_dirs[0].name

        # Plusieurs comptes : on prend le dossier le plus récemment modifié.
        most_recent = max(steam_dirs, key=lambda x: x.stat().st_mtime)
        return most_recent.name

    @staticmethod
    def get_saves_folder():
        """Retourne le chemin du dossier de saves du SteamID local, ou None."""
        steam_id = CS2Manager.get_steam_id()
        if steam_id:
            return str(CS2Manager.BASE_SAVES_PATH / steam_id)
        return None

    @staticmethod
    def find_save_files(saves_folder, save_name):
        """Liste tous les FICHIERS correspondant à la save (fichier principal + annexes).

        On ne code pas l'extension en dur : on prend le fichier nommé exactement
        `save_name` et tous ceux qui commencent par `save_name.` (ex: .cok, .cok.cid).
        Cela évite d'attraper par erreur "VilleNeuve" quand la save est "Ville".
        """
        folder = Path(saves_folder)
        if not folder.exists():
            return []

        matching = []
        for f in folder.iterdir():
            if not f.is_file():
                continue  # on ignore les sous-dossiers (dont le backup)
            if f.name == save_name or f.name.startswith(save_name + "."):
                matching.append(f)

        return matching

    @staticmethod
    def get_save_size(saves_folder, save_name):
        """Taille totale (octets) des fichiers de la save locale."""
        total = 0
        for f in CS2Manager.find_save_files(saves_folder, save_name):
            try:
                total += f.stat().st_size
            except OSError:
                pass
        return total

    @staticmethod
    def get_latest_save_mtime(saves_folder, save_name):
        """Date de modif (epoch) du fichier de save le plus récent, ou 0 si aucun."""
        files = CS2Manager.find_save_files(saves_folder, save_name)
        if not files:
            return 0
        return max(f.stat().st_mtime for f in files)

    @staticmethod
    def backup_save(saves_folder, save_name):
        """Copie de secours horodatée. On n'écrase jamais un backup précédent."""
        backup_root = Path(saves_folder) / CS2Manager.BACKUP_DIR_NAME
        backup_dir = backup_root / datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)

        for f in CS2Manager.find_save_files(saves_folder, save_name):
            shutil.copy2(f, backup_dir / f.name)

        return str(backup_dir)

    @staticmethod
    def zip_save(saves_folder, save_name):
        """Zippe tous les fichiers de la save et renvoie le chemin du .zip temporaire."""
        save_files = CS2Manager.find_save_files(saves_folder, save_name)

        if not save_files:
            raise FileNotFoundError(f"Aucune save trouvée : {save_name}")

        # IMPORTANT (Windows) : on récupère un chemin puis on ferme le handle
        # AVANT d'ouvrir le ZIP, sinon PermissionError (fichier déjà ouvert).
        fd, zip_path = tempfile.mkstemp(suffix='.zip', prefix='citysync_')
        os.close(fd)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in save_files:
                zf.write(f, arcname=f.name)

        return zip_path

    @staticmethod
    def unzip_save(zip_path, saves_folder):
        """Dézippe la save dans le dossier du SteamID local."""
        Path(saves_folder).mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(saves_folder)

    @staticmethod
    def is_game_running():
        """Vrai si Cities2.exe tourne (refus d'agir pendant le jeu)."""
        try:
            result = subprocess.run(
                ['tasklist'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=_NO_WINDOW,
            )
            return 'Cities2.exe' in result.stdout
        except Exception:
            return False
