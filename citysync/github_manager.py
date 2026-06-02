import subprocess
import json
import os
import sys
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone


IS_WINDOWS = sys.platform.startswith("win")
# Cache une console parasite pour les commandes non interactives (exe --windowed).
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# Ouvre une VRAIE console pour les commandes interactives (gh auth login, winget).
CREATE_NEW_CONSOLE = 0x00000010


def _no_window_flags():
    return CREATE_NO_WINDOW if IS_WINDOWS else 0


def _new_console_flags():
    return CREATE_NEW_CONSOLE if IS_WINDOWS else 0


def _parse_dt(value):
    """Parse une date ISO/RFC3339 GitHub (gère le suffixe 'Z')."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class GitHubManager:
    """Toutes les interactions GitHub passent par la CLI `gh` (pas de git requis)."""

    def __init__(self, repo):
        self.repo = repo

    # ----------------------------------------------------------------- helpers
    def _run(self, args, timeout=30):
        """Lance une commande non interactive, console masquée."""
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_no_window_flags(),
        )

    # ------------------------------------------------------- état de l'install
    def is_gh_installed(self):
        """Vérifie si GitHub CLI est installé."""
        try:
            r = self._run(['gh', '--version'], timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def is_authenticated(self):
        """Vérifie si `gh` est authentifié."""
        try:
            r = self._run(['gh', 'auth', 'status'], timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def install_gh(self):
        """Installe GitHub CLI via winget (console visible, bloquant).

        NB : le PATH du processus courant ne verra `gh` qu'après redémarrage
        de l'appli. L'UI doit prévenir l'utilisateur.
        """
        try:
            p = subprocess.Popen(
                [
                    'winget', 'install', '--id', 'GitHub.cli', '-e',
                    '--accept-package-agreements', '--accept-source-agreements',
                ],
                creationflags=_new_console_flags(),
            )
            p.wait(timeout=600)
            return p.returncode == 0
        except Exception:
            return False

    def auth_login(self):
        """Lance `gh auth login` dans une vraie console (interactif, non bloquant)."""
        try:
            if IS_WINDOWS:
                subprocess.Popen(['cmd', '/k', 'gh', 'auth', 'login'],
                                 creationflags=_new_console_flags())
            else:
                subprocess.Popen(['gh', 'auth', 'login'])
            return True
        except Exception:
            return False

    # ----------------------------------------------------------------- dépôt
    def repo_exists(self):
        """Vérifie que le dépôt existe et est accessible."""
        if not self.repo:
            return False
        try:
            r = self._run(['gh', 'repo', 'view', self.repo], timeout=10)
            return r.returncode == 0
        except Exception:
            return False

    def create_repo(self, private=True):
        """Crée le dépôt distant (vide). Le state.json sera créé via l'API contents."""
        try:
            cmd = ['gh', 'repo', 'create', self.repo,
                   '--private' if private else '--public']
            r = self._run(cmd, timeout=60)
            return r.returncode == 0
        except Exception:
            return False

    # ------------------------------------------------------------- state.json
    def get_state(self):
        """Lit et décode le state.json distant (ou None)."""
        try:
            r = self._run(['gh', 'api', f'repos/{self.repo}/contents/state.json'], timeout=10)
            if r.returncode != 0:
                return None
            data = json.loads(r.stdout)
            content = base64.b64decode(data['content']).decode('utf-8')
            return json.loads(content)
        except Exception:
            return None

    def _get_file_sha(self, path):
        """Récupère le SHA d'un fichier distant (nécessaire pour le mettre à jour)."""
        try:
            r = self._run(['gh', 'api', f'repos/{self.repo}/contents/{path}'], timeout=10)
            if r.returncode != 0:
                return None
            return json.loads(r.stdout).get('sha')
        except Exception:
            return None

    def set_state(self, state_dict):
        """Crée ou met à jour state.json via l'API contents (contenu en base64).

        Fonctionne aussi sur un dépôt vide : l'API crée alors la branche par défaut.
        """
        try:
            raw = json.dumps(state_dict, indent=2, ensure_ascii=False).encode('utf-8')
            content_b64 = base64.b64encode(raw).decode('ascii')

            args = [
                'gh', 'api', '--method', 'PUT',
                f'repos/{self.repo}/contents/state.json',
                '-f', 'message=CitySync: mise a jour du tour',
                '-f', f'content={content_b64}',
            ]

            # Si le fichier existe déjà, GitHub exige son SHA.
            sha = self._get_file_sha('state.json')
            if sha:
                args += ['-f', f'sha={sha}']

            r = self._run(args, timeout=30)
            return r.returncode == 0
        except Exception:
            return False

    def create_initial_state(self, player_name):
        """Crée un state.json initial s'il n'existe pas déjà."""
        if self.get_state() is not None:
            return True
        state = {
            "holder": player_name,
            "latest_release": None,
            "updated_at": datetime.now().isoformat(timespec='seconds'),
            "updated_by": player_name,
        }
        return self.set_state(state)

    # -------------------------------------------------------------- releases
    def create_release(self, tag, asset_path, save_playset_path=None):
        """Crée une release et attache la save zippée (+ playset optionnel)."""
        try:
            cmd = [
                'gh', 'release', 'create', tag,
                asset_path,
                '--repo', self.repo,
                '--title', tag,
                '--notes', f'Sauvegarde CitySync du {datetime.now().isoformat(timespec="seconds")}',
            ]
            if save_playset_path and Path(save_playset_path).exists():
                cmd.append(save_playset_path)

            # Pas de capture : upload potentiellement long, on laisse gh gérer.
            r = subprocess.run(cmd, timeout=1800, creationflags=_no_window_flags())
            return r.returncode == 0
        except Exception:
            return False

    def get_latest_release(self):
        """Tag de la dernière release, ou None."""
        try:
            r = self._run(
                ['gh', 'release', 'list', '-R', self.repo, '-L', '1', '--json', 'tagName'],
                timeout=10,
            )
            if r.returncode != 0:
                return None
            data = json.loads(r.stdout)
            if data:
                return data[0].get('tagName')
            return None
        except Exception:
            return None

    def get_latest_release_info(self):
        """Infos de la dernière release : tag, date de publication, taille de l'asset save."""
        tag = self.get_latest_release()
        if not tag:
            return None
        try:
            r = self._run(
                ['gh', 'release', 'view', tag, '-R', self.repo,
                 '--json', 'tagName,publishedAt,createdAt,assets'],
                timeout=10,
            )
            data = json.loads(r.stdout)
            asset = self._pick_save_asset(data.get('assets', []))
            return {
                'tag': data.get('tagName', tag),
                'published': data.get('publishedAt') or data.get('createdAt'),
                'size': asset.get('size', 0) if asset else 0,
            }
        except Exception:
            return {'tag': tag, 'published': None, 'size': 0}

    @staticmethod
    def _pick_save_asset(assets):
        """Choisit l'asset de save : on privilégie le .zip (le playset n'en est pas un)."""
        if not assets:
            return None
        zips = [a for a in assets if a.get('name', '').lower().endswith('.zip')]
        return zips[0] if zips else assets[0]

    def download_release_asset(self, tag, output_path):
        """Télécharge l'asset .zip de la release vers output_path (écrase si besoin)."""
        try:
            r = self._run(
                ['gh', 'release', 'view', tag, '-R', self.repo, '--json', 'assets'],
                timeout=10,
            )
            if r.returncode != 0:
                return False
            data = json.loads(r.stdout)
            asset = self._pick_save_asset(data.get('assets', []))
            if not asset:
                return False

            asset_name = asset['name']
            dest_dir = Path(output_path).parent

            dl = subprocess.run(
                ['gh', 'release', 'download', tag, '-R', self.repo,
                 '-p', asset_name, '-D', str(dest_dir), '--clobber'],
                timeout=1800,
                creationflags=_no_window_flags(),
            )
            if dl.returncode != 0:
                return False

            downloaded = dest_dir / asset_name
            # os.replace écrase la cible même si elle existe (contrairement à rename sur Windows).
            os.replace(downloaded, output_path)
            return True
        except Exception:
            return False

    def delete_old_releases(self, days=7):
        """Supprime releases ET tags de plus de N jours (garde au moins une semaine)."""
        try:
            r = self._run(
                ['gh', 'release', 'list', '-R', self.repo, '--json', 'tagName,createdAt'],
                timeout=10,
            )
            if r.returncode != 0:
                return
            releases = json.loads(r.stdout)
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            for release in releases:
                created = _parse_dt(release.get('createdAt'))
                if created and created < cutoff:
                    self._run(
                        ['gh', 'release', 'delete', release['tagName'],
                         '-R', self.repo, '--yes', '--cleanup-tag'],
                        timeout=15,
                    )
        except Exception:
            pass
