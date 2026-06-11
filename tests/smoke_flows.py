"""Test bout-en-bout des flux Envoyer/Récupérer (threads reels, GitHub simule)."""
import os, sys, time, json, tempfile, zipfile

TMP = tempfile.mkdtemp(prefix="citysync_home_")
os.environ["HOME"] = TMP
os.environ.pop("APPDATA", None)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from citysync import github_manager as gm
from citysync import cs2_manager as cm
from citysync import main_app as ma

cm.CS2Manager.is_game_running = staticmethod(lambda: False)

# --- Dossier de saves factice avec fichier principal + annexe
SAVES = tempfile.mkdtemp(prefix="saves_")
for n in ["VilleCommune.cok", "VilleCommune.cok.cid"]:
    open(os.path.join(SAVES, n), "wb").write(b"DATA" * 1000)

created_tags = []
pushed_states = []

class FakeGH:
    def __init__(self, repo): self.repo = repo
    def is_authenticated(self): return True
    def repo_exists(self): return True
    def is_gh_installed(self): return True
    def get_state(self): return {"holder": "Alex", "latest_release": "save-OLD",
                                 "updated_at": "2026-06-01T10:00:00", "updated_by": "Alex"}
    def get_latest_release_info(self): return {"tag": "save-OLD", "published": None, "size": 4000}
    # --- conflit pilote par la variable de classe
    latest = "save-OLD"
    def get_latest_release(self): return FakeGH.latest
    def create_release(self, tag, asset, playset=None):
        created_tags.append(tag); assert os.path.exists(asset); return True
    def set_state(self, state): pushed_states.append(state); return True
    def delete_old_releases(self, days=7): return None
    def download_release_asset(self, tag, output_path):
        with zipfile.ZipFile(output_path, "w") as z:
            z.writestr("VilleCommune.cok", b"FROM_FRIEND")
        return True

gm.GitHubManager = FakeGH
ma.GitHubManager = FakeGH

# Config valide -> pas de wizard
from citysync.config_manager import ConfigManager
cfg = ConfigManager()
for k, v in {"player_name": "Sam", "save_name": "VilleCommune",
             "github_repo": "test/repo", "saves_folder": SAVES,
             "last_synced_release": "save-OLD", "last_synced_at": time.time()}.items():
    cfg.set(k, v)

# Auto-repond OUI aux dialogues de conflit
import tkinter.messagebox as mb
asked = []
mb.askyesno = lambda title, message, **k: (asked.append(title), True)[1]

app = ma.MainApp()

def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        app.update_idletasks(); app.update(); time.sleep(0.02)

def log_text():
    return app.log_text.get("1.0", "end")

errors = []
pump(1.0)

# ---------- 1) ENVOI sans conflit (latest == last_synced) ----------
FakeGH.latest = "save-OLD"
app.on_send_click()
pump(2.5)
lt = log_text()
if "Envoi terminé" not in lt: errors.append("envoi: pas de message de fin\n" + lt)
if not created_tags: errors.append("envoi: aucune release creee")
new_tag = created_tags[-1] if created_tags else None
if app.config_manager.get("last_synced_release") != new_tag:
    errors.append(f"envoi: last_synced_release pas maj ({new_tag})")
if not pushed_states or pushed_states[-1]["holder"] != "Sam":
    errors.append("envoi: state.json pas pousse avec holder=Sam")
print(f"  [ENVOI] tag={new_tag} | holder pousse={pushed_states[-1]['holder']} | conflit demande={len(asked)}")

# ---------- 2) ENVOI avec conflit (latest != last_synced) -> dialogue ----------
FakeGH.latest = "save-AMI-PLUS-RECENT"
before = len(asked)
app.on_send_click()
pump(2.5)
if len(asked) <= before: errors.append("conflit: dialogue confirmer/annuler non declenche")
print(f"  [CONFLIT] dialogue declenche={len(asked) > before}")

# ---------- 3) RECUPERATION ----------
app.state_data = {"holder": "Sam"}  # je detiens le tour
app.config_manager.set("last_synced_at", time.time())  # rien de non envoye
app.on_receive_click()
pump(2.5)
lt = log_text()
if "Récupération terminée" not in lt: errors.append("recup: pas de message de fin\n" + lt)
extracted = os.path.join(SAVES, "VilleCommune.cok")
if open(extracted, "rb").read() != b"FROM_FRIEND":
    errors.append("recup: fichier non remplace par la version distante")
print(f"  [RECUP] fichier importe OK | backups crees={os.path.isdir(os.path.join(SAVES, '.citysync_backup'))}")

app.destroy()
if errors:
    print("\nECHEC:"); [print("  -", e) for e in errors]; sys.exit(1)
print("\nOK [flows] — envoi, conflit et recuperation fonctionnent")
