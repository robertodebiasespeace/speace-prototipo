"""
Knowledge Graph - World Model Internal Representation
Implementazione del knowledge graph per SPEACE.
Versione: 1.0
Data: 23 Aprile 2026
"""

from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
import logging

logger = logging.getLogger("SPEACE-KnowledgeGraph")


class KnowledgeGraph:
    """
    Knowledge Graph per rappresentazione interna della realta.

    Funzionalita:
    - Triple storage (subject, predicate, object)
    - Query entity e relationships
    - Path finding tra entita
    - Inferenza causale base
    - World state tracking
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.name = "SPEACE_KnowledgeGraph"
        self.version = "1.0"
        self.config = config or {}

        # Core storage
        self.triples: List[Tuple[str, str, str]] = []
        self.entities: Set[str] = set()
        self.predicates: Set[str] = set()

        # Indices
        self.entity_triples: Dict[str, List[Tuple[str, str, str]]] = {}
        self.predicate_triples: Dict[str, List[Tuple[str, str, str]]] = {}

        # World state
        self.world_state: Dict[str, Any] = {}
        self.state_history: List[Dict] = []

        # Stats
        self.last_update = datetime.now()
        self.query_count = 0

        # Initialize base knowledge
        self._init_base_knowledge()

    def _init_base_knowledge(self):
        """Inizializza conoscenza base SPEACE"""
        base_knowledge = [
            ("SPEACE", "type", "Cybernetic_Organism"),
            ("SPEACE", "has_component", "Neural_Engine"),
            ("SPEACE", "has_component", "SMFOI_Kernel"),
            ("SPEACE", "has_component", "Adaptive_Consciousness"),
            ("SPEACE", "has_component", "9_Comparti_Cerebrali"),
            ("SPEACE", "version", "1.0"),
            ("SPEACE", "phase", "Embryonic"),
            ("Neural_Engine", "implements", "Computational_Graph"),
            ("Neural_Engine", "has_capability", "Evolution"),
            ("Neural_Engine", "has_capability", "Plasticity"),
            ("SMFOI_Kernel", "implements", "6Step_Protocol"),
            ("SMFOI_Kernel", "version", "0.3"),
            ("Adaptive_Consciousness", "has_component", "Phi_Calculator"),
            ("Adaptive_Consciousness", "has_component", "Global_Workspace"),
            ("Adaptive_Consciousness", "has_component", "Metacognitive_Module"),
            ("9_Comparti_Cerebrali", "includes", "Prefrontal_Cortex"),
            ("9_Comparti_Cerebrali", "includes", "Perception_Module"),
            ("9_Comparti_Cerebrali", "includes", "World_Model"),
            ("9_Comparti_Cerebrali", "includes", "Hippocampus"),
            ("9_Comparti_Cerebrali", "includes", "Temporal_Lobe"),
            ("9_Comparti_Cerebrali", "includes", "Parietal_Lobe"),
            ("9_Comparti_Cerebrali", "includes", "Cerebellum"),
            ("9_Comparti_Cerebrali", "includes", "Default_Mode_Network"),
            ("9_Comparti_Cerebrali", "includes", "Curiosity_Module"),
            ("9_Comparti_Cerebrali", "includes", "Safety_Module"),
            ("DigitalDNA", "governs", "SPEACE_Evolution"),
            ("SafeProactive", "provides", "Safety_Gates"),
            ("SPEACE", "aligned_with", "TINA_Framework"),
            ("SPEACE", "objective", "Super_Intelligence"),
        ]

        for triple in base_knowledge:
            self.add_triple(*triple)

    def add_triple(self, subject: str, predicate: str, obj: str) -> bool:
        """Aggiunge una triple al grafo"""
        triple = (subject, predicate, obj)

        if triple in self.triples:
            return False

        self.triples.append(triple)
        self.entities.add(subject)
        self.entities.add(obj)
        self.predicates.add(predicate)

        # Update indices
        if subject not in self.entity_triples:
            self.entity_triples[subject] = []
        self.entity_triples[subject].append(triple)

        if obj not in self.entity_triples:
            self.entity_triples[obj] = []
        self.entity_triples[obj].append(triple)

        if predicate not in self.predicate_triples:
            self.predicate_triples[predicate] = []
        self.predicate_triples[predicate].append(triple)

        self.last_update = datetime.now()
        return True

    def get_entity_triples(self, entity: str) -> List[Tuple[str, str, str]]:
        """Ottiene tutte le triple per un'entita"""
        self.query_count += 1
        return self.entity_triples.get(entity, [])

    def get_predicate_triples(self, predicate: str) -> List[Tuple[str, str, str]]:
        """Ottiene tutte le triple per un predicato"""
        self.query_count += 1
        return self.predicate_triples.get(predicate, [])

    def query(self, entity: str) -> Dict[str, Any]:
        """Query completa su un'entita"""
        triples = self.get_entity_triples(entity)

        outgoing = [(s, p, o) for s, p, o in triples if s == entity]
        incoming = [(s, p, o) for s, p, o in triples if o == entity]

        return {
            "entity": entity,
            "outgoing": outgoing,
            "incoming": incoming,
            "total_relations": len(triples),
        }

    def find_path(self, start: str, end: str, max_depth: int = 3) -> Optional[List[str]]:
        """Trova path tra due entita (BFS)"""
        if start == end:
            return [start]

        visited = {start}
        queue = [(start, [start])]

        while queue:
            current, path = queue.pop(0)

            if len(path) > max_depth:
                continue

            for s, p, o in self.get_entity_triples(current):
                neighbor = o if s == current else s

                if neighbor == end:
                    return path + [neighbor]

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def infer(self, entity: str) -> List[Tuple[str, str, str]]:
        """Inferisce nuove relazioni per un'entita"""
        inferred = []
        entity_triples = self.get_entity_triples(entity)

        # Se X has_component Y e Y implements Z -> X indirect_implements Z
        for s, p, o in entity_triples:
            if p == "has_component":
                component_triples = self.get_entity_triples(o)
                for s2, p2, o2 in component_triples:
                    if p2 == "implements":
                        inferred.append((s, "indirect_" + p2, o2))

        return inferred

    def update_world_state(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Aggiorna world state"""
        old_state = dict(self.world_state)

        for key, value in updates.items():
            self.world_state[key] = value

        self.state_history.append({
            "timestamp": datetime.now().isoformat(),
            "updates": updates,
            "old_state": old_state,
        })

        self.last_update = datetime.now()

        return {"updated": list(updates.keys()), "current_state": self.world_state}

    def get_stats(self) -> Dict[str, Any]:
        """Statistiche del knowledge graph"""
        return {
            "total_triples": len(self.triples),
            "total_entities": len(self.entities),
            "total_predicates": len(self.predicates),
            "query_count": self.query_count,
            "last_update": self.last_update.isoformat(),
        }

    def export_triples(self) -> List[Tuple[str, str, str]]:
        """Esporta tutte le triple"""
        return list(self.triples)
