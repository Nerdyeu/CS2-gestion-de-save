# Guide de développement CitySync

## Environnement

```bash
# Créer un virtualenv
python -m venv venv
venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

## Exécution locale

```bash
python main.py
```

## Compilation en .exe

```bash
# Installer PyInstaller si ce n'est pas déjà fait
pip install PyInstaller

# Compiler
python build_exe.py

# L'exécutable sera dans ./dist/CitySync.exe
```

## Structure du code

### `config_manager.py`
Gestion de la configuration locale stockée dans `%APPDATA%\CitySync\config.json`.
Responsable de persister les préférences utilisateur.

### `cs2_manager.py`
Interface avec le système fichier de Cities Skylines 2.
- Détection du dossier SteamID
- Localisation des sauvegardes
- Compression/décompression ZIP
- Backup de sécurité
- Vérification que le jeu est fermé

### `github_manager.py`
Interface avec GitHub API via `gh` CLI.
- Authentification et vérification de repo
- Création/récupération/suppression de releases
- Gestion du fichier `state.json`
- Téléchargement des assets

### `setup_wizard.py`
Assistant de configuration initiale en CustomTkinter.
- Vérification/installation de GitHub CLI
- Authentification GitHub
- Création/sélection du dépôt
- Configuration des paramètres locaux

### `main_app.py`
Interface principale de l'application.
- Affichage du statut (GitHub, Jeu, Tour)
- Boutons Envoyer/Récupérer
- Journal d'événements
- Écran Réglages

## Points clés d'implémentation

### Détection du SteamID
Le chemin `%USERPROFILE%\AppData\LocalLow\Colossal Order\Cities Skylines II\Saves\<SteamID>\` contient un ou plusieurs sous-dossiers numériques.
L'app détecte automatiquement le plus récemment modifié.

### Gestion des sauvegardes
- **Ne pas** coder en dur l'extension du fichier
- Chercher tous les fichiers correspondant au nom de la save
- Inclure les fichiers annexes (métadonnées, etc.)
- Toujours zipper l'ensemble

### GitHub Releases
- Chaque envoi = 1 release avec tag horodaté (`save-YYYYMMDD-HHMMSS`)
- Asset principal = fichier ZIP de la save
- Asset secondaire optionnel = playset Skyve
- Auto-purge des releases >7 jours

### Sécurité
- Backup local automatique avant tout écrasement
- Refus d'agir si `Cities2.exe` est en cours
- Détection des conflits (avertissement si l'ami a joué)
- Pas de suppression irréversible sans backup

## Tests manuels recommandés

1. **Setup initial**
   - Vérifier que l'assistant guide correctement
   - Tester la création de dépôt
   - Vérifier la création de `config.json`

2. **Envoi simple**
   - Créer une save dans le jeu
   - Cliquer "Envoyer ma partie"
   - Vérifier que la release est créée
   - Vérifier que le state.json est mis à jour

3. **Réception simple**
   - Sur une 2e instance/pseudo
   - Cliquer "Récupérer la partie"
   - Vérifier que la save est restaurée
   - Vérifier que la save fonctionne dans le jeu

4. **Conflits**
   - Envoyer sans avoir récupéré (devrait avertir)
   - Récupérer sans avoir envoyé (devrait avertir si nécessaire)

5. **Purge des releases**
   - Créer plusieurs releases
   - Attendre ou forcer l'horodatage
   - Envoyer une nouvelle save
   - Vérifier que les releases >7j sont supprimées

## Dépannage courant

| Erreur | Cause | Solution |
|--------|-------|----------|
| "gh not found" | GitHub CLI non installé | L'app propose l'installation |
| "Not authenticated" | `gh` n'est pas connecté | Lancer `gh auth login` |
| "Repo not found" | Mauvaise URL ou pas d'accès | Vérifier l'URL et les permissions |
| "No save found" | Mauvais dossier ou nom | Vérifier config, créer une save |
| "game is running" | Cities2.exe ouvert | Fermer le jeu |

## Tests automatisés (sans écran)

L'UF se teste sous écran virtuel (Linux + Xvfb), ce qui attrape les vrais bugs
d'interface (API CustomTkinter, mises à jour de widgets depuis des threads…) :

```bash
# Sur une machine Linux avec Tk + Xvfb
python3 -m pip install customtkinter==5.2.0 pillow==10.1.0
xvfb-run -a python3 tests/smoke_ui.py main      # construit la fenetre principale
xvfb-run -a python3 tests/smoke_ui.py wizard    # parcourt tout l'assistant
xvfb-run -a python3 tests/smoke_flows.py        # flux Envoyer / Conflit / Recuperer (GitHub simule)
```

Les appels réseau/`gh`/`winget`/`tasklist` sont remplacés par des doublures :
ces tests valident l'UI et l'orchestration, pas l'intégration réelle à GitHub
(à vérifier manuellement sur Windows).

## Build automatique du .exe

Le workflow `.github/workflows/build-windows.yml` compile `CitySync.exe` sur un
runner Windows à chaque push de code. L'exécutable est récupérable dans
**Actions > (le run) > Artifacts**.

## Améliorations futures

- [ ] Interface pour gérer l'historique des releases
- [ ] Synchronisation des mods via le playset Skyve
- [ ] Support du multijoueur temps réel (via webhook)
- [ ] Intégration Discord pour notifier les joueurs
- [ ] Signature/vérification des releases
- [ ] Compression avec moteur alternatif (7z, RAR)
