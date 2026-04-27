"""
SPEACE – Entry Point Principale
SuPer Entità Autonoma Cibernetica Evolutiva

Avvia il sistema SPEACE completo:
- Inizializza SafeProactive (snapshot iniziale)
- Attiva World Model
- Esegue cicli SMFOI-KERNEL
- Coordina Cortex e Team Scientifico
- [NEU-003] Integra BrainIntegration (BRN-001->015) nel loop cognitivo

Versione: 1.1 | 2026-04-26
Uso: python SPEACE-main.py [--once] [--cycles=N] [--team] [--neural] [--brain]
Note:
  --neural  attiva il Neural Engine per automazione processi cerebrali
  --brain   attiva il Brain Biologico (BRN-001->015) nel loop cognitivo (default OFF)
"""

import sys
import os
import json
import argparse
import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

BANNER = """
+----------------------------------------------------------+
|   SPEACE  -  SuPer Entita Autonoma Cibernetica Evolutiva |
|   Versione 1.1 | Fase 1 - Embrionale                    |
|   Fondatore: Roberto De Biase (Rigene Project)           |
+----------------------------------------------------------+
"""


def check_dependencies():
    """Verifica che le dipendenze Python siano installate."""
    missing = []
    deps = ["yaml", "requests", "psutil"]
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    if missing:
        print(f"[SPEACE] ATTENZIONE - Dipendenze mancanti: {', '.join(missing)}")
        print(f"[SPEACE] Installa con: pip install {' '.join(missing)}")
        print("[SPEACE] oppure esegui: setup.bat")
        return False
    return True


def initialize_system():
    """Inizializza il sistema SPEACE al primo avvio."""
    print("[SPEACE] Inizializzazione sistema...")

    state_file = ROOT_DIR / "state.json"
    if not state_file.exists():
        state = {
            "version": "1.1",
            "phase": 1,
            "created": datetime.datetime.now().isoformat(),
            "cycles": [],
            "last_fitness": 0.0,
            "last_cycle": None,
            "last_run": None,
        }
        state_file.write_text(json.dumps(state, indent=2))
        print("[SPEACE] OK state.json creato")

    memory_file = ROOT_DIR / "memory" / "MEMORY.md"
    if not memory_file.exists():
        memory_file.write_text(
            "# SPEACE Memory Index\n\n"
            "Indice della memoria persistente di SPEACE.\n\n"
            f"Creato: {datetime.datetime.now().isoformat()}\n\n"
        )
        print("[SPEACE] OK MEMORY.md creato")


def _run_brain_cycle(brain, smfoi_result: dict, cycle_n: int) -> dict:
    """
    NEU-003 - Esegue un ciclo del Brain Biologico (BRN-001->015).

    Converte l'output SMFOI in input sensoriale per il cervello e ritorna
    lo stato cognitivo risultante (consciousness_level, emotional_state, action).

    Il brain lavora in parallelo al SMFOI-KERNEL: riceve lo stesso contesto
    (push, fitness, ciclo_id) ma lo elabora via circuiti biologici simulati
    (cortex -> thalamus -> amygdala -> basal_ganglia -> working_memory).
    """
    import numpy as np

    fitness = float(smfoi_result.get("outcome", {}).get("fitness_after", 0.5))
    cycle_seed = cycle_n % 1000

    rng = np.random.RandomState(cycle_seed)
    sensory_input = rng.randn(256).astype(np.float32)
    # Modula con fitness: alta fitness -> stimolo piu positivo
    sensory_input[:64] += (fitness - 0.5) * 2.0

    try:
        cognitive_result = brain.process_sensory_input(sensory_input, modality="somatosensory")
        return {
            "consciousness_level": cognitive_result.consciousness_level,
            "emotional_state": cognitive_result.emotional_state,
            "action": cognitive_result.action,
            "processing_time_ms": cognitive_result.processing_time_ms,
        }
    except Exception as e:
        return {
            "consciousness_level": 0.0,
            "emotional_state": {"valence": 0.0},
            "action": None,
            "error": str(e),
        }


