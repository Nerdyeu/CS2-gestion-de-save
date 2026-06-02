import subprocess
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
import base64


class GitHubManager:
    """Gère les opérations GitHub (releases, state.json)."""

    def __init__(self, repo):
        self.repo = repo

    def is_gh_installed(self):
        """Vérifie si GitHub CLI est installé."""
        try:
            subprocess.run(['gh', '--version'], capture_output=True, check=True, timeout=5)
            return True
        except:
            return False

    def is_authenticated(self):
        """Vérifie si gh est authentifié."""
        try:
            subprocess.run(['gh', 'auth', 'status'], capture_output=True, check=True, timeout=5)
            return True
        except:
            return False

    def install_gh(self):
        """Installe GitHub CLI via winget."""
        try:
            subprocess.run(['winget', 'install', '--id', 'GitHub.cli', '-e'], timeout=300, check=False)
            return True
        except:
            return False

    def auth_login(self):
        """Lance gh auth login."""
        try:
            subprocess.run(['gh', 'auth', 'login'], check=False)
            return True
        except:
            return False

    def repo_exists(self):
        """Vérifie si le dépôt existe et est accessible."""
        try:
            subprocess.run(
                ['gh', 'repo', 'view', self.repo],
                capture_output=True,
                check=True,
                timeout=10
            )
            return True
        except:
            return False

    def create_repo(self, private=True):
        """Crée un nouveau dépôt."""
        try:
            cmd = ['gh', 'repo', 'create', self.repo, '--private' if private else '--public']
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)

            # Initialiser le dépôt avec state.json
            subprocess.run(['git', 'clone', f'https://github.com/{self.repo}.git', '/tmp/citysync_init'],
                          capture_output=True, timeout=30, check=False)

            return True
        except:
            return False

    def get_state(self):
        """Récupère le state.json distant."""
        try:
            result = subprocess.run(
                ['gh', 'api', f'repos/{self.repo}/contents/state.json'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            data = json.loads(result.stdout)
            content = base64.b64decode(data['content']).decode('utf-8')
            return json.loads(content)
        except:
            return None

    def create_initial_state(self, player_name):
        """Crée un state.json initial."""
        state = {
            "holder": player_name,
            "latest_release": None,
            "updated_at": datetime.now().isoformat(),
            "updated_by": player_name
        }
        return self._commit_file('state.json', json.dumps(state, indent=2))

    def update_state(self, state_dict):
        """Met à jour le state.json distant via git."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Clone
                subprocess.run(
                    ['git', 'clone', f'https://github.com/{self.repo}.git', tmpdir],
                    capture_output=True,
                    timeout=30,
                    check=False
                )

                # Écrire state.json
                state_file = Path(tmpdir) / 'state.json'
                with open(state_file, 'w') as f:
                    json.dump(state_dict, f, indent=2)

                # Commit
                subprocess.run(
                    ['git', 'config', 'user.email', 'citysync@local'],
                    cwd=tmpdir,
                    capture_output=True
                )
                subprocess.run(
                    ['git', 'config', 'user.name', 'CitySync'],
                    cwd=tmpdir,
                    capture_output=True
                )
                subprocess.run(['git', 'add', 'state.json'], cwd=tmpdir, capture_output=True)
                subprocess.run(
                    ['git', 'commit', '-m', 'Update save state'],
                    cwd=tmpdir,
                    capture_output=True
                )
                subprocess.run(['git', 'push'], cwd=tmpdir, capture_output=True, timeout=30)

            return True
        except:
            return False

    def _commit_file(self, filename, content):
        """Commit un fichier dans le dépôt."""
        try:
            result = subprocess.run(
                ['gh', 'api', f'repos/{self.repo}/contents/{filename}', '-f', 'message=Initial commit', '-f', f'content={content}'],
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        except:
            return False

    def create_release(self, tag, asset_path, save_playset_path=None):
        """Crée une release et attache l'asset."""
        try:
            cmd = [
                'gh', 'release', 'create', tag,
                asset_path,
                '--repo', self.repo,
                '--notes', f'Save created at {datetime.now().isoformat()}'
            ]

            if save_playset_path and Path(save_playset_path).exists():
                cmd.append(save_playset_path)

            subprocess.run(cmd, check=True, timeout=300)
            return True
        except Exception as e:
            return False

    def get_latest_release(self):
        """Récupère le tag de la dernière release."""
        try:
            result = subprocess.run(
                ['gh', 'release', 'list', '-R', self.repo, '-L', '1', '--json', 'tagName'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                return data[0].get('tagName')
            return None
        except:
            return None

    def download_release_asset(self, tag, output_path):
        """Télécharge le premier asset d'une release."""
        try:
            # Lister les assets
            result = subprocess.run(
                ['gh', 'release', 'view', tag, '-R', self.repo, '--json', 'assets'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            data = json.loads(result.stdout)

            if data.get('assets') and len(data['assets']) > 0:
                asset_name = data['assets'][0]['name']

                # Télécharger
                subprocess.run(
                    ['gh', 'release', 'download', tag, '-R', self.repo, '-p', asset_name, '-D', str(Path(output_path).parent)],
                    check=True,
                    timeout=300
                )

                # Renommer
                downloaded = Path(output_path).parent / asset_name
                downloaded.rename(output_path)
                return True
        except Exception as e:
            pass

        return False

    def delete_old_releases(self, days=7):
        """Supprime les releases de plus de N jours."""
        try:
            result = subprocess.run(
                ['gh', 'release', 'list', '-R', self.repo, '--json', 'tagName,createdAt'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )

            releases = json.loads(result.stdout)
            cutoff = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(days=days)

            for release in releases:
                try:
                    created = datetime.fromisoformat(release['createdAt'])
                    if created < cutoff:
                        subprocess.run(
                            ['gh', 'release', 'delete', release['tagName'], '-R', self.repo, '--yes'],
                            capture_output=True,
                            timeout=10
                        )
                except:
                    pass
        except:
            pass
