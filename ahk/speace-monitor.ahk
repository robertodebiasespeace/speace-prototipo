; ============================================================
; SPEACE Monitor AHK v2
; Monitora il workspace SPEACE e invia alert in caso di errori
;
; Funzioni:
; - Monitoraggio continuo file workspace (errori, modifiche)
; - Alert popup su errori critici
; - Tray icon con stato SPEACE
; - Hotkey per aprire report status
;
; Versione: 1.0 | 2026-04-17
; Richiede: AutoHotkey v2
; ============================================================

#Requires AutoHotkey v2.0
#SingleInstance Force

; ---- CONFIGURAZIONE ----
SPEACE_DIR := A_ScriptDir "\.."              ; Root del progetto
STATUS_FILE := SPEACE_DIR "\logs\status_current.md"
PROPOSALS_FILE := SPEACE_DIR "\safeproactive\PROPOSALS.md"
WAL_LOG := SPEACE_DIR "\safeproactive\WAL.log"
MONITOR_INTERVAL := 120000                    ; ms (2 minuti)
PYTHON_CMD := "python"                        ; o "py" su Windows

; ---- TRAY ICON ----
TraySetIcon("shell32.dll", 168)              ; Icona globe
A_TrayMenu.Delete()
A_TrayMenu.Add("📊 Apri Status Report", OpenStatusReport)
A_TrayMenu.Add("🗳️ Apri Proposals", OpenProposals)
A_TrayMenu.Add("▶ Esegui Monitor Ora", RunMonitorNow)
A_TrayMenu.Add("▶ Esegui Evolver Ora", RunEvolverNow)
A_TrayMenu.Add()
A_TrayMenu.Add("❌ Esci", (*) => ExitApp())
A_TrayMenu.Default := "📊 Apri Status Report"
TrayTip("SPEACE Monitor", "Sistema di monitoraggio attivo", "Info")

; ---- VARIABILI DI STATO ----
global LastErrorCount := 0
global MonitorCycles := 0

; ---- HOTKEYS ----
^!s:: OpenStatusReport(*)    ; Ctrl+Alt+S → apri status
^!p:: OpenProposals(*)       ; Ctrl+Alt+P → apri proposals
^!e:: RunEvolverNow(*)       ; Ctrl+Alt+E → ciclo evolver

; ---- LOOP PRINCIPALE ----
SetTimer(MonitorCycle, MONITOR_INTERVAL)
MonitorCycle()                               ; Prima esecuzione immediata

MonitorCycle(*) {
    global LastErrorCount, MonitorCycles
    MonitorCycles++

    ; Controlla file status
    if FileExist(STATUS_FILE) {
        try {
            content := FileRead(STATUS_FILE, "UTF-8")

            ; Conta errori
            errorCount := 0
            pos := 1
            while (pos := InStr(content, "❌", , pos)) {
                errorCount++
                pos++
            }

            ; Conta proposals pending
            pendingCount := 0
            pos := 1
            while (pos := InStr(content, "pending", , pos)) {
                pendingCount++
                pos++
            }

            ; Alert se nuovi errori
            if errorCount > LastErrorCount {
                newErrors := errorCount - LastErrorCount
                TrayTip("SPEACE ⚠️ ALERT",
                    newErrors " file/i mancante/i rilevato/i!`nAprire Status Report.",
                    "Warning")
                LastErrorCount := errorCount
            }

            ; Alert proposals pendenti
            if pendingCount > 0 && Mod(MonitorCycles, 5) = 0 {
                TrayTip("SPEACE 📋 Proposals",
                    pendingCount " proposta/e in attesa di approvazione.",
                    "Info")
            }

            ; Status nominale
            if errorCount = 0 {
                LastErrorCount := 0
            }
        }
    } else {
        ; File status non trovato → esegui monitor
        if MonitorCycles = 1 {
            RunMonitorNow(*)
        }
    }
}

; ---- FUNZIONI ----
OpenStatusReport(*) {
    if FileExist(STATUS_FILE)
        Run('notepad.exe "' STATUS_FILE '"')
    else
        MsgBox("File status non trovato. Eseguire prima il monitor.", "SPEACE", "Icon!")
}

OpenProposals(*) {
    if FileExist(PROPOSALS_FILE)
        Run('notepad.exe "' PROPOSALS_FILE '"')
    else
        MsgBox("File proposals non trovato.", "SPEACE", "Icon!")
}

RunMonitorNow(*) {
    monitor_script := SPEACE_DIR "\evolver\speace-status-monitor.py"
    if FileExist(monitor_script) {
        TrayTip("SPEACE", "Esecuzione Status Monitor...", "Info")
        Run(PYTHON_CMD ' "' monitor_script '" --once', SPEACE_DIR, "Hide")
        Sleep(3000)
        TrayTip("SPEACE ✅", "Status Monitor completato", "Info")
    } else {
        MsgBox("speace-status-monitor.py non trovato in:\n" monitor_script, "SPEACE", "Icon!")
    }
}

RunEvolverNow(*) {
    evolver_script := SPEACE_DIR "\evolver\speace-cortex-evolver.py"
    if FileExist(evolver_script) {
        TrayTip("SPEACE", "Esecuzione Evolver (ciclo singolo)...", "Info")
        Run(PYTHON_CMD ' "' evolver_script '" --once', SPEACE_DIR, "Hide")
        Sleep(5000)
        TrayTip("SPEACE ✅", "Evolver completato. Nuova proposta in PROPOSALS.md", "Info")
    } else {
        MsgBox("speace-cortex-evolver.py non trovato.", "SPEACE", "Icon!")
    }
}
