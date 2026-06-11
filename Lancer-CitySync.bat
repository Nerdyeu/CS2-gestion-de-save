@echo off
chcp 65001 >nul
title CitySync
cd /d "%~dp0"

echo ===================================================
echo   CitySync - lancement
echo ===================================================
echo.

REM --- 1) Python present ? (lanceur "py" fourni avec Python sur Windows)
where py >nul 2>nul
if errorlevel 1 (
    echo Python n'est pas installe. Installation via winget...
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo.
    echo ---------------------------------------------------
    echo  Python vient d'etre installe.
    echo  FERME cette fenetre puis relance "Lancer-CitySync.bat".
    echo ---------------------------------------------------
    pause
    exit /b
)

REM --- 2) Dependances (rapide si deja installees)
echo Verification des dependances...
py -m pip install --quiet --upgrade pip
py -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERREUR pendant l'installation des dependances.
    pause
    exit /b
)

REM --- 3) Lancement
echo Lancement de CitySync...
py main.py
if errorlevel 1 (
    echo.
    echo CitySync s'est arrete sur une erreur (voir au-dessus).
    pause
)
