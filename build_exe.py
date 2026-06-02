#!/usr/bin/env python3
"""
Compile CitySync en un .exe autonome avec PyInstaller.

Usage (sur Windows) :
    pip install -r requirements.txt
    python build_exe.py

Le résultat : dist\\CitySync.exe (double-cliquable, sans Python installé).
"""

import os
from pathlib import Path

import PyInstaller.__main__

# Séparateur de --add-data : ';' sur Windows, ':' ailleurs.
SEP = os.pathsep  # ';' sous Windows, ':' sous Linux/Mac

args = [
    'main.py',
    '--onefile',
    '--windowed',
    '--name=CitySync',
    '--noconfirm',
    '--clean',
    f'--add-data=citysync{SEP}citysync',
    '--collect-all=customtkinter',
    '--collect-all=PIL',
    '--hidden-import=customtkinter',
    '--hidden-import=PIL',
    '--distpath=dist',
    '--workpath=build',     # NB : c'est --workpath (et non --buildpath)
    '--specpath=.',
]

# Icône optionnelle : seulement si le fichier existe vraiment.
icon = Path('citysync') / 'assets' / 'icon.ico'
if icon.exists():
    args.append(f'--icon={icon}')

PyInstaller.__main__.run(args)
