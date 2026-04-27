"""
SPEACE Status Monitor
Report di stato ogni 40 minuti (configurabile).

Funzioni:
- Controlla stato avanzamento (file, errori, task attive)
- Compila report di stato compatto
- Salva report su file e log
- Opzionale: invia via email (configura SMTP) o stampa su console

Versione: 1.0 | 2026-04-17
Esecuzione: python speace-status-monitor.py [--once] [--interval=40]
"""

import sys
import os
import json
import time
import yaml
import datetime
import argparse
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
MONITOR_LOG = LOGS_DIR / "monitor.log"
REPORTS_DIR = ROOT_DIR / "logs" / "status_reports"
REPORTS_DIR.mkdir(exist_ok=True)


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [MONITOR] {msg}"
    print(line)
    with open(MONITOR_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check_core_files() -> dict:
    """Verifica presenza e integrità dei file core."""
    critical_files = {
        "genome.yaml": ROOT_DIR / "digitaldna" / "genome.yaml",
        "epigenome.yaml": ROOT_DIR / "digitaldna" / "epigenome.yaml",
        "mutation_rules.yaml": ROOT_DIR / "digitaldna" / "mutation_rules.yaml",
        "PROPOSALS.md": ROOT_DIR / "safeproactive" / "PROPOSALS.md",
        "WAL.log": ROOT_DIR / "safeproactive" / "WAL.log",
        "SMFOI-v3.py": ROOT_DIR / "cortex" / "SMFOI-v3.py",
        "world_model.json": ROOT_DIR / "memory" / "world_model.json",
        "state.json": ROOT_DIR / "state.json",
    }

    results = {}
    for name, path in critical_files.items():
        results[name] = {
            "exists": path.exists(),
            "size_kb": round(path.stat().st_size / 1024, 1) if path.exists() else 0,
            "modified": datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None,
        }
    return results


def check_speace_state() -> dict:
    """Legge stato runtime SPEACE."""
    state_file = ROOT_DIR / "state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            return {}
    return {}


def check_epigenome() -> dict:
    """Legge fitness e parametri chiave dall'epigenome."""
    ep_file = ROOT_DIR / "digitaldna" / "epigenome.yaml"
    if ep_file.exists():
        try:
            with open(ep_file, "r", encoding="utf-8") as f:
                ep = yaml.safe_load(f) or {}
            return {
                "current_fitness": ep.get("fitness_metrics", {}).get("current_fitness", 0.0),
                "learning_rate": ep.get("learning", {}).get("learning_rate", 0.05),
                "mutation_count": ep.get("meta", {}).get("mutation_count", 0),
                "last_updated": ep.get("meta", {}).get("last_updated", "N/A"),
                "safe_mode": ep.get("flags", {}).get("safe_mode", True),
                "rollback_active": ep.get("flags", {}).get("rollback_system_active", True),
            }
        except Exception:
            return {}
    return {}


def count_pending_proposals() -> int:
    """Conta proposte in attesa di approvazione."""
    proposals_file = ROOT_DIR / "safeproactive" / "PROPOSALS.md"
    if proposals_file.exists():
        text = proposals_file.read_text(encoding="utf-8")
        return text.count("pending") + text.count("PENDING")
    return 0


def check_snapshots() -> dict:
    """Controlla snapshot disponibili."""
    snap_dir = ROOT_DIR / "safeproactive" / "snapshots"
    snaps = [d for d in snap_dir.iterdir() if d.is_dir()] if snap_dir.exists() else []
    return {
        "count": len(snaps),
        "latest": snaps[-1].name if snaps else None,
    }


def check_log_errors() -> list:
    """Cerca errori nei log recenti."""
    errors = []
    for log_file in LOGS_DIR.glob("*.log"):
        try:
            lines = log_file.read_text(encoding="utf-8").split("\n")
            # Ultime 100 righe
            for line in lines[-100:]:
                if "ERROR" in line.upper() or "ERRORE" in line.upper():
                    errors.append(f"{log_file.name}: {line.strip()[:120]}")
        except Exception:
            continue
    return errors[-10:]  # Massimo 10 errori


def compile_report() -> str:
    """Compila il report di stato completo."""
    ts = datetime.datetime.now().isoformat()
    files = check_core_files()
    state = check_speace_state()
    epigenome = check_epigenome()
    pending = count_pending_proposals()
    snapshots = check_snapshots()
    errors = check_log_errors()

    # Status globale
    all_files_ok = all(v["exists"] for v in files.values())
    status_icon = "✅" if all_files_ok and not errors else "⚠️"

    lines = [
        f"# {status_icon} SPEACE Status Report",
        f"**Timestamp:** {ts}",
        f"**Cicli eseguiti:** {len(state.get('cycles', []))}",
        f"**Ultimo ciclo:** {state.get('last_cycle', 'N/A')}",
        "",
        "## 📊 Fitness & Epigenome",
        f"- Fitness corrente: `{epigenome.get('current_fitness', 0):.4f}`",
        f"- Learning rate: `{epigenome.get('learning_rate', 0.05)}`",
        f"- Mutazioni proposte: `{epigenome.get('mutation_count', 0)}`",
        f"- Safe mode: `{epigenome.get('safe_mode', True)}`",
        f"- Rollback attivo: `{epigenome.get('rollback_active', True)}`",
        "",
        "## 📁 File Core",
    ]

    for fname, info in files.items():
        icon = "✅" if info["exists"] else "❌"
        lines.append(f"- {icon} `{fname}` ({info['size_kb']} KB)")

    lines.extend([
        "",
        "## 🗳️ SafeProactive",
        f"- Proposte in attesa: `{pending}`",
        f"- Snapshot disponibili: `{snapshots['count']}`",
        f"- Ultimo snapshot: `{snapshots['latest'] or 'nessuno'}`",
    ])

    if errors:
        lines.extend(["", "## ⚠️ Errori Rilevati"])
        for err in errors[:5]:
            lines.append(f"- `{err}`")

    lines.extend([
        "",
        "## 🎯 Azioni Consigliate",
    ])

    if pending > 0:
        lines.append(f"- Revisionare {pending} proposte in `safeproactive/PROPOSALS.md`")
    if snapshots["count"] == 0:
        lines.append("- Creare snapshot iniziale: `python -c \"from safeproactive import SafeProactive; SafeProactive().snapshot('manual')\"` ")
    if not errors and all_files_ok:
        lines.append("- Sistema nominale. Prossimo ciclo evolver programmato.")

    return "\n".join(lines)


def send_report_email(report: str, smtp_config: dict):
    """Invia report via email (opzionale)."""
    try:
        msg = MIMEText(report, "plain", "utf-8")
        msg["Subject"] = f"SPEACE Status Report – {datetime.date.today()}"
        msg["From"] = smtp_config["from"]
        msg["To"] = smtp_config["to"]

        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.sendmail(smtp_config["from"], smtp_config["to"], msg.as_string())
        log("Report inviato via email")
    except Exception as e:
        log(f"Invio email fallito: {e}")


def monitor_cycle(smtp_config: dict = None):
    """Esegue un ciclo di monitoraggio."""
    log("=== CICLO MONITOR AVVIATO ===")
    report = compile_report()

    # Salva report
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORTS_DIR / f"status_{date_str}.md"
    report_file.write_text(report, encoding="utf-8")

    # Aggiorna report corrente
    (ROOT_DIR / "logs" / "status_current.md").write_text(report, encoding="utf-8")

    print("\n" + "="*60)
    print(report)
    print("="*60 + "\n")

    if smtp_config:
        send_report_email(report, smtp_config)

    log(f"=== CICLO MONITOR COMPLETATO | Report: {report_file.name} ===\n")
    return report


def run_continuous(interval_min: int = 40, smtp_config: dict = None):
    """Esegue il monitor in loop continuo."""
    log(f"Monitor avviato in modalità continua | Heartbeat: {interval_min} min")
    while True:
        try:
            monitor_cycle(smtp_config)
        except Exception as e:
            log(f"ERRORE nel ciclo monitor: {e}")
        log(f"Prossimo report tra {interval_min} minuti...")
        time.sleep(interval_min * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPEACE Status Monitor")
    parser.add_argument("--once", action="store_true", help="Esegui un solo ciclo e termina")
    parser.add_argument("--interval", type=int, default=40, help="Intervallo in minuti (default: 40)")
    parser.add_argument("--email-to", type=str, help="Indirizzo email destinatario")
    args = parser.parse_args()

    smtp_config = None
    if args.email_to:
        smtp_config = {
            "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            "port": int(os.environ.get("SMTP_PORT", 587)),
            "user": os.environ.get("SMTP_USER", ""),
            "password": os.environ.get("SMTP_PASSWORD", ""),
            "from": os.environ.get("SMTP_FROM", "speace@rigene.eu"),
            "to": args.email_to,
        }

    if args.once:
        monitor_cycle(smtp_config)
    else:
        run_continuous(args.interval, smtp_config)
