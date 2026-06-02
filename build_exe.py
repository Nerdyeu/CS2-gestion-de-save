#!/usr/bin/env python3
"""
Script de compilation de CitySync en .exe avec PyInstaller.
Usage: python build_exe.py
"""

import PyInstaller.__main__
import sys

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--windowed',
    '--name=CitySync',
    '--icon=citysync/assets/icon.ico' if False else '',  # Ajouter un icon plus tard si souhaité
    '--add-data=citysync:citysync',
    '--collect-all=customtkinter',
    '--collect-all=pillow',
    '--hidden-import=customtkinter',
    '--hidden-import=PIL',
    '--distpath=dist',
    '--buildpath=build',
    '--specpath=.',
    '--clean',
])
