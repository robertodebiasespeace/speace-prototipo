"""
InferenceEngine — M6.4 (World Model / Inference)

Motore di inferenza causale per scenari "what-if" sul WorldSnapshot.
Supporta:
  - Regole causali (IF condizione THEN effetti)
  - Simulazione di scenari: applica un set di variazioni e calcola effetti
  - Scoring di plausibilità e impatto Rigene
  - Output compatibile con WorldSnapshot.scenarios

Milestone: M6.4
Versione: 1.0 | 2026-04-27
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("speace.world_model.inference")


# ---------------------------------------------------------------------------
# Causal rules
# ---------------------------------------------------------------------------

@dataclass
class CausalRule:
    """
    Regola causale: IF condition(snapshot) THEN effetti.
    """
    rule_id:     str
    description: str
    condition:   Callable[[Dict[str, Any]], bool]   # (snapshot_dict) → bool
    effects:     List[Tuple[str, Any]]               # [(path, delta_or_value), ...]
    confidence:  float = 0.80                        # [0..1]
    domain:      str = "general"                     # "climate", "social", "tech", ...
    rigene_impact: float = 0.0                       # [-1..+1] impatto su obiettivi Rigene


# ---------------------------------------------------------------------------
# Built-in rule library
# ---------------------------------------------------------------------------

def _get(d: dict, path: str, default: Any = None) -> Any:
    """Legge un valore da dict tramite path puntato."""
    node = d
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


BUILTIN_RULES: List[CausalRule] = [
    CausalRule(
        rule_id="R001",
        description="CO2 > 430 ppm → global temp anomaly increases (+0.1°C)",
        condition=lambda s: (_get(s, "planet_state.climate.co2_ppm") or 0) > 430,
        effects=[("planet_state.climate.global_temp_anomaly_c", +0.1)],
        confidence=0.85, domain="climate", rigene_impact=-0.15,
    ),
    CausalRule(
        rule_id="R002",
        description="Climate status critical → SDG13 progress regresses",
        condition=lambda s: _get(s, "planet_state.climate.status") == "critical",
        effects=[("planet_state.social.sdg_progress", "insufficient")],
        confidence=0.90, domain="climate", rigene_impact=-0.20,
    ),
    CausalRule(
        rule_id="R003",
        description="SPEACE phase ≥ 2 → AI capability escalates",
        condition=lambda s: (_get(s, "speace_state.phase") or 1) >= 2,
        effects=[("technology_state.ai_capability_level", "general")],
        confidence=0.70, domain="tech", rigene_impact=+0.25,
    ),
    CausalRule(
        rule_id="R004",
        description="Biodiversity declining + climate critical → species risk > 35%",
        condition=lambda s: (
            _get(s, "planet_state.biodiversity.status") == "declining"
            and _get(s, "planet_state.climate.status") == "critical"
        ),
        effects=[("planet_state.biodiversity.species_at_risk_pct", 35.0)],
        confidence=0.75, domain="ecosystem", rigene_impact=-0.30,
    ),
    CausalRule(
        rule_id="R005",
        description="SPEACE M5 complete → fitness improves",
        condition=lambda s: _get(s, "speace_state.m5_complete") is True,
        effects=[("speace_state.fitness", 0.72)],
        confidence=0.95, domain="speace", rigene_impact=+0.10,
    ),
    CausalRule(
        rule_id="R006",
        description="IoT devices > 20B → integration opportunities increase",
        condition=lambda s: (_get(s, "technology_state.iot_connected_devices_bn") or 0) > 20,
        effects=[("technology_state.integration_readiness", "high")],
        confidence=0.65, domain="tech", rigene_impact=+0.15,
    ),
]


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """Un singolo scenario what-if."""
    scenario_id:    str
    name:           str
    description:    str
    interventions:  Dict[str, Any]           # path → new_value (input)
    triggered_rules: List[str] = field(default_factory=list)
    effects:        Dict[str, Any] = field(default_factory=dict)  # path → final_value
    plausibility:   float = 0.0              # [0..1] media confidenza regole attivate
    rigene_score:   float = 0.0              # [−1..+1] impatto aggregato Rigene
    ts:             Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id":     self.scenario_id,
            "name":            self.name,
            "description":     self.description,
            "interventions":   self.interventions,
            "triggered_rules": self.triggered_rules,
            "effects":         self.effects,
            "plausibility":    round(self.plausibility, 3),
            "rigene_score":    round(self.rigene_score, 3),
            "ts":              self.ts,
        }


# ---------------------------------------------------------------------------
# InferenceEngine
# ---------------------------------------------------------------------------

def _set_path(d: dict, path: str, value: Any) -> None:
    """Imposta un valore in dict tramite path puntato (crea nodi intermedi)."""
    parts = path.split(".")
    node = d
    for part in parts[:-1]:
        if part not in node or not isinstance(node[part], dict):
            node[part] = {}
        node = node[part]
    leaf = parts[-1]
    # Delta support: if value is a float and existing value is float, add
    existing = node.get(leaf)
    if isinstance(value, float) and isinstance(existing, float):
        node[leaf] = existing + value
    else:
        node[leaf] = value


class InferenceEngine:
    """
    M6.4 — Motore di inferenza causale sul WorldSnapshot.

    Uso:
        engine = InferenceEngine()
        engine.load_rules(BUILTIN_RULES)

        # Applica regole sullo snapshot corrente
        active = engine.apply_rules(snapshot_dict)

        # Simula uno scenario what-if
        scenario = engine.simulate(
            snapshot_dict,
            name="CO2 spike",
            interventions={"planet_state.climate.co2_ppm": 445.0},
        )
    """

    def __init__(self, rules: Optional[List[CausalRule]] = None) -> None:
        self._rules = list(rules or BUILTIN_RULES)
        self._scenario_counter = 0

    def load_rules(self, rules: List[CausalRule]) -> None:
        self._rules = list(rules)

    def add_rule(self, rule: CausalRule) -> None:
        self._rules.append(rule)

    # ----------------------------------------------------------- apply rules

    def apply_rules(
        self,
        snapshot: Dict[str, Any],
        domain_filter: Optional[str] = None,
    ) -> List[CausalRule]:
        """
        Applica le regole causali allo snapshot e ritorna quelle che si attivano.
        Non modifica lo snapshot originale.
        """
        activated: List[CausalRule] = []
        for rule in self._rules:
            if domain_filter and rule.domain != domain_filter:
                continue
            try:
                if rule.condition(snapshot):
                    activated.append(rule)
                    logger.debug("[InferenceEngine] rule %s activated", rule.rule_id)
            except Exception as e:
                logger.warning("[InferenceEngine] rule %s error: %s", rule.rule_id, e)
        return activated

    # ----------------------------------------------------------- what-if simulation

    def simulate(
        self,
        snapshot: Dict[str, Any],
        name: str,
        interventions: Dict[str, Any],
        description: str = "",
        max_iterations: int = 3,
    ) -> Scenario:
        """
        Simula uno scenario what-if.

        1. Copia lo snapshot
        2. Applica le `interventions` (path → value)
        3. Itera l'applicazione delle regole fino a convergenza (max_iterations)
        4. Calcola plausibility e rigene_score

        Returns:
            Scenario con gli effetti computati.
        """
        self._scenario_counter += 1
        sc_id = f"SC-{self._scenario_counter:04d}"
        sim = copy.deepcopy(snapshot)

        # Apply interventions
        for path, value in interventions.items():
            _set_path(sim, path, value)

        # Iterate rules
        all_triggered: List[str] = []
        all_effects:   Dict[str, Any] = {}
        confidence_sum = 0.0
        rigene_sum = 0.0

        for _iter in range(max_iterations):
            activated = self.apply_rules(sim)
            new_triggers = [r.rule_id for r in activated if r.rule_id not in all_triggered]
            if not new_triggers:
                break
            for rule in activated:
                if rule.rule_id not in all_triggered:
                    all_triggered.append(rule.rule_id)
                    confidence_sum += rule.confidence
                    rigene_sum += rule.rigene_impact
                    for path, val in rule.effects:
                        _set_path(sim, path, val)
                        all_effects[path] = _get(sim, path)

        plausibility = (confidence_sum / len(all_triggered)) if all_triggered else 0.0
        rigene_score = max(-1.0, min(1.0, rigene_sum / max(1, len(all_triggered))))

        scenario = Scenario(
            scenario_id=sc_id,
            name=name,
            description=description or f"What-if: {', '.join(f'{k}={v}' for k,v in interventions.items())}",
            interventions=interventions,
            triggered_rules=all_triggered,
            effects=all_effects,
            plausibility=plausibility,
            rigene_score=rigene_score,
            ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        logger.info("[InferenceEngine] scenario %s: %d rules triggered, rigene=%.3f",
                    sc_id, len(all_triggered), rigene_score)
        return scenario

    # ----------------------------------------------------------- batch scenarios

    def run_standard_scenarios(self, snapshot: Dict[str, Any]) -> List[Scenario]:
        """Esegue i 3 scenari standard di SPEACE."""
        scenarios = []

        # S1: CO2 spike
        scenarios.append(self.simulate(
            snapshot, name="CO2 Spike +20ppm",
            interventions={"planet_state.climate.co2_ppm": 445.0},
            description="CO2 aumenta di 20 ppm rispetto al baseline",
        ))
        # S2: SPEACE advances to phase 2
        scenarios.append(self.simulate(
            snapshot, name="SPEACE Phase 2",
            interventions={"speace_state.phase": 2},
            description="SPEACE avanza alla fase 2 di autonomia operativa",
        ))
        # S3: IoT expansion
        scenarios.append(self.simulate(
            snapshot, name="IoT Expansion 25B",
            interventions={"technology_state.iot_connected_devices_bn": 25},
            description="Espansione IoT a 25 miliardi di dispositivi connessi",
        ))
        return scenarios

    def get_stats(self) -> Dict[str, Any]:
        return {
            "rules_loaded":     len(self._rules),
            "scenarios_run":    self._scenario_counter,
            "domains":          list({r.domain for r in self._rules}),
        }


__all__ = ["CausalRule", "Scenario", "InferenceEngine", "BUILTIN_RULES"]
