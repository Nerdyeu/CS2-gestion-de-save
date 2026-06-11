# CitySync 🎮

Partage de sauvegarde **Cities Skylines 2** entre 2 joueurs via GitHub en "multijoueur asynchrone tour par tour".

## Concept

Deux amis, une ville, un tour à la fois. Quand tu termines ta session, tu envoies ta sauvegarde sur GitHub ; ton ami la récupère pour jouer à son tour.

## Prérequis

- **Windows 10/11**
- **Steam** avec Cities Skylines 2 installé
- **Compte GitHub** (gratuit, dépôt privé possible)
- **Python 3.9+** (si compilation depuis le source)

## Lancer sur mon PC (Windows)

Tu n'as **rien à installer à la main** : choisis l'option qui te convient.

### Option A — Le `.exe` tout prêt (zéro Python) ✅ recommandé

1. Va dans l'onglet **Actions** du dépôt GitHub → ouvre le dernier run **« Build Windows EXE »** (pastille verte).
2. En bas, section **Artifacts**, télécharge **`CitySync-windows`** (un `.zip`).
3. Dézippe-le → tu obtiens **`CitySync.exe`** → double-clique dessus.
4. Suis l'assistant de configuration au 1er lancement.

> Le `.exe` est reconstruit automatiquement à chaque mise à jour du code. Pas besoin de Python ni de quoi que ce soit.

### Option B — Double-clic depuis le source

1. Télécharge le projet (bouton vert **Code → Download ZIP**) et dézippe-le.
2. Double-clique sur **`Lancer-CitySync.bat`**.
   - S'il manque Python, le script propose de l'installer (via winget) ; relance le `.bat` ensuite.
   - Il installe les dépendances puis lance l'appli.

### Option C — Fabriquer le `.exe` toi-même

Double-clique sur **`Construire-EXE.bat`** : il installe PyInstaller et génère **`dist\CitySync.exe`**.

> **GitHub CLI (`gh`)** n'a pas besoin d'être installé à l'avance : l'assistant de
> configuration de l'appli s'en charge (via winget) et te guide pour la connexion.
> **Git n'est pas requis.**

### Pour les développeurs (depuis le source, à la main)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Configuration initiale

À la première exécution, un assistant te guide :

1. **Installation de GitHub CLI** (si nécessaire)
2. **Authentification GitHub** (`gh auth login`)
3. **Création du dépôt** (le premier joueur crée, le second indique juste le lien)
4. **Configuration locale** :
   - Ton pseudo (ex: "Alex")
   - Nom de la sauvegarde partagée (ex: "VilleCommune")
   - Chemin du dossier de sauvegardes (auto-détecté)
   - (Optionnel) Playset Skyve

## Mode d'emploi

### 📤 Envoyer ma partie

1. Ferme Cities Skylines 2
2. Clique sur **"Envoyer ma partie"**
3. Ton ami reçoit une notif et peut récupérer la save

### 📥 Récupérer la partie

1. Clique sur **"Récupérer la partie"**
2. La dernière save de ton ami se télécharge
3. Lance le jeu normalement

## ⚠️ Mods Skyve

**Important** : La sauvegarde ne contient PAS les mods, elle en dépend. Les deux joueurs doivent avoir **exactement le même playset Skyve**.

- Achetez les mêmes mods via [Paradox Mods](https://mods.paradoxinteractive.com/)
- Gérez vos playset dans Skyve
- Vérifiez la cohérence avant de jouer

## Stockage des données

- **Sauvegardes** : stockées dans les **GitHub Releases** (pas de commit, pas de limite LFS)
- **État du jeu** : dans `state.json` (léger, texte)
- **Historique** : listes des releases (auto-purgé après 7 jours)

## Sécurité

- Chaque envoi crée une **sauvegarde de secours locale** automatiquement
- Détecte si la save locale a changé depuis la dernière synchro
- Refuse d'agir si CS2 est ouvert
- Authentification GitHub sécurisée

## Compilation en .exe

Si tu veux packager toi-même :

```bash
pip install PyInstaller
python build_exe.py
# Le .exe sera dans ./dist/CitySync.exe
```

## Configuration du dépôt entre 2 joueurs

### Joueur 1 (créateur)

1. Lance CitySync
2. L'app propose de créer le dépôt GitHub → accepte
3. Récupère l'URL du dépôt

### Joueur 2 (collaborateur)

1. Le Joueur 1 t'ajoute comme **collaborateur** sur GitHub
2. Lance CitySync
3. Indique la même URL de dépôt que le Joueur 1
4. Tu peux jouer !

## Troubleshooting

| Problème | Solution |
|----------|----------|
| "GitHub CLI non installé" | L'app propose d'l'installer via `winget` |
| "Non authentifié" | Lance `gh auth login` dans Terminal |
| "Aucune save trouvée" | Vérifie le chemin du dossier, crée une save dans le jeu |
| "Cities2.exe est ouvert" | Ferme le jeu et réessaye |
| "Save reçue ne marche pas" | Vous n'avez pas le même playset Skyve → synchronisez les mods |

## Structure du code

```
citysync/
  ├── config_manager.py    # Gestion config locale
  ├── cs2_manager.py       # Logique sauvegardes CS2
  ├── github_manager.py    # Logique GitHub (releases, state.json)
  ├── setup_wizard.py      # Assistant config initiale
  └── main_app.py          # Interface principale
main.py                     # Point d'entrée
build_exe.py               # Script PyInstaller
```

## Licence

MIT - Open source, modifiable librement.

## Feedback

Bugs, suggestions ? Ouvre une [Issue](https://github.com/nerdyeu/cs2-gestion-de-save/issues) sur GitHub.

---

**Bon jeu! 🏙️**
