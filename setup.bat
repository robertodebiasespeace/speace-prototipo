@echo off
REM ============================================================
REM SPEACE Setup Script per Windows
REM Installa tutte le dipendenze e verifica l'ambiente
REM ============================================================

echo.
echo  ====================================================
echo   SPEACE Setup - SuPer Entita Autonoma Cibernetica
echo  ====================================================
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Python non trovato nel PATH.
    echo Scarica Python da: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo [OK] %%i

REM Installa dipendenze
echo.
echo [SPEACE] Installazione dipendenze Python...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo [ATTENZIONE] Alcune dipendenze potrebbero non essere installate correttamente.
    echo Prova: pip install pyyaml requests psutil schedule python-dotenv
) else (
    echo [OK] Dipendenze installate correttamente.
)

REM Crea file .env se non esiste
if not exist ".env" (
    echo.
    echo [SPEACE] Creazione file .env per configurazione...
    (
        echo # SPEACE Environment Variables
        echo # Configura la tua API key Anthropic per abilitare il Team Scientifico LLM
        echo ANTHROPIC_API_KEY=sk-your-api-key-here
        echo.
        echo # Email per status report (opzionale)
        echo SMTP_HOST=smtp.gmail.com
        echo SMTP_PORT=587
        echo SMTP_USER=
        echo SMTP_PASSWORD=
        echo SMTP_FROM=speace@rigene.eu
    ) > .env
    echo [OK] File .env creato. Configura la tua API key in .env
)

REM Crea cartelle necessarie
echo.
echo [SPEACE] Verifica struttura directory...
if not exist "logs" mkdir logs
if not exist "logs\status_reports" mkdir logs\status_reports
if not exist "memory\episodic" mkdir memory\episodic
if not exist "safeproactive\snapshots" mkdir safeproactive\snapshots
if not exist "scientific-team\outputs" mkdir scientific-team\outputs
echo [OK] Directory verificate.

REM Test rapido
echo.
echo [SPEACE] Test rapido del sistema...
python -c "import yaml, requests, psutil; print('[OK] Moduli core importati correttamente')"

echo.
echo  ====================================================
echo   Setup completato!
echo.
echo   Comandi disponibili:
echo   python SPEACE-main.py           -> 2 cicli SMFOI
echo   python SPEACE-main.py --once    -> 1 ciclo singolo
echo   python SPEACE-main.py --team    -> con Team Scientifico
echo   python SPEACE-main.py --continuous -> loop infinito
echo.
echo   python evolver\speace-cortex-evolver.py --once
echo   python evolver\speace-status-monitor.py --once
echo.
echo   AHK: doppio click su ahk\speace-launcher.ahk
echo  ====================================================
echo.
pause
