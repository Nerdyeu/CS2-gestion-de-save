import customtkinter as ctk
from threading import Thread

from .config_manager import ConfigManager
from .github_manager import GitHubManager
from .cs2_manager import CS2Manager
from .ui_thread import ThreadSafeUIMixin


class SetupWizard(ThreadSafeUIMixin, ctk.CTkToplevel):
    """Assistant de configuration initiale (fenêtre fille de l'app principale)."""

    def __init__(self, master=None):
        super().__init__(master)
        self.title("CitySync - Configuration initiale")
        self.geometry("520x620")
        self.resizable(False, False)

        # File d'UI thread-safe (démarrée sur le thread principal).
        self._init_ui_queue()

        self.config_manager = ConfigManager()

        # Valeurs persistées entre les étapes (les widgets, eux, sont détruits
        # à chaque changement d'étape, donc on ne s'appuie jamais sur eux).
        self.values = {}
        for key in ['github_repo', 'player_name', 'save_name',
                    'saves_folder', 'skyve_playset_path']:
            val = self.config_manager.get(key)
            if val:
                self.values[key] = val
        if not self.values.get('saves_folder'):
            detected = CS2Manager.get_saves_folder()
            if detected:
                self.values['saves_folder'] = detected

        # Widget d'entrée de l'étape courante (pour capture avant navigation).
        self._entry = None
        self._entry_key = None

        self.current_step = 0
        self.steps = [
            self.step_github_cli,
            self.step_github_auth,
            self.step_github_repo,
            self.step_player_name,
            self.step_save_name,
            self.step_saves_folder,
            self.step_skyve_playset,
            self.step_done,
        ]

        self.build_ui()
        self.show_step(0)

        # Fenêtre modale par-dessus l'app principale.
        self.after(200, self._safe_grab)

    def _safe_grab(self):
        try:
            self.grab_set()
        except Exception:
            pass

    # ------------------------------------------------------------------- UI
    def build_ui(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(self.main_frame, text="", font=("Arial", 16, "bold"))
        self.title_label.pack(pady=10)

        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, pady=10)

        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(fill="x", pady=10)

        self.back_btn = ctk.CTkButton(self.button_frame, text="Retour",
                                      command=self.prev_step, width=100)
        self.back_btn.pack(side="left", padx=5)

        self.next_btn = ctk.CTkButton(self.button_frame, text="Suivant",
                                      command=self.next_step, width=100)
        self.next_btn.pack(side="right", padx=5)

    def clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _make_entry(self, key, placeholder=""):
        """Crée un champ, le pré-remplit depuis self.values et l'enregistre pour capture."""
        entry = ctk.CTkEntry(self.content_frame, placeholder_text=placeholder)
        entry.pack(pady=10, fill="x")
        if self.values.get(key):
            entry.insert(0, self.values[key])
        self._entry = entry
        self._entry_key = key
        return entry

    def _capture(self):
        """Sauvegarde la valeur du champ courant AVANT de détruire les widgets."""
        if self._entry_key and self._entry is not None:
            try:
                self.values[self._entry_key] = self._entry.get()
            except Exception:
                pass

    # --------------------------------------------------------------- navigation
    def show_step(self, step_idx):
        self._entry = None
        self._entry_key = None
        self.current_step = step_idx
        self.steps[step_idx]()
        self.back_btn.configure(state="disabled" if step_idx == 0 else "normal")
        self.next_btn.configure(
            state="disabled" if step_idx == len(self.steps) - 1 else "normal"
        )

    def next_step(self):
        self._capture()
        if self.current_step < len(self.steps) - 1:
            self.show_step(self.current_step + 1)

    def prev_step(self):
        self._capture()
        if self.current_step > 0:
            self.show_step(self.current_step - 1)

    # ------------------------------------------------------------------ étapes
    def step_github_cli(self):
        self.clear_content()
        self.title_label.configure(text="1. GitHub CLI")

        label = ctk.CTkLabel(self.content_frame, text="Vérification de GitHub CLI...",
                             wraplength=420)
        label.pack(pady=20)
        status = ctk.CTkLabel(self.content_frame, text="", wraplength=420)
        status.pack(pady=5)

        def work():
            gh = GitHubManager("")
            if gh.is_gh_installed():
                self.post(lambda: label.configure(text="✓ GitHub CLI est déjà installé"))
                return
            self.post(lambda: label.configure(
                text="GitHub CLI absent. Installation via winget (une console va s'ouvrir)..."))
            ok = gh.install_gh()
            if ok:
                self.post(lambda: status.configure(
                    text="✓ Installé. IMPORTANT : ferme et relance CitySync\n"
                         "pour que 'gh' soit reconnu.", text_color="orange"))
            else:
                self.post(lambda: status.configure(
                    text="✗ Échec. Installe manuellement :\nwinget install --id GitHub.cli",
                    text_color="red"))

        Thread(target=work, daemon=True).start()

    def step_github_auth(self):
        self.clear_content()
        self.title_label.configure(text="2. Connexion GitHub")

        label = ctk.CTkLabel(self.content_frame, text="Vérification de l'authentification...",
                             wraplength=420)
        label.pack(pady=20)

        def add_login_button():
            # Création ET pack du widget sur le thread principal (sûr).
            btn = ctk.CTkButton(self.content_frame, text="Se connecter à GitHub",
                                command=lambda: GitHubManager("").auth_login())
            btn.pack(pady=10)

        def work():
            gh = GitHubManager("")
            if gh.is_authenticated():
                self.post(lambda: label.configure(text="✓ Vous êtes déjà connecté à GitHub"))
            else:
                self.post(lambda: label.configure(
                    text="Non connecté. Cliquez sur le bouton : une console s'ouvre,\n"
                         "suivez les instructions, puis revenez ici et cliquez 'Suivant'."))
                self.post(add_login_button)

        Thread(target=work, daemon=True).start()

    def step_github_repo(self):
        self.clear_content()
        self.title_label.configure(text="3. Dépôt GitHub")

        ctk.CTkLabel(self.content_frame,
                     text="Dépôt partagé (format owner/repo).\n"
                          "Le 2e joueur indique EXACTEMENT le même dépôt\n"
                          "(le propriétaire doit l'ajouter comme collaborateur).",
                     wraplength=420).pack(pady=10)
        self._make_entry('github_repo', "ex: monpseudo/citysync-save")

        # Bouton de création de dépôt privé (pour le 1er joueur).
        info = ctk.CTkLabel(self.content_frame, text="", wraplength=420)
        info.pack(pady=5)

        def create_repo():
            self._capture()
            repo = self.values.get('github_repo', '').strip()
            if not repo:
                info.configure(text="Renseigne d'abord owner/repo.", text_color="orange")
                return
            info.configure(text="Création en cours...", text_color="gray")

            def work():
                gh = GitHubManager(repo)
                if gh.repo_exists():
                    self.post(lambda: info.configure(
                        text="✓ Ce dépôt existe déjà et est accessible.", text_color="green"))
                    return
                ok = gh.create_repo(private=True)
                if ok:
                    GitHubManager(repo).create_initial_state(
                        self.values.get('player_name', 'Joueur'))
                    self.post(lambda: info.configure(
                        text="✓ Dépôt privé créé.", text_color="green"))
                else:
                    self.post(lambda: info.configure(
                        text="✗ Création impossible (déjà pris ? non connecté ?).",
                        text_color="red"))
            Thread(target=work, daemon=True).start()

        ctk.CTkButton(self.content_frame, text="Créer ce dépôt en privé",
                      command=create_repo).pack(pady=5)

    def step_player_name(self):
        self.clear_content()
        self.title_label.configure(text="4. Votre pseudo")
        ctk.CTkLabel(self.content_frame, text="Pseudo (sert à savoir qui a le tour) :",
                     wraplength=420).pack(pady=10)
        self._make_entry('player_name', "ex: Alex")

    def step_save_name(self):
        self.clear_content()
        self.title_label.configure(text="5. Nom de la sauvegarde")
        ctk.CTkLabel(self.content_frame,
                     text="Nom EXACT de la sauvegarde partagée (identique des 2 côtés) :",
                     wraplength=420).pack(pady=10)
        self._make_entry('save_name', "ex: VilleCommune")

    def step_saves_folder(self):
        self.clear_content()
        self.title_label.configure(text="6. Dossier des sauvegardes")
        detected = self.values.get('saves_folder') or CS2Manager.get_saves_folder()
        ctk.CTkLabel(self.content_frame,
                     text=f"Dossier détecté :\n{detected or 'Non trouvé — saisis-le à la main'}",
                     wraplength=420).pack(pady=10)
        self._make_entry('saves_folder', r"...\Saves\<SteamID>")

    def step_skyve_playset(self):
        self.clear_content()
        self.title_label.configure(text="7. Playset Skyve (optionnel)")
        ctk.CTkLabel(self.content_frame,
                     text="Chemin du fichier playset Skyve à joindre aux envois (optionnel).\n"
                          "Laisse vide si tu ne veux pas le synchroniser.",
                     wraplength=420).pack(pady=10)
        self._make_entry('skyve_playset_path', "Optionnel")

    def step_done(self):
        self.clear_content()
        self.title_label.configure(text="Terminé !")

        # Toutes les valeurs ont déjà été capturées via next_step. On enregistre.
        for key, val in self.values.items():
            self.config_manager.set(key, val)

        ctk.CTkLabel(self.content_frame, text="✓ Configuration enregistrée",
                     text_color="green", font=("Arial", 14)).pack(pady=15)

        state_status = ctk.CTkLabel(self.content_frame, text="Initialisation du dépôt...",
                                    text_color="gray", wraplength=420)
        state_status.pack(pady=5)

        ctk.CTkLabel(self.content_frame,
                     text="Rappel : les 2 joueurs doivent avoir EXACTEMENT\n"
                          "le même playset Skyve, sinon la save plante.",
                     text_color="orange", wraplength=420, font=("Arial", 11)).pack(pady=10)

        ctk.CTkButton(self.content_frame, text="Fermer et démarrer",
                      command=self.destroy).pack(pady=10)

        def work():
            repo = self.values.get('github_repo', '')
            player = self.values.get('player_name', 'Joueur')
            gh = GitHubManager(repo)
            try:
                if gh.repo_exists():
                    created = gh.create_initial_state(player)
                    msg = ("✓ state.json prêt sur le dépôt" if created
                           else "⚠️ state.json non créé (droits ?)")
                    color = "green" if created else "orange"
                else:
                    msg = "⚠️ Dépôt inaccessible — vérifie l'étape 3 et tes droits."
                    color = "orange"
            except Exception:
                msg = "⚠️ Initialisation impossible (réseau ?)."
                color = "orange"
            self.post(lambda: state_status.configure(text=msg, text_color=color))

        Thread(target=work, daemon=True).start()
