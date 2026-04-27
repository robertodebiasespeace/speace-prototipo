@echo off
REM ============================================================
REM  SPEACE EA Integration Launcher
REM  Avvia il ciclo di monitoraggio SPEACE <-> MT5 XAUUSD EA
REM  Roberto De Biase / SPEACE Cortex
REM ============================================================

setlocal

SET SPEACE_ROOT=%USERPROFILE%\Documents\Claude\Projects\SPEACE-prototipo
SET MT5_COMMON=%APPDATA%\MetaQuotes\Terminal\Common
SET EA_SHARED=%MT5_COMMON%\speace-ea-integration\shared_state
SET LOG_DIR=%SPEACE_ROOT%\speace-ea-integration\logs

echo [SPEACE-EA] ============================================
echo [SPEACE-EA]  SPEACE XAUUSD EA Launcher
echo [SPEACE-EA] ============================================
echo.

REM Creazione cartelle
if not exist "%EA_SHARED%" mkdir "%EA_SHARED%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Scrittura ea_params.json iniziale (default)
echo [SPEACE-EA] Writing initial ea_params.json...
(
echo {
echo   "LotSize": 0.1,
echo   "StopLossPips": 500,
echo   "TakeProfitPips": 1000,
echo   "RSI_Period": 14,
echo   "MA_Fast_Period": 10,
echo   "MA_Slow_Period": 30,
echo   "MaxTrades": 3
echo }
) > "%EA_SHARED%\ea_params.json"

REM Scrittura ea_state.json iniziale
echo [SPEACE-EA] Writing initial ea_state.json...
(
echo {
echo   "ea_name": "SPEACE_XAUUSD_EA",
echo   "version": "1.00",
echo   "mt5_account": 0,
echo   "open_positions": 0,
echo   "params_loaded": false,
echo   "pending_mutations": []
echo }
) > "%EA_SHARED%\ea_state.json"

REM Avvio EA Evolver in background
echo [SPEACE-EA] Starting SPEACE EA Evolver (5min cycle)...
start "SPEACE-EA-EVOLVER" cmd /c "cd /d "%SPEACE_ROOT%" ^&^& python speace-ea-integration\speace-ea-evolver.py --interval 5"

REM Avvio Status Monitor
echo [SPEACE-EA] Starting SPEACE EA Status Monitor...
start "SPEACE-EA-MONITOR" cmd /c "cd /d "%SPEACE_ROOT%" ^&^& python speace-ea-integration\speace-ea-evolver.py --status-loop"

echo.
echo [SPEACE-EA] ============================================
echo [SPEACE-EA]  SPEACE EA Integration Active
echo [SPEACE-EA] ============================================
echo.
echo Shared State: %EA_SHARED%
echo Logs:         %LOG_DIR%
echo.
echo [SPEACE-EA] MT5 Configuration:
echo [SPEACE-EA]   - Copy SPEACE_XAUUSD_EA.mq5 to MT5 MQL5\Experts
echo [SPEACE-EA]   - Compile in MetaEditor (F7)
echo [SPEACE-EA]   - Drag onto XAUUSD chart in Demo account
echo [SPEACE-EA]   - Set Common tab: "Allow live trading"
echo [SPEACE-EA]   - Set Inputs: SPEACE_RelativePath = speace-ea-integration\shared_state\
echo.
echo [SPEACE-EA] To stop: close SPEACE-EA-EVOLVER window
echo [SPEACE-EA] ============================================
pause
