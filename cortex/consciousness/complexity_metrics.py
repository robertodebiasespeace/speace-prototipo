"""
SPEACE – Adaptive Complexity Metrics (A-complexity)
Basato su Adaptive Metacognition – Cleeremans et al. (2007).

A-complexity misura la capacità metacognitiva di SPEACE:
  - quanto monitora se stesso
  - quanto adatta le strategie in risposta ai risultati
  - quanto varia il suo comportamento cognitivo (plasticità)

Alta A-complexity = sistema che impara attivamente e si adatta.
Bassa A-complexity = sistema rigido, non adattivo.

Componenti:
  1. Self-monitoring score: frequenza e profondità dell'auto-monitoraggio
  2. Adaptation rate: quanto cambiano le strategie in risposta al feedback
  3. Cognitive load variation: variabilità del carico cognitivo (troppo uniforme = rigidità)
"""

import math
from typing import Dict, List, Optional


class ComplexityMetrics:
    """
    Calcola A-complexity (complessità adattiva metacognitiva) per SPEACE.
    """

    def __init__(self):
        self._cycle_history: List[Dict] = []
        self._strategy_history: List[str] = []
        self._fitness_history: List[float] = []
        self._complexity_history: List[float] = []

    def compute(self, state: Dict) -> float:
        """
        Calcola A-complexity per il ciclo corrente.

        Args:
            state: contesto ciclo SMFOI

        Returns:
            float: A-complexity in [0.0, 1.0]
        """
        # Registra snapshot del ciclo
        snapshot = self._extract_snapshot(state)
        self._cycle_history.append(snapshot)
        if len(self._cycle_history) > 100:
            self._cycle_history.pop(0)

        # Calcola i tre componenti
        sm_score = self._self_monitoring_score(snapshot)
        adapt_rate = self._adaptation_rate()
        cog_variation = self._cognitive_load_variation()

        # A-complexity = media pesata dei tre componenti
        a_complexity = (
            sm_score * 0.40 +
            adapt_rate * 0.35 +
            cog_variation * 0.25
        )

        a_complexity = max(0.0, min(1.0, a_complexity))
        self._complexity_history.append(a_complexity)
        if len(self._complexity_history) > 100:
            self._complexity_history.pop(0)

        return round(a_complexity, 4)

    def _extract_snapshot(self, state: Dict) -> Dict:
        """Estrae le feature rilevanti per la metacognizione dal contesto."""
        outcome = state.get("outcome", {})
        action = state.get("action_plan", {})
        sea = state.get("sea_state", {})
        constraints = state.get("constraints", {})
        hw = constraints.get("hardware", {})

        strategy = action.get("action", "heartbeat")
        fitness = outcome.get("fitness_after", sea.get("fitness_current", 0.0))
        fitness_delta = outcome.get("fitness_delta", 0.0)
        mutation_suggested = outcome.get("mutation_suggested", False)
        recursion_level = sea.get("recursion_level", 1)
        ram_used = hw.get("ram_used_pct", 50.0)
        cpu_used = hw.get("cpu_pct", 20.0)

        self._strategy_history.append(strategy)
        if len(self._strategy_history) > 50:
            self._strategy_history.pop(0)

        self._fitness_history.append(fitness)
        if len(self._fitness_history) > 50:
            self._fitness_history.pop(0)

        return {
            "strategy": strategy,
            "fitness": fitness,
            "fitness_delta": fitness_delta,
            "mutation_suggested": mutation_suggested,
            "recursion_level": recursion_level,
            "ram_used": ram_used,
            "cpu_used": cpu_used,
            "reflection_depth": sea.get("flags", {}).get("reflection_depth", 2),
        }

    def _self_monitoring_score(self, snapshot: Dict) -> float:
        """
        Misura quanto SPEACE monitora attivamente se stesso.

        Indicatori:
        - Recursion level alto → più meta-cognizione
        - Mutation suggested → il sistema ha rilevato un problema
        - Fitness tracking attivo
        - Reflection depth alta
        """
        score = 0.0

        # Recursion level contribuisce alla metacognizione
        rec_level = snapshot.get("recursion_level", 1)
        score += min(0.30, rec_level * 0.10)

        # Mutation suggestion indica auto-monitoraggio attivo
        if snapshot.get("mutation_suggested", False):
            score += 0.20

        # Fitness tracking (se abbiamo storia)
        if len(self._fitness_history) >= 3:
            score += 0.20

        # Reflection depth
        refl = snapshot.get("reflection_depth", 2)
        score += min(0.20, refl * 0.05)

        # Presenza di cicli precedenti (memoria del proprio comportamento)
        history_bonus = min(0.10, len(self._cycle_history) * 0.01)
        score += history_bonus

        return min(1.0, score)

    def _adaptation_rate(self) -> float:
        """
        Misura quanto le strategie cambiano in risposta al feedback.

        Alta adaptation rate = il sistema cambia strategia quando serve.
        Troppo alta = instabile. Troppo bassa = rigido.
        """
        if len(self._strategy_history) < 3:
            return 0.3  # valore neutro di default

        # Conta i cambiamenti di strategia
        changes = sum(
            1 for i in range(1, len(self._strategy_history))
            if self._strategy_history[i] != self._strategy_history[i - 1]
        )
        n = len(self._strategy_history)
        raw_rate = changes / (n - 1) if n > 1 else 0

        # Correlazione con fitness: i cambiamenti sono adattativi?
        if len(self._fitness_history) >= 3:
            # Verifica se i cambiamenti di strategia migliorano la fitness
            fitness_improvements = sum(
                1 for i in range(1, len(self._fitness_history))
                if self._fitness_history[i] > self._fitness_history[i - 1]
            )
            improvement_rate = fitness_improvements / (len(self._fitness_history) - 1)

            # A-rate ottimale: cambiamenti moderati correlati a miglioramenti
            # troppo frequenti (>0.7) o troppo rari (<0.1) = non ottimale
            if raw_rate > 0.7:
                adaptation = 0.5 * improvement_rate  # penalizza instabilità
            elif raw_rate < 0.1:
                adaptation = 0.3 * improvement_rate  # penalizza rigidità
            else:
                adaptation = 0.6 + 0.4 * improvement_rate  # range ottimale
        else:
            # Senza storia: usa solo il raw rate modulato
            if 0.1 <= raw_rate <= 0.5:
                adaptation = 0.5 + raw_rate
            else:
                adaptation = 0.3

        return min(1.0, max(0.0, adaptation))

    def _cognitive_load_variation(self) -> float:
        """
        Misura la variabilità del carico cognitivo nel tempo.

        Un sistema metacognitivo vero varia il suo carico:
        non è sempre al massimo (esaurimento) né sempre minimo (apatia).
        La varianza ottimale indica plasticità cognitiva.
        """
        if len(self._cycle_history) < 3:
            return 0.4  # default neutro

        # Calcola varianza della RAM e CPU usata
        ram_values = [c.get("ram_used", 50) for c in self._cycle_history[-20:]]
        cpu_values = [c.get("cpu_used", 20) for c in self._cycle_history[-20:]]

        def variance(values: List[float]) -> float:
            if len(values) < 2:
                return 0.0
            mean = sum(values) / len(values)
            return sum((v - mean) ** 2 for v in values) / len(values)

        var_ram = variance(ram_values)
        var_cpu = variance(cpu_values)

        # Normalizza: varianza 0 = rigidità, varianza alta = caos
        # Varianza "ottimale" ≈ 50-200 per RAM%, 10-100 per CPU%
        norm_var_ram = min(1.0, var_ram / 150.0)
        norm_var_cpu = min(1.0, var_cpu / 80.0)

        # Curva a campana: picco a varianza media
        optimal_ram = 1.0 - abs(norm_var_ram - 0.3) * 2.5
        optimal_cpu = 1.0 - abs(norm_var_cpu - 0.3) * 2.5

        variation_score = (max(0, optimal_ram) + max(0, optimal_cpu)) / 2

        # Aggiungi bonus per variabilità della fitness (apprendimento reale)
        if len(self._fitness_history) >= 5:
            fitness_var = variance(self._fitness_history[-10:])
            fitness_variation = min(1.0, fitness_var * 50)  # fitness varia poco per design
            variation_score = 0.6 * variation_score + 0.4 * fitness_variation

        return max(0.0, min(1.0, variation_score))

    def get_metacognitive_report(self) -> Dict:
        """Genera un report metacognitivo riassuntivo."""
        if not self._cycle_history:
            return {"status": "no_data"}

        last = self._cycle_history[-1]
        return {
            "cycles_tracked": len(self._cycle_history),
            "current_strategy": last.get("strategy", "?"),
            "strategy_changes": sum(
                1 for i in range(1, len(self._strategy_history))
                if self._strategy_history[i] != self._strategy_history[i - 1]
            ),
            "fitness_trend": (self._fitness_history[-1] - self._fitness_history[0]
                              if len(self._fitness_history) >= 2 else 0.0),
            "mean_a_complexity": (sum(self._complexity_history) / len(self._complexity_history)
                                  if self._complexity_history else 0.0),
            "plasticity_index": self._adaptation_rate(),
        }

    def get_history(self) -> List[float]:
        return list(self._complexity_history)
