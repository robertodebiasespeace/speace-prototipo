"""
KnowledgeGraph — M6.2 (World Model / Knowledge Graph)

Grafo semantico di entità e relazioni per SPEACE.
Supporta:
  - Entità tipizzate con proprietà arbitrarie
  - Relazioni dirette e inverse (es. "created_by" ↔ "creates")
  - Query per tipo, relazione, proprietà
  - Export compatibile con WorldSnapshot.knowledge_graph

Tipi di entità predefiniti (estendibili):
  AI_AGENT, HUMAN, ORGANIZATION, TECHNOLOGY, ECOSYSTEM,
  PLANET, CONCEPT, OBJECTIVE, EVENT

Milestone: M6.2
Versione: 1.0 | 2026-04-27
"""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Entity types
# ---------------------------------------------------------------------------

class EntityType:
    AI_AGENT     = "AI_AGENT"
    HUMAN        = "HUMAN"
    ORGANIZATION = "ORGANIZATION"
    TECHNOLOGY   = "TECHNOLOGY"
    ECOSYSTEM    = "ECOSYSTEM"
    PLANET       = "PLANET"
    CONCEPT      = "CONCEPT"
    OBJECTIVE    = "OBJECTIVE"
    EVENT        = "EVENT"
    UNKNOWN      = "UNKNOWN"


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class Relation:
    rel:     str                   # relation type (e.g. "created_by")
    target:  str                   # target entity id
    weight:  float = 1.0
    props:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"rel": self.rel, "target": self.target}
        if self.weight != 1.0:
            d["weight"] = self.weight
        if self.props:
            d["props"] = self.props
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Relation":
        return cls(
            rel=d["rel"], target=d["target"],
            weight=d.get("weight", 1.0), props=d.get("props", {})
        )


@dataclass
class Entity:
    id:         str
    entity_type: str = EntityType.UNKNOWN
    properties:  Dict[str, Any] = field(default_factory=dict)
    relations:   List[Relation]  = field(default_factory=list)
    added_at:    Optional[str]   = None

    def add_relation(self, rel: str, target: str, weight: float = 1.0,
                     props: Optional[Dict[str, Any]] = None) -> None:
        # Prevent duplicates
        for r in self.relations:
            if r.rel == rel and r.target == target:
                r.weight = weight
                if props:
                    r.props.update(props)
                return
        self.relations.append(Relation(rel=rel, target=target,
                                       weight=weight, props=props or {}))

    def get_relations(self, rel_type: Optional[str] = None) -> List[Relation]:
        if rel_type is None:
            return list(self.relations)
        return [r for r in self.relations if r.rel == rel_type]

    def neighbors(self, rel_type: Optional[str] = None) -> List[str]:
        return [r.target for r in self.get_relations(rel_type)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "properties": copy.deepcopy(self.properties),
            "relations":  [r.to_dict() for r in self.relations],
            "added_at":   self.added_at,
        }

    @classmethod
    def from_dict(cls, entity_id: str, d: Dict[str, Any]) -> "Entity":
        rels = [Relation.from_dict(r) for r in d.get("relations", [])]
        return cls(
            id=entity_id,
            entity_type=d.get("properties", {}).get("type", EntityType.UNKNOWN),
            properties=d.get("properties", {}),
            relations=rels,
            added_at=d.get("added_at"),
        )


# ---------------------------------------------------------------------------
# KnowledgeGraph
# ---------------------------------------------------------------------------

_INVERSE_RELATIONS: Dict[str, str] = {
    "created_by":     "creates",
    "creates":        "created_by",
    "part_of":        "contains",
    "contains":       "part_of",
    "depends_on":     "required_by",
    "required_by":    "depends_on",
    "aligned_with":   "aligned_with",
    "conflicts_with": "conflicts_with",
    "monitors":       "monitored_by",
    "monitored_by":   "monitors",
    "feeds":          "fed_by",
    "fed_by":         "feeds",
}


