@echo off
chcp 65001 >nul
title CitySync - construction de l'EXE
cd /d "%~dp0"

echo ===================================================
echo   Construction de CitySync.exe (autonome)
echo ===================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python n'est pas installe. Lance d'abord "Lancer-CitySync.bat".
    pause
    exit /b
)

echo Installation des dependances + PyInstaller...
py -m pip install --quiet --upgrade pip
py -m pip install --quiet -r requirements.txt
py -m pip install --quiet pyinstaller==6.1.0
if errorlevel 1 (
    echo ERREUR pendant l'installation. Voir au-dessus.
    pause
    exit /b
)

echo Compilation...
py build_exe.py
if errorlevel 1 (
    echo ERREUR pendant la compilation.
    pause
    exit /b
)

echo.
echo ===================================================
echo   Termine ! Ton executable est ici :
echo   %cd%\dist\CitySync.exe
echo ===================================================
pause
