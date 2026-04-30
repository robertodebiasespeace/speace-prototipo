@echo off
REM ============================================================
REM SPEACE – Avvio rapido (Windows)
REM Doppio-click per avviare SPEACE
REM ============================================================
cd /d "%~dp0"

echo.
echo  ███████╗██████╗ ███████╗ █████╗  ██████╗███████╗
echo  ██╔════╝██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝
echo  ███████╗██████╔╝█████╗  ███████║██║     █████╗
echo  ╚════██║██╔═══╝ ██╔══╝  ██╔══██║██║     ██╔══╝
echo  ███████║██║     ███████╗██║  ██║╚██████╗███████╗
echo  ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝
echo.
echo  SuPer Entita Autonoma Cibernetica Evolutiva v0.1.0
echo  Rigene Project -- Roberto De Biase
echo  ============================================================
echo.

REM Controlla Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Python non trovato. Installa Python 3.10+ da https://python.org
    pause
    exit /b 1
)

REM Controlla dipendenze
python -c "import yaml, requests, psutil" >nul 2>&1
if %errorlevel% neq 0 (
    echo [SETUP] Installazione dipendenze...
    pip install -r requirements.txt
)

REM Avvio modalità scelta
echo Scegli modalità di avvio:
echo   [1] Standard     (SMFOI + DigitalDNA + SafeProactive)
echo   [2] Brain        (+ BRN-001 to BRN-020 cognitive architecture)
echo   [3] Brain+Team   (+ SPEACE Scientific Team)
echo   [4] Single cycle (test rapido)
echo   [5] Dashboard    (Streamlit localhost:8501)
echo.
set /p choice="Scelta [1-5]: "

if "%choice%"=="1" python SPEACE-main.py
if "%choice%"=="2" python SPEACE-main.py --brain
if "%choice%"=="3" python SPEACE-main.py --brain --team
if "%choice%"=="4" python SPEACE-main.py --once --brain
if "%choice%"=="5" streamlit run dashboard/speace_dashboard.py

echo.
pause
