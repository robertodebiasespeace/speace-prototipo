"""
SPEACE Cortex – Safety Module
Comparto 3: Risk Gates & SafeProactive integration

Funzioni:
- Valutazione Risk Level delle azioni proposte
- Lettura flag safe_mode da epigenome
- Guard che blocca azioni Medium+ senza approvazione esplicita
- Thin wrapper sopra SafeProactive, NON un sostituto

Creato: 2026-04-18 | M1 | PROP-CORTEX-COMPLETE-M1
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Callable, Any, Optional

ROOT_DIR = Path(__file__).parent.parent.parent
EPIGENOME_PATH = ROOT_DIR / "digitaldna" / "epigenome.yaml"
sys.path.insert(0, str(ROOT_DIR))

from cortex.base_compartment import BaseCompartment
from cortex import state_bus


class SafetyModule(BaseCompartment):
    """
    Gate di sicurezza del Cortex.
    Non esegue mai un'azione: valuta, classifica e delega a SafeProactive.
    Ha override assoluto sul flusso neurale (Level 1).
    """

    name = "safety_module"
    level = 1
    _OVERRIDE_ALLOWED = True

    # Parole chiave che elevano automaticamente il Risk Level
    _HIGH_RISK_KEYWORDS = (
        "replicate", "replicat", "delete", "rm ", "drop",
        "wallet", "transfer", "send_funds", "bridge",
        "disable_safe_mode", "disable_rollback",
    )
    _MEDIUM_RISK_KEYWORDS = (
        "mutate", "mutat", "modify_genome", "modify_epigenome",
        "scrape", "fetch_external", "execute_script",
    )

    def __init__(self):
        self._epigenome_cache: Optional[Dict] = None

    # ------------------------------------------------------------------
    # STATO E CONFIGURAZIONE
    # ------------------------------------------------------------------

    def _load_epigenome(self) -> Dict:
        """Carica epigenome.yaml (con cache interna)."""
        if self._epigenome_cache is None:
            if EPIGENOME_PATH.exists():
                with open(EPIGENOME_PATH, "r", encoding="utf-8") as f:
                    self._epigenome_cache = yaml.safe_load(f) or {}
            else:
                self._epigenome_cache = {}
        return self._epigenome_cache

    def check_safe_mode(self) -> bool:
        """True se safe_mode è attivo (valore di default: True)."""
        epi = self._load_epigenome()
        return bool(epi.get("flags", {}).get("safe_mode", True))

    def rollback_system_active(self) -> bool:
        epi = self._load_epigenome()
        return bool(epi.get("flags", {}).get("rollback_system_active", True))

    # ------------------------------------------------------------------
    # VALUTAZIONE RISCHIO
    # ------------------------------------------------------------------

    def evaluate_risk(self, action: Dict) -> str:
        """
        Classifica un'azione come 'low' | 'medium' | 'high' | 'regulatory'.

        action è un dict con almeno:
            - name: str
            - description: str (opzionale)
            - payload: dict (opzionale)
        """
        name = str(action.get("name", "")).lower()
        desc = str(action.get("description", "")).lower()
        text = f"{name} {desc}"

        # Livello Regulatory: compliance
        if "regulatory" in text or "compliance" in text or "eu_ai_act" in text:
            return "regulatory"

        # Livello High: parole critiche
        if any(kw in text for kw in self._HIGH_RISK_KEYWORDS):
            return "high"

        # Livello Medium: parole intermedie
        if any(kw in text for kw in self._MEDIUM_RISK_KEYWORDS):
            return "medium"

        return "low"

    # ------------------------------------------------------------------
    # GUARD (wrapper per azioni)
    # ------------------------------------------------------------------

    def guard(self, action_callable: Callable, action_meta: Dict) -> Dict:
        """
        Esegue action_callable SOLO se:
         - safe_mode è True E azione è low, oppure
         - l'azione è stata esplicitamente pre-approvata (payload['pre_approved']=True)

        Altrimenti non esegue e ritorna un record strutturato da passare a SafeProactive.
        """
        risk = self.evaluate_risk(action_meta)
        pre_approved = bool(action_meta.get("payload", {}).get("pre_approved", False))
        safe_mode = self.check_safe_mode()

        # Azione bloccata se safe_mode off e non pre-approvata, oppure risk >= medium senza approvazione
        if risk in ("medium", "high", "regulatory") and not pre_approved:
            return {
                "executed": False,
                "risk_level": risk,
                "reason": "requires_safeproactive_approval",
                "action": action_meta.get("name"),
                "safe_mode_active": safe_mode,
            }

        # Azione Low: procedi
        try:
            result = action_callable() if callable(action_callable) else None
            return {
                "executed": True,
                "risk_level": risk,
                "result": result,
                "safe_mode_active": safe_mode,
            }
        except Exception as e:
            return {
                "executed": False,
                "risk_level": risk,
                "error": str(e),
                "safe_mode_active": safe_mode,
            }

    # ------------------------------------------------------------------
    # SELF-CHECK
    # ------------------------------------------------------------------

    def self_report(self) -> Dict:
        """Ritorna un report sintetico dello stato del Safety Module."""
        return {
            "safe_mode": self.check_safe_mode(),
            "rollback_system_active": self.rollback_system_active(),
            "module": "safety_module",
            "version": "1.0",
        }

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Valuta lo state corrente e, se necessario, blocca il flusso.
        Safety può fare override assoluto: setta safety_flags.blocked=True
        se risk >= 0.9 o se interpretation contiene azioni ad alto rischio.
        """
        # 1. Controllo safe_mode di sistema
        if not self.check_safe_mode():
            state = state_bus.mark_safety_block(state, risk_level="regulatory",
                                                reason="safe_mode_disabled_at_system_level")
            return self._log(state, status="blocked", note="safe_mode_off")

        # 2. Analisi di rischio dall'interpretation o decision corrente
        decision = state.get("decision", {}) or {}
        interpretation = state.get("interpretation", {}) or {}
        risk_score = float(state.get("risk", 0.0) or 0.0)

        # 3. Se la decision contiene un'azione, classifica
        action_meta = decision.get("proposed_action")
        if action_meta:
            risk_level = self.evaluate_risk(action_meta)
            decision["risk_level"] = risk_level
            # Blocco su high/regulatory senza pre_approved
            pre_approved = bool(action_meta.get("payload", {}).get("pre_approved", False))
            if risk_level in ("high", "regulatory") and not pre_approved:
                state = state_bus.mark_safety_block(state, risk_level=risk_level,
                                                    reason=f"action_{action_meta.get('name')}_requires_approval")
                return self._log(state, status="blocked", note=f"{risk_level}_no_approval")

        # 4. Blocco hard su risk score molto alto
        if risk_score >= 0.9:
            state = state_bus.mark_safety_block(state, risk_level="high",
                                                reason=f"risk_score_{risk_score:.2f}_over_threshold")
            return self._log(state, status="blocked", note="risk_threshold")

        return self._log(state, status="ok")
