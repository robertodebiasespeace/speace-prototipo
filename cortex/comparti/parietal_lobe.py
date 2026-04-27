"""
SPEACE Cortex – Parietal Lobe
Comparto 5: Sensory / Tools (API, IoT, external fetches)

Fase 1: Solo fetch HTTP verso whitelist rigorosa, nessun IoT reale.
Il gate safe_mode può disattivare qualsiasi chiamata esterna.

Creato: 2026-04-18 | M1 | PROP-CORTEX-COMPLETE-M1
M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
  Parietal è la "porta d'ingresso" sensoriale del flusso neurale.
"""

import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cortex.base_compartment import BaseCompartment
from cortex import state_bus

# Whitelist domini approvati per Fase 1
_APPROVED_DOMAINS = (
    "rigeneproject.org",
    "www.rigeneproject.org",
    "noaa.gov",
    "www.noaa.gov",
    "unstats.un.org",
    "artificialintelligenceact.eu",
    "www.artificialintelligenceact.eu",
    "oecd.ai",
)


class ParietalLobe(BaseCompartment):
    """Interfaccia sensoriale / API / IoT (read-only in Fase 1)."""

    name = "parietal_lobe"
    level = 4  # Azione (porta d'ingresso sensoriale)

    def __init__(self):
        self._last_fetch_result: Optional[Dict] = None

    # ------------------------------------------------------------------
    # SAFE MODE CHECK (evita dipendenza circolare con SafetyModule)
    # ------------------------------------------------------------------

    def _safe_mode_active(self) -> bool:
        try:
            import yaml
            epi_path = ROOT_DIR / "digitaldna" / "epigenome.yaml"
            if epi_path.exists():
                with open(epi_path, "r", encoding="utf-8") as f:
                    epi = yaml.safe_load(f) or {}
                return bool(epi.get("flags", {}).get("safe_mode", True))
        except Exception:
            pass
        return True  # fallback: safe_mode ON

    # ------------------------------------------------------------------
    # FETCH API con whitelist
    # ------------------------------------------------------------------

    def _domain_allowed(self, url: str) -> bool:
        try:
            host = urlparse(url).hostname or ""
            return host.lower() in _APPROVED_DOMAINS
        except Exception:
            return False

    def fetch_api(self, endpoint: str, safe_only: bool = True, timeout: int = 10) -> Dict:
        """
        Fetch HTTP GET di un endpoint.
        - Accetta solo URL https
        - Solo domini nella whitelist se safe_only=True
        - Rispetta safe_mode (se True, niente rete)
        """
        if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
            return {"status": "rejected", "reason": "invalid_url_scheme"}

        if safe_only and not self._domain_allowed(endpoint):
            return {
                "status": "rejected",
                "reason": "domain_not_in_whitelist",
                "allowed": list(_APPROVED_DOMAINS),
            }

        if self._safe_mode_active() and safe_only is False:
            # Se l'utente vuole bypassare la whitelist, safe_mode deve essere OFF (non è, in Fase 1)
            return {
                "status": "rejected",
                "reason": "safe_mode_active_and_safe_only_disabled",
            }

        try:
            import requests  # import lazy per non forzare la dipendenza se non usata
            resp = requests.get(endpoint, timeout=timeout)
            result = {
                "status": "ok",
                "http_status": resp.status_code,
                "content_length": len(resp.content),
                "endpoint": endpoint,
            }
            self._last_fetch_result = result
            return result
        except Exception as e:
            return {"status": "error", "reason": str(e), "endpoint": endpoint}

    # ------------------------------------------------------------------
    # IoT (stub Fase 1)
    # ------------------------------------------------------------------

    def iot_read(self, sensor_id: str) -> Dict:
        """
        STUB: nessun sensore IoT connesso in Fase 1.
        L'Agente Organismico che gestirà sensori reali è pianificato per Fase 2+.
        """
        return {
            "sensor_id": sensor_id,
            "status": "no_iot_connected_phase1",
            "reason": "Agente Organismico non attivo. Sensori reali in Fase 2+.",
        }

    def self_report(self) -> Dict:
        return {
            "module": "parietal_lobe",
            "version": "1.0",
            "allowed_domains": list(_APPROVED_DOMAINS),
            "iot_connected": False,
            "safe_mode": self._safe_mode_active(),
        }

    # ------------------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # ------------------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Normalizza il sensory_input del ciclo.
        In Fase 1 NON esegue automaticamente fetch HTTP: il Parietal è "passivo"
        rispetto a state.sensory_input che viene popolato dal chiamante
        (SMFOI-v3 o un agente esterno). Se presente un flag 'fetch_hint' con
        endpoint whitelisted, può arricchire sensory_input.fetch_status.
        """
        if state_bus.is_blocked(state):
            return self._log(state, status="skipped", note="state_blocked")

        sensory = state.setdefault("sensory_input", {})
        # Normalizzazione: almeno text vuoto se nulla
        if "text" not in sensory:
            sensory["text"] = sensory.get("raw", "") or ""

        # Fetch opzionale (solo se esplicitamente richiesto e whitelisted)
        fetch_hint = sensory.get("fetch_hint")
        if fetch_hint and isinstance(fetch_hint, str):
            fetch_result = self.fetch_api(fetch_hint, safe_only=True)
            sensory["fetch_status"] = fetch_result.get("status", "unknown")
            sensory["fetch_endpoint"] = fetch_hint
            note = f"fetch:{sensory['fetch_status']}"
        else:
            sensory["fetch_status"] = "not_requested"
            note = "passive"

        return self._log(state, status="ok", note=note)