class KnowledgeGraph:
    """
    M6.2 — Grafo semantico di entità e relazioni.

    Thread-safe. Supporta:
    - add_entity / add_relation
    - query per tipo, relazione, proprietà
    - BFS traversal
    - export/import dict (compatibile con WorldSnapshot.knowledge_graph)
    """

    def __init__(self) -> None:
        self._lock     = threading.RLock()
        self._entities: Dict[str, Entity] = {}

    # ----------------------------------------------------------- build

    def add_entity(
        self,
        entity_id: str,
        entity_type: str = EntityType.UNKNOWN,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Entity:
        """Aggiunge (o aggiorna) un'entità. Ritorna l'entità."""
        with self._lock:
            if entity_id in self._entities:
                e = self._entities[entity_id]
                if entity_type != EntityType.UNKNOWN:
                    e.entity_type = entity_type
                if properties:
                    e.properties.update(properties)
                return e
            now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
            props = properties or {}
            props.setdefault("type", entity_type)
            e = Entity(id=entity_id, entity_type=entity_type,
                       properties=props, added_at=now)
            self._entities[entity_id] = e
            return e

    def add_relation(
        self,
        src: str,
        rel: str,
        dst: str,
        weight: float = 1.0,
        props: Optional[Dict[str, Any]] = None,
        add_inverse: bool = True,
    ) -> None:
        """Aggiunge relazione src→rel→dst. Crea entità se non esistono."""
        with self._lock:
            if src not in self._entities:
                self.add_entity(src)
            if dst not in self._entities:
                self.add_entity(dst)
            self._entities[src].add_relation(rel, dst, weight, props)
            if add_inverse and rel in _INVERSE_RELATIONS:
                inv = _INVERSE_RELATIONS[rel]
                self._entities[dst].add_relation(inv, src, weight)

    # ----------------------------------------------------------- query

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        with self._lock:
            return self._entities.get(entity_id)

    def entity_ids(self) -> List[str]:
        with self._lock:
            return list(self._entities.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._entities)

    def find_by_type(self, entity_type: str) -> List[Entity]:
        with self._lock:
            return [e for e in self._entities.values()
                    if e.entity_type == entity_type or
                       e.properties.get("type") == entity_type]

    def find_by_property(self, key: str, value: Any) -> List[Entity]:
        with self._lock:
            return [e for e in self._entities.values()
                    if e.properties.get(key) == value]

    def neighbors(self, entity_id: str, rel_type: Optional[str] = None) -> List[str]:
        with self._lock:
            e = self._entities.get(entity_id)
            if not e:
                return []
            return e.neighbors(rel_type)

    def path_exists(self, src: str, dst: str, max_depth: int = 5) -> bool:
        """BFS: controlla se esiste un percorso da src a dst."""
        with self._lock:
            if src not in self._entities or dst not in self._entities:
                return False
            visited: Set[str] = set()
            queue = [src]
            depth = 0
            while queue and depth <= max_depth:
                next_queue: List[str] = []
                for node in queue:
                    if node == dst:
                        return True
                    if node in visited:
                        continue
                    visited.add(node)
                    e = self._entities.get(node)
                    if e:
                        next_queue.extend(e.neighbors())
                queue = next_queue
                depth += 1
            return False

    def subgraph(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
        """Estrae sotto-grafo BFS centrato su entity_id."""
        with self._lock:
            visited: Set[str] = set()
            result: Dict[str, Any] = {}
            queue = [(entity_id, 0)]
            while queue:
                node, d = queue.pop(0)
                if node in visited or d > depth:
                    continue
                visited.add(node)
                e = self._entities.get(node)
                if e:
                    result[node] = e.to_dict()
                    for neighbor in e.neighbors():
                        if neighbor not in visited:
                            queue.append((neighbor, d + 1))
            return result

    # ----------------------------------------------------------- triple iteration

    def triples(self) -> Iterator[Tuple[str, str, str]]:
        """Genera tutte le triple (src, rel, dst)."""
        with self._lock:
            for eid, entity in self._entities.items():
                for r in entity.relations:
                    yield (eid, r.rel, r.target)

    def triple_count(self) -> int:
        with self._lock:
            return sum(len(e.relations) for e in self._entities.values())

    # ----------------------------------------------------------- seed

    def seed_from_rigene(self) -> None:
        """Popola il KG con le entità fondamentali del Rigene Project / SPEACE."""
        with self._lock:
            # Core entities
            self.add_entity("SPEACE",            EntityType.AI_AGENT,
                            {"name": "SPEACE", "phase": 1, "milestone": "M6"})
            self.add_entity("Roberto_De_Biase",  EntityType.HUMAN,
                            {"name": "Roberto De Biase", "role": "founder"})
            self.add_entity("Rigene_Project",    EntityType.ORGANIZATION,
                            {"name": "Rigene Project", "domain": "sustainability"})
            self.add_entity("TINA",              EntityType.TECHNOLOGY,
                            {"name": "TINA", "full": "Technical Intelligent Nervous Adaptive System"})
            self.add_entity("Earth",             EntityType.PLANET,
                            {"name": "Earth", "status": "critical"})
            self.add_entity("UN_SDG_2030",       EntityType.OBJECTIVE,
                            {"name": "UN Agenda 2030 SDGs", "goals": 17})
            self.add_entity("Climate_Change",    EntityType.CONCEPT,
                            {"name": "Climate Change", "severity": "critical"})
            self.add_entity("Digital_DNA",       EntityType.TECHNOLOGY,
                            {"name": "Digital DNA", "version": "1.0"})
            self.add_entity("SPEACE_Cortex",     EntityType.AI_AGENT,
                            {"name": "SPEACE Cortex", "comparti": 9})
            self.add_entity("World_Model",       EntityType.TECHNOLOGY,
                            {"name": "World Model", "milestone": "M6", "compartment": 9})

            # Relations
            self.add_relation("SPEACE",         "created_by",    "Roberto_De_Biase")
            self.add_relation("SPEACE",         "aligned_with",  "Rigene_Project")
            self.add_relation("SPEACE",         "aligned_with",  "UN_SDG_2030")
            self.add_relation("SPEACE",         "monitors",      "Earth")
            self.add_relation("SPEACE",         "monitors",      "Climate_Change")
            self.add_relation("SPEACE",         "contains",      "SPEACE_Cortex")
            self.add_relation("SPEACE",         "contains",      "Digital_DNA")
            self.add_relation("SPEACE_Cortex",  "contains",      "World_Model")
            self.add_relation("Rigene_Project", "created_by",    "Roberto_De_Biase")
            self.add_relation("Rigene_Project", "aligned_with",  "UN_SDG_2030")
            self.add_relation("TINA",           "part_of",       "Rigene_Project")
            self.add_relation("Climate_Change", "affects",       "Earth")
            self.add_relation("World_Model",    "feeds",         "SPEACE_Cortex")

    # ----------------------------------------------------------- import / export

    def to_dict(self) -> Dict[str, Any]:
        """Export compatibile con WorldSnapshot.knowledge_graph."""
        with self._lock:
            return {eid: e.to_dict() for eid, e in self._entities.items()}

    def load_dict(self, data: Dict[str, Any]) -> None:
        """Import da dict (formato WorldSnapshot.knowledge_graph)."""
        with self._lock:
            for eid, edata in data.items():
                if isinstance(edata, dict):
                    e = Entity.from_dict(eid, edata)
                    self._entities[eid] = e

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            types: Dict[str, int] = {}
            for e in self._entities.values():
                t = e.entity_type
                types[t] = types.get(t, 0) + 1
            return {
                "entity_count": len(self._entities),
                "triple_count": self.triple_count(),
                "entity_types": types,
            }


__all__ = [
    "EntityType",
    "Relation",
    "Entity",
    "KnowledgeGraph",
    "_INVERSE_RELATIONS",
]
