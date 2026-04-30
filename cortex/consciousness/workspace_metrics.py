"""
SPEACE – Global Workspace Metrics (W-activation)
Basato su Global Workspace Theory (GWT) – Baars, 1988.

Il Global Workspace è uno spazio cognitivo a capacità LIMITATA dove
le informazioni più salienti "vincono la competizione" e vengono trasmesse
in broadcast a tutti gli altri comparti del Cortex.

W-activation misura la percentuale di slot del workspace effettivamente
attivati in un ciclo. Alta W-activation = buona distribuzione dell'informazione.

Implementazione SPEACE:
  - Il World Model funge da Global Workspace centrale
  - I 9 comparti competono per accedere al workspace
  - Solo i top-k per salienza ottengono l'accesso broadcast
  - W-activation = k_attivi / capacità_totale
"""

import math
from typing import Dict, List, Tuple


class WorkspaceMetrics:
    """
    Implementa il meccanismo di workspace globale ispirato a GWT
    e calcola la metrica W-activation per il C-index di SPEACE.
    """

    WORKSPACE_CAPACITY = 4  # slot limitati (ispirato al "magical number 4" della cognizione)

    # Salienza base di ciascun comparto (quanto compete per il workspace)
    BASE_SALIENCE = {
        "prefrontal_cortex":    0.85,  # planning → alta priorità
        "hippocampus":          0.70,  # memoria → alta
        "safety_module":        0.95,  # sicurezza → massima priorità
        "temporal_lobe":        0.65,  # linguaggio → media-alta
        "parietal_lobe":        0.55,  # sensoriale → media
        "cerebellum":           0.40,  # esecuzione → bassa (automatica)
        "default_mode_network": 0.60,  # riflessione → media
        "curiosity_module":     0.50,  # esplorazione → media
        "world_model":          0.80,  # knowledge hub → alta
    }

    def __init__(self, capacity: int = None):
        self.capacity = capacity or self.WORKSPACE_CAPACITY
        self._workspace_memory: List[str] = []   # comparti nell'ultimo workspace
        self._activation_history: List[float] = []
        self._broadcast_log: List[Dict] = []

    def compute(self, state: Dict) -> Tuple[float, List[str]]:
        """
        Calcola W-activation per il ciclo corrente.

        Args:
            state: contesto ciclo SMFOI

        Returns:
            Tuple[float, List[str]]:
                - W-activation in [0.0, 1.0]
                - lista dei comparti che hanno accesso al workspace
        """
        # 1. Calcola salienza contestuale per ogni comparto
        saliences = self._compute_contextual_saliences(state)

        # 2. Competizione: top-k per salienza ottengono l'accesso
        k = self.capacity // 2  # solo metà del workspace è "new content"
        ranked = sorted(saliences.items(), key=lambda x: x[1], reverse=True)
        winners = [name for name, _ in ranked[:k]]

        # 3. Aggiorna workspace memory con persistenza parziale (80%)
        persistence = 0.8
        persisted = self._workspace_memory[:int(len(self._workspace_memory) * persistence)]
        new_entries = [w for w in winners if w not in persisted]
        self._workspace_memory = (persisted + new_entries)[:self.capacity]

        # 4. Calcola W-activation = slot occupati / capacità totale
        unique_active = list(set(self._workspace_memory))
        w_activation = len(unique_active) / self.capacity

        # 5. Registra
        self._activation_history.append(w_activation)
        if len(self._activation_history) > 100:
            self._activation_history.pop(0)

        broadcast = {
            "cycle_id": state.get("cycle_id", "?"),
            "winners": winners,
            "workspace": unique_active,
            "w_activation": round(w_activation, 4),
            "saliences": {k: round(v, 3) for k, v in saliences.items()},
        }
        self._broadcast_log.append(broadcast)
        if len(self._broadcast_log) > 50:
            self._broadcast_log.pop(0)

        return round(w_activation, 4), unique_active

    def _compute_contextual_saliences(self, state: Dict) -> Dict[str, float]:
        """
        Modula la salienza base di ciascun comparto in base al contesto del ciclo.
        """
        saliences = dict(self.BASE_SALIENCE)

        push = state.get("push", {})
        action = state.get("action_plan", {})
        sea = state.get("sea_state", {})
        constraints = state.get("constraints", {})

        push_type = push.get("type", "none")
        push_priority = push.get("priority", 0)
        action_type = action.get("action", "heartbeat")

        # Modula in base al tipo di push
        if push_type == "user_request":
            saliences["prefrontal_cortex"] += 0.10
            saliences["temporal_lobe"] += 0.15
            saliences["hippocampus"] += 0.05
        elif push_type == "pending_proposals":
            saliences["safety_module"] += 0.05
            saliences["prefrontal_cortex"] += 0.05
        elif push_type in ["iot_event", "sensor_data"]:
            saliences["parietal_lobe"] += 0.20
            saliences["world_model"] += 0.10

        # Modula in base all'azione pianificata
        if action_type == "heartbeat":
            saliences["default_mode_network"] += 0.15
            saliences["curiosity_module"] += 0.10
        elif action_type == "stabilize":
            saliences["safety_module"] += 0.10
            saliences["cerebellum"] += 0.20
        elif action_type in ["optimize_epigenome", "propose_evolution"]:
            saliences["default_mode_network"] += 0.10
            saliences["curiosity_module"] += 0.15
            saliences["world_model"] += 0.05

        # Modula in base ai vincoli di risorse
        hw = constraints.get("hardware", {})
        if hw.get("ram_used_pct", 0) > 75:
            saliences["safety_module"] += 0.15  # safety diventa ancora più saliente
            saliences["cerebellum"] -= 0.10     # meno esecuzione

        # Modula in base alla fitness
        fitness = sea.get("fitness_current", 0.5)
        if fitness < 0.4:
            saliences["default_mode_network"] += 0.10  # più riflessione
        elif fitness > 0.8:
            saliences["curiosity_module"] += 0.15      # più esplorazione

        # Normalizza in [0, 1]
        saliences = {k: max(0.0, min(1.0, v)) for k, v in saliences.items()}
        return saliences

    def get_broadcast_info(self) -> Dict:
        """Ritorna l'ultima snapshot del workspace broadcast."""
        if self._broadcast_log:
            return self._broadcast_log[-1]
        return {}

    def get_history(self) -> List[float]:
        return list(self._activation_history)

    def get_mean_activation(self, window: int = 10) -> float:
        """Media W-activation degli ultimi N cicli."""
        recent = self._activation_history[-window:]
        return sum(recent) / len(recent) if recent else 0.0
