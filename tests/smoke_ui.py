"""Smoke-test headless de l'UI CitySync (lance sous xvfb).
Usage: python smoke_ui.py [main|wizard]
"""
import os, sys, time, json, tempfile

# HOME temporaire -> ConfigManager ecrit la config ici (APPDATA absent sous Linux)
TMP = tempfile.mkdtemp(prefix="citysync_home_")
os.environ["HOME"] = TMP
os.environ.pop("APPDATA", None)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

mode = sys.argv[1] if len(sys.argv) > 1 else "main"

# --- Neutralise tout appel reseau / process externe -------------------------
from citysync import github_manager as gm
from citysync import cs2_manager as cm

cm.CS2Manager.is_game_running = staticmethod(lambda: False)

def patch_gh():
    gm.GitHubManager.is_authenticated = lambda self: True
    gm.GitHubManager.repo_exists = lambda self: True
    gm.GitHubManager.is_gh_installed = lambda self: True
    gm.GitHubManager.get_state = lambda self: {
        "holder": "Alex", "latest_release": "save-20260602-153000",
        "updated_at": "2026-06-02T15:30:00", "updated_by": "Alex"}
    gm.GitHubManager.get_latest_release_info = lambda self: {
        "tag": "save-20260602-153000", "published": "2026-06-02T15:30:00",
        "size": 137_000_000}
    gm.GitHubManager.create_initial_state = lambda self, p: True

patch_gh()

import customtkinter as ctk

errors = []

def pump(win, seconds=1.5):
    end = time.time() + seconds
    while time.time() < end:
        win.update_idletasks(); win.update()
        time.sleep(0.02)

if mode == "main":
    # Pre-ecrit une config valide pour sauter le wizard
    from citysync.config_manager import ConfigManager
    cfg = ConfigManager()
    for k, v in {"player_name": "Sam", "save_name": "VilleCommune",
                 "github_repo": "test/repo", "saves_folder": TMP}.items():
        cfg.set(k, v)

    from citysync.main_app import MainApp
    app = MainApp()
    pump(app, 1.8)  # laisse refresh_status (thread + after) s'executer
    # Verifie que les labels ont bien ete mis a jour par le thread de refresh
    checks = {
        "github": app.github_status.cget("text"),
        "repo": app.repo_status.cget("text"),
        "game": app.game_status.cget("text"),
        "turn": app.turn_label.cget("text"),
        "last": app.last_sync_label.cget("text"),
        "size": app.size_label.cget("text"),
    }
    for name, txt in checks.items():
        print(f"  label[{name}] = {txt!r}")
    if "✓" not in checks["github"]: errors.append("github status pas a jour")
    if "Alex" not in checks["turn"]: errors.append("turn label pas a jour")
    if "Mo" not in checks["size"]: errors.append("size label pas formate")
    # Exerce log / busy
    app.log("ligne de test")
    app._busy(True); pump(app, 0.3); app._busy(False); pump(app, 0.3)
    print("  send_btn state apres busy:", app.send_btn.cget("state"))
    app.destroy()

elif mode == "wizard":
    from citysync.setup_wizard import SetupWizard
    root = ctk.CTk(); root.withdraw()
    w = SetupWizard(root)
    pump(root, 0.6)
    fill = {"github_repo": "moi/citysync-save", "player_name": "Sam",
            "save_name": "VilleCommune", "saves_folder": TMP,
            "skyve_playset_path": ""}
    # Parcourt toutes les etapes en remplissant les champs presents
    for _ in range(len(w.steps) - 1):
        if getattr(w, "_entry", None) is not None and w._entry_key in fill:
            try:
                w._entry.delete(0, "end"); w._entry.insert(0, fill[w._entry_key])
            except Exception as e:
                errors.append(f"entry {w._entry_key}: {e}")
        w.next_step()
        pump(root, 0.15)
    pump(root, 0.6)
    # La config doit avoir ete ecrite a l'etape finale
    cfg_path = os.path.join(TMP, "CitySync", "config.json")
    if not os.path.exists(cfg_path):
        errors.append("config.json non cree par le wizard")
    else:
        data = json.load(open(cfg_path))
        print("  config ecrite:", json.dumps(data, ensure_ascii=False))
        for k in ["github_repo", "player_name", "save_name", "saves_folder"]:
            if data.get(k) != fill[k]:
                errors.append(f"valeur perdue: {k}={data.get(k)!r} (attendu {fill[k]!r})")
    try: w.destroy()
    except Exception: pass
    root.destroy()

if errors:
    print("ECHEC:", errors); sys.exit(1)
print(f"OK [{mode}] — aucune erreur UI")
