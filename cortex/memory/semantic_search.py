"""
cortex.memory.semantic_search
===============================
M13.3 — SemanticSearch: ricerca per similarità semantica sulla memoria SPEACE.

Aggiunge capacità di ricerca semantica (cosine similarity) all'AutobiographicalMemory,
che attualmente supporta solo ricerca per tag e timestamp.

Architettura:
  RealEmbeddings (Ollama nomic-embed-text / fallback hash)
       ↓
  SemanticMemoryStore (in-memory index: episode_id → embedding)
       ↓
  cosine_similarity(query_emb, stored_emb) * importance_weight
       ↓
  top-K episodi semanticamente più vicini alla query

Integrazione con AutobiographicalMemory:
  AutobiographicalMemory.search_semantic(query, top_k) →
    SemanticSearch.search(query, top_k) → List[SemanticResult]

Ispirato a GROK SPEACE v3.0 ImprovedVectorMemory.
M13.3 | 2026-04-29
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .real_embeddings import RealEmbeddings

logger = logging.getLogger("speace.memory.semantic")


# ─────────────────────────────────────────────────────────────────────────────
# SemanticEntry — vettore associato a un episodio
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SemanticEntry:
    """
    Rappresentazione vettoriale di un episodio in memoria.

    Attributi:
        episode_id:  ID univoco dell'episodio (int dal DB SQLite, o str)
        content:     testo del contenuto (per debug/display)
        embedding:   vettore embedding [float × dim]
        importance:  peso di importanza [0, 1] — scala il similarity score
        tags:        tag opzionali per filtri aggiuntivi
        timestamp:   UNIX timestamp di creazione
    """
    episode_id:  str
    content:     str
    embedding:   List[float]
    importance:  float = 0.5
    tags:        List[str] = field(default_factory=list)
    timestamp:   float = field(default_factory=time.time)


@dataclass
class SemanticResult:
    """
    Risultato di una ricerca semantica.

    Attributi:
        episode_id:   ID dell'episodio trovato
        content:      testo del contenuto
        score:        score finale = cosine_sim * importance [0, 1]
        cosine_sim:   similarità coseno grezza [−1, +1]
        importance:   importanza dell'episodio
        tags:         tag dell'episodio
    """
    episode_id:   str
    content:      str
    score:        float
    cosine_sim:   float
    importance:   float
    tags:         List[str]

    def summary(self) -> str:
        return (
            f"[SemanticResult] id={self.episode_id} "
            f"score={self.score:.4f} (cos={self.cosine_sim:.4f} × imp={self.importance:.2f}) "
            f"tags={self.tags} | {self.content[:60]}..."
        )


# ─────────────────────────────────────────────────────────────────────────────
# SemanticSearch — motore di ricerca semantica
# ─────────────────────────────────────────────────────────────────────────────

class SemanticSearch:
    """
    M13.3 — Motore di ricerca semantica per la memoria autobiografica di SPEACE.

    Mantiene un indice in-memory di embedding + importance per tutti gli episodi
    indicizzati. La ricerca avviene tramite cosine similarity pesata per importanza.

    Uso semplice (sincrono con fallback):
        search = SemanticSearch()
        search.index_sync("ep_1", "oceani in pericolo", importance=0.8)
        search.index_sync("ep_2", "crisi climatica terrestre", importance=0.7)
        search.index_sync("ep_3", "ricetta pizza", importance=0.3)

        results = search.search_sync("cambiamento climatico", top_k=2)
        # → [ep_1, ep_2] con score alto (semanticamente correlati)

    Uso asincrono (preferito, usa Ollama se disponibile):
        results = await search.search("cambiamento climatico", top_k=2)

    Integrazione AutobiographicalMemory:
        # In autobiographical_memory.py:
        self._semantic = SemanticSearch()
        # Al salvataggio di un episodio:
        self._semantic.index_sync(str(episode_id), episode_content, importance)
        # Alla ricerca semantica:
        return self._semantic.search_sync(query, top_k)
    """

    def __init__(
        self,
        embedder: Optional[RealEmbeddings] = None,
        min_score: float = 0.0,
    ) -> None:
        self._embedder = embedder or RealEmbeddings()
        self._index:    Dict[str, SemanticEntry] = {}
        self._min_score = min_score
        self._n_indexed   = 0
        self._n_searches  = 0

    # ── Indicizzazione ────────────────────────────────────────────────────────

    async def index(
        self,
        episode_id: str,
        content:    str,
        importance: float = 0.5,
        tags:       Optional[List[str]] = None,
    ) -> None:
        """
        Indicizza un episodio nel semantic store (asincrono).
        Sovrascrive se episode_id già presente.
        """
        embedding = await self._embedder.embed(content)
        self._index[episode_id] = SemanticEntry(
            episode_id = episode_id,
            content    = content[:500],   # tronca per risparmiare memoria
            embedding  = embedding,
            importance = float(max(0.0, min(1.0, importance))),
            tags       = tags or [],
        )
        self._n_indexed += 1
        logger.debug("[SemanticSearch] indexed ep=%s (total=%d)", episode_id, len(self._index))

    def index_sync(
        self,
        episode_id: str,
        content:    str,
        importance: float = 0.5,
        tags:       Optional[List[str]] = None,
    ) -> None:
        """Indicizza un episodio (sincrono, usa embed_sync → fallback)."""
        embedding = self._embedder.embed_sync(content)
        self._index[episode_id] = SemanticEntry(
            episode_id = episode_id,
            content    = content[:500],
            embedding  = embedding,
            importance = float(max(0.0, min(1.0, importance))),
            tags       = tags or [],
        )
        self._n_indexed += 1

    def remove(self, episode_id: str) -> bool:
        """Rimuove un episodio dall'indice. Ritorna True se trovato."""
        if episode_id in self._index:
            del self._index[episode_id]
            return True
        return False

    def update_importance(self, episode_id: str, importance: float) -> bool:
        """Aggiorna l'importanza di un episodio già indicizzato."""
        if episode_id in self._index:
            self._index[episode_id].importance = max(0.0, min(1.0, importance))
            return True
        return False

    # ── Ricerca ───────────────────────────────────────────────────────────────

    async def search(
        self,
        query:   str,
        top_k:   int = 5,
        tag_filter: Optional[List[str]] = None,
        min_score:  Optional[float] = None,
    ) -> List[SemanticResult]:
        """
        Ricerca semantica asincrona.

        Args:
            query:       testo della query
            top_k:       numero massimo di risultati
            tag_filter:  se specificato, considera solo episodi con almeno un tag incluso
            min_score:   soglia minima score (default: self._min_score)

        Returns:
            Lista di SemanticResult ordinata per score decrescente (max top_k)
        """
        if not self._index:
            return []

        query_emb = await self._embedder.embed(query)
        return self._rank(query_emb, top_k, tag_filter, min_score)

    def search_sync(
        self,
        query:   str,
        top_k:   int = 5,
        tag_filter: Optional[List[str]] = None,
        min_score:  Optional[float] = None,
    ) -> List[SemanticResult]:
        """
        Ricerca semantica sincrona (usa fallback embedding).

        Stesse semantiche di search() ma senza await.
        """
        if not self._index:
            return []

        query_emb = self._embedder.embed_sync(query)
        return self._rank(query_emb, top_k, tag_filter, min_score)

    # ── Core ranking ─────────────────────────────────────────────────────────

    def _rank(
        self,
        query_emb:  List[float],
        top_k:      int,
        tag_filter: Optional[List[str]],
        min_score:  Optional[float],
    ) -> List[SemanticResult]:
        """Calcola cosine similarity × importance per tutti gli entry e ritorna top-K."""
        self._n_searches += 1
        threshold = min_score if min_score is not None else self._min_score
        scores: List[Tuple[float, SemanticEntry]] = []

        for entry in self._index.values():
            # Filtro tag opzionale
            if tag_filter and not any(t in entry.tags for t in tag_filter):
                continue

            cos = _cosine_similarity(query_emb, entry.embedding)
            # Mappa cosine [-1,+1] → [0,1] per moltiplicazione con importance
            cos_norm = (cos + 1.0) / 2.0
            final_score = cos_norm * entry.importance

            if final_score >= threshold:
                scores.append((final_score, entry))

        scores.sort(key=lambda x: x[0], reverse=True)

        results = []
        for final_score, entry in scores[:top_k]:
            cos_raw = _cosine_similarity(query_emb, entry.embedding)
            results.append(SemanticResult(
                episode_id  = entry.episode_id,
                content     = entry.content,
                score       = round(final_score, 5),
                cosine_sim  = round(cos_raw, 5),
                importance  = entry.importance,
                tags        = list(entry.tags),
            ))

        return results

    # ── Diagnostica ──────────────────────────────────────────────────────────

    @property
    def n_indexed(self) -> int:
        """Numero di episodi nell'indice."""
        return len(self._index)

    def get_stats(self) -> dict:
        return {
            "n_indexed":   self.n_indexed,
            "n_indexed_total": self._n_indexed,
            "n_searches":  self._n_searches,
            "embedder":    self._embedder.get_stats(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Funzione cosine similarity — pure Python, no numpy required
# ─────────────────────────────────────────────────────────────────────────────

def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Cosine similarity tra due vettori di uguale dimensione.

    Returns:
        float in [-1.0, +1.0]. 1.0 = identici, 0.0 = ortogonali, -1.0 = opposti.
        Ritorna 0.0 se uno dei vettori ha norma zero.
    """
    if len(a) != len(b):
        # Fallback: tronca al minore
        n = min(len(a), len(b))
        a, b = a[:n], b[:n]

    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))

    denom = norm_a * norm_b
    if denom < 1e-9:
        return 0.0
    return max(-1.0, min(1.0, dot / denom))


__all__ = [
    "SemanticSearch",
    "SemanticEntry",
    "SemanticResult",
    "RealEmbeddings",
]
