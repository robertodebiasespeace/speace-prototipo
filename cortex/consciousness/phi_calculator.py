"""
SPEACE – Phi (Φ) Calculator
Implementa tre livelli di approssimazione della metrica Φ (IIT – Integrated Information Theory).

Φ misura quanta informazione il sistema genera come un TUTTO rispetto alle sue parti.
Φ alto → il sistema è cognitivamente integrato (nessun comparto funziona in isolamento).
Φ basso → i comparti lavorano in silos, senza integrazione.

Livelli:
  Fast-Φ  : entropia differenziale (leggerissimo, per ogni ciclo SMFOI)
  Medium-Φ : analisi grafo di connettività dei comparti Cortex
  Full-Φ  : Minimum Information Partition (pesante, per audit periodici)

Riferimento: Tononi, G. (2004). An information integration theory of consciousness.
"""

import math
import time
from typing import List, Dict, Optional


class PhiCalculator:
    """
    Calcola la metrica Φ (phi) di integrazione dell'informazione
    per il SPEACE Cortex a 9 comparti.
    """

    # Nomi dei 9 comparti Cortex di SPEACE
    CORTEX_COMPARTMENTS = [
        "prefrontal_cortex",
        "hippocampus",
        "safety_module",
        "temporal_lobe",
        "parietal_lobe",
        "cerebellum",
        "default_mode_network",
        "curiosity_module",
        "world_model",
    ]

    def __init__(self, mode: str = "fast"):
        """
        Args:
            mode: "fast" | "medium" | "full"
        """
        self.mode = mode
        self._history: List[float] = []

    def compute(self, state: Dict) -> float:
        """
        Calcola Φ in base alla modalità configurata.

        Args:
            state: dizionario con lo stato corrente del ciclo SMFOI
                   (contiene informazioni sui comparti attivi, metriche, ecc.)

        Returns:
            float: valore Φ in [0.0, 1.0]
        """
        if self.mode == "fast":
            phi = self._fast_phi(state)
        elif self.mode == "medium":
            phi = self._medium_phi(state)
        else:
            phi = self._full_phi(state)

        phi = max(0.0, min(1.0, phi))
        self._history.append(phi)
        if len(self._history) > 100:
            self._history.pop(0)
        return round(phi, 4)

    def _fast_phi(self, state: Dict) -> float:
        """
        Fast-Φ: approssimazione tramite entropia differenziale.
        Misura quanto è distribuita l'attività tra i 9 comparti.
        Entropia alta = attività distribuita = Φ alto.
        Entropia bassa = un solo comparto attivo = Φ basso.

        Non richiede librerie esterne.
        """
        # Estrai vettore di attivazioni dei comparti dal contesto del ciclo
        activations = self._extract_compartment_activations(state)

        # Normalizza le attivazioni come distribuzione di probabilità
        total = sum(activations)
        if total == 0:
            return 0.0

        probs = [a / total for a in activations]

        # Calcola entropia di Shannon
        entropy_total = -sum(p * math.log2(p) for p in probs if p > 0)

        # Calcola entropia massima teorica (distribuzione uniforme su N comparti)
        n = len(probs)
        entropy_max = math.log2(n) if n > 1 else 1.0

        # Φ come rapporto: 0 = concentrato su un comparto, 1 = perfettamente distribuito
        phi_raw = entropy_total / entropy_max if entropy_max > 0 else 0.0

        # Differenziale rispetto alla partizione in due metà (approssimazione IIT)
        half = n // 2
        probs_a = probs[:half]
        probs_b = probs[half:]

        total_a = sum(probs_a)
        total_b = sum(probs_b)

        entropy_a = -sum((p / total_a) * math.log2(p / total_a)
                         for p in probs_a if p > 0) if total_a > 0 else 0
        entropy_b = -sum((p / total_b) * math.log2(p / total_b)
                         for p in probs_b if p > 0) if total_b > 0 else 0

        max_half = math.log2(half) if half > 1 else 1.0
        entropy_partitioned = ((entropy_a / max_half if max_half > 0 else 0) +
                               (entropy_b / max_half if max_half > 0 else 0)) / 2

        # Φ = entropia totale - entropia partizionata (informazione irriducibile)
        phi = max(0.0, phi_raw - entropy_partitioned * 0.5)
        return phi

    def _medium_phi(self, state: Dict) -> float:
        """
        Medium-Φ: analisi grafo di connettività dei comparti.
        Usa solo Python standard (nessuna dipendenza esterna).

        Costruisce una matrice di adiacenza simbolica basata sulle
        interazioni implicite tra i comparti nel ciclo corrente.
        """
        # Matrice di connettività simbolica del Cortex SPEACE (9x9)
        # Basata sull'architettura: chi parla con chi per design
        # 1 = connessione diretta, 0 = nessuna connessione diretta
        connectivity = [
            # PFC  HIP  SAF  TEM  PAR  CER  DMN  CUR  WM
            [0,    1,   1,   1,   1,   0,   1,   1,   1],  # Prefrontal
            [1,    0,   0,   1,   0,   0,   1,   0,   1],  # Hippocampus
            [1,    0,   0,   0,   0,   1,   0,   0,   1],  # Safety Module
            [1,    1,   0,   0,   1,   0,   1,   0,   1],  # Temporal Lobe
            [1,    0,   0,   1,   0,   1,   0,   1,   1],  # Parietal Lobe
            [0,    0,   1,   0,   1,   0,   0,   0,   0],  # Cerebellum
            [1,    1,   0,   1,   0,   0,   0,   1,   1],  # Default Mode Network
            [1,    0,   0,   0,   1,   0,   1,   0,   1],  # Curiosity Module
            [1,    1,   1,   1,   1,   0,   1,   1,   0],  # World Model
        ]

        n = len(connectivity)
        activations = self._extract_compartment_activations(state)
        total_act = sum(activations)
        if total_act == 0:
            return 0.0

        # Centralità approssimata: per ogni nodo, somma dei vicini attivi pesata
        centrality = []
        for i in range(n):
            neighbors_active = sum(
                connectivity[i][j] * (activations[j] / total_act)
                for j in range(n) if connectivity[i][j] > 0
            )
            centrality.append(neighbors_active)

        # Clustering locale approssimato
        clustering = []
        for i in range(n):
            neighbors = [j for j in range(n) if connectivity[i][j] > 0]
            if len(neighbors) < 2:
                clustering.append(0.0)
                continue
            triangles = sum(
                1 for j in neighbors for k in neighbors
                if j != k and connectivity[j][k] > 0
            )
            possible = len(neighbors) * (len(neighbors) - 1)
            clustering.append(triangles / possible if possible > 0 else 0.0)

        mean_centrality = sum(centrality) / n if n > 0 else 0
        mean_clustering = sum(clustering) / n if n > 0 else 0

        # Φ medium = prodotto di centralità e clustering (come nel paper)
        phi = mean_centrality * mean_clustering * 2.0  # scala a [0,1]
        return min(1.0, phi)

    def _full_phi(self, state: Dict) -> float:
        """
        Full-Φ: Minimum Information Partition (MIP).
        Computazionalmente pesante – usare solo per audit periodici.
        Approssimazione pratica senza librerie ML pesanti.
        """
        activations = self._extract_compartment_activations(state)
        n = len(activations)
        total = sum(activations)
        if total == 0:
            return 0.0

        probs = [a / total for a in activations]
        entropy_whole = -sum(p * math.log2(p) for p in probs if p > 0)

        # Prova tutte le bipartizioni e trova la MIP (quella che minimizza Φ)
        min_phi = float('inf')
        partitions = self._generate_bipartitions(n)

        for part_a, part_b in partitions:
            if not part_a or not part_b:
                continue

            probs_a = [probs[i] for i in part_a]
            probs_b = [probs[i] for i in part_b]

            sum_a = sum(probs_a)
            sum_b = sum(probs_b)

            ent_a = (-sum((p / sum_a) * math.log2(p / sum_a)
                          for p in probs_a if p > 0)
                     if sum_a > 0 else 0)
            ent_b = (-sum((p / sum_b) * math.log2(p / sum_b)
                          for p in probs_b if p > 0)
                     if sum_b > 0 else 0)

            # Effective information di questa partizione
            max_ent_a = math.log2(len(probs_a)) if len(probs_a) > 1 else 1.0
            max_ent_b = math.log2(len(probs_b)) if len(probs_b) > 1 else 1.0
            norm_a = ent_a / max_ent_a if max_ent_a > 0 else 0
            norm_b = ent_b / max_ent_b if max_ent_b > 0 else 0
            partition_phi = abs(norm_a - norm_b)

            if partition_phi < min_phi:
                min_phi = partition_phi

        # Φ = entropia totale - MIP (informazione irriducibile alle parti)
        max_ent = math.log2(n) if n > 1 else 1.0
        phi = max(0.0, (entropy_whole / max_ent) - min_phi)
        return min(1.0, phi)

    def _extract_compartment_activations(self, state: Dict) -> List[float]:
        """
        Estrae un vettore di attivazione per ciascun comparto Cortex
        dal contesto del ciclo SMFOI.
        """
        activations = []

        # Usa i dati del ciclo per inferire l'attivazione simbolica di ciascun comparto
        sea = state.get("sea_state", {})
        constraints = state.get("constraints", {})
        push = state.get("push", {})
        action = state.get("action_plan", {})
        outcome = state.get("outcome", {})

        # Prefrontal Cortex: attivo quando c'è planning (sempre un po')
        activations.append(0.7 + 0.3 * min(1.0, sea.get("fitness_current", 0.5)))

        # Hippocampus: attivo proporzionalmente ai cicli accumulati
        activations.append(min(1.0, 0.2 + 0.1 * min(8, sea.get("cycle", 1))))

        # Safety Module: più attivo con safe_mode e vincoli
        safe = 1.0 if sea.get("flags", {}).get("safe_mode", True) else 0.3
        activations.append(safe)

        # Temporal Lobe: attivo con push di tipo linguaggio/analisi
        lang_active = 0.5 + 0.5 * (1.0 if push.get("type") in ["user_request", "brief"] else 0.0)
        activations.append(lang_active)

        # Parietal Lobe: attivo con dati sensoriali/IoT/API
        parietal = 0.4 + 0.6 * (1.0 if push.get("source") in ["api", "iot", "external"] else 0.0)
        activations.append(parietal)

        # Cerebellum: attivo durante esecuzione (step 5)
        action_type = action.get("action", "")
        cerebellum = 0.8 if action_type in ["stabilize", "optimize_epigenome"] else 0.3
        activations.append(cerebellum)

        # Default Mode Network: attivo in heartbeat/riflessione
        dmn = 0.9 if action_type == "heartbeat" else 0.4
        activations.append(dmn)

        # Curiosity Module: attivo con exploration alta
        exploration = state.get("epigenome_snapshot", {}).get("exploration_rate", 0.15)
        activations.append(0.2 + 0.8 * exploration)

        # World Model: sempre moderatamente attivo
        activations.append(0.6 + 0.4 * (1.0 if outcome.get("success", False) else 0.0))

        return activations

    def _generate_bipartitions(self, n: int) -> List[tuple]:
        """
        Genera tutte le bipartizioni di n elementi (per Full-Φ).
        Limitato a n<=9 per praticità.
        """
        partitions = []
        for mask in range(1, (1 << n) - 1):
            part_a = [i for i in range(n) if mask & (1 << i)]
            part_b = [i for i in range(n) if not (mask & (1 << i))]
            # Evita duplicati (A,B) == (B,A)
            if len(part_a) <= n // 2 or (len(part_a) == n // 2 and part_a[0] == 0):
                partitions.append((part_a, part_b))
        return partitions

    def get_history(self) -> List[float]:
        return list(self._history)

    def get_trend(self) -> float:
        """Tendenza recente di Φ: positiva = in crescita."""
        if len(self._history) < 2:
            return 0.0
        recent = self._history[-5:]
        if len(recent) < 2:
            return 0.0
        return recent[-1] - recent[0]
