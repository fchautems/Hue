@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 goto :error

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas accessible. Installe Python et ajoute-le au PATH.
    goto :error
)

if not exist "requirements.txt" (
    echo [ERREUR] requirements.txt est introuvable.
    goto :error
)

python -c "import fastapi, uvicorn, requests, jinja2" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installation des dependances Python manquantes...
    python -m pip install -r "requirements.txt"
    if errorlevel 1 (
        echo [ERREUR] Installation echouee. Verifie la sortie ci-dessus.
        goto :error
    )
)

python -c "import fastapi, uvicorn, requests, jinja2" >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Une dependance est encore manquante apres installation.
    goto :error
)

echo [INFO] Demarrage de Hue Web : http://127.0.0.1:8765
python hue_web.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo [ERREUR] Hue Web n'a pas pu demarrer.
pause
exit /b 1