def run_speace(cycles: int = 1, run_team: bool = False, continuous: bool = False,
               run_neural: bool = False, run_brain: bool = False):
    """Esegue il sistema SPEACE."""

    print(BANNER)
    print(f"[SPEACE] Avvio {datetime.datetime.now().isoformat()}")
    print(f"[SPEACE] Modalita: {'continua' if continuous else f'{cycles} ciclo/i'}")
    print(f"[SPEACE] Neural Engine: {'Attivo' if run_neural else 'Disattivo'}")
    print(f"[SPEACE] Brain Biologico: {'Attivo (BRN-001->015)' if run_brain else 'Disattivo (usa --brain per attivare)'}")

    if not check_dependencies():
        sys.exit(1)

    initialize_system()

    # Importa moduli SPEACE
    try:
        from safeproactive.safeproactive import SafeProactive, RiskLevel
        from cortex.SMFOI_v3 import SMFOIKernel
        from cortex.world_model import WorldModel
        from cortex.comparti.default_mode_network import DefaultModeNetwork
    except ImportError as e:
        print(f"[SPEACE] Errore import moduli: {e}")
        print("[SPEACE] Verifica che tutti i file siano presenti e le dipendenze installate.")
        sys.exit(1)

    # NEU-003: Importa Brain Biologico se richiesto
    brain = None
    if run_brain:
        try:
            from cortex.brain.brain_integration import create_brain
            print("\n[SPEACE] Inizializzazione Brain Biologico (BRN-001->015)...")
            brain = create_brain("SPEACE_Brain")
            print(f"[SPEACE] OK Brain Biologico attivo | Moduli: BRN-001->015")
        except ImportError as e:
            print(f"[SPEACE] ATTENZIONE Brain Biologico non disponibile: {e}")
        except Exception as e:
            print(f"[SPEACE] ATTENZIONE Errore inizializzazione Brain: {e}")

    # Importa Neural Engine se richiesto
    neural_engine = None
    if run_neural:
        try:
            from neural_engine.neural_main import SPEACENeuralEngine
            print("\n[SPEACE] Inizializzazione Neural Engine...")
            neural_engine = SPEACENeuralEngine()
            neural_engine.initialize()
            print("[SPEACE] OK Neural Engine attivo")
        except ImportError as e:
            print(f"[SPEACE] ATTENZIONE Neural Engine non disponibile: {e}")

    # 1. Inizializza SafeProactive e snapshot
    print("\n[SPEACE] Inizializzazione SafeProactive...")
    sp = SafeProactive()
    snap_id = sp.snapshot(label="startup")
    print(f"[SPEACE] OK Snapshot iniziale: {snap_id}")

    # 2. Inizializza World Model
    print("\n[SPEACE] Inizializzazione World Model...")
    wm = WorldModel()
    wm_summary = wm.get_summary()
    print(f"[SPEACE] OK World Model attivo | Nodi KG: {wm_summary['knowledge_nodes']}")

    # 3. Fetch obiettivi Rigene Project
    print("\n[SPEACE] Fetch obiettivi Rigene Project...")
    objs = wm.fetch_rigene_objectives()
    print(f"[SPEACE] OK {len(objs)} obiettivi caricati")

    # 4. Inizializza SMFOI-KERNEL
    print("\n[SPEACE] Inizializzazione SMFOI-KERNEL v0.3...")
    kernel = SMFOIKernel(agent_name="SPEACE-MAIN", recursion_level=1)
    dmn = DefaultModeNetwork()

    # Notifica avvio
    sp.propose(
        action_name="system_startup",
        description=f"Avvio sistema SPEACE v1.1 | {cycles} cicli pianificati | Brain={'ON' if brain else 'OFF'}",
        risk_level=RiskLevel.LOW,
        source_agent="speace-main"
    )

    # 5. Esegui cicli SMFOI
    cycle_history = []
    print(f"\n[SPEACE] Esecuzione {cycles} ciclo/i SMFOI...")

    if continuous:
        import time
        cycle_n = 0
        if neural_engine:
            neural_engine.start_background()
        try:
            while True:
                cycle_n += 1
                print(f"\n[SPEACE] {'='*40}")
                print(f"[SPEACE] CICLO CONTINUO #{cycle_n}")
                result = kernel.run_cycle()
                cycle_history.append(result)
                wm.update_speace_state(
                    last_cycle=result.get("cycle_id"),
                    fitness=result.get("outcome", {}).get("fitness_after", 0)
                )
                # NEU-003: ciclo cerebrale
                if brain is not None:
                    br = _run_brain_cycle(brain, result, cycle_n)
                    print(f"[SPEACE] Brain: consciousness={br['consciousness_level']:.3f} | "
                          f"emotion={br['emotional_state'].get('valence', 0.0)} | "
                          f"cycles={brain.cycle_count}")
                if neural_engine:
                    neural_status = neural_engine.get_status()
                    print(f"[SPEACE] Neural: {neural_status['cycle_count']} cicli | "
                          f"Balance: {neural_status['evolution']['balance']:.2f}")
                print(f"[SPEACE] Prossimo ciclo tra 60 secondi (Ctrl+C per fermare)...")
                time.sleep(60)
        finally:
            if neural_engine:
                neural_engine.stop_background()
    else:
        for i in range(cycles):
            print(f"\n[SPEACE] --- Ciclo {i+1}/{cycles} ---")
            result = kernel.run_cycle()
            cycle_history.append(result)
            wm.update_speace_state(
                last_cycle=result.get("cycle_id"),
                fitness=result.get("outcome", {}).get("fitness_after", 0)
            )
            # NEU-003: ciclo cerebrale
            if brain is not None:
                br = _run_brain_cycle(brain, result, i + 1)
                print(f"[SPEACE] Brain: consciousness={br['consciousness_level']:.3f} | "
                      f"emotion={br['emotional_state'].get('valence', 0.0)} | "
                      f"cycles={brain.cycle_count}")

    # 6. Riflessione post-ciclo (Default Mode Network)
    print("\n[SPEACE] Auto-riflessione (Default Mode Network)...")
    reflection = dmn.reflect(cycle_history, wm)
    if reflection["insights"]:
        print("[SPEACE] Insights:")
        for insight in reflection["insights"]:
            print(f"  - {insight}")
    if reflection["suggestions"]:
        print("[SPEACE] Suggerimenti:")
        for sug in reflection["suggestions"]:
            print(f"  - {sug}")

    # 7. Team Scientifico (opzionale)
    if run_team:
        print("\n[SPEACE] Avvio Team Scientifico...")
        try:
            sys.path.insert(0, str(ROOT_DIR / "scientific-team"))
            from orchestrator import ScientificTeamOrchestrator
            orchestrator = ScientificTeamOrchestrator()
            brief = orchestrator.run_daily_brief(wm_summary)
            print(f"\n[SPEACE] OK Daily Brief generato")
            print(brief[:500] + "...\n")
        except ImportError as e:
            print(f"[SPEACE] Team Scientifico non disponibile: {e}")
            print("[SPEACE] Assicurati che anthropic sia installato per usare il team.")

    # 8. Riepilogo finale
    final_fitness = cycle_history[-1].get("outcome", {}).get("fitness_after", 0) if cycle_history else 0
    print(f"\n{'='*60}")
    print(f"[SPEACE] SESSIONE COMPLETATA")
    print(f"[SPEACE] Cicli eseguiti: {len(cycle_history)}")
    print(f"[SPEACE] Fitness finale: {final_fitness:.4f}")
    if brain is not None:
        brain_state = brain.get_system_state()
        print(f"[SPEACE] Brain cicli: {brain_state['cycle_count']} | "
              f"Consciousness: {brain_state['consciousness_index']:.3f} | "
              f"Dopamina: {brain_state['dopamine_level']:.3f} | "
              f"WM items: {brain_state['working_memory']['total_items']}")
    print(f"[SPEACE] Proposte pending: vedere safeproactive/PROPOSALS.md")
    print(f"[SPEACE] Log disponibili in: logs/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SPEACE - Entry Point")
    parser.add_argument("--once", action="store_true", help="Ciclo singolo")
    parser.add_argument("--cycles", type=int, default=2, help="Numero di cicli (default: 2)")
    parser.add_argument("--team", action="store_true", help="Attiva Team Scientifico")
    parser.add_argument("--continuous", action="store_true", help="Modalita continua (loop)")
    parser.add_argument("--neural", action="store_true", help="Attiva Neural Engine (background)")
    parser.add_argument("--brain", action="store_true",
                        help="Attiva Brain Biologico BRN-001->015 nel loop cognitivo (default OFF)")
    args = parser.parse_args()

    cycles = 1 if args.once else args.cycles
    run_speace(cycles=cycles, run_team=args.team, continuous=args.continuous,
               run_neural=args.neural, run_brain=args.brain)
