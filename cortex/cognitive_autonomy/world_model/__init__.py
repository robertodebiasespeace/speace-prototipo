"""
World Model — M6 (9° Comparto SPEACE Cortex)

World Model / Knowledge Graph è il 9° comparto del SPEACE Cortex.
Funge da centro cognitivo centralizzato: gli altri comparti
(Perception, Reasoning, Planning, ecc.) interrogano e aggiornano
il WorldSnapshot per mantenere una visione coerente della realtà.

Architettura:
    Perception → WorldModel ← Reasoning ← Planning
                     ↕
              KnowledgeGraph
                     ↕
           AutobiographicalMemory (via MemoryBridge)
                     ↕
           ExternalFeeds (NASA, NOAA, UN SDG)
                     ↕
           InferenceEngine (what-if scenarios)

Componenti:
    WorldSnapshot     — store centralizzato stato mondo (M6.1)
    KnowledgeGraph    — grafo semantico entità+relazioni (M6.2)
    FeedConnectors    — dati esterni read-only (M6.3)
    InferenceEngine   — scenari what-if causali (M6.4)
    MemoryBridge      — ponte AutobiographicalMemory↔WorldModel (M6.5)
    WorldModelCortex  — facade unificata (M6.6)

Milestone: M6
Versione: 1.0 | 2026-04-27
"""

from .snapshot      import WorldSnapshot
from .knowledge_graph import KnowledgeGraph, EntityType, Entity, Relation
from .inference     import InferenceEngine, Scenario, CausalRule, BUILTIN_RULES
from .memory_bridge import MemoryBridge
from .cortex        import WorldModelCortex

__version__ = "1.0.0"
__milestone__ = "M6"

__all__ = [
    "WorldSnapshot",
    "KnowledgeGraph", "EntityType", "Entity", "Relation",
    "InferenceEngine", "Scenario", "CausalRule", "BUILTIN_RULES",
    "MemoryBridge",
    "WorldModelCortex",
]
