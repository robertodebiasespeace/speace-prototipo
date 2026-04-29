"""
cortex.cognitive_autonomy.valence
===================================
M12.1 — ValenceIntegrator: segnale dolore/piacere unificato per SPEACE.

Principio biologico:
  Amigdala + Nucleus Accumbens + Corteccia Cingolata Anteriore formano
  il circuito di valenza cerebrale: traducono ogni esperienza in un segnale
  scalare unificato PIACERE ↔ DOLORE (valence, da -1.0 a +1.0).

  Funzioni della valenza:
    1. ORIENTAMENTO: guida l'attenzione verso stimoli rilevanti
    2. MOTIVAZIONE: amplifica i drive in direzione della riduzione del dolore
       e del massimizzare il piacere
    3. MEMORIA: potenzia la formazione di ricordi con alta valenza (amigdala
       modula l'ippocampo — i ricordi emotivi sono più forti)
    4. DECISIONE: la valenza è uno dei principali input al sistema di decisione
       (Damasio's Somatic Marker Hypothesis)

  "The brain's job is to keep the organism alive by predicting and
   regulating the body's internal state. Affect — valence and arousal —
   is the brain's summary report of how well this regulation is going."
   — Lisa Feldman Barrett, 2017

Analogia SPEACE:
  ValenceIntegrator aggrega i segnali di outcome da tutti i drive SPEACE
  e produce un segnale di valenza scalare [-1.0, +1.0]:
    +1.0 = massimo piacere (tutti i drive soddisfatti, evoluzione in corso)
    -1.0 = massimo dolore (crisi esistenziale, safety breach, stagnazione)
    0.0  = neutrale (equilibrio stabile)

M12.1 | 2026-04-28
"""

from .valence_integrator import (
    ValenceIntegrator,
    ValenceConfig,
    ValenceState,
    ValenceSignal,
    AffectiveState,
)

__all__ = [
    "ValenceIntegrator",
    "ValenceConfig",
    "ValenceState",
    "ValenceSignal",
    "AffectiveState",
]
