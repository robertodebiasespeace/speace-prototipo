"""
cortex.memory.real_embeddings
==============================
M13.3 — RealEmbeddings: embeddings semantici via Ollama con fallback deterministico.

Utilizza il modello `nomic-embed-text` di Ollama (768 dimensioni) per generare
embedding densi e semanticamente significativi per la memoria autobiografica.

Se Ollama non è disponibile (connessione rifiutata, timeout, modello mancante),
fallback automatico a embedding deterministico hash-based normalizzato — garantisce
che il sistema funzioni sempre, anche offline.

Ispirato a GROK SPEACE v3.0 RealEmbeddings + ImprovedVectorMemory.
M13.3 | 2026-04-29
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from typing import List, Optional

logger = logging.getLogger("speace.memory.embeddings")

# Dimensione embedding nomic-embed-text
EMBEDDING_DIM = 768


class RealEmbeddings:
    """
    Motore di embedding semantico per SPEACE.

    Prova a usare Ollama (nomic-embed-text) come prima scelta.
    In caso di errore, genera un embedding deterministico hash-based
    normalizzato che garantisce:
      - stessa stringa → stesso vettore (determinismo)
      - stringhe diverse → vettori diversi (discriminazione)
      - vettori normalizzati a norma 1 (cosine similarity corretta)

    Uso:
        emb = RealEmbeddings()
        vector = emb.embed_sync("cambiamento climatico oceani")
        # → List[float] di lunghezza 768, norma ≈ 1.0

    Uso asincrono (preferito):
        vector = await emb.embed("cambiamento climatico oceani")
    """

    def __init__(
        self,
        base_url:   str = "http://localhost:11434",
        model:      str = "nomic-embed-text",
        timeout_s:  float = 5.0,
        dim:        int = EMBEDDING_DIM,
    ) -> None:
        self._base_url  = base_url.rstrip("/")
        self._model     = model
        self._timeout   = timeout_s
        self._dim       = dim
        self._ollama_ok: Optional[bool] = None   # None = non ancora testato
        self._n_ollama  = 0
        self._n_fallback = 0

    # ── API asincrona ─────────────────────────────────────────────────────────

    async def embed(self, text: str) -> List[float]:
        """
        Genera embedding per `text`.
        Tenta Ollama, poi fallback deterministico se non disponibile.

        Returns:
            List[float] di lunghezza self._dim, normalizzato (norma ≈ 1.0)
        """
        if self._ollama_ok is not False:
            result = await self._try_ollama(text)
            if result is not None:
                self._ollama_ok = True
                self._n_ollama += 1
                return result
            else:
                self._ollama_ok = False
                logger.debug("[RealEmbeddings] Ollama non disponibile — usando fallback deterministico")

        self._n_fallback += 1
        return self._fallback_embed(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embedding per lista di testi."""
        results = []
        for text in texts:
            results.append(await self.embed(text))
        return results

    # ── API sincrona (per compatibilità con codice non-async) ─────────────────

    def embed_sync(self, text: str) -> List[float]:
        """
        Versione sincrona di embed() — usa solo il fallback deterministico.
        Utile in contesti non-async (test, script, dashboard).
        """
        if self._ollama_ok is not False:
            result = self._try_ollama_sync(text)
            if result is not None:
                self._ollama_ok = True
                self._n_ollama += 1
                return result
            self._ollama_ok = False

        self._n_fallback += 1
        return self._fallback_embed(text)

    # ── Ollama ────────────────────────────────────────────────────────────────

    async def _try_ollama(self, text: str) -> Optional[List[float]]:
        """Tenta chiamata asincrona a Ollama /api/embeddings."""
        try:
            import aiohttp
            payload = {"model": self._model, "prompt": text}
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self._base_url}/api/embeddings",
                    json=payload,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        emb = data.get("embedding", [])
                        if emb and len(emb) > 0:
                            return [float(x) for x in emb]
        except Exception as e:
            logger.debug("[RealEmbeddings] Ollama async error: %s", e)
        return None

    def _try_ollama_sync(self, text: str) -> Optional[List[float]]:
        """Tenta chiamata sincrona a Ollama /api/embeddings."""
        try:
            import urllib.request
            import json as _json
            payload = _json.dumps({"model": self._model, "prompt": text}).encode()
            req = urllib.request.Request(
                f"{self._base_url}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = _json.loads(resp.read().decode())
                emb = data.get("embedding", [])
                if emb and len(emb) > 0:
                    return [float(x) for x in emb]
        except Exception as e:
            logger.debug("[RealEmbeddings] Ollama sync error: %s", e)
        return None

    # ── Fallback deterministico ───────────────────────────────────────────────

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Embedding deterministico hash-based.

        Algoritmo:
          1. SHA-256 del testo → seed uint32
          2. LCG pseudo-random con quel seed → dim float values
          3. Perturbazione text-dipendente basata sui caratteri
          4. Normalizzazione a norma 1 (cosine similarity corretta)

        Proprietà:
          - Determinismo: stessa stringa → stesso vettore, sempre
          - Discriminazione: stringhe diverse producono vettori diversi
          - Distribuzione quasi-Gaussiana (LCG su spazio grande)
          - Norma = 1.0 (pronto per cosine similarity)
        """
        # Seed deterministico da SHA-256
        h = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        seed = int(h[:8], 16)   # 32 bit

        # LCG (Linear Congruential Generator) — parametri Knuth
        a, c, m = 1664525, 1013904223, 2**32
        state = seed
        values: List[float] = []
        for _ in range(self._dim):
            state = (a * state + c) % m
            # Mappa [0, 2^32) → [-1, +1]
            values.append((state / (m - 1)) * 2.0 - 1.0)

        # Perturbazione text-dipendente (aumenta discriminazione su testi simili)
        text_bytes = text.encode("utf-8", errors="replace")[:256]
        for i, byte_val in enumerate(text_bytes):
            idx = (i * 7 + byte_val * 3) % self._dim
            values[idx] += (byte_val - 128) * 0.003

        # Normalizzazione L2
        norm = math.sqrt(sum(v * v for v in values))
        if norm > 1e-9:
            values = [v / norm for v in values]
        else:
            values = [0.0] * self._dim
            values[0] = 1.0   # degenerate case: unit vector

        return values

    # ── Diagnostica ───────────────────────────────────────────────────────────

    @property
    def using_ollama(self) -> bool:
        """True se Ollama è disponibile e funzionante."""
        return self._ollama_ok is True

    @property
    def dim(self) -> int:
        return self._dim

    def get_stats(self) -> dict:
        return {
            "model":       self._model,
            "dim":         self._dim,
            "ollama_ok":   self._ollama_ok,
            "n_ollama":    self._n_ollama,
            "n_fallback":  self._n_fallback,
        }


__all__ = ["RealEmbeddings", "EMBEDDING_DIM"]
