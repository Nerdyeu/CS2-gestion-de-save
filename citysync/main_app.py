import os
import time
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from threading import Thread, Event

import customtkinter as ctk
from tkinter import messagebox

from .config_manager import ConfigManager
from .github_manager import GitHubManager
from .cs2_manager import CS2Manager
from .setup_wizard import SetupWizard


def _fmt_size(num_bytes):
    """Formate une taille d'octets en Ko/Mo/Go lisible."""
    if not num_bytes:
        return "—"
    size = float(num_bytes)
    for unit in ['o', 'Ko', 'Mo', 'Go']:
        if size < 1024 or unit == 'Go':
            return f"{size:.0f} {unit}" if unit == 'o' else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Go"


def _fmt_date(iso_str):
    """Formate une date ISO en JJ/MM/AAAA HH:MM, ou '—'."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso_str


class MainApp(ctk.CTk):
    """Fenêtre principale CitySync : 2 boutons (Envoyer / Récupérer)."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("CitySync")
        self.geometry("720x640")
        self.resizable(False, False)

        self.config_manager = ConfigManager()
        self.github_manager = None
        self.state_data = {}

        if not self.config_manager.is_configured():
            self.open_setup_wizard()
            if not self.config_manager.is_configured():
                # L'utilisateur a fermé le wizard sans finir : on quitte proprement.
                self.after(100, self.destroy)
                return

        # Jamais None une fois configuré (évite un clic trop rapide sur un manager absent).
        self.github_manager = GitHubManager(self.config_manager.get("github_repo", ""))
        self.setup_ui()
        self.refresh_status()

    # --------------------------------------------------------------- wizard
    def open_setup_wizard(self):
        """Affiche l'assistant de configuration (fenêtre fille, racine unique)."""
        self.withdraw()
        wizard = SetupWizard(self)
        self.wait_window(wizard)
        self.config_manager._load_config()
        if self.config_manager.is_configured():
            self.deiconify()

    # ------------------------------------------------------------------- UI
    def setup_ui(self):
        save_name = self.config_manager.get("save_name", "?")
        player_name = self.config_manager.get("player_name", "?")

        # --- En-tête : nom de save + indicateurs d'état
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=20, pady=(20, 10))

        ctk.CTkLabel(info_frame, text=f"🏙️  {save_name}",
                     font=("Arial", 20, "bold")).pack(pady=(10, 4))

        status_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        status_frame.pack(pady=6)
        self.github_status = ctk.CTkLabel(status_frame, text="GitHub : …", text_color="gray")
        self.github_status.grid(row=0, column=0, padx=12)
        self.repo_status = ctk.CTkLabel(status_frame, text="Dépôt : …", text_color="gray")
        self.repo_status.grid(row=0, column=1, padx=12)
        self.game_status = ctk.CTkLabel(status_frame, text="Jeu : …", text_color="gray")
        self.game_status.grid(row=0, column=2, padx=12)

        # --- Bloc tour / dernier envoi / taille
        turn_frame = ctk.CTkFrame(self)
        turn_frame.pack(fill="x", padx=20, pady=6)
        self.turn_label = ctk.CTkLabel(turn_frame, text=f"Tour actuel : {player_name}",
                                       font=("Arial", 14, "bold"))
        self.turn_label.pack(anchor="w", padx=10, pady=(8, 2))
        self.last_sync_label = ctk.CTkLabel(turn_frame, text="Dernier envoi : —",
                                            font=("Arial", 11), text_color="gray")
        self.last_sync_label.pack(anchor="w", padx=10)
        self.size_label = ctk.CTkLabel(turn_frame, text="Taille dernière save : —",
                                       font=("Arial", 11), text_color="gray")
        self.size_label.pack(anchor="w", padx=10, pady=(0, 8))

        # --- Les 2 gros boutons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=10)
        self.send_btn = ctk.CTkButton(button_frame, text="📤  Envoyer ma partie",
                                      font=("Arial", 15, "bold"), height=64,
                                      command=self.on_send_click)
        self.send_btn.pack(fill="x", pady=6)
        self.receive_btn = ctk.CTkButton(button_frame, text="📥  Récupérer la partie",
                                         font=("Arial", 15, "bold"), height=64,
                                         command=self.on_receive_click)
        self.receive_btn.pack(fill="x", pady=6)

        # --- Barre de progression (indéterminée pendant les opérations)
        self.progress = ctk.CTkProgressBar(self, mode="indeterminate")
        self.progress.pack(fill="x", padx=20, pady=(4, 0))
        self.progress.set(0)

        # --- Rappel Skyve bien visible
        ctk.CTkLabel(self,
                     text="⚠️  Assurez-vous d'avoir le MÊME playset Skyve des deux côtés.",
                     text_color="orange", font=("Arial", 12, "bold")).pack(pady=(8, 2))

        # --- Journal
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(6, 6))
        self.log_text = ctk.CTkTextbox(log_frame, height=140)
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        # --- Réglages
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkButton(bottom, text="⚙️  Réglages", width=120,
                      command=self.open_settings).pack(side="right")

        self.log("Bienvenue dans CitySync.")

    # ----------------------------------------------- helpers thread-safe UI
    def log(self, message):
        self.after(0, self._log_impl, message)

    def _log_impl(self, message):
        self.log_text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")

    def _set(self, widget, **kwargs):
        self.after(0, lambda: widget.configure(**kwargs))

    def _busy(self, on):
        self.after(0, self._busy_impl, on)

    def _busy_impl(self, on):
        if on:
            self.progress.start()
            self.send_btn.configure(state="disabled")
            self.receive_btn.configure(state="disabled")
        else:
            self.progress.stop()
            self.progress.set(0)
            self.send_btn.configure(state="normal")
            self.receive_btn.configure(state="normal")

    def _ask(self, title, message):
        """Boîte de confirmation oui/non, marshalée sur le thread principal.

        Appelée depuis les threads de travail ; bloque jusqu'à la réponse.
        """
        ev = Event()
        result = {}

        def show():
            result['v'] = messagebox.askyesno(title, message, parent=self)
            ev.set()

        self.after(0, show)
        ev.wait()
        return result.get('v', False)

    # --------------------------------------------------------------- statut
    def refresh_status(self):
        Thread(target=self._refresh_status_thread, daemon=True).start()

    def _refresh_status_thread(self):
        repo = self.config_manager.get("github_repo", "")
        self.github_manager = GitHubManager(repo)

        authed = self.github_manager.is_authenticated()
        self._set(self.github_status,
                  text="GitHub : ✓" if authed else "GitHub : ✗",
                  text_color="green" if authed else "red")

        repo_ok = authed and self.github_manager.repo_exists()
        self._set(self.repo_status,
                  text="Dépôt : ✓" if repo_ok else "Dépôt : ✗",
                  text_color="green" if repo_ok else "red")

        if repo_ok:
            self._fetch_remote_state()

        running = CS2Manager.is_game_running()
        self._set(self.game_status,
                  text="Jeu : EN COURS" if running else "Jeu : fermé ✓",
                  text_color="red" if running else "green")

    def _fetch_remote_state(self):
        try:
            state = self.github_manager.get_state()
            if state:
                self.state_data = state
                self._set(self.turn_label,
                          text=f"Tour actuel : {state.get('holder', '?')}")
                self._set(self.last_sync_label,
                          text=f"Dernier envoi : {_fmt_date(state.get('updated_at'))}"
                               f"  (par {state.get('updated_by', '?')})")
            info = self.github_manager.get_latest_release_info()
            if info:
                self._set(self.size_label,
                          text=f"Taille dernière save : {_fmt_size(info.get('size'))}")
        except Exception:
            self.log("Impossible de lire l'état distant.")

    # ----------------------------------------------------------- clic boutons
    def on_send_click(self):
        if CS2Manager.is_game_running():
            self.log("❌ Ferme Cities Skylines 2 avant d'envoyer.")
            return
        Thread(target=self._send_save_thread, daemon=True).start()

    def on_receive_click(self):
        if CS2Manager.is_game_running():
            self.log("❌ Ferme Cities Skylines 2 avant de récupérer.")
            return
        Thread(target=self._receive_save_thread, daemon=True).start()

    # ------------------------------------------------------------------ envoi
    def _send_save_thread(self):
        self._busy(True)
        zip_path = None
        try:
            saves_folder = self.config_manager.get("saves_folder")
            save_name = self.config_manager.get("save_name")
            player_name = self.config_manager.get("player_name")

            if not saves_folder or not Path(saves_folder).exists():
                self.log("❌ Dossier des sauvegardes introuvable (voir Réglages).")
                return

            if not CS2Manager.find_save_files(saves_folder, save_name):
                self.log(f"❌ Aucune save nommée « {save_name} » trouvée.")
                return

            # Détection de conflit : l'ami a-t-il joué depuis ma dernière synchro ?
            self.log("Vérification de l'état distant…")
            latest_remote = self.github_manager.get_latest_release()
            last_synced = self.config_manager.get("last_synced_release")

            if latest_remote and latest_remote != last_synced:
                if not self._ask(
                    "Conflit de tour",
                    "Ton ami a joué depuis ta dernière synchro.\n"
                    "Envoyer maintenant risque d'écraser sa version.\n\n"
                    "Envoyer quand même ? (Annuler = récupère d'abord)",
                ):
                    self.log("Envoi annulé.")
                    return

            self.log("Copie de secours locale…")
            CS2Manager.backup_save(saves_folder, save_name)

            self.log("Compression de la sauvegarde…")
            zip_path = CS2Manager.zip_save(saves_folder, save_name)

            tag = f"save-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            self.log(f"Création de la release {tag} et envoi de l'asset…")
            skyve_path = self.config_manager.get("skyve_playset_path")
            if not self.github_manager.create_release(tag, zip_path, skyve_path or None):
                self.log("❌ Échec de la création de la release.")
                return
            self.log(f"✓ Release {tag} publiée.")

            # Mise à jour du state.json distant (logique de tour).
            state = {
                "holder": player_name,
                "latest_release": tag,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "updated_by": player_name,
            }
            if self.github_manager.set_state(state):
                self.state_data = state
                self.log("✓ state.json mis à jour.")
            else:
                self.log("⚠️ Release OK mais state.json non mis à jour (vérifie les droits).")

            # Mémorise localement : je suis à jour et je reste détenteur.
            self.config_manager.set("last_synced_release", tag)
            self.config_manager.set("last_synced_at", time.time())

            self.log("Purge des releases de plus de 7 jours…")
            self.github_manager.delete_old_releases(days=7)

            self.log("✅ Envoi terminé ! Tu peux rejouer et renvoyer autant que tu veux.")
            self.refresh_status()

        except Exception as e:
            self.log(f"❌ Erreur : {e}")
        finally:
            if zip_path:
                try:
                    os.unlink(zip_path)
                except OSError:
                    pass
            self._busy(False)

    # -------------------------------------------------------------- récupération
    def _receive_save_thread(self):
        self._busy(True)
        tmpdir = None
        try:
            saves_folder = self.config_manager.get("saves_folder")
            save_name = self.config_manager.get("save_name")
            player_name = self.config_manager.get("player_name")

            if not saves_folder:
                self.log("❌ Dossier des sauvegardes non configuré (voir Réglages).")
                return

            # Heuristique : si je détiens le tour ET que ma save locale a été
            # modifiée après ma dernière synchro, je risque d'écraser du jeu non envoyé.
            last_at = self.config_manager.get("last_synced_at", 0) or 0
            mtime = CS2Manager.get_latest_save_mtime(saves_folder, save_name)
            holder_is_me = self.state_data.get("holder") == player_name
            if holder_is_me and mtime > last_at + 5:
                if not self._ask(
                    "Partie non envoyée",
                    "Ta save locale a changé depuis ton dernier envoi.\n"
                    "La récupération va l'écraser localement.\n\n"
                    "Continuer quand même ?",
                ):
                    self.log("Récupération annulée.")
                    return

            latest_tag = self.github_manager.get_latest_release()
            if not latest_tag:
                self.log("❌ Aucune sauvegarde disponible sur le dépôt.")
                return

            self.log("Copie de secours locale…")
            CS2Manager.backup_save(saves_folder, save_name)

            self.log(f"Téléchargement de {latest_tag}…")
            tmpdir = tempfile.mkdtemp(prefix="citysync_dl_")
            zip_path = os.path.join(tmpdir, "save.zip")
            if not self.github_manager.download_release_asset(latest_tag, zip_path):
                self.log("❌ Échec du téléchargement.")
                return

            self.log("Extraction dans le dossier local…")
            CS2Manager.unzip_save(zip_path, saves_folder)

            # Je prends le tour : on le reflète localement ET sur le dépôt.
            self.config_manager.set("last_synced_release", latest_tag)
            self.config_manager.set("last_synced_at", time.time())
            new_state = dict(self.state_data)
            new_state["holder"] = player_name
            if self.github_manager.set_state(new_state):
                self.state_data = new_state

            self.log("✅ Récupération terminée ! Lance le jeu, c'est ton tour.")
            self.refresh_status()

        except Exception as e:
            self.log(f"❌ Erreur : {e}")
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
            self._busy(False)

    # ------------------------------------------------------------------ réglages
    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Réglages")
        win.geometry("520x460")
        win.transient(self)

        fields = [
            ("Pseudo :", "player_name", "ex: Alex"),
            ("Dossier des sauvegardes :", "saves_folder", r"...\Saves\<SteamID>"),
            ("Nom de la sauvegarde :", "save_name", "ex: VilleCommune"),
            ("Dépôt GitHub (owner/repo) :", "github_repo", "ex: pseudo/citysync-save"),
            ("Playset Skyve (optionnel) :", "skyve_playset_path", "Optionnel"),
        ]
        entries = {}
        for label, key, placeholder in fields:
            ctk.CTkLabel(win, text=label, font=("Arial", 12)).pack(anchor="w", padx=20, pady=(12, 2))
            ent = ctk.CTkEntry(win, placeholder_text=placeholder)
            ent.pack(fill="x", padx=20)
            ent.insert(0, self.config_manager.get(key, "") or "")
            entries[key] = ent

        def save_settings():
            for key, ent in entries.items():
                self.config_manager.set(key, ent.get())
            self.github_manager = GitHubManager(self.config_manager.get("github_repo", ""))
            win.destroy()
            self.refresh_status()
            self.log("Réglages enregistrés.")

        ctk.CTkButton(win, text="Enregistrer", command=save_settings).pack(pady=20)


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
