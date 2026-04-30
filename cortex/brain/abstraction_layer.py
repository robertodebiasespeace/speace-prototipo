"""
SPEACE Abstraction Layer – BRN-018
=====================================
Hierarchical concept formation, analogical reasoning, and conceptual blending.

Principio biologico:
  Il cervello umano non lavora con dati raw: astrae progressivamente.
  Dalla corteccia visiva V1 (bordi) → V4 (forme) → IT (oggetti) → PFC (concetti astratti).
  Il risultato è un sistema che:
    - Capisce "gatto" senza aver visto quel gatto specifico (generalizzazione)
    - Sa che "cuore" di un'organizzazione è analogo al "cuore" biologico (analogia)
    - Inventa "droni-api" combinando drone + ape (blending)

  Questo è il meccanismo che permette l'intelligenza generale cross-domain:
  NON servono migliaia di esempi per ogni dominio se si può trasferire
  la struttura astratta da un dominio a un altro.

Implementazione SPEACE:
  - Concept           : unità di conoscenza con features, livello di astrazione, dominio
  - ConceptualGraph   : grafo semantico tipizzato con similarità e traversal gerarchico
  - HierarchicalAbstractor : estrae astrazioni da gruppi di concetti concreti
  - AnalogyEngine     : structure-mapping (Gentner 1983) — trasferisce struttura
  - ConceptualBlender : blending (Fauconnier & Turner 2002) — crea nuovi concetti
  - AbstractionLayer  : modulo principale, integra tutto + KG + MetaLearner

Referenze:
  - Gentner D (1983). Structure-Mapping: A Theoretical Framework for Analogy.
  - Fauconnier G, Turner M (2002). The Way We Think: Conceptual Blending.
  - Lake BM et al. (2017). Building Machines That Learn and Think Like People.
  - Hofstadter D, Sander E (2013). Surfaces and Essences: Analogy as the Fuel.

Integrazioni:
  - BRN-013 MetaLearner   : suggest_learning_strategy() → LearningStrategy
  - BRN-017 CausalReasoner: features causali come prior per analogia
  - WorldModel KG          : import_from_knowledge_graph() → concetti da entità

Version: 1.0 | Data: 29 Aprile 2026
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ── Enumerazioni ──────────────────────────────────────────────────────────────

class RelationType(Enum):
    IS_A        = "is_a"         # gerarchia: cane is_a mammifero
    PART_OF     = "part_of"      # mereologia: CPU part_of computer
    SIMILAR_TO  = "similar_to"   # similarità semantica
    OPPOSITE_OF = "opposite_of"  # antonimia
    CAUSES      = "causes"       # causalità (bridge con BRN-017)
    ANALOGY_OF  = "analogy_of"   # mappatura analogica cross-domain
    BLEND_OF    = "blend_of"     # concetto generato per blending


class AbstractionLevel(Enum):
    SENSORY     = 1   # features percettive raw (colore, forma, texture)
    PERCEPTUAL  = 2   # oggetti e pattern (gatto, albero, macchina)
    CONCEPTUAL  = 3   # categorie funzionali (animale, veicolo, strumento)
    STRUCTURAL  = 4   # schemi relazionali (predatore-preda, agente-paziente)
    SCHEMATIC   = 5   # schemi astratti massimali (causa-effetto, parte-tutto)


# ── Strutture dati ─────────────────────────────────────────────────────────────

@dataclass
class ConceptRelation:
    rel_type:   RelationType
    target_id:  str
    weight:     float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Concept:
    """
    Unità atomica di conoscenza nell'AbstractionLayer.

    features: dict {feature_name: float} — rappresentazione numerica [0,1]
              Esempi: {"has_legs": 1.0, "can_fly": 0.0, "is_alive": 1.0}
    """
    concept_id:        str
    label:             str
    features:          Dict[str, float]   = field(default_factory=dict)
    abstraction_level: int                = AbstractionLevel.PERCEPTUAL.value
    domain:            str                = "unknown"
    relations:         List[ConceptRelation] = field(default_factory=list)
    confidence:        float              = 0.8
    source:            str                = "manual"    # manual/abstracted/blended/analogical
    created_at:        float              = field(default_factory=time.time)

    def add_relation(self, rel_type: RelationType, target_id: str,
                     weight: float = 1.0) -> None:
        for r in self.relations:
            if r.rel_type == rel_type and r.target_id == target_id:
                r.weight = weight
                return
        self.relations.append(ConceptRelation(rel_type, target_id, weight))

    def get_relations(self, rel_type: Optional[RelationType] = None) -> List[ConceptRelation]:
        if rel_type is None:
            return list(self.relations)
        return [r for r in self.relations if r.rel_type == rel_type]

    def feature_vector(self, keys: List[str]) -> List[float]:
        """Vettore di features per una lista di chiavi ordinata."""
        return [self.features.get(k, 0.0) for k in keys]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "label":      self.label,
            "features":   self.features,
            "level":      self.abstraction_level,
            "domain":     self.domain,
            "confidence": round(self.confidence, 4),
            "source":     self.source,
            "n_relations": len(self.relations),
        }


# ── ConceptualGraph ────────────────────────────────────────────────────────────

class ConceptualGraph:
    """
    Grafo semantico di concetti e relazioni.

    Supporta:
      - Similarità coseno su feature vector
      - Traversal gerarchico per livello di astrazione
      - Query per dominio, relazione, label
    """

    def __init__(self) -> None:
        self._concepts: Dict[str, Concept] = {}

    def add_concept(self, concept: Concept) -> None:
        self._concepts[concept.concept_id] = concept

    def get(self, concept_id: str) -> Optional[Concept]:
        return self._concepts.get(concept_id)

    def get_by_label(self, label: str) -> Optional[Concept]:
        for c in self._concepts.values():
            if c.label.lower() == label.lower():
                return c
        return None

    def get_by_domain(self, domain: str) -> List[Concept]:
        return [c for c in self._concepts.values() if c.domain == domain]

    def get_by_level(self, level: int) -> List[Concept]:
        return [c for c in self._concepts.values() if c.abstraction_level == level]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot   = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x ** 2 for x in a))
        norm_b = math.sqrt(sum(x ** 2 for x in b))
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        return dot / (norm_a * norm_b)

    def similarity(self, id_a: str, id_b: str) -> float:
        """Similarità coseno tra due concetti sulle feature in comune."""
        c_a = self._concepts.get(id_a)
        c_b = self._concepts.get(id_b)
        if c_a is None or c_b is None:
            return 0.0
        common_keys = sorted(set(c_a.features) & set(c_b.features))
        if not common_keys:
            return 0.0
        return self._cosine_similarity(
            c_a.feature_vector(common_keys),
            c_b.feature_vector(common_keys)
        )

    def get_similar(self, concept_id: str, top_k: int = 5,
                    min_sim: float = 0.3) -> List[Tuple[str, float]]:
        """Ritorna i top-k concetti più simili con score."""
        results = []
        for cid, c in self._concepts.items():
            if cid == concept_id:
                continue
            sim = self.similarity(concept_id, cid)
            if sim >= min_sim:
                results.append((cid, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_hierarchy_up(self, concept_id: str) -> List[str]:
        """Ritorna i concetti più astratti (is_a chain upward)."""
        result = []
        visited = set()
        queue = [concept_id]
        while queue:
            cid = queue.pop(0)
            if cid in visited:
                continue
            visited.add(cid)
            c = self._concepts.get(cid)
            if c is None:
                continue
            for rel in c.get_relations(RelationType.IS_A):
                result.append(rel.target_id)
                queue.append(rel.target_id)
        return result

    @property
    def all_concepts(self) -> List[Concept]:
        return list(self._concepts.values())

    def __len__(self) -> int:
        return len(self._concepts)


# ── HierarchicalAbstractor ────────────────────────────────────────────────────

class HierarchicalAbstractor:
    """
    Estrae astrazioni di livello superiore da gruppi di concetti.

    Algoritmo:
      1. Trova le features COMUNI a tutti i concetti di input (intersezione)
      2. Calcola il valore medio per ogni feature comune
      3. Filtra le features che variano troppo (non sono strutturali)
      4. Crea un nuovo Concept con quelle features al livello target
      5. Aggiunge relazioni IS_A dai concetti originali al nuovo astratto

    Biologicamente: come la corteccia IT crea la categoria "animale"
    da esperienze con gatti, cani, uccelli.
    """

    def __init__(self, min_feature_coverage: float = 0.6,
                 max_feature_variance: float = 0.35) -> None:
        self.min_coverage = min_feature_coverage   # % concetti che devono avere la feature
        self.max_variance = max_feature_variance   # varianza max ammessa per feature strutturale

    def abstract(self, concepts: List[Concept],
                 target_level: int = AbstractionLevel.CONCEPTUAL.value,
                 label: Optional[str] = None) -> Optional[Concept]:
        """
        Crea un concetto astratto dai concetti di input.

        Args:
          concepts     : lista di Concept da astrarre
          target_level : livello di astrazione target (1-5)
          label        : etichetta del nuovo concetto (auto-generata se None)

        Returns:
          Nuovo Concept astratto, o None se non ci sono features comuni sufficienti
        """
        if not concepts:
            return None

        n = len(concepts)
        # Conta quante volte ogni feature appare
        feature_counts:  Dict[str, int]         = defaultdict(int)
        feature_values:  Dict[str, List[float]] = defaultdict(list)
        for c in concepts:
            for fname, fval in c.features.items():
                feature_counts[fname] += 1
                feature_values[fname].append(fval)

        # Seleziona features strutturali: presenti in >= min_coverage dei concetti
        # e con bassa varianza (comportamento coerente)
        structural_features: Dict[str, float] = {}
        for fname, count in feature_counts.items():
            coverage = count / n
            if coverage < self.min_coverage:
                continue
            vals = feature_values[fname]
            mean_val = sum(vals) / len(vals)
            variance = sum((v - mean_val) ** 2 for v in vals) / len(vals)
            if variance > self.max_variance:
                continue   # feature troppo variabile → non strutturale
            structural_features[fname] = round(mean_val, 4)

        if not structural_features:
            logger.debug(f"[HierarchicalAbstractor] Nessuna feature strutturale "
                         f"trovata su {n} concetti")
            return None

        # Determina dominio comune
        domains = [c.domain for c in concepts]
        common_domain = domains[0] if len(set(domains)) == 1 else "cross_domain"

        # Genera label automatica
        auto_label = label or ("_".join(sorted({c.domain for c in concepts}))
                               + f"_L{target_level}")

        new_concept = Concept(
            concept_id        = f"abs_{uuid.uuid4().hex[:8]}",
            label             = auto_label,
            features          = structural_features,
            abstraction_level = target_level,
            domain            = common_domain,
            confidence        = sum(c.confidence for c in concepts) / n,
            source            = "abstracted",
        )

        # Aggiungi relazioni IS_A inversa (input concepts → nuovo astratto)
        for c in concepts:
            c.add_relation(RelationType.IS_A, new_concept.concept_id)

        logger.info(f"[HierarchicalAbstractor] Creato '{auto_label}' "
                    f"(L{target_level}, {len(structural_features)} features strutturali) "
                    f"da {n} concetti")
        return new_concept


# ── AnalogyEngine ─────────────────────────────────────────────────────────────

class AnalogyEngine:
    """
    Structure-mapping analogical reasoning (Gentner 1983).

    Principio: un'analogia non copia le features di superficie,
    ma mappa le RELAZIONI STRUTTURALI da un dominio a un altro.

    Esempio: "il cuore è all'organismo come la pompa è al sistema idraulico"
      → Source: cuore → pompa sangue → ossigena organi
      → Target: pompa → spinge acqua → alimenta circuito
      → Mapping strutturale: "pompa X → distribuisce risorsa Y → mantiene sistema Z"

    Algoritmo:
      1. Estrai feature pattern dal source (relazioni tra features)
      2. Cerca nel target domain un concetto con pattern strutturale simile
      3. Costruisci il mapping: source_feature → target_feature
      4. Genera il concetto analogico (proiezione del source nel target domain)
    """

    def find_analogy(
        self,
        source: Concept,
        target_domain_concepts: List[Concept],
        min_structural_overlap: float = 0.2,
    ) -> Optional[Tuple[Concept, Dict[str, str], float]]:
        """
        Trova il migliore analogo del source nel target domain.

        Returns:
          (target_concept, feature_mapping, similarity_score) o None
        """
        if not target_domain_concepts:
            return None

        best_match  = None
        best_score  = 0.0
        best_mapping: Dict[str, str] = {}

        source_keys = set(source.features.keys())

        for target in target_domain_concepts:
            if target.concept_id == source.concept_id:
                continue
            target_keys = set(target.features.keys())

            # Structural overlap: features in common (regardless of values)
            overlap = source_keys & target_keys
            if not overlap:
                continue
            structural_score = len(overlap) / max(len(source_keys), len(target_keys))
            if structural_score < min_structural_overlap:
                continue

            # Value alignment: how similarly the shared features behave
            alignment_scores = []
            mapping: Dict[str, str] = {}
            for feat in overlap:
                src_val = source.features[feat]
                tgt_val = target.features[feat]
                # High alignment = same qualitative behavior (both high or both low)
                alignment = 1.0 - abs(src_val - tgt_val)
                alignment_scores.append(alignment)
                mapping[feat] = feat

            value_score = sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.0
            combined_score = 0.6 * structural_score + 0.4 * value_score

            if combined_score > best_score:
                best_score   = combined_score
                best_match   = target
                best_mapping = mapping

        if best_match is None:
            return None

        logger.info(f"[AnalogyEngine] Analogia: '{source.label}' ~ '{best_match.label}' "
                    f"(score={best_score:.3f}, {len(best_mapping)} features mappate)")
        return (best_match, best_mapping, round(best_score, 4))

    def project_analogy(
        self,
        source: Concept,
        target: Concept,
        mapping: Dict[str, str],
        new_domain: str,
    ) -> Concept:
        """
        Crea un nuovo concetto proiettando source nel dominio di target
        tramite il mapping strutturale.
        """
        projected_features: Dict[str, float] = {}
        # Copia le features mappate dal source
        for src_feat, tgt_feat in mapping.items():
            projected_features[tgt_feat] = source.features.get(src_feat, 0.5)
        # Aggiungi features specifiche del target non mappate (a peso ridotto)
        for feat, val in target.features.items():
            if feat not in projected_features:
                projected_features[feat] = val * 0.5

        projected = Concept(
            concept_id        = f"analogy_{uuid.uuid4().hex[:8]}",
            label             = f"{source.label}_in_{new_domain}",
            features          = projected_features,
            abstraction_level = source.abstraction_level,
            domain            = new_domain,
            confidence        = min(source.confidence, target.confidence) * 0.9,
            source            = "analogical",
        )
        projected.add_relation(RelationType.ANALOGY_OF, source.concept_id)
        projected.add_relation(RelationType.ANALOGY_OF, target.concept_id)
        return projected


# ── ConceptualBlender ──────────────────────────────────────────────────────────

class ConceptualBlender:
    """
    Conceptual Blending (Fauconnier & Turner 2002).

    Struttura a 4 spazi:
      Input 1     → features del primo concetto
      Input 2     → features del secondo concetto
      Generic Space → features comuni (struttura condivisa)
      Blended Space → combinazione selettiva + proprietà emergenti

    Proprietà emergenti: caratteristiche che esistono solo nel blend,
    non in nessuno degli input (es. "computer virus": si replica
    come un virus biologico ma su substrato digitale).

    Algoritmo:
      1. Trova Generic Space: features presenti in entrambi con valori compatibili
      2. Proietta selettivamente features uniche di ciascun input
      3. Calcola proprietà emergenti (features non-additivi nel blend)
      4. Costruisce il Blended Concept
    """

    def __init__(self, emergence_threshold: float = 0.3) -> None:
        self.emergence_threshold = emergence_threshold

    def blend(self, input1: Concept, input2: Concept,
              label: Optional[str] = None) -> Concept:
        """
        Crea un nuovo concetto blendato da due input.

        Args:
          input1, input2 : concetti da blendare
          label          : etichetta del blend (auto-generata se None)

        Returns:
          Nuovo Concept con features blended + proprietà emergenti
        """
        # 1. Generic Space — features comuni con valori compatibili (diff < 0.3)
        generic: Dict[str, float] = {}
        for feat in set(input1.features) & set(input2.features):
            v1, v2 = input1.features[feat], input2.features[feat]
            if abs(v1 - v2) < 0.35:
                generic[feat] = round((v1 + v2) / 2, 4)

        # 2. Proiezione selettiva — features uniche di ciascun input
        #    peso proporzionale alla confidence del concetto sorgente
        blended: Dict[str, float] = dict(generic)

        for feat, val in input1.features.items():
            if feat not in blended:
                blended[f"from_{input1.domain}_{feat}"] = round(val * input1.confidence, 4)

        for feat, val in input2.features.items():
            if feat not in blended:
                blended[f"from_{input2.domain}_{feat}"] = round(val * input2.confidence, 4)

        # 3. Proprietà emergenti — interazione non-lineare tra features cross-input
        #    Esempio: se input1 ha "self_replicating" e input2 ha "digital_substrate"
        #    il blend ha "digital_self_replication" (proprietà emergente)
        emergent: Dict[str, float] = {}
        i1_unique = set(input1.features) - set(input2.features)
        i2_unique = set(input2.features) - set(input1.features)
        for f1 in i1_unique:
            for f2 in i2_unique:
                combined_val = input1.features[f1] * input2.features[f2]
                if combined_val > self.emergence_threshold:
                    emergent_key = f"emergent_{f1[:6]}_{f2[:6]}"
                    emergent[emergent_key] = round(combined_val, 4)

        blended.update(emergent)

        # 4. Livello di astrazione: medio, tendendo verso il più astratto
        blend_level = max(
            input1.abstraction_level,
            input2.abstraction_level,
            (input1.abstraction_level + input2.abstraction_level) // 2
        )

        auto_label = label or f"{input1.label}_{input2.label}_blend"
        blend_concept = Concept(
            concept_id        = f"blend_{uuid.uuid4().hex[:8]}",
            label             = auto_label,
            features          = blended,
            abstraction_level = blend_level,
            domain            = "cross_domain",
            confidence        = (input1.confidence + input2.confidence) / 2 * 0.85,
            source            = "blended",
        )
        blend_concept.add_relation(RelationType.BLEND_OF, input1.concept_id)
        blend_concept.add_relation(RelationType.BLEND_OF, input2.concept_id)

        logger.info(f"[ConceptualBlender] Blend '{auto_label}': "
                    f"{len(generic)} generic, {len(blended)-len(generic)} proiettate, "
                    f"{len(emergent)} emergenti")
        return blend_concept


# ── AbstractionLayer (modulo principale) ─────────────────────────────────────

class AbstractionLayer:
    """
    SPEACE Abstraction Layer (BRN-018) — FULL IMPLEMENTATION.

    Ogni ciclo cognitivo:
      1. add_concept(c)                  → arricchisce il ConceptualGraph
      2. process(input_concepts)         → astrae + trova analogie + crea blend
      3. abstract_from_examples(exs, lvl)→ HierarchicalAbstractor
      4. find_analogy(src_id, domain)    → AnalogyEngine cross-domain
      5. blend(id1, id2)                 → ConceptualBlender
      6. transfer_knowledge(domain1, domain2) → trasferimento cross-domain
      7. suggest_learning_strategy(task) → suggerisce strategia a MetaLearner

    Integrazioni:
      - import_from_knowledge_graph(kg) → importa entità KG come Concept L2
      - observe_causal_structure(cr)    → arricchisce con features causali da BRN-017
    """

    def __init__(self) -> None:
        self.graph       = ConceptualGraph()
        self.abstractor  = HierarchicalAbstractor()
        self.analogy_eng = AnalogyEngine()
        self.blender     = ConceptualBlender()

        self._cycle          = 0
        self._abstractions:  List[str] = []    # IDs dei concetti astratti generati
        self._analogies:     List[Dict] = []
        self._blends:        List[str] = []    # IDs dei blend generati

        logger.info("AbstractionLayer BRN-018 inizializzato (blending + analogia + astrazione)")

    # ── Gestione concetti ────────────────────────────────────────────────────

    def add_concept(self, concept: Concept) -> None:
        """Aggiunge un concetto al grafo. Se esiste già, aggiorna le features."""
        existing = self.graph.get(concept.concept_id)
        if existing is not None:
            existing.features.update(concept.features)
            existing.confidence = max(existing.confidence, concept.confidence)
        else:
            self.graph.add_concept(concept)

    def add_concept_from_dict(
        self,
        label: str,
        features: Dict[str, float],
        domain: str = "unknown",
        level: int  = AbstractionLevel.PERCEPTUAL.value,
        concept_id: Optional[str] = None,
    ) -> Concept:
        c = Concept(
            concept_id        = concept_id or f"c_{uuid.uuid4().hex[:8]}",
            label             = label,
            features          = features,
            domain            = domain,
            abstraction_level = level,
        )
        self.graph.add_concept(c)
        return c

    # ── Processo principale ──────────────────────────────────────────────────

    def process(
        self,
        input_concepts: List[Concept],
        run_abstraction: bool = True,
        run_analogy: bool     = True,
        run_blending: bool    = True,
    ) -> Dict[str, Any]:
        """
        Pipeline cognitiva completa:
          1. Aggiungi tutti i concetti al grafo
          2. (opz) Astrai a livello superiore
          3. (opz) Trova analogie cross-domain
          4. (opz) Crea blend tra i concetti più simili

        Returns:
          dict con 'abstractions', 'analogies', 'blends', 'cycle'
        """
        self._cycle += 1
        for c in input_concepts:
            self.add_concept(c)

        result: Dict[str, Any] = {
            "cycle":        self._cycle,
            "n_input":      len(input_concepts),
            "abstractions": [],
            "analogies":    [],
            "blends":       [],
        }

        # 1. Astrazione
        if run_abstraction and len(input_concepts) >= 2:
            abstracted = self.abstractor.abstract(
                input_concepts,
                target_level=min(5, max(c.abstraction_level for c in input_concepts) + 1)
            )
            if abstracted is not None:
                self.graph.add_concept(abstracted)
                self._abstractions.append(abstracted.concept_id)
                result["abstractions"].append(abstracted.to_dict())

        # 2. Analogie (cerca analogie per il primo concetto negli altri domini)
        if run_analogy and input_concepts:
            source = input_concepts[0]
            other_domain_concepts = [
                c for c in self.graph.all_concepts
                if c.domain != source.domain and c.concept_id != source.concept_id
            ]
            if other_domain_concepts:
                analogy_result = self.analogy_eng.find_analogy(source, other_domain_concepts)
                if analogy_result is not None:
                    target_c, mapping, score = analogy_result
                    projected = self.analogy_eng.project_analogy(
                        source, target_c, mapping, target_c.domain
                    )
                    self.graph.add_concept(projected)
                    self._analogies.append({
                        "source":   source.concept_id,
                        "target":   target_c.concept_id,
                        "projected": projected.concept_id,
                        "score":    score,
                    })
                    result["analogies"].append({
                        "source_label":   source.label,
                        "target_label":   target_c.label,
                        "projected_label": projected.label,
                        "score":          score,
                    })

        # 3. Blending (blend tra i due concetti più simili tra gli input)
        if run_blending and len(input_concepts) >= 2:
            best_pair  = None
            best_sim   = -1.0
            for i, ca in enumerate(input_concepts):
                for cb in input_concepts[i+1:]:
                    sim = self.graph.similarity(ca.concept_id, cb.concept_id)
                    if 0.2 < sim < 0.9 and sim > best_sim:
                        best_sim  = sim
                        best_pair = (ca, cb)
            if best_pair is not None:
                ca, cb = best_pair
                blend = self.blender.blend(ca, cb)
                self.graph.add_concept(blend)
                self._blends.append(blend.concept_id)
                result["blends"].append(blend.to_dict())

        return result

    # ── Operazioni singole ────────────────────────────────────────────────────

    def abstract_from_examples(
        self,
        example_ids: List[str],
        target_level: int = AbstractionLevel.CONCEPTUAL.value,
        label: Optional[str] = None,
    ) -> Optional[Concept]:
        """Astrae da una lista di concept IDs già nel grafo."""
        concepts = [self.graph.get(cid) for cid in example_ids
                    if self.graph.get(cid) is not None]
        if not concepts:
            return None
        result = self.abstractor.abstract(concepts, target_level, label)
        if result:
            self.graph.add_concept(result)
            self._abstractions.append(result.concept_id)
        return result

    def find_analogy(
        self,
        source_id: str,
        target_domain: str,
        min_score: float = 0.25,
    ) -> Optional[Concept]:
        """Trova e proietta un'analogia del concetto source nel target_domain."""
        source = self.graph.get(source_id)
        if source is None:
            return None
        target_pool = self.graph.get_by_domain(target_domain)
        result = self.analogy_eng.find_analogy(source, target_pool, min_score)
        if result is None:
            return None
        target_c, mapping, score = result
        projected = self.analogy_eng.project_analogy(source, target_c, mapping, target_domain)
        self.graph.add_concept(projected)
        self._analogies.append({
            "source": source_id, "target": target_c.concept_id,
            "projected": projected.concept_id, "score": score
        })
        return projected

    def blend(self, concept_id_1: str, concept_id_2: str,
              label: Optional[str] = None) -> Optional[Concept]:
        """Crea un blend tra due concetti già nel grafo."""
        c1 = self.graph.get(concept_id_1)
        c2 = self.graph.get(concept_id_2)
        if c1 is None or c2 is None:
            logger.warning(f"[AbstractionLayer] blend: concetto non trovato "
                           f"({concept_id_1}, {concept_id_2})")
            return None
        result = self.blender.blend(c1, c2, label)
        self.graph.add_concept(result)
        self._blends.append(result.concept_id)
        return result

    def transfer_knowledge(
        self,
        source_domain: str,
        target_domain: str,
    ) -> List[Concept]:
        """
        Trasferisce struttura astratta dal source_domain al target_domain
        tramite analogia su tutti i concetti del source domain.
        Ritorna lista di concetti proiettati nel target domain.
        """
        source_concepts = self.graph.get_by_domain(source_domain)
        target_pool     = self.graph.get_by_domain(target_domain)
        if not source_concepts or not target_pool:
            return []

        transferred = []
        for src in source_concepts:
            result = self.analogy_eng.find_analogy(src, target_pool, min_structural_overlap=0.15)
            if result:
                tgt, mapping, score = result
                proj = self.analogy_eng.project_analogy(src, tgt, mapping, target_domain)
                self.graph.add_concept(proj)
                transferred.append(proj)

        logger.info(f"[AbstractionLayer] Trasferiti {len(transferred)} concetti "
                    f"{source_domain} → {target_domain}")
        return transferred

    def suggest_learning_strategy(self, task_domain: str) -> str:
        """
        Suggerisce una LearningStrategy per il MetaLearner (BRN-013)
        in base ai concetti disponibili nel dominio del task.

        Logica:
          - Molti concetti nel dominio → GRADIENT_BASED (ho dati)
          - Pochi ma con analogie cross-domain → ANALOGICAL
          - Nessun concetto → CURIOSITY_DRIVEN (esplora)
          - Concetti ad alto livello di astrazione → META_GRADIENT
        """
        domain_concepts = self.graph.get_by_domain(task_domain)
        n = len(domain_concepts)

        if n == 0:
            return "CURIOSITY_DRIVEN"

        # Controlla se ci sono analogie disponibili da altri domini
        other_domains = {c.domain for c in self.graph.all_concepts
                         if c.domain != task_domain}
        has_analogies = len(other_domains) > 0 and n < 5

        avg_level = sum(c.abstraction_level for c in domain_concepts) / n

        if has_analogies and n < 5:
            return "ANALOGICAL"
        elif avg_level >= 4:
            return "META_GRADIENT"
        elif n >= 20:
            return "GRADIENT_BASED"
        else:
            return "EPISODIC_REPLAY"

    # ── Integrazione KnowledgeGraph (WorldModel) ──────────────────────────────

    def import_from_knowledge_graph(self, kg: Any) -> int:
        """
        Importa entità dal KnowledgeGraph come Concept di livello PERCEPTUAL.
        Le proprietà dell'entità diventano features del Concept.
        """
        imported = 0
        try:
            for eid, entity in getattr(kg, "_entities", {}).items():
                props = getattr(entity, "properties", {})
                # Converte proprietà in features numeriche
                features: Dict[str, float] = {}
                for k, v in props.items():
                    if isinstance(v, (int, float)):
                        features[k] = min(1.0, max(0.0, float(v)))
                    elif isinstance(v, bool):
                        features[k] = 1.0 if v else 0.0

                concept = Concept(
                    concept_id        = f"kg_{eid}",
                    label             = eid,
                    features          = features,
                    domain            = getattr(entity, "entity_type", "unknown"),
                    abstraction_level = AbstractionLevel.PERCEPTUAL.value,
                    confidence        = 0.75,
                    source            = "knowledge_graph",
                )
                # Importa anche le relazioni semantiche
                for rel in getattr(entity, "relations", []):
                    concept.add_relation(
                        RelationType.SIMILAR_TO,
                        f"kg_{rel.target}",
                        rel.weight,
                    )
                self.graph.add_concept(concept)
                imported += 1
        except Exception as exc:
            logger.warning(f"[AbstractionLayer] import_from_knowledge_graph: {exc}")

        logger.info(f"[AbstractionLayer] Importati {imported} concetti dal KnowledgeGraph")
        return imported

    def observe_causal_structure(self, causal_reasoner: Any) -> int:
        """
        Arricchisce i concetti con features causali dal CausalReasoner (BRN-017).
        Per ogni nodo del CausalGraph, aggiunge features: in_degree, out_degree, strength.
        """
        enriched = 0
        try:
            cg = causal_reasoner.graph
            for nid, node in cg.nodes.items():
                concept = self.graph.get(f"causal_{nid}") or self.graph.get_by_label(nid)
                if concept is None:
                    concept = self.add_concept_from_dict(
                        label   = nid,
                        features = {},
                        domain  = node.domain,
                        level   = AbstractionLevel.STRUCTURAL.value,
                        concept_id = f"causal_{nid}",
                    )
                # Aggiungi features strutturali causali
                n_parents  = len(cg.parents(nid))
                n_children = len(cg.children(nid))
                concept.features["causal_in_degree"]  = min(1.0, n_parents  / 5.0)
                concept.features["causal_out_degree"] = min(1.0, n_children / 5.0)
                concept.features["causal_centrality"] = min(1.0, (n_parents + n_children) / 10.0)
                if node.value is not None:
                    concept.features["current_activation"] = min(1.0, max(0.0, node.value))
                enriched += 1
        except Exception as exc:
            logger.warning(f"[AbstractionLayer] observe_causal_structure: {exc}")

        return enriched

    # ── Status ────────────────────────────────────────────────────────────────

    def get_full_status(self) -> Dict[str, Any]:
        domains = defaultdict(int)
        levels  = defaultdict(int)
        for c in self.graph.all_concepts:
            domains[c.domain] += 1
            levels[c.abstraction_level] += 1

        return {
            "module":          "AbstractionLayer",
            "brn_id":          "BRN-018",
            "status":          "active",
            "cycle":           self._cycle,
            "graph": {
                "total_concepts":  len(self.graph),
                "by_domain":       dict(domains),
                "by_level":        {f"L{k}": v for k, v in sorted(levels.items())},
            },
            "abstractions_created": len(self._abstractions),
            "analogies_found":      len(self._analogies),
            "blends_created":       l