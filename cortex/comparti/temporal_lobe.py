"""
SPEACE Cortex – Temporal Lobe
Comparto 4: Language, Crypto & Market Analysis (Fase 1: solo linguaggio)

Funzioni:
- Analisi di testo: conteggio token, keyword extraction, sentiment placeholder
- Market scan: STUB read-only (Fase 1 ha blockchain_wallet=read_only)

Nessuna dipendenza di rete in Fase 1.
Creato: 2026-04-18 | M1 | PROP-CORTEX-COMPLETE-M1
M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
  In M3L.4 sarà wrappato da LLM adapter (regex_offline fallback).
"""

import re
import sys
from pathlib import Path
from typing import Dict, List
from collections import Counter

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
from cortex.base_compartment import BaseCompartment
from cortex import state_bus

# Parole vuote italiano + inglese (minimal)
_STOPWORDS = {
    # IT
    "il", "la", "lo", "le", "gli", "i", "un", "una", "uno", "di", "a", "da", "in", "con", "su", "per", "tra", "fra",
    "e", "ed", "o", "ma", "se", "che", "non", "è", "sono", "essere", "del", "della", "dello", "degli", "delle",
    # EN
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "with", "and", "or", "but", "if", "that", "not",
    "is", "are", "be", "this", "these", "those",
}


class TemporalLobe(BaseCompartment):
    """Analisi del linguaggio e (stub) mercati."""

    name = "temporal_lobe"
    level = 2  # Cognizione

    def analyze_language(self, text: str) -> Dict:
        """
        Ritorna:
            - token_count (semplice split)
            - char_count
            - word_freq top 5 (escludendo stopwords)
            - sentiment_placeholder: stima euristica (+1 / 0 / -1) su parole chiave
        """
        if not isinstance(text, str):
            return {"error": "input_not_string"}

        tokens = re.findall(r"\w+", text.lower())
        chars = len(text)

        # Frequenza parole (escludi stopword e parole ≤ 2 char)
        meaningful = [t for t in tokens if t not in _STOPWORDS and len(t) > 2]
        freq = Counter(meaningful).most_common(5)

        # Sentiment euristico minimalista
        pos_words = {"good", "better", "excellent", "peace", "harmony", "improve", "bene", "ottimo", "armonia", "pace"}
        neg_words = {"bad", "worse", "error", "fail", "crash", "war", "conflict", "male", "errore", "conflitto"}
        pos_count = sum(1 for t in tokens if t in pos_words)
        neg_count = sum(1 for t in tokens if t in neg_words)
        if pos_count > neg_count:
            sentiment = 1
        elif neg_count > pos_count:
            sentiment = -1
        else:
            sentiment = 0

        return {
            "token_count": len(tokens),
            "char_count": chars,
            "word_freq_top5": freq,
            "sentiment_placeholder": sentiment,
            "note": "sentiment is a heuristic placeholder; replace with calibrated model post-M3",
        }

    def extract_keywords(self, text: str, k: int = 10) -> List[str]:
        """Estrae le top-k keyword (per frequenza, escludendo stopword)."""
        tokens = re.findall(r"\w+", text.lower())
        meaningful = [t for t in tokens if t not in _STOPWORDS and len(t) > 3]
        freq = Counter(meaningful).most_common(k)
        return [w for w, _ in freq]

    def market_scan(self, symbol: str) -> Dict:
        """
        STUB: In Fase 1 blockchain_wallet è read_only e le integrazioni esterne
        di mercato NON sono attivate. Questo metodo documenta l'intento architetturale
        ma non esegue alcuna chiamata esterna.
        """
        return {
            "symbol": symbol,
            "status": "disabled_phase1",
            "reason": "blockchain_wallet=read_only AND no network integrations in Phase 1",
            "will_be_enabled": "Phase 2 (Autonomia Operativa) post-benchmark-validation",
        }

    def self_report(self) -> Dict:
        return {
            "module": "temporal_lobe",
            "version": "1.0",
            "capabilities": ["analyze_language", "extract_keywords", "market_scan (stub)"],
            "network_calls": False,
        }

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def _use_llm_enabled(self) -> bool:
        """Legge epigenome.yaml → llm.use_in_temporal_lobe (default False)."""
        try:
            import yaml
            epi_path = ROOT_DIR / "digitaldna" / "epigenome.yaml"
            if epi_path.exists():
                epi = yaml.safe_load(epi_path.read_text(encoding="utf-8")) or {}
                return bool(
                    (epi.get("llm") or {}).get("use_in_temporal_lobe", False)
                )
        except Exception:
            return False
        return False

    def _llm_interpret(self, text: str) -> Dict:
        """
        Arricchimento semantico via LLM. Se l'LLM non è raggiungibile,
        ritorna {} e il caller userà solo regex_offline.
        """
        try:
            from cortex.llm import LLMClient
            client = LLMClient.from_epigenome()
            resp = client.complete(
                prompt=(
                    "Analizza questo input e rispondi in UNA riga con:\n"
                    "intent=<una parola>; sentiment=<-1|0|+1>; topic=<max 3 parole>.\n"
                    f"Input: {text}"
                ),
                max_tokens=80,
                temperature=0.1,
            )
            return {
                "llm_raw": resp.text,
                "backend": resp.backend,
                "is_stub": resp.is_stub,
                "latency_ms": resp.latency_ms,
            }
        except Exception as e:
            return {"llm_error": str(e)}

    def process(self, state: Dict) -> Dict:
        """
        Trasforma sensory_input.text (o sensory_input.raw) in interpretation.
        Usa regex_offline come base, e (se abilitato da epigenome) arricchisce
        con LLM. Il fallback cascade garantisce che l'assenza dell'LLM non
        interrompa mai il flusso neurale.
        """
        if state_bus.is_blocked(state):
            return self._log(state, status="skipped", note="state_blocked")

        sensory = state.get("sensory_input", {}) or {}
        text = sensory.get("text") or sensory.get("raw") or ""

        if not text:
            interp = state.setdefault("interpretation", {})
            interp["source"] = "temporal_lobe"
            interp["mode"] = "regex_offline"
            interp["empty_input"] = True
            interp["sentiment"] = 0
            interp["keywords"] = []
            state["uncertainty"] = max(float(state.get("uncertainty", 0.0) or 0.0), 0.6)
            return self._log(state, status="ok", note="empty_input")

        lang_result = self.analyze_language(text)
        keywords = self.extract_keywords(text, k=10)

        interp = state.setdefault("interpretation", {})
        interp["source"] = "temporal_lobe"
        interp["mode"] = "regex_offline"
        interp["sentiment"] = lang_result.get("sentiment_placeholder", 0)
        interp["token_count"] = lang_result.get("token_count", 0)
        interp["keywords"] = keywords
        interp["top_freq"] = lang_result.get("word_freq_top5", [])

        # Arricchimento LLM opzionale (opt-in)
        if self._use_llm_enabled():
            llm_out = self._llm_interpret(text)
            interp["llm"] = llm_out
            # Se l'LLM non è stub, promuovi il mode
            if llm_out.get("is_stub") is False:
                interp["mode"] = f"llm+{llm_out.get('backend','?')}"

        # Euristica uncertainty
        tokens = lang_result.get("token_count", 0)
        if tokens < 5:
            state["uncertainty"] = max(float(state.get("uncertainty", 0.0) or 0.0), 0.7)
        elif tokens < 20:
            state["uncertainty"] = max(float(state.get("uncertainty", 0.0) or 0.0), 0.4)

        return self._log(state, status="ok", note=f"tokens={tokens}")
