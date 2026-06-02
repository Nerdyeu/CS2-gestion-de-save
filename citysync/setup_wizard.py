import customtkinter as ctk
from pathlib import Path
from .config_manager import ConfigManager
from .github_manager import GitHubManager
from .cs2_manager import CS2Manager


# Importer ici pour éviter les imports circulaires
def get_github_manager(repo):
    return GitHubManager(repo)


class SetupWizard(ctk.CTk):
    """Assistant de configuration initial."""

    def __init__(self):
        super().__init__()
        self.title("CitySync - Configuration initiale")
        self.geometry("500x600")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")

        self.config_manager = ConfigManager()
        self.github_manager = None
        self.current_step = 0
        self.steps = [
            self.step_github_cli,
            self.step_github_auth,
            self.step_github_repo,
            self.step_player_name,
            self.step_save_name,
            self.step_saves_folder,
            self.step_skyve_playset,
            self.step_done
        ]

        self.build_ui()
        self.show_step(0)

    def build_ui(self):
        """Construit l'UI de base."""
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(self.main_frame, text="", font=("Arial", 16, "bold"))
        self.title_label.pack(pady=10)

        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, pady=10)

        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", pady=10)

        self.back_btn = ctk.CTkButton(self.button_frame, text="Retour", command=self.prev_step, width=100)
        self.back_btn.pack(side="left", padx=5)

        self.next_btn = ctk.CTkButton(self.button_frame, text="Suivant", command=self.next_step, width=100)
        self.next_btn.pack(side="right", padx=5)

    def clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def show_step(self, step_idx):
        self.current_step = step_idx
        self.steps[step_idx]()
        self.back_btn.configure(state="disabled" if step_idx == 0 else "normal")
        self.next_btn.configure(state="disabled" if step_idx == len(self.steps) - 1 else "normal")

    def next_step(self):
        if self.current_step < len(self.steps) - 1:
            self.show_step(self.current_step + 1)

    def prev_step(self):
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    def step_github_cli(self):
        self.clear_content()
        self.title_label.configure(text="GitHub CLI")

        label = ctk.CTkLabel(self.content_frame, text="Vérification de GitHub CLI...", wraplength=400)
        label.pack(pady=20)

        gh_mgr = GitHubManager("")
        if gh_mgr.is_gh_installed():
            label.configure(text="✓ GitHub CLI est installé")
            status_label = ctk.CTkLabel(self.content_frame, text="", text_color="green")
            status_label.pack()
        else:
            label.configure(text="GitHub CLI n'est pas installé.\nInstallation en cours...")
            status_label = ctk.CTkLabel(self.content_frame, text="", text_color="orange")
            status_label.pack()

            if gh_mgr.install_gh():
                status_label.configure(text="✓ Installé avec succès", text_color="green")
            else:
                status_label.configure(text="✗ Erreur lors de l'installation", text_color="red")

    def step_github_auth(self):
        self.clear_content()
        self.title_label.configure(text="Authentification GitHub")

        label = ctk.CTkLabel(self.content_frame, text="Vérification de l'authentification...", wraplength=400)
        label.pack(pady=20)

        gh_mgr = GitHubManager("")
        if gh_mgr.is_authenticated():
            label.configure(text="✓ Vous êtes déjà authentifié")
        else:
            label.configure(text="Non authentifié. Cliquez sur 'Suivant' pour vous connecter.")
            login_btn = ctk.CTkButton(self.content_frame, text="Ouvrir la connexion GitHub", command=gh_mgr.auth_login)
            login_btn.pack(pady=10)

    def step_github_repo(self):
        self.clear_content()
        self.title_label.configure(text="Dépôt GitHub")

        label = ctk.CTkLabel(self.content_frame, text="Entrez le dépôt GitHub (owner/repo):", wraplength=400)
        label.pack(pady=10)

        self.repo_entry = ctk.CTkEntry(self.content_frame, placeholder_text="ex: monpseudo/citysync-save")
        self.repo_entry.pack(pady=10, fill="x")

        if self.config_manager.get("github_repo"):
            self.repo_entry.insert(0, self.config_manager.get("github_repo"))

    def step_player_name(self):
        self.clear_content()
        self.title_label.configure(text="Votre pseudo")

        label = ctk.CTkLabel(self.content_frame, text="Quel est votre pseudo?", wraplength=400)
        label.pack(pady=10)

        self.player_entry = ctk.CTkEntry(self.content_frame, placeholder_text="ex: Alex")
        self.player_entry.pack(pady=10, fill="x")

        if self.config_manager.get("player_name"):
            self.player_entry.insert(0, self.config_manager.get("player_name"))

    def step_save_name(self):
        self.clear_content()
        self.title_label.configure(text="Nom de la sauvegarde")

        label = ctk.CTkLabel(self.content_frame, text="Nom de la sauvegarde partagée:", wraplength=400)
        label.pack(pady=10)

        self.save_entry = ctk.CTkEntry(self.content_frame, placeholder_text="ex: VilleCommune")
        self.save_entry.pack(pady=10, fill="x")

        if self.config_manager.get("save_name"):
            self.save_entry.insert(0, self.config_manager.get("save_name"))

    def step_saves_folder(self):
        self.clear_content()
        self.title_label.configure(text="Dossier des sauvegardes")

        detected_folder = CS2Manager.get_saves_folder()

        label = ctk.CTkLabel(
            self.content_frame,
            text=f"Dossier détecté:\n{detected_folder or 'Non trouvé'}",
            wraplength=400
        )
        label.pack(pady=10)

        self.saves_folder_entry = ctk.CTkEntry(self.content_frame)
        self.saves_folder_entry.pack(pady=10, fill="x")

        if detected_folder:
            self.saves_folder_entry.insert(0, detected_folder)
        elif self.config_manager.get("saves_folder"):
            self.saves_folder_entry.insert(0, self.config_manager.get("saves_folder"))

    def step_skyve_playset(self):
        self.clear_content()
        self.title_label.configure(text="Playset Skyve (optionnel)")

        label = ctk.CTkLabel(
            self.content_frame,
            text="Chemin du playset Skyve (optionnel, pour synchroniser les mods):",
            wraplength=400
        )
        label.pack(pady=10)

        self.skyve_entry = ctk.CTkEntry(self.content_frame, placeholder_text="Laisser vide si non utilisé")
        self.skyve_entry.pack(pady=10, fill="x")

        if self.config_manager.get("skyve_playset_path"):
            self.skyve_entry.insert(0, self.config_manager.get("skyve_playset_path"))

    def step_done(self):
        self.clear_content()
        self.title_label.configure(text="Configuration terminée!")

        # Sauvegarder la config
        if self.current_step == len(self.steps) - 1:
            self.config_manager.set("github_repo", self.repo_entry.get())
            self.config_manager.set("player_name", self.player_entry.get())
            self.config_manager.set("save_name", self.save_entry.get())
            self.config_manager.set("saves_folder", self.saves_folder_entry.get())
            self.config_manager.set("skyve_playset_path", self.skyve_entry.get())

            # Créer state.json initial si nécessaire
            repo = self.repo_entry.get()
            player_name = self.player_entry.get()
            gh_mgr = get_github_manager(repo)

            try:
                if gh_mgr.repo_exists():
                    existing_state = gh_mgr.get_state()
                    if not existing_state:
                        gh_mgr.create_initial_state(player_name)
            except:
                pass

        label = ctk.CTkLabel(self.content_frame, text="✓ CitySync est prêt!", text_color="green", font=("Arial", 14))
        label.pack(pady=20)

        info_label = ctk.CTkLabel(
            self.content_frame,
            text="Rappel: synchronisez les mods Skyve avec votre ami!",
            text_color="gray",
            wraplength=400,
            font=("Arial", 10)
        )
        info_label.pack(pady=5)

        close_btn = ctk.CTkButton(self.content_frame, text="Fermer et démarrer", command=self.quit)
        close_btn.pack(pady=10)


if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
