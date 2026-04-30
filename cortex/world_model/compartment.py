"""
SPEACE World Model / Knowledge Graph
9° comparto del Cortex – Centro Cognitivo Centrale

Mantiene un modello interno dinamico della realtà:
- Stato del pianeta, ecosistemi, tecnologia, SPEACE stesso
- Inferenza sistemica e simulazione scenari
- Memoria semantica a lungo termine

Versione: 1.0 | 2026-04-17
M3L.1 refactor (2026-04-19): inherits BaseCompartment, adds process(state).
"""

import sys
import json
import datetime
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(__file__).parent.parent
WORLD_MODEL_FILE = ROOT_DIR / "memory" / "world_model.json"
WORLD_MODEL_FILE.parent.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT_DIR))
from cortex.base_compartment import BaseCompartment
from cortex import state_bus


class WorldModel(BaseCompartment):
    """
    Modello interno dinamico della realtà di SPEACE.
    Tutti i comparti Cortex interrogano e aggiornano questo modello.
    """

    name = "world_model"
    level = 2  # Cognizione (centro cognitivo)

    def __init__(self):
        self.data = self._load()
        self._ensure_structure()

    def _ensure_structure(self):
        """Inizializza struttura se assente."""
        defaults = {
            "meta": {
                "version": "1.0",
                "created": datetime.datetime.now().isoformat(),
                "last_updated": datetime.datetime.now().isoformat(),
                "update_count": 0,
            },
            "speace_state": {
                "phase": 1,
                "fitness": 0.0,
                "active_agents": [],
                "last_cycle": None,
                "proposals_pending": 0,
            },
            "planet_state": {
                "climate": {"status": "critical", "co2_ppm": 422, "last_updated": None},
                "biodiversity": {"status": "declining", "last_updated": None},
                "social": {"sdg_progress": "insufficient", "last_updated": None},
            },
            "technology_state": {
                "ai_capability_level": "narrow_general",
                "iot_connected_devices_bn": 16,
                "quantum_readiness": "experimental",
            },
            "rigene_objectives": [],
            "knowledge_graph": {},
            "scenarios": [],
        }
        for key, val in defaults.items():
            if key not in self.data:
                self.data[key] = val
        self._save()

    # -------------------------------------------------------
    # AGGIORNAMENTO
    # -------------------------------------------------------

    def update(self, domain: str, key: str, value: Any, source: str = "internal"):
        """Aggiorna un nodo del World Model."""
        if domain not in self.data:
            self.data[domain] = {}
        self.data[domain][key] = value
        self.data["meta"]["last_updated"] = datetime.datetime.now().isoformat()
        self.data["meta"]["update_count"] += 1
        self._save()

    def update_speace_state(self, **kwargs):
        """Aggiorna stato interno SPEACE."""
        self.data["speace_state"].update(kwargs)
        self.data["meta"]["last_updated"] = datetime.datetime.now().isoformat()
        self._save()

    def add_knowledge(self, entity: str, properties: Dict, relations: List[Dict] = None):
        """
        Aggiunge nodo al Knowledge Graph.
        entity: nome entità (es. "CO2_emissions")
        properties: dict di proprietà
        relations: lista di {"rel": "causes", "target": "climate_change"}
        """
        kg = self.data.setdefault("knowledge_graph", {})
        kg[entity] = {
            "properties": properties,
            "relations": relations or [],
            "added_at": datetime.datetime.now().isoformat(),
        }
        self._save()

    def fetch_rigene_objectives(self) -> List[str]:
        """
        Fetch obiettivi dal sito Rigene Project.
        Fallback su obiettivi predefiniti se non raggiungibile.
        """
        try:
            response = requests.get("https://www.rigeneproject.org", timeout=10)
            if response.status_code == 200:
                # Parsing semplificato: cerca keywords chiave
                text = response.text
                objectives = self._extract_objectives_from_text(text)
                self.data["rigene_objectives"] = objectives
                self.data["meta"]["last_updated"] = datetime.datetime.now().isoformat()
                self._save()
                return objectives
        except Exception as e:
            pass

        # Fallback su obiettivi hardcoded dal documento SPEACE
        fallback = [
            "Guide AI and tech ecosystem toward improvement of life and natural ecosystems",
            "Solve global problems: climate change, pollution, poverty, pandemic",
            "Develop Digital DNA framework for safe technological evolution",
            "Achieve UN SDGs Agenda 2030",
            "Create TINA - Technical Intelligent Nervous Adaptive System",
            "Build distributed cognitive collective brain",
            "Promote harmony, peace, ecological-social-technological balance",
        ]
        self.data["rigene_objectives"] = fallback
        self._save()
        return fallback

    def _extract_objectives_from_text(self, text: str) -> List[str]:
        """Estrazione semplice di obiettivi dal testo HTML."""
        keywords = ["objective", "goal", "mission", "vision", "target", "purpose"]
        lines = text.split("\n")
        objectives = []
        for line in lines:
            line_clean = line.strip()
            if any(kw in line_clean.lower() for kw in keywords) and len(line_clean) > 20:
                import re
                clean = re.sub(r'<[^>]+>', '', line_clean).strip()
                if len(clean) > 20:
                    objectives.append(clean[:200])
        return objectives[:10] if objectives else []

    # -------------------------------------------------------
    # QUERY E INFERENZA
    # -------------------------------------------------------

    def query(self, domain: str, key: Optional[str] = None) -> Any:
        """Query al World Model."""
        if domain not in self.data:
            return None
        if key:
            return self.data[domain].get(key)
        return self.data[domain]

    def get_summary(self) -> Dict:
        """Restituisce summary dello stato corrente."""
        return {
            "last_updated": self.data["meta"]["last_updated"],
            "speace_fitness": self.data["speace_state"]["fitness"],
            "speace_phase": self.data["speace_state"]["phase"],
            "planet_climate": self.data["planet_state"]["climate"]["status"],
            "rigene_objectives_count": len(self.data.get("rigene_objectives", [])),
            "knowledge_nodes": len(self.data.get("knowledge_graph", {})),
            "update_count": self.data["meta"]["update_count"],
        }

    def run_scenario(self, scenario_name: str, params: Dict) -> Dict:
        """
        Simulazione 'what-if' semplificata.
        """
        result = {
            "scenario": scenario_name,
            "params": params,
            "timestamp": datetime.datetime.now().isoformat(),
            "outcome": "Scenario simulato (implementazione avanzata in Fase 2)",
            "confidence": 0.3,
        }
        self.data.setdefault("scenarios", []).append(result)
        self._save()
        return result

    # -------------------------------------------------------
    # PERSISTENZA
    # -------------------------------------------------------

    def _load(self) -> Dict:
        if WORLD_MODEL_FILE.exists():
            try:
                return json.loads(WORLD_MODEL_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self):
        WORLD_MODEL_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))

    # -------------------------------------------------------
    # NEURAL FLOW (BaseCompartment.process)
    # -------------------------------------------------------

    def process(self, state: Dict) -> Dict:
        """
        Fornisce al neural flow un'istantanea leggera del World Model
        (world_snapshot) e calcola un segnale di sensory_drift grezzo.
        Non esegue fetch esterni di default.
        """
        if state_bus.is_blocked(state):
            return self._log(state, status="skipped", note="state_blocked")

        summary = self.get_summary()
        state["world_snapshot"] = summary

        # Drift: euristica banale basata su età dell'ultimo update
        try:
            last_ts = datetime.datetime.fromisoformat(
                self.data["meta"].get("last_updated")
            )
            delta_min = (datetime.datetime.now() - last_ts).total_seconds() / 60.0
            # >60 min => drift 0.5+ (approx)
            drift = min(1.0, max(0.0, delta_min / 120.0))
        except Exception:
            drift = 0.5

        # Prendi il massimo per non abbassare valori già calcolati
        state["sensory_drift"] = max(float(state.get("sensory_drift", 0.0) or 0.0), drift)

        return self._log(state, status="ok", note=f"drift={drift:.2f}")


# Test rapido
if __name__ == "__main__":
    wm = WorldModel()
    print("World Model inizializzato")
    print("Fetch obiettivi Rigene Project...")
    objs = wm.fetch_rigene_objectives()
    print(f"Obiettivi caricati: {len(objs)}")
    for i, o in enumerate(objs[:3], 1):
        print(f"  {i}. {o[:80]}")
    print("\nSummary:")
    print(json.dumps(wm.get_summary(), indent=2))
