"""
SPEACE Cortex Evolver
Agente stimolatore evolutivo con heartbeat configurabile.

Funzioni:
- Fetch obiettivi da rigeneproject.org ogni 60 min
- Genera proposte mutazione epigenetica
- Stimola World Model con nuovi dati
- Interagisce con SafeProactive per approvazione

Versione: 1.0 | 2026-04-17
Esecuzione: python speace-cortex-evolver.py [--once] [--interval=60]
"""

import sys
import time
import json
import yaml
import datetime
import argparse
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
EVOLVER_LOG = LOGS_DIR / "evolver.log"
STATE_FILE = ROOT_DIR / "state.json"
EPIGENOME_PATH = ROOT_DIR / "digitaldna" / "epigenome.yaml"


def log(msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [EVOLVER] {msg}"
    print(line)
    with open(EVOLVER_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_epigenome() -> dict:
    try:
        with open(EPIGENOME_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def save_epigenome(data: dict):
    with open(EPIGENOME_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def fetch_rigene_objectives() -> list:
    """Fetch obiettivi da rigeneproject.org con fallback."""
    try:
        import requests
        resp = requests.get("https://www.rigeneproject.org", timeout=15)
        if resp.status_code == 200:
            import re
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text)
            keywords = ["harmony", "peace", "ecosystem", "sustainable", "evolution",
                        "digital DNA", "TINA", "SDG", "climate", "AI"]
            sentences = text.split('.')
            objectives = []
            for s in sentences:
                if any(kw.lower() in s.lower() for kw in keywords):
                    clean = s.strip()[:200]
                    if len(clean) > 30:
                        objectives.append(clean)
            return objectives[:8] if objectives else _fallback_objectives()
    except Exception as e:
        log(f"Fetch Rigene Project fallito: {e} — uso fallback")
    return _fallback_objectives()


def _fallback_objectives() -> list:
    return [
        "Guide AI toward improvement of life and natural ecosystems",
        "Develop Digital DNA framework for safe technological evolution",
        "Achieve UN SDGs Agenda 2030",
        "Create distributed cognitive collective brain (TINA)",
        "Promote harmony, peace, ecological-social-technological balance",
        "Enable planetary autonomous organism for global problem solving",
        "Implement ethical governance for AI systems",
    ]


def generate_mutation_proposal(epigenome: dict, objectives: list) -> dict:
    """Genera una proposta di mutazione epigenetica."""
    import random

    # Parametri mutabili
    mutable = [
        ("learning", "learning_rate", 0.01, 0.2, 0.005),
        ("learning", "exploration_rate", 0.05, 0.4, 0.02),
        ("learning", "yield_priority", 1, 9, 1),
        ("evolution", "heartbeat_interval_min", 30, 120, 5),
    ]

    section, key, lo, hi, step = random.choice(mutable)
    current = epigenome.get(section, {}).get(key, (lo + hi) / 2)

    direction = random.choice([-1, 1])
    new_val = round(max(lo, min(hi, current + direction * step)), 4)

    selected_obj = random.choice(objectives) if objectives else "Evoluzione SPEACE"

    return {
        "id": f"EPI-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "type": "epigenetic_mutation",
        "parameter": f"{section}.{key}",
        "current_value": current,
        "proposed_value": new_val,
        "delta": round(new_val - current, 4),
        "rationale": f"Stimolazione evolutiva da Rigene Project: '{selected_obj[:80]}'",
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "pending_approval",
        "risk_level": "medium",
    }


def write_proposal_to_safeproactive(proposal: dict):
    """Scrive la proposta nel file PROPOSALS.md."""
    proposals_file = ROOT_DIR / "safeproactive" / "PROPOSALS.md"
    with open(proposals_file, "a", encoding="utf-8") as f:
        f.write(f"\n## {proposal['id']}\n")
        f.write(f"- **Timestamp:** {proposal['timestamp']}\n")
        f.write(f"- **Tipo:** {proposal['type']}\n")
        f.write(f"- **Parametro:** `{proposal['parameter']}`\n")
        f.write(f"- **Valore attuale:** `{proposal['current_value']}`\n")
        f.write(f"- **Valore proposto:** `{proposal['proposed_value']}`\n")
        f.write(f"- **Delta:** `{proposal['delta']:+.4f}`\n")
        f.write(f"- **Rationale:** {proposal['rationale']}\n")
        f.write(f"- **Risk Level:** {proposal['risk_level'].upper()}\n")
        f.write(f"- **Status:** PENDING APPROVAL → Approvare in safeproactive/PROPOSALS.md\n")
        f.write("\n---\n")
    log(f"Proposta {proposal['id']} scritta in PROPOSALS.md")


def update_world_model(objectives: list):
    """Aggiorna il World Model con nuovi obiettivi Rigene."""
    wm_file = ROOT_DIR / "memory" / "world_model.json"
    if wm_file.exists():
        try:
            data = json.loads(wm_file.read_text(encoding="utf-8"))
            data["rigene_objectives"] = objectives
            data["meta"]["last_updated"] = datetime.datetime.now().isoformat()
            data["meta"]["update_count"] = data["meta"].get("update_count", 0) + 1
            wm_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            log(f"World Model aggiornato con {len(objectives)} obiettivi Rigene")
        except Exception as e:
            log(f"Errore aggiornamento World Model: {e}")


def evolver_cycle():
    """Esegue un ciclo dell'evolver."""
    log("=== CICLO EVOLVER AVVIATO ===")

    # 1. Carica stato corrente
    epigenome = load_epigenome()
    mutation_count = epigenome.get("meta", {}).get("mutation_count", 0)

    # 2. Fetch obiettivi
    log("Fetch obiettivi da rigeneproject.org...")
    objectives = fetch_rigene_objectives()
    log(f"Obiettivi caricati: {len(objectives)}")

    # 3. Aggiorna World Model
    update_world_model(objectives)

    # 4. Genera proposta mutazione
    proposal = generate_mutation_proposal(epigenome, objectives)
    log(f"Proposta generata: {proposal['id']} | {proposal['parameter']} {proposal['current_value']} → {proposal['proposed_value']}")

    # 5. Scrivi proposta SafeProactive
    write_proposal_to_safeproactive(proposal)

    # 6. Aggiorna metadata epigenome
    if "meta" not in epigenome:
        epigenome["meta"] = {}
    epigenome["meta"]["last_updated"] = datetime.datetime.now().isoformat()
    epigenome["meta"]["mutation_count"] = mutation_count + 1
    save_epigenome(epigenome)

    log(f"=== CICLO EVOLVER COMPLETATO | Totale mutazioni proposte: {mutation_count + 1} ===\n")
    return proposal


def run_continuous(interval_min: int = 60):
    """Esegue l'evolver in loop continuo."""
    log(f"Evolver avviato in modalità continua | Heartbeat: {interval_min} min")
    while True:
        try:
            evolver_cycle()
        except Exception as e:
            log(f"ERRORE nel ciclo evolver: {e}")
        log(f"Prossimo ciclo tra {interval_min} minuti...")
        time.sleep(interval_min * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPEACE Cortex Evolver")
    parser.add_argument("--once", action="store_true", help="Esegui un solo ciclo e termina")
    parser.add_argument("--interval", type=int, default=60, help="Intervallo in minuti (default: 60)")
    args = parser.parse_args()

    if args.once:
        log("Modalità: singolo ciclo")
        evolver_cycle()
    else:
        run_continuous(args.interval)
