"""
SPEACE Cortex Mesh — Continuous Neural Mesh (M4-CNM)

Grafo tipizzato adattivo di neuroni-script + Needs Driver + Daemon di background,
con Organism Language Contract (OLC) come protocollo di interoperabilità.

Milestone: M4 (PROP-CORTEX-NEURAL-MESH-M4, approved 2026-04-19)
Stato: in costruzione — opt-in, feature flag `epigenome.mesh.enabled` default OFF.

Moduli principali:
  - olc/                 (M4.3): ✅ Organism Language Contract — registry tipi condivisi
                                 (12 tipi seed v1.0, smoke test 6/6 pass 2026-04-20)
  - contract.py          (M4.2): ✅ validatore statico/runtime del NeuronContract
                                 (37/37 test pass, AC-1..AC-10, CONTRACT_VERSION=1.0)
  - execution_rules.yaml (M4.4): ✅ ceiling strutturali runtime mesh (v1.0)
  - execution_rules.py   (M4.4): ✅ loader tipato thread-safe + whitelist helpers
                                 (smoke test 8/8 pass 2026-04-20,
                                  contract.py integrato via _ceilings_from_rules)
  - graph.py             (M4.5): ✅ DAG tipizzato adattivo (MeshGraph)
                                 (18/18 test pass, 100 neuroni+99 archi+topo in 6.7ms,
                                  cycle-reject/type-check/auto_wire/find_paths/layers)
  - runtime.py           (M4.6): ✅ scheduler asincrono con backpressure/harmony safeguard
                                 (11/11 test pass, RUNTIME_VERSION=1.0,
                                  lifecycle+submit+propagate+strike+quarantine+heartbeat
                                  +freeze/resume+throughput 200 task in 110ms con 4 worker,
                                  fail-safe error_rate>50% per ≥2 heartbeat → FROZEN)
  - registry.py          (M4.7): neuron discovery via decoratore @neuron
  - neurons/             (M4.8): adapter per 9 comparti Cortex, DNA, Scientific Team
  - needs_driver.py      (M4.9): modello bisogni survival/expansion/self-impr/integration/harmony
  - harmony.py           (M4.10): policy di equilibrio
  - task_generator.py    (M4.11): bisogni → proposte SafeProactive
  - telemetry.py         (M4.13): mesh_state.jsonl append-only audit
  - plasticity.py        (M5 — rimandato come da decisione 11.2)
"""

__version__ = "0.5.0-dev"  # bumped at M4.5 close (MeshGraph landed)
