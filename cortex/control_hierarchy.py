"""
SPEACE Cortex – Control Hierarchy
Gerarchia di controllo a 5 livelli che organizza i 9 comparti.

Concetto cardine:
  Il Cortex NON è una lista di 9 comparti indipendenti — è la *dinamica*
  tra i comparti, regolata da una gerarchia esplicita di controllo.

Livelli (dal più alto al più basso):
  L1 – Controllo       : Prefrontal Cortex + Safety Module (override assoluto)
  L2 – Cognizione      : Temporal Lobe, World Model, Default Mode Network
  L3 – Memoria         : Hippocampus
  L4 – Azione          : Parietal Lobe (sensoriale), Cerebellum (motoria)
  L5 – Evoluzione      : Curiosity Module

Regole fondamentali:
  - Safety Module (L1, override=True) può bloccare il flusso in qualunque momento.
    Dopo un blocco, nessun comparto ≥ L2 deve processare (verificato via
    state.safety_flags.blocked).
  - Prefrontal (L1) decide, Safety (L1) veta. Il conflitto si risolve con
    precedenza al veto (Safety-first principle).
  - L2/L3 producono contesto; L4 esegue; L5 suggerisce mutazioni da inviare
    a SafeProactive (MAI esegue direttamente mutazioni).
  - Ogni comparto deve ereditare BaseCompartment e dichiarare `level`.

Questo modulo NON esegue i comparti: espone solo metadata strutturale
(ordering, precedenza, validazione). L'esecuzione è compito di NeuralFlow.

Creato: 2026-04-19 | M3L.2 | PROP-CORTEX-NEURAL-M3L
"""

from __future__ import annotations
from typing import Dict, List, Tuple


# Mappa canonica comparto → livello
COMPARTMENT_LEVELS: Dict[str, int] = {
    "prefrontal_cortex":     1,
    "safety_module":         1,
    "temporal_lobe":         2,
    "world_model":           2,
    "default_mode_network":  2,
    "hippocampus":           3,
    "parietal_lobe":         4,
    "cerebellum":            4,
    "curiosity_module":      5,
}

LEVEL_NAMES: Dict[int, str] = {
    1: "Controllo",
    2: "Cognizione",
    3: "Memoria",
    4: "Azione",
    5: "Evoluzione",
}

# Solo questi comparti hanno potere di override sul flusso
OVERRIDE_ALLOWED = {"safety_module"}


def level_of(compartment_name: str) -> int:
    """Ritorna il livello di un comparto, o 99 se sconosciuto."""
    return COMPARTMENT_LEVELS.get(compartment_name, 99)


def sort_by_level(compartments: List) -> List:
    """
    Ordina una lista di compartment instance per livello crescente,
    poi alfabeticamente (per riproducibilità).
    """
    return sorted(compartments, key=lambda c: (level_of(getattr(c, "name", "")),
                                               getattr(c, "name", "")))


def validate_hierarchy(compartments: List) -> List[str]:
    """
    Verifica che ogni comparto dichiari un livello coerente con la mappa canonica.
    Ritorna lista di issue (vuota se tutto OK).
    """
    issues: List[str] = []
    seen_names = set()
    for c in compartments:
        name = getattr(c, "name", None)
        declared_level = getattr(c, "level", None)
        if not name:
            issues.append(f"compartment_missing_name:{c!r}")
            continue
        if name in seen_names:
            issues.append(f"duplicate_compartment:{name}")
        seen_names.add(name)
        canonical = COMPARTMENT_LEVELS.get(name)
        if canonical is None:
            issues.append(f"compartment_not_in_canonical_map:{name}")
        elif declared_level != canonical:
            issues.append(
                f"level_mismatch:{name} declared={declared_level} canonical={canonical}"
            )
        # Solo Safety può avere override attivo
        if getattr(c, "_OVERRIDE_ALLOWED", False) and name not in OVERRIDE_ALLOWED:
            issues.append(f"unauthorized_override:{name}")
    return issues


def level_description(level: int) -> str:
    return LEVEL_NAMES.get(level, f"L{level}?")


def resolve_precedence(candidate_a: str, candidate_b: str) -> str:
    """
    Regola di precedenza tra due comparti in conflitto.
    1) override > non-override (Safety > Prefrontal su veti)
    2) livello più basso vince (L1 > L2 > ...)
    3) in parità, alfabetico
    """
    a_override = candidate_a in OVERRIDE_ALLOWED
    b_override = candidate_b in OVERRIDE_ALLOWED
    if a_override and not b_override:
        return candidate_a
    if b_override and not a_override:
        return candidate_b
    la, lb = level_of(candidate_a), level_of(candidate_b)
    if la < lb:
        return candidate_a
    if lb < la:
        return candidate_b
    return sorted([candidate_a, candidate_b])[0]


def summary() -> Dict[str, List[str]]:
    """Ritorna un summary testuale della gerarchia (per documentazione)."""
    out: Dict[str, List[str]] = {}
    for name, lvl in sorted(COMPARTMENT_LEVELS.items(), key=lambda x: (x[1], x[0])):
        key = f"L{lvl} – {LEVEL_NAMES[lvl]}"
        out.setdefault(key, []).append(name)
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(summary(), indent=2, ensure_ascii=False))
