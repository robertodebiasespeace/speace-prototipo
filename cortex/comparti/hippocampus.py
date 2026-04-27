"""
SPEACE Cortex – Hippocampus
Comparto 2: Memory & Long-term Storage

Funzioni:
- Memoria episodica (log cicli)
- Memoria semantica (collegata a World Model)
- Recupero contesto da sessioni precedenti

M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
"""

import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

ROOT_DIR = Path(__file__).parent.parent.parent
MEMORY_DIR = ROOT_DIR / "memory"
EPISODIC_DIR = MEMORY_DIR / "episodic"
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
EPISODIC_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(ROOT_DIR))
from cortex.base_compartment import BaseCompartment
from cortex import state_bus


class Hippocampus(BaseCompartment):
    """Gestione memoria a lungo termine di SPEACE."""

    name = "hippocampus"
    level = 3  # Memoria

    def store_episode(self, cycle_id: str, context: Dict):
        """Salva un episodio nel log episodico."""
        today = datetime.date.today().isoformat()
        episode_file = EPISODIC_DIR / f"{today}.jsonl"
        with open(episode_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"cycle_id": cycle_id, "context": context}) + "\n")

    def recall(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Recupera episodi rilevanti per una query.
        Implementazione semplice: cerca per keyword nel log.
        """
        results = []
        for ep_file in sorted(EPISODIC_DIR.glob("*.jsonl"), reverse=True):
            with open(ep_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        ep = json.loads(line)
                        if query.lower() in json.dumps(ep).lower():
                            results.append(ep)
                            if len(results) >= max_results:
                                return results
                    except Exception:
                        continue
        return results

    def get_recent_fitness_trend(self, n: int = 10) -> List[float]:
        """Restituisce trend fitness degli ultimi n cicli."""
        state_file = ROOT_DIR / "state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            cycles = state.get("cycles", [])[-n:]
            return [c.get("fitness", 0.0) for c in cycles]
        return []

    def update_memory_index(self, entry: str):
        """Aggiunge una riga all'indice memoria."""
        with open(MEMORY_INDEX, "a", encoding="utf-8") as f:
            f.write(f"- {entry}\n")

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Consolida l'esito del ciclo in memory_delta e storicizza l'episodio.
        Non fa mai rollback dello state.
        """
        cycle_id = state.get("cycle_id", "unknown")
        # Snapshot minimale dell'episodio (evita di scrivere lo state intero)
        episode_context = {
            "decision": state.get("decision", {}).get("goal"),
            "safety_blocked": state.get("safety_flags", {}).get("blocked", False),
            "action_status": state.get("action_result", {}).get("status"),
            "risk": state.get("risk", 0.0),
            "novelty": state.get("novelty", 0.0),
        }
        try:
            self.store_episode(cycle_id, episode_context)
            status = "ok"
            note = "episode_stored"
        except Exception as e:
            status = "error"
            note = f"store_failed:{e}"

        # Aggiorna memory_delta nello state
        delta = state.setdefault("memory_delta", {})
        delta["last_cycle_id"] = cycle_id
        delta["last_store_status"] = status
        return self._log(state, status=status, note=note)
