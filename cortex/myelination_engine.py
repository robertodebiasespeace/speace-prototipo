"""
L3 - Myelination Engine (Oligodendrocytes).
Digital myelin: priority paths that strengthen with high Phi.
Unused paths get pruned over time.
Version: 1.0
Data: 24 Aprile 2026
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("MyelinationEngine")

ROOT_DIR = Path(__file__).parent.parent


class MyelinationEngine:
    """
    Oligodendrociti digitali.

    - Traccia tutte le connessioni tra comparti (sinapsi digitali)
    - Assegna peso (mielinizzazione) basato su Phi
    - Path con Phi alto -> mielinizzazione aumentata -> esecuzione prioritaria
    - Path inutilizzati -> demielinizzazione -> pruning eventuale

    Myelin weight: 0.0 (assente) a 1.0 (completamente mielinizzato)
    """

    def __init__(self, myelination_log: Optional[Path] = None):
        self.mlog = myelination_log or ROOT_DIR / "logs" / "myelination_state.json"
        self.mlog.parent.mkdir(parents=True, exist_ok=True)

        self.synapses: Dict[Tuple[str, str], Dict] = {}
        self._load_state()

        self.myelination_rate = 0.05
        self.demyelination_rate = 0.02
        self.pruning_threshold = 0.05
        self.reinforcement_threshold = 0.15

        logger.info(f"MyelinationEngine: {len(self.synapses)} sinapsi caricate")

    def _load_state(self):
        if self.mlog.exists():
            try:
                with open(self.mlog, encoding='utf-8') as f:
                    data = json.load(f)
                    self.synapses = {
                        tuple(k.split("→")): v for k, v in data.get("synapses", {}).items()
                    }
            except:
                pass

    def _save_state(self):
        with open(self.mlog, 'w', encoding='utf-8') as f:
            json.dump({
                "synapses": {
                    f"{s}→{t}": v for (s, t), v in self.synapses.items()
                },
                "updated": datetime.now().isoformat(),
                "total_synapses": len(self.synapses)
            }, f, indent=2)

    def register_synapse(self, source: str, target: str, initial_weight: float = 0.1) -> None:
        """Registra una nuova connessione tra comparti"""
        key = (source, target)
        if key not in self.synapses:
            self.synapses[key] = {
                "weight": initial_weight,
                "created": time.time(),
                "last_used": time.time(),
                "phi_history": [],
                "activation_count": 0
            }
            logger.debug(f"Nuova sinapsi: {source} → {target}")

    def activate_path(self, source: str, target: str, phi: float) -> float:
        """Attiva un path e aggiorna la sua mielinizzazione."""
        key = (source, target)
        self.register_synapse(source, target)

        synapse = self.synapses[key]
        synapse["last_used"] = time.time()
        synapse["activation_count"] += 1
        synapse["phi_history"].append(phi)

        if len(synapse["phi_history"]) > 20:
            synapse["phi_history"] = synapse["phi_history"][-20:]

        avg_phi = sum(synapse["phi_history"]) / len(synapse["phi_history"])

        if avg_phi > 0.7:
            synapse["weight"] = min(1.0, synapse["weight"] + self.myelination_rate)
        elif avg_phi < 0.4:
            synapse["weight"] = max(0.0, synapse["weight"] - self.demyelination_rate)

        return synapse["weight"]

    def decay_unused_paths(self, current_time: Optional[float] = None) -> List[str]:
        """Demielinizza path non utilizzati. Restituisce lista di path prunati."""
        if current_time is None:
            current_time = time.time()

        pruned = []
        time_threshold = 3600

        for key, synapse in list(self.synapses.items()):
            inactive_time = current_time - synapse["last_used"]

            if inactive_time > time_threshold:
                synapse["weight"] = max(0.0, synapse["weight"] - self.demyelination_rate * 2)

                if synapse["weight"] <= self.pruning_threshold:
                    del self.synapses[key]
                    pruned.append(f"{key[0]}→{key[1]}")
                    logger.info(f"Sinapsi prunata: {key[0]} → {key[1]}")

        if pruned:
            self._save_state()

        return pruned

    def get_priority_paths(self, top_n: int = 5) -> List[Tuple[str, str, float]]:
        """Restituisce i path più mielinizzati (esecuzione prioritaria)."""
        sorted_synapses = sorted(
            self.synapses.items(),
            key=lambda x: x[1]["weight"],
            reverse=True
        )
        return [
            (source, target, data["weight"])
            for (source, target), data in sorted_synapses[:top_n]
        ]

    def get_reinforcement_candidates(self) -> List[Tuple[str, str, float]]:
        """Path che hanno superato la soglia di rinforzo."""
        return [
            (s, t, d["weight"])
            for (s, t), d in self.synapses.items()
            if d["weight"] > self.reinforcement_threshold
        ]

    def get_network_density(self) -> float:
        """Densità della rete (quanto è connesso il sistema)"""
        if not self.synapses:
            return 0.0
        active = sum(1 for d in self.synapses.values() if d["weight"] > 0.1)
        return active / len(self.synapses) if self.synapses else 0.0

    def get_status(self) -> Dict:
        active = sum(1 for d in self.synapses.values() if d["weight"] > 0.1)
        return {
            "total_synapses": len(self.synapses),
            "active_synapses": active,
            "network_density": self.get_network_density(),
            "priority_paths": self.get_priority_paths(3),
            "reinforcement_candidates": len(self.get_reinforcement_candidates()),
        }

    def update_from_cycle(self, active_connections: List[Tuple[str, str]], phi: float):
        """Chiamato ad ogni ciclo SMFOI."""
        for source, target in active_connections:
            self.activate_path(source, target, phi)

        pruned = self.decay_unused_paths()
        self._save_state()

        return {"activated": len(active_connections), "pruned": len(pruned)}