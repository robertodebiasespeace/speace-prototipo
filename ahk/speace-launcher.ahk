; ============================================================
; SPEACE Launcher AHK v2
; Avvia tutti i componenti SPEACE con un click
;
; Componenti avviati:
; 1. SPEACE Main (ciclo singolo o continuo)
; 2. Cortex Evolver (background)
; 3. Status Monitor (background)
; 4. SPEACE Monitor AHK
;
; Versione: 1.0 | 2026-04-17
; ============================================================

#Requires AutoHotkey v2.0
#SingleInstance Force

SPEACE_DIR := A_ScriptDir "\.."
PYTHON_CMD := "python"

; Mostra GUI di lancio
LauncherGui := Gui("+AlwaysOnTop", "🚀 SPEACE Launcher v1.0")
LauncherGui.SetFont("s10", "Segoe UI")
LauncherGui.Add("Text",, "Scegli modalità di avvio SPEACE:")
LauncherGui.Add("Text",, "")

BtnFull := LauncherGui.Add("Button", "w250 h35", "▶ Avvia SPEACE Completo")
BtnOnce := LauncherGui.Add("Button", "w250 h35", "🔄 Ciclo Singolo (test)")
BtnEvolver := LauncherGui.Add("Button", "w250 h35", "🧬 Solo Evolver")
BtnMonitor := LauncherGui.Add("Button", "w250 h35", "📊 Solo Status Monitor")
BtnStatus := LauncherGui.Add("Button", "w250 h35", "📋 Apri Status Corrente")
BtnProposals := LauncherGui.Add("Button", "w250 h35", "🗳️ Apri Proposals")

BtnFull.OnEvent("Click", LaunchFull)
BtnOnce.OnEvent("Click", LaunchOnce)
BtnEvolver.OnEvent("Click", LaunchEvolver)
BtnMonitor.OnEvent("Click", LaunchMonitor)
BtnStatus.OnEvent("Click", OpenStatus)
BtnProposals.OnEvent("Click", OpenProposals)

LauncherGui.Add("Text",, "")
LauncherGui.Add("Text",, "💡 Usa Ctrl+Alt+S per status rapido")
LauncherGui.Add("Text",, "    Usa Ctrl+Alt+P per proposals")

LauncherGui.Show()

LaunchFull(*) {
    LauncherGui.Hide()
    TrayTip("SPEACE", "Avvio sistema completo...", "Info")

    ; Avvia main
    Run(PYTHON_CMD ' "' SPEACE_DIR '\SPEACE-main.py"', SPEACE_DIR)
    Sleep(2000)

    ; Avvia evolver in background
    Run(PYTHON_CMD ' "' SPEACE_DIR '\evolver\speace-cortex-evolver.py" --interval=60',
        SPEACE_DIR, "Hide")

    ; Avvia monitor in background
    Run(PYTHON_CMD ' "' SPEACE_DIR '\evolver\speace-status-monitor.py" --interval=40',
        SPEACE_DIR, "Hide")

    ; Avvia AHK monitor
    ahk_monitor := SPEACE_DIR "\ahk\speace-monitor.ahk"
    if FileExist(ahk_monitor)
        Run('"' A_AhkPath '" "' ahk_monitor '"')

    TrayTip("SPEACE ✅", "Sistema avviato!", "Info")
    LauncherGui.Show()
}

LaunchOnce(*) {
    TrayTip("SPEACE", "Ciclo singolo in esecuzione...", "Info")
    Run(PYTHON_CMD ' "' SPEACE_DIR '\SPEACE-main.py" --once', SPEACE_DIR)
}

LaunchEvolver(*) {
    TrayTip("SPEACE 🧬", "Evolver avviato (ciclo singolo)...", "Info")
    Run(PYTHON_CMD ' "' SPEACE_DIR '\evolver\speace-cortex-evolver.py" --once', SPEACE_DIR)
}

LaunchMonitor(*) {
    TrayTip("SPEACE 📊", "Status Monitor avviato...", "Info")
    Run(PYTHON_CMD ' "' SPEACE_DIR '\evolver\speace-status-monitor.py" --once', SPEACE_DIR)
    Sleep(3000)
    OpenStatus(*)
}

OpenStatus(*) {
    status_file := SPEACE_DIR "\logs\status_current.md"
    if FileExist(status_file)
        Run('notepad.exe "' status_file '"')
    else
        MsgBox("Eseguire prima il monitor per generare il report.", "SPEACE", "Icon!")
}

OpenProposals(*) {
    proposals_file := SPEACE_DIR "\safeproactive\PROPOSALS.md"
    if FileExist(proposals_file)
        Run('notepad.exe "' proposals_file '"')
    else
        MsgBox("File proposals non trovato.", "SPEACE", "Icon!")
}
