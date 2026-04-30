"""
cortex.cognitive_autonomy.glial
=================================
M11.2 — Supporto Gliale: integrazione AstrocyteNetwork nel pipeline cognitivo.

Principio biologico:
  Le cellule gliali (astrociti, oligodendrociti, microglia) non sono
  semplici "colla cerebrale" — svolgono funzioni cognitive attive:

  1. Astrociti (90% del volume cerebrale):
     - Tripartite synapse: regolano la forza sinaptica in tempo reale
     - Lactate shuttle: forniscono lattato ai neuroni come carburante
     - Calcium waves: coordinazione a lunga distanza tra regioni
     - Glymphatic system: clearance dei metaboliti tossici (durante il sonno)

  2. Microglia:
     - Synaptic pruning: eliminano sinapsi deboli (plasticità adattiva)
     - Neuroinfiammazione: risposta immunitaria cerebrale

  "Astrocytes are active participants in tripartite synapses, regulating
   synaptic strength, metabolic supply, and long-range coordination."
   — Verkhratsky & Nedergaard, 2018

Analogia SPEACE:
  GlialSupport usa AstrocyteNetwork (già in cortex/) come modulatore:
    - plasticity_boost: onde di calcio → boost temporaneo della plasticità
    - metabolic_supply: metabolic_reserve degli astrociti → "carburante" per neuroni
    - cleanup_rate: glymphatic analog → clearance dei trace episodici obsoleti
    - coherence_propagation: calcium wave → sincronizzazione cross-compartment

M11.2 | 2026-04-28
"""

from .glial_support import (
    GlialSupport,
    GlialConfig,
    GlialState,
    GlialEffect,
)

__all__ = [
    "GlialSupport",
    "GlialConfig",
    "GlialState",
    "GlialEffect",
]
