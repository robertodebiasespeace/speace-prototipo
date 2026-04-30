"""cortex.cognitive_autonomy.memory — Memoria Autobiografica (M5.8+M5.9)

Backend SQLite + FTS5 per episodi, classificatore EVENT/STRUCTURE,
Experience Replay ponderata per importanza.

Milestone completate: M5.8 (schema SQLite + ops base),
                      M5.9 (EventClassifier + SPEACEOnlineLearner)
Prossima:            M5.10 (continuity_score full impl)
"""

from .autobiographical import (
    AutobiographicalMemory,
    Episode,
    MemoryType,
    EventClassifier,
    SPEACEOnlineLearner,
)

__all__ = [
    "AutobiographicalMemory",
    "Episode",
    "MemoryType",
    "EventClassifier",
    "SPEACEOnlineLearner",
]
