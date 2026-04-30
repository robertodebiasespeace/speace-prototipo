"""
cortex.mesh.adapters — Neuron Adapters for existing SPEACE components (M4.8)

Questo pacchetto espone i comparti del Cortex (9 comparti M3+M3L), il
`DigitalDNA` (mutazioni epigenetiche) e lo `SPEACE Team Scientifico` (SPT)
come **neuroni** della Continuous Neural Mesh (CNM).

Design:
  - Ogni adapter è una funzione decorata con `@neuron(...)` che espone un
    contratto OLC → OLC ben tipizzato.
  - Il comparto sottostante viene istanziato **lazy** al primo `execute` per
    non causare side-effect all'import (coerente con la policy di
    `cortex.cognitive_autonomy`).
  - I neuroni sono **opt-in**: vengono scoperti solo se esplicitamente
    inclusi nel walk di `discover_neurons(["cortex.mesh.adapters"])`. Il
    boot CNM decide quali caricare in base a `epigenome.yaml`.
  - Robustezza: ogni adapter wrappa l'esecuzione del comparto in un
    try/except difensivo e restituisce un OLC frame coerente anche in
    caso di errore (es. ActionResult con `ok=False, error=...`). Questo
    evita che una failure di un comparto in-boot invalidi l'intera mesh.

Milestone: M4.8 (PROP-CORTEX-NEURAL-MESH-M4)

Moduli:
  - `compartments` — 9 comparti Cortex come neuroni mesh
  - `digitaldna`   — DigitalDNA ops (apply/evaluate mutazioni)
  - `scientific_team` — SPT Orchestrator come neurone multi-expert

Registrazione tipica (M4.14 daemon):

    from cortex.mesh.registry import discover_neurons
    from cortex.mesh.graph import MeshGraph

    rep = discover_neurons("cortex.mesh.adapters")
    graph = MeshGraph()
    graph.attach_from_registry()
    graph.auto_wire()           # topologia di default rispettosa dei tipi

Filosofia "Neurone vs Comparto":
  Un "comparto" è un'unità macro di coordinazione (N4 NeuralFlow), con
  stato interno e chiamate multiple. Un "neurone" è un'unità atomica,
  stateless e idempotente. Gli adapter trasformano i primi nei secondi
  **senza modificare i comparti**: il comparto resta come nel pipeline
  classico (SMFOI-KERNEL), la mesh è un percorso parallelo adottivo.
"""

from __future__ import annotations

__all__: list[str] = []

__version__ = "1.0.0-m4.8"
