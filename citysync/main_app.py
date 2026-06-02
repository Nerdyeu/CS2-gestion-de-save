import customtkinter as ctk
import os
import tempfile
import json
from pathlib import Path
from datetime import datetime
from threading import Thread

from .config_manager import ConfigManager
from .github_manager import GitHubManager
from .cs2_manager import CS2Manager
from .setup_wizard import SetupWizard


class MainApp(ctk.CTk):
    """Application principale CitySync."""

    def __init__(self):
        super().__init__()
        self.title("CitySync")
        self.geometry("700x600")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_color_scheme("blue")

        self.config_manager = ConfigManager()
        self.github_manager = None
        self.state_data = {}

        if not self.config_manager.is_configured():
            self.open_setup_wizard()
            return

        self.setup_ui()
        self.refresh_status()

    def open_setup_wizard(self):
        """Ouvre l'assistant de configuration."""
        self.withdraw()
        wizard = SetupWizard()
        self.wait_window(wizard)
        self.config_manager._load_config()

        if self.config_manager.is_configured():
            self.setup_ui()
            self.deiconify()
            self.refresh_status()
        else:
            self.quit()

    def setup_ui(self):
        """Construit l'interface."""
        # Top frame: info
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=20, pady=(20, 10))

        save_name = self.config_manager.get("save_name", "?")
        player_name = self.config_manager.get("player_name", "?")

        title = ctk.CTkLabel(
            info_frame,
            text=f"Sauvegarde: {save_name}",
            font=("Arial", 18, "bold")
        )
        title.pack()

        # Status indicators
        status_frame = ctk.CTkFrame(info_frame)
        status_frame.pack(fill="x", pady=10)

        self.github_status = ctk.CTkLabel(status_frame, text="GitHub: ...", text_color="gray")
        self.github_status.pack(side="left", padx=5)

        self.game_status = ctk.CTkLabel(status_frame, text="Jeu: fermé", text_color="green")
        self.game_status.pack(side="left", padx=5)

        # Turn info
        turn_frame = ctk.CTkFrame(self)
        turn_frame.pack(fill="x", padx=20, pady=10)

        self.turn_label = ctk.CTkLabel(
            turn_frame,
            text=f"Tour: {player_name}",
            font=("Arial", 12)
        )
        self.turn_label.pack(anchor="w")

        self.last_sync_label = ctk.CTkLabel(
            turn_frame,
            text="Dernier envoi: jamais",
            font=("Arial", 10),
            text_color="gray"
        )
        self.last_sync_label.pack(anchor="w")

        # Buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.send_btn = ctk.CTkButton(
            button_frame,
            text="📤 Envoyer ma partie",
            font=("Arial", 14, "bold"),
            command=self.send_save,
            height=60
        )
        self.send_btn.pack(fill="both", expand=True, pady=10)

        self.receive_btn = ctk.CTkButton(
            button_frame,
            text="📥 Récupérer la partie",
            font=("Arial", 14, "bold"),
            command=self.receive_save,
            height=60
        )
        self.receive_btn.pack(fill="both", expand=True, pady=10)

        # Log
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.log_text = ctk.CTkTextbox(log_frame, height=150)
        self.log_text.pack(fill="both", expand=True)

        # Settings button
        settings_btn = ctk.CTkButton(
            self,
            text="⚙️ Réglages",
            width=100,
            command=self.open_settings
        )
        settings_btn.pack(side="right", padx=20, pady=10)

    def log(self, message):
        """Ajoute un message au journal."""
        self.log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")

    def refresh_status(self):
        """Rafraîchit les indicateurs d'état."""
        Thread(target=self._refresh_status_thread, daemon=True).start()

    def _refresh_status_thread(self):
        """Détermination de l'état en arrière-plan."""
        repo = self.config_manager.get("github_repo", "")
        self.github_manager = GitHubManager(repo)

        # GitHub
        if self.github_manager.is_authenticated() and self.github_manager.repo_exists():
            self.github_status.configure(text="GitHub: ✓", text_color="green")
            self._fetch_remote_state()
        else:
            self.github_status.configure(text="GitHub: ✗", text_color="red")

        # Game
        if CS2Manager.is_game_running():
            self.game_status.configure(text="Jeu: EN COURS", text_color="red")
        else:
            self.game_status.configure(text="Jeu: fermé", text_color="green")

    def _fetch_remote_state(self):
        """Récupère l'état distant."""
        try:
            state = self.github_manager.get_state()
            if state:
                self.state_data = state
                holder = state.get("holder", "?")
                updated_at = state.get("updated_at", "?")
                self.turn_label.configure(text=f"Tour: {holder}")
                self.last_sync_label.configure(text=f"Dernier envoi: {updated_at}")
        except:
            self.log("Erreur lors de la lecture du state.json distant.")

    def send_save(self):
        """Envoie la sauvegarde."""
        if CS2Manager.is_game_running():
            self.log("❌ Impossible: Cities Skylines 2 est en cours d'exécution!")
            return

        Thread(target=self._send_save_thread, daemon=True).start()

    def _send_save_thread(self):
        """Envoi de la sauvegarde en arrière-plan."""
        try:
            self.log("Préparation de l'envoi...")

            # Config
            saves_folder = self.config_manager.get("saves_folder")
            save_name = self.config_manager.get("save_name")
            player_name = self.config_manager.get("player_name")
            repo = self.config_manager.get("github_repo")

            if not saves_folder or not Path(saves_folder).exists():
                self.log("❌ Dossier des sauvegardes non trouvé!")
                return

            # Vérifier les conflits
            latest_remote = self.github_manager.get_latest_release()
            last_synced = self.config_manager.get("last_synced_release", None)

            if latest_remote and latest_remote != last_synced:
                self.log("⚠️ Ton ami a joué depuis ta dernière synchro!")
                self.log("Récupère d'abord ou confirme l'écrasement.")
                return

            # Backup
            self.log("Création d'une sauvegarde de sécurité...")
            CS2Manager.backup_save(saves_folder, save_name)

            # Zipper
            self.log("Compression de la sauvegarde...")
            zip_path = CS2Manager.zip_save(saves_folder, save_name)

            # Release
            tag = f"save-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            self.log(f"Création de la release {tag}...")

            skyve_path = self.config_manager.get("skyve_playset_path")
            if self.github_manager.create_release(tag, zip_path, skyve_path):
                self.log(f"✓ Release créée: {tag}")
            else:
                self.log("❌ Erreur lors de la création de la release")
                return

            # Update state
            self.log("Mise à jour du state.json...")
            self.state_data = {
                "holder": player_name,
                "latest_release": tag,
                "updated_at": datetime.now().isoformat(),
                "updated_by": player_name
            }

            self.config_manager.set("last_synced_release", tag)

            # Cleanup old releases
            self.log("Nettoyage des anciennes releases (>7j)...")
            self.github_manager.delete_old_releases(days=7)

            self.log("✓ Envoi terminé avec succès!")
            self.refresh_status()

            # Cleanup
            Path(zip_path).unlink()

        except Exception as e:
            self.log(f"❌ Erreur: {str(e)}")

    def receive_save(self):
        """Récupère la sauvegarde."""
        if CS2Manager.is_game_running():
            self.log("❌ Impossible: Cities Skylines 2 est en cours d'exécution!")
            return

        Thread(target=self._receive_save_thread, daemon=True).start()

    def _receive_save_thread(self):
        """Récupération de la sauvegarde en arrière-plan."""
        try:
            self.log("Récupération de la sauvegarde...")

            # Config
            saves_folder = self.config_manager.get("saves_folder")
            save_name = self.config_manager.get("save_name")
            player_name = self.config_manager.get("player_name")

            # Vérifier si le joueur local a des changements non envoyés
            last_synced = self.config_manager.get("last_synced_release")
            if self.state_data.get("holder") == player_name and last_synced:
                save_files = CS2Manager.find_save_files(saves_folder, save_name)
                if save_files:
                    latest_file = max(save_files, key=lambda x: x.stat().st_mtime)
                    self.log("⚠️ Tu n'as pas encore envoyé ta dernière partie!")
                    self.log("La récupération va l'écraser.")
                    return

            # Backup
            self.log("Création d'une sauvegarde de sécurité...")
            CS2Manager.backup_save(saves_folder, save_name)

            # Download
            latest_tag = self.github_manager.get_latest_release()
            if not latest_tag:
                self.log("❌ Aucune release disponible!")
                return

            self.log(f"Téléchargement de {latest_tag}...")
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                if self.github_manager.download_release_asset(latest_tag, tmp.name):
                    self.log("Extraction...")
                    CS2Manager.unzip_save(tmp.name, saves_folder)
                    Path(tmp.name).unlink()
                else:
                    self.log("❌ Erreur lors du téléchargement")
                    return

            # Update local state
            self.config_manager.set("last_synced_release", latest_tag)
            self.state_data["holder"] = player_name

            self.log("✓ Récupération terminée!")
            self.refresh_status()

        except Exception as e:
            self.log(f"❌ Erreur: {str(e)}")

    def open_settings(self):
        """Ouvre l'écran de réglages."""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("Réglages")
        settings_window.geometry("500x400")

        # Pseudo
        ctk.CTkLabel(settings_window, text="Pseudo:", font=("Arial", 12)).pack(anchor="w", padx=20, pady=(20, 5))
        player_entry = ctk.CTkEntry(settings_window)
        player_entry.pack(fill="x", padx=20, pady=5)
        player_entry.insert(0, self.config_manager.get("player_name", ""))

        # Dossier saves
        ctk.CTkLabel(settings_window, text="Dossier des sauvegardes:", font=("Arial", 12)).pack(anchor="w", padx=20, pady=(20, 5))
        saves_entry = ctk.CTkEntry(settings_window)
        saves_entry.pack(fill="x", padx=20, pady=5)
        saves_entry.insert(0, self.config_manager.get("saves_folder", ""))

        # Nom save
        ctk.CTkLabel(settings_window, text="Nom de la sauvegarde:", font=("Arial", 12)).pack(anchor="w", padx=20, pady=(20, 5))
        save_entry = ctk.CTkEntry(settings_window)
        save_entry.pack(fill="x", padx=20, pady=5)
        save_entry.insert(0, self.config_manager.get("save_name", ""))

        # Dépôt
        ctk.CTkLabel(settings_window, text="Dépôt GitHub (owner/repo):", font=("Arial", 12)).pack(anchor="w", padx=20, pady=(20, 5))
        repo_entry = ctk.CTkEntry(settings_window)
        repo_entry.pack(fill="x", padx=20, pady=5)
        repo_entry.insert(0, self.config_manager.get("github_repo", ""))

        def save_settings():
            self.config_manager.set("player_name", player_entry.get())
            self.config_manager.set("saves_folder", saves_entry.get())
            self.config_manager.set("save_name", save_entry.get())
            self.config_manager.set("github_repo", repo_entry.get())

            self.github_manager = GitHubManager(repo_entry.get())
            settings_window.destroy()
            self.refresh_status()

        save_btn = ctk.CTkButton(settings_window, text="Enregistrer", command=save_settings)
        save_btn.pack(pady=20)


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
