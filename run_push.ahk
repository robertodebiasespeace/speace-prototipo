#Requires AutoHotkey v2.0
; SPEACE – Lancia il push Python automaticamente
; Questo script viene eseguito da AHK e non necessita di terminale

SCRIPT_DIR := A_ScriptDir
PY_SCRIPT := SCRIPT_DIR . "\git_push_github.py"

; Verifica che lo script Python esista
if !FileExist(PY_SCRIPT) {
    MsgBox("Script non trovato: " . PY_SCRIPT, "SPEACE Push", 16)
    ExitApp(1)
}

; Avvia Python in una finestra cmd visibile
pid := Run('cmd.exe /c python "' . PY_SCRIPT . '" & echo. & echo Premi un tasto... & pause', SCRIPT_DIR, "")

; Attendi che il processo finisca (max 120 secondi)
if pid {
    WinWait("ahk_pid " . pid,, 120)
    MsgBox("Push completato! Controlla git_push_log.txt per i dettagli.", "SPEACE Push", 64)
} else {
    MsgBox("Impossibile avviare Python. Assicurati che Python sia nel PATH.", "SPEACE Push", 16)
}

ExitApp(0)
