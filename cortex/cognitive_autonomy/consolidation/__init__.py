"""
cortex.cognitive_autonomy.consolidation
========================================
M10.4 — ConsolidationPass: consolidamento notturno della memoria.

Principio biologico:
  Durante il sonno (NREM / slow-wave sleep), l'ippocampo "riproduce"
  (replay) le esperienze recenti e le trasferisce alla neocortex per
  lo storage a lungo termine. Questo processo:
    - Raffforza i ricordi ad alta importanza
    - Sopprime i ricordi irrilevanti (pruning)
    - Estrae pattern e generalizzazioni (schema extraction)
    - Libera la memoria episodica per nuovi apprendimenti

  "The sleeping brain replays waking experience to consolidate memory."
   — Wilson & McNaughton, 1994

Analogia SPEACE:
  ConsolidationPass gira durante WakeState.DEEP_SLEEP e:
    1. Legge episodi recenti da AutobiographicalMemory
    2. Identifica pattern ricorrenti (successi/fallimenti)
    3. Genera "traces" compresse da salvare in LongTermTrace store
    4. Pruning degli episodi a bassa importanza
    5. Emette MEMORY_CONSOLIDATED sull'EventBus

M10.4 | 2026-04-28
"""

from .consolidation_pass import (
    ConsolidationPass,
    ConsolidationConfig,
    ConsolidationResult,
    MemoryTrace,
)

__all__ = [
    "ConsolidationPass",
    "ConsolidationConfig",
    "ConsolidationResult",
    "MemoryTrace",
]
