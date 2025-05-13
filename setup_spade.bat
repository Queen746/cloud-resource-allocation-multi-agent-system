@echo off
echo ========================================================
echo    Configuration d'un environnement propre pour SPADE
echo ========================================================
echo.

:: Vérifier si Python 3.9 est disponible
python -c "import sys; print(sys.version); sys.exit(1 if sys.version_info.major != 3 or sys.version_info.minor != 9 else 0)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python 3.9.x est requis pour cette installation.
    echo Veuillez installer Python 3.9 depuis https://www.python.org/downloads/release/python-3913/
    exit /b 1
)

:: Supprimer l'ancien environnement virtuel s'il existe
if exist .venv-py39 (
    echo [INFO] Suppression de l'environnement virtuel existant...
    rmdir /s /q .venv-py39
)

:: Créer un nouvel environnement virtuel
echo [INFO] Création d'un nouvel environnement virtuel avec Python 3.9...
python -m venv .venv-py39

:: Activer l'environnement virtuel
echo [INFO] Activation de l'environnement virtuel...
call .venv-py39\Scripts\activate.bat

:: Mettre à jour pip et installer les outils de base
echo [INFO] Mise à jour de pip et installation des outils de base...
python -m pip install --upgrade pip setuptools wheel

:: Installer les dépendances une par une
echo [INFO] Installation des dépendances (cela peut prendre quelques minutes)...
pip install aioxmpp
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation de aioxmpp.
    goto error
)
pip install aiohttp
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation de aiohttp.
    goto error
)
pip install aiodns
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation de aiodns.
    goto error
)
pip install async-timeout
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation de async-timeout.
    goto error
)
pip install networkx
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation de networkx.
    goto error
)
pip install flask
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation de flask.
    goto error
)
pip install spade
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de l'installation de spade.
    goto error
)

:: Vérifier l'installation de SPADE
echo [INFO] Vérification de l'installation de SPADE...
python -c "import spade; print(f'SPADE version: {spade.__version__}')"
if %errorlevel% neq 0 (
    echo [ERREUR] Échec de la vérification de SPADE.
    goto error
)

echo.
echo [SUCCÈS] Configuration terminée avec succès!
echo.
echo Pour démarrer le système:
echo 1. Activez l'environnement: .venv-py39\Scripts\activate.bat
echo 2. Lancez le système: python system_launcher.py
echo.
goto :eof

:error
echo.
echo [ERREUR] Une erreur est survenue lors de l'installation.
echo Si vous ne parvenez pas à résoudre ce problème, envisagez de passer à JADE.
echo.