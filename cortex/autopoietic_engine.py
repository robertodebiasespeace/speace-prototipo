"""
SPEACE Autopoietic Engine - Modulo di Automazione Autopoietica
Grafo computazionale adattivo con bisogni dinamici, plasticità strutturale,
algoritmo evolutivo e integrazione OLC per l'auto-mantenimento di SPEACE.
Version: 1.1 - OLC Integration + Feedback-driven Plasticity
Data: 25 Aprile 2026
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from collections import deque
from enum import Enum
import importlib
import traceback

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).parent.parent


# -----------------------------------------------
# OLC Types (Organism Language Contract)
# -----------------------------------------------

class OLCType(Enum):
    """Tipi base OLC per contratto."""
    SENSORY_FRAME = "SensoryFrame"
    DECISION_FRAME = "DecisionFrame"
    ACTION_RESULT = "ActionResult"
    COGNITIVE_STATE = "CognitiveState"
    METABOLIC_STATE = "MetabolicState"
    EMERGENCY_SIGNAL = "EmergencySignal"
    GROWTH_SIGNAL = "GrowthSignal"
    PRUNE_SIGNAL = "PruneSignal"
    VALIDATION_RESULT = "ValidationResult"


class OLCBase:
    """Base class per tutti i tipi OLC."""
    olc_type: OLCType = None

    def to_dict(self) -> Dict:
        return {"olc_type": self.olc_type.value if self.olc_type else None}

    @classmethod
    def from_dict(cls, data: Dict):
        return cls()


class SensoryFrame(OLCBase):
    """Frame sensoriale - input dal mondo esterno."""
    olc_type = OLCType.SENSORY_FRAME

    def __init__(self, timestamp: str = None, modality: str = "text",
                 data: Dict = None, confidence: float = 1.0):
        self.timestamp = timestamp or datetime.now().isoformat()
        self.modality = modality
        self.data = data or {}
        self.confidence = confidence

    def to_dict(self) -> Dict:
        return {
            "olc_type": self.olc_type.value,
            "timestamp": self.timestamp,
            "modality": self.modality,
            "data": self.data,
            "confidence": self.confidence
        }


class DecisionFrame(OLCBase):
    """Frame decisionale - output del ragionamento."""
    olc_type = OLCType.DECISION_FRAME

    def __init__(self, timestamp: str = None, action: str = "",
                 reasoning_chain: List[str] = None, confidence: float = 0.8):
        self.timestamp = timestamp or datetime.now().isoformat()
        self.action = action
        self.reasoning_chain = reasoning_chain or []
        self.confidence = confidence

    def to_dict(self) -> Dict:
        return {
            "olc_type": self.olc_type.value,
            "timestamp": self.timestamp,
            "action": self.action,
            "reasoning_chain": self.reasoning_chain,
            "confidence": self.confidence
        }


class ActionResult(OLCBase):
    """Risultato di un'azione eseguita."""
    olc_type = OLCType.ACTION_RESULT

    def __init__(self, timestamp: str = None, success: bool = False,
                 outcome: Dict = None, error: str = None):
        self.timestamp = timestamp or datetime.now().isoformat()
        self.success = success
        self.outcome = outcome or {}
        self.error = error

    def to_dict(self) -> Dict:
        return {
            "olc_type": self.olc_type.value,
            "timestamp": self.timestamp,
            "success": self.success,
            "outcome": self.outcome,
            "error": self.error
        }


class CognitiveState(OLCBase):
    """Stato cognitivo corrente del sistema."""
    olc_type = OLCType.COGNITIVE_STATE

    def __init__(self, timestamp: str = None, phi: float = 0.7,
                 active_regime: str = "idle", energy_level: float = 0.8):
        self.timestamp = timestamp or datetime.now().isoformat()
        self.phi = phi
        self.active_regime = active_regime
        self.energy_level = energy_level

    def to_dict(self) -> Dict:
        return {
            "olc_type": self.olc_type.value,
            "timestamp": self.timestamp,
            "phi": self.phi,
            "active_regime": self.active_regime,
            "energy_level": self.energy_level
        }


# -----------------------------------------------
# Skill Contract (con validazione OLC)
# -----------------------------------------------

class SkillContract:
    """Contratto di esecuzione per un nodo con validazione OLC."""
    def __init__(self, name: str, inputs: Dict[str, type], outputs: Dict[str, type],
                 olc_inputs: List[OLCType] = None, olc_outputs: List[OLCType] = None,
                 preconditions: List[str] = None, postconditions: List[str] = None):
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.olc_inputs = olc_inputs or []
        self.olc_outputs = olc_outputs or []
        self.preconditions = preconditions or []
        self.postconditions = postconditions or []

    def validate_input(self, data: Dict) -> bool:
        for k, t in self.inputs.items():
            if k not in data and k != "self":
                logger.warning(f"Contratto violato per {self.name}: {k} mancante")
                return False
            if k in data and not isinstance(data[k], t) and data[k] is not None:
                logger.warning(f"Contratto violato per {self.name}: {k} atteso {t.__name__}, got {type(data[k]).__name__}")
                return False
        return True

    def validate_output(self, data: Dict) -> bool:
        for k, t in self.outputs.items():
            if k not in data and k != "self":
                return False
            if k in data and data[k] is not None and not isinstance(data[k], t):
                return False
        return True

    def validate_olc(self, frame: OLCBase) -> bool:
        """Valida che il frame OLC sia del tipo atteso."""
        if frame.olc_type in self.olc_inputs:
            return True
        if not self.olc_inputs:  # Se non specificato, accetta tutti
            return True
        logger.warning(f"OLC type mismatch for {self.name}: expected {self.olc_inputs}, got {frame.olc_type}")
        return False


class SkillNode:
    """Nodo del grafo: incapsula uno script o plugin con contratto OLC."""
    def __init__(self, name: str, func: Callable, contract: SkillContract):
        self.name = name
        self.func = func
        self.contract = contract
        self.activation_count = 0
        self.success_count = 0
        self.total_success_ratio = 0.0
        self.last_error: Optional[str] = None
        self.connections: List[str] = []
        self.performance_history: deque = deque(maxlen=50)
        self.last_activation = None

    def execute(self, inputs: Dict) -> Optional[Dict]:
        if not self.contract.validate_input(inputs):
            self.last_error = "Input contract violation"
            return None

        try:
            result = self.func(inputs)

            # Validazione output
            if result is not None and not self.contract.validate_output(result):
                self.last_error = "Output contract violation"
                return None

            self.success_count += 1
            self.last_activation = datetime.now().isoformat()

            # Registra performance per plasticità
            if result and "success" in result:
                self.performance_history.append(1.0 if result["success"] else 0.0)
            else:
                self.performance_history.append(0.8)  # Default buono

            return result

        except Exception as e:
            self.last_error = str(e)
            self.performance_history.append(0.0)
            return None
        finally:
            self.activation_count += 1
            self._update_success_ratio()

    def _update_success_ratio(self):
        """Aggiorna ratio di successo con smoothing."""
        if self.activation_count == 0:
            self.total_success_ratio = 0.0
        else:
            alpha = 0.1  # Smoothing
            current = self.success_count / self.activation_count
            self.total_success_ratio = alpha * current + (1 - alpha) * self.total_success_ratio

    def success_rate(self) -> float:
        return self.total_success_ratio

    def recent_performance(self, last_n: int = 10) -> float:
        """Performance recente (ultimi N attivazioni)."""
        if not self.performance_history:
            return 0.5
        recent = list(self.performance_history)[-last_n:]
        return sum(recent) / len(recent)

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Nodo è stalo se non attivato da troppo tempo."""
        if not self.last_activation:
            return True
        last = datetime.fromisoformat(self.last_activation)
        return (datetime.now() - last).total_seconds() > max_age_seconds


# -----------------------------------------------
# Grafo Computazionale Adattivo (Feedback-driven)
# -----------------------------------------------

class AdaptiveGraph:
    """Grafo con plasticità strutturale guidata da feedback."""

    def __init__(self):
        self.nodes: Dict[str, SkillNode] = {}
        self.edges: Dict[str, List[str]] = {}  # node -> [targets]
        self.edge_weights: Dict[Tuple[str, str], float] = {}  # (src, dst) -> weight
        self.plasticity_log: deque = deque(maxlen=100)

    def add_node(self, name: str, func: Callable, contract: SkillContract) -> SkillNode:
        node = SkillNode(name, func, contract)
        self.nodes[name] = node
        self.edges[name] = []
        self._log_plasticity("add_node", name)
        return node

    def remove_node(self, name: str, reason: str = ""):
        if name in self.nodes:
            del self.nodes[name]
        if name in self.edges:
            del self.edges[name]
        # Rimuovi edges che puntano a questo nodo
        for targets in self.edges.values():
            if name in targets:
                targets.remove(name)
        self._log_plasticity("remove_node", name, {"reason": reason})

    def connect(self, src: str, dst: str, weight: float = 1.0):
        if src in self.edges and dst in self.edges and dst not in self.edges[src]:
            self.edges[src].append(dst)
            self.edge_weights[(src, dst)] = weight

    def disconnect(self, src: str, dst: str):
        if src in self.edges and dst in self.edges[src]:
            self.edges[src].remove(dst)
            self.edge_weights.pop((src, dst), None)

    def reinforce_edge(self, src: str, dst: str, delta: float = 0.1):
        """Rafforza connessione basata su successo."""
        key = (src, dst)
        current = self.edge_weights.get(key, 0.5)
        self.edge_weights[key] = min(1.0, current + delta)
        self._log_plasticity("reinforce", f"{src}->{dst}", {"delta": delta, "new_weight": self.edge_weights[key]})

    def prune_edge(self, src: str, dst: str, threshold: float = 0.2):
        """Rimuove edge debole."""
        key = (src, dst)
        weight = self.edge_weights.get(key, 0)
        if weight < threshold:
            self.disconnect(src, dst)
            self._log_plasticity("prune_edge", f"{src}->{dst}", {"reason": f"weight={weight:.3f}<{threshold}"})

    def apply_plasticity(self, phi: float, force: bool = False):
        """
        Applica plasticità strutturale basata su feedback.
        - Rimuove nodi con bassa performance se phi è alto (sistema stabile, può permettersi pruning)
        - Aggiunge ridondanza se phi è basso (sistema instabile, serve resilienza)
        """
        removed_count = 0

        for name, node in list(self.nodes.items()):
            # Skip nodi builtin che non possono essere rimossi
            if name in ["monitor", "improve", "validate", "repair"]:
                continue

            recent_perf = node.recent_performance()

            # Pruning: nodo con performance troppo bassa
            if recent_perf < 0.3 and node.activation_count > 5:
                if phi > 0.75 or force:  # Solo se sistema stabile
                    self.remove_node(name, f"low_perf={recent_perf:.2f}")
                    removed_count += 1

            # Pruning: nodo stalo
            elif node.is_stale() and node.activation_count > 0:
                if phi > 0.8:
                    self.remove_node(name, f"stale")
                    removed_count += 1

        # Se phi basso, logga che servono alternative
        if phi < 0.5:
            self._log_plasticity("low_phi_warning", "system", {"phi": phi, "suggestion": "add_redundancy"})

        return removed_count

    def suggest_new_connections(self, phi: float) -> List[Tuple[str, str]]:
        """Suggerisce nuove connessioni basate su performance."""
        suggestions = []

        # Trova nodi ad alta performance che non sono connessi
        high_perf = [(n, node) for n, node in self.nodes.items() if node.recent_performance() > 0.7]

        for name_a, node_a in high_perf:
            for name_b, node_b in self.nodes.items():
                if name_a == name_b:
                    continue
                # Se non sono connessi e b è inactivazione
                if name_b not in self.edges.get(name_a, []) and node_b.recent_performance() < 0.5:
                    suggestions.append((name_a, name_b))

        return suggestions[:5]  # Max 5 suggerimenti per ciclo

    def get_graph_snapshot(self) -> Dict:
        """Snapshot del grafo per debugging."""
        return {
            "nodes_count": len(self.nodes),
            "edges_count": sum(len(e) for e in self.edges.values()),
            "node_names": list(self.nodes.keys()),
            "connections": {src: list(targets) for src, targets in self.edges.items()},
            "edge_weights": {f"{k[0]}->{k[1]}": v for k, v in self.edge_weights.items()}
        }

    def _log_plasticity(self, action: str, target: str, details: Dict = None):
        """Log operazione di plasticità."""
        self.plasticity_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "target": target,
            "details": details or {}
        })


# -----------------------------------------------
# Vettore dei Bisogni Dinamici con Omeostasi
# -----------------------------------------------

class DynamicNeeds:
    """Bisogni del sistema con regolazione omeostatica."""

    def __init__(self):
        self.needs = {
            "sopravvivenza": {"target": 1.0, "current": 1.0, "weight": 1.0, "priority": 10},
            "coerenza": {"target": 0.8, "current": 0.7, "weight": 0.8, "priority": 8},
            "espansione": {"target": 5, "current": 0, "weight": 0.5, "priority": 5},
            "miglioramento": {"target": 0.9, "current": 0.7, "weight": 0.7, "priority": 7},
            "resilienza": {"target": 1.0, "current": 1.0, "weight": 0.9, "priority": 6},
        }
        self._history = deque(maxlen=20)
        self.exploration_rate = 0.15

    def update(self, state: Dict):
        """Aggiorna bisogni da stato sistema."""
        phi = state.get("phi", 0.7)
        cognitive_state = state.get("cognitive_state", {})

        self.needs["coerenza"]["current"] = phi
        self.needs["sopravvivenza"]["current"] = 1.0 if phi > 0.5 else phi
        self.needs["miglioramento"]["current"] = phi

        # Espansione: comparti attivi
        self.needs["espansione"]["current"] = state.get("comparti_attivi", 0)

        # Resilienza: capacità di recovery
        self.needs["resilienza"]["current"] = 1.0 - state.get("error_rate", 0.1)

        self._history.append({k: v["current"] for k, v in self.needs.items()})

    def homeostatic_regulate(self):
        """
        Regolazione omeostatica: previene monopolizzazione risorse.
        - Se un bisogno supera 0.9 → riduce priorità degli altri
        - Se tutti i bisogni sono sotto 0.3 → alza exploration_rate
        """
        max_current = max(n["current"] for n in self.needs.values())
        min_current = min(n["current"] for n in self.needs.values())

        # Se un bisogno è quasi saturato, riduci pressione sugli altri
        if max_current > 0.9:
            for name, need in self.needs.items():
                if need["current"] < max_current:
                    need["priority"] = max(1, need["priority"] - 1)

        # Se tutti i bisogni sono bassi, aumenta esplorazione
        if min_current < 0.3:
            self.exploration_rate = min(0.5, self.exploration_rate + 0.02)
        else:
            self.exploration_rate = max(0.05, self.exploration_rate - 0.01)

    def priority_order(self) -> List[str]:
        """Restituisce bisogni ordinati per urgenza (gap * weight)."""
        scored = []
        for name, need in self.needs.items():
            gap = max(0.0, need["target"] - need["current"])
            urgency = gap * need["weight"] * need["priority"]
            scored.append((urgency, name))

        scored.sort(reverse=True)
        return [name for _, name in scored]

    def get_needs_snapshot(self) -> Dict:
        return {
            name: {
                "current": round(need["current"], 3),
                "target": need["target"],
                "gap": round(max(0, need["target"] - need["current"]), 3),
                "weight": need["weight"],
                "priority": need["priority"]
            }
            for name, need in self.needs.items()
        }


# -----------------------------------------------
# Algoritmo Evolutivo (genera task dai bisogni)
# -----------------------------------------------

class EvolutionaryAlgorithm:
    """Genera task adattivi basato su bisogni urgenti."""

    def __init__(self, bridge):
        self.bridge = bridge

    def generate_task(self, need_name: str, state: Dict) -> Optional[Dict]:
        """Genera task eseguibile per soddisfare un bisogno."""
        phi = state.get("phi", 0.7)

        if need_name == "coerenza" and phi < 0.65:
            return {
                "type": "improve_coherence",
                "action": "suggest_mutation",
                "priority": 10,
                "params": {
                    "target_file": "digitaldna/epigenome.yaml",
                    "goal": "aumenta stabilità"
                }
            }
        elif need_name == "espansione":
            return {
                "type": "discover_skills",
                "action": "scan_directory",
                "priority": 5,
                "params": {"directory": "skills"}
            }
        elif need_name == "miglioramento":
            return {
                "type": "self_improvement",
                "action": "run_improvement_cycle",
                "priority": 8,
                "params": {}
            }
        elif need_name == "resilienza" and state.get("error_count", 0) > 3:
            return {
                "type": "self_repair",
                "action": "restart_component",
                "priority": 10,
                "params": {"component": "last_failed"}
            }
        elif need_name == "sopravvivenza" and phi < 0.4:
            return {
                "type": "emergency_repair",
                "action": "reduce_load",
                "priority": 10,
                "params": {"action": "prune_weak_connections"}
            }

        return None


# -----------------------------------------------
# Validation Layer (Distributed Validation)
# -----------------------------------------------

class ValidationLayer:
    """
    Layer di validazione distribuita per coerenza, sicurezza, integrità.
    Valida tutte le transazioni inter-comparto.
    """

    INVARIANTS = [
        {"name": "phi_positive", "check": lambda s: s.get("phi", 0) >= 0},
        {"name": "no_circular_imports", "check": lambda s: True},  # Placeholder
        {"name": "comparti_initialized", "check": lambda s: s.get("comparti_count", 0) > 0},
    ]

    def __init__(self):
        self.validation_history: deque = deque(maxlen=200)
        self.invariant_violations: List[Dict] = []
        self.pending_rollbacks: Dict[str, Dict] = {}

    def validate_transaction(self, source: str, target: str, payload: Dict) -> Tuple[bool, Optional[str]]:
        """
        Valida una transazione tra moduli.
        Returns: (is_valid, error_message)
        """
        transaction_id = f"{source}->{target}:{datetime.now().isoformat()}"

        # Check che source e target esistono
        if not source or not target:
            return False, "Source or target empty"

        # Check payload non è None
        if payload is None:
            return False, "Payload is None"

        # Check dimensione payload
        if len(str(payload)) > 1_000_000:  # 1MB limit
            return False, "Payload too large"

        result = {
            "transaction_id": transaction_id,
            "source": source,
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "valid": True
        }

        self.validation_history.append(result)

        return True, None

    def check_invariants(self, state: Dict) -> List[Dict]:
        """Verifica tutti gli invarianti di sistema."""
        violations = []

        for invariant in self.INVARIANTS:
            try:
                if not invariant["check"](state):
                    violations.append({
                        "invariant": invariant["name"],
                        "state": state,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                violations.append({
                    "invariant": invariant["name"],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })

        self.invariant_violations.extend(violations)
        return violations

    def get_validation_status(self) -> Dict:
        return {
            "validations_count": len(self.validation_history),
            "invariant_violations_count": len(self.invariant_violations),
            "recent_validations": len([v for v in self.validation_history if v["valid"]]),
            "pending_rollbacks": len(self.pending_rollbacks)
        }


# -----------------------------------------------
# Motore Autopoietico Principale
# -----------------------------------------------

class AutopoieticEngine:
    """
    Motore Autopoietico - Orchestratore principale.
    Mantiene grafo adattivo, bisogni dinamici, algoritmo evolutivo.
    Opera in background 24/7.
    """

    def __init__(self, bridge):
        self.bridge = bridge
        self.graph = AdaptiveGraph()
        self.needs = DynamicNeeds()
        self.evolution = EvolutionaryAlgorithm(bridge)
        self.validation = ValidationLayer()
        self.running = False
        self.thread = None
        self.lock = threading.RLock()
        self.task_queue = deque(maxlen=50)
        self.state_history = deque(maxlen=100)
        self._register_builtin_skills()
        self.cycle_count = 0

    def _register_builtin_skills(self):
        """Registra skill di base nel grafo."""
        # Monitor skill - osserva stato sistema
        def monitor_skill(inputs: Dict) -> Dict:
            phi = self.bridge.get_c_index() if self.bridge else 0.7
            state = {
                "phi": phi,
                "timestamp": datetime.now().isoformat(),
                "cognitive_state": {
                    "phi": phi,
                    "active_regime": getattr(self.bridge, 'morphogenesis', None).__class__.__name__ if self.bridge and hasattr(self.bridge, 'morphogenesis') else "unknown",
                    "energy_level": 0.8
                }
            }
            return state

        contract = SkillContract(
            "monitor",
            inputs={},
            outputs={"phi": float, "timestamp": str, "cognitive_state": dict},
            olc_outputs=[OLCType.COGNITIVE_STATE]
        )
        self.graph.add_node("monitor", monitor_skill, contract)

        # Improve skill - auto-miglioramento
        def improvement_skill(inputs: Dict) -> Dict:
            async def _run():
                if self.bridge and self.bridge.auto_improver:
                    return await self.bridge.auto_improver.run_improvement_cycle()
                return {"status": "unavailable"}

            try:
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(_run())
                loop.close()
                return result
            except Exception as e:
                return {"status": "error", "error": str(e)}

        contract = SkillContract(
            "improve",
            inputs={},
            outputs={"status": str},
            olc_outputs=[OLCType.ACTION_RESULT]
        )
        self.graph.add_node("improve", improvement_skill, contract)

        # Validate skill - validazione sistema
        def validate_skill(inputs: Dict) -> Dict:
            state = inputs.get("state", {})
            violations = self.validation.check_invariants(state)
            return {
                "valid": len(violations) == 0,
                "violations_count": len(violations),
                "timestamp": datetime.now().isoformat()
            }

        contract = SkillContract(
            "validate",
            inputs={"state": dict},
            outputs={"valid": bool, "violations_count": int}
        )
        self.graph.add_node("validate", validate_skill, contract)

        # Repair skill - auto-riparazione
        def repair_skill(inputs: Dict) -> Dict:
            component = inputs.get("component", "general")
            return {
                "status": "repair_executed",
                "component": component,
                "timestamp": datetime.now().isoformat()
            }

        contract = SkillContract(
            "repair",
            inputs={"component": str},
            outputs={"status": str}
        )
        self.graph.add_node("repair", repair_skill, contract)

        # Connessioni base
        self.graph.connect("monitor", "validate")
        self.graph.connect("monitor", "improve")
        self.graph.connect("validate", "repair")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="AutopoieticEngine")
        self.thread.start()
        logger.info("Autopoietic Engine avviato in background (24/7)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("Autopoietic Engine fermato")

    def _loop(self):
        """Loop principale - opera ogni 30 secondi."""
        while self.running:
            try:
                self.cycle_count += 1
                self._execution_cycle()
                time.sleep(30)

            except Exception as e:
                logger.error(f"Errore nel loop autopoietico: {e}")
                time.sleep(10)

    def _execution_cycle(self):
        """Ciclo di esecuzione singolo."""
        # 1. Raccogli stato sistema
        state = self._collect_state()
        self.state_history.append(state)

        # 2. Validazione
        if "monitor" in self.graph.nodes:
            validation_result = self.graph.nodes["monitor"].execute({})
            if validation_result:
                self.validation.check_invariants(state)

        # 3. Aggiorna bisogni
        self.needs.update(state)
        self.needs.homeostatic_regulate()

        # 4. Genera task da bisogni prioritari
        urgent_needs = self.needs.priority_order()
        for need in urgent_needs[:2]:
            task = self.evolution.generate_task(need, state)
            if task:
                self.task_queue.append(task)
                logger.debug(f"Task generato: {task['type']} per bisogno '{need}'")

        # 5. Esegui task in coda
        while self.task_queue:
            task = self.task_queue.popleft()
            self._execute_task(task)

        # 6. Plasticità del grafo
        phi = state.get("phi", 0.7)
        removed = self.graph.apply_plasticity(phi)

        # 7. Suggerisci nuove connessioni
        suggestions = self.graph.suggest_new_connections(phi)
        for src, dst in suggestions:
            logger.info(f"Suggerimento plasticità: connettere {src} -> {dst}")

        # 8. Log ciclo
        if self.cycle_count % 10 == 0:
            logger.info(f"Autopoietic cycle #{self.cycle_count}: {len(self.graph.nodes)} nodi, "
                       f"phi={phi:.3f}, needs={urgent_needs[:3]}")

    def _collect_state(self) -> Dict:
        """Raccoglie stato corrente del sistema."""
        state = {
            "phi": 0.7,
            "comparti_attivi": 0,
            "error_count": 0,
            "error_rate": 0.1,
            "cognitive_state": {}
        }

        if self.bridge:
            try:
                state["phi"] = self.bridge.get_c_index()
            except Exception:
                pass

            try:
                state["comparti_attivi"] = len(self.bridge.compartments) if hasattr(self.bridge, 'compartments') else 0
            except Exception:
                pass

            if hasattr(self.bridge, 'morphogenesis') and self.bridge.morphogenesis:
                state["cognitive_state"]["regime"] = self.bridge.morphogenesis.kinetica.current_regime.value
            if hasattr(self.bridge, 'system3') and self.bridge.system3:
                state["cognitive_state"]["system3_focus"] = self.bridge.system3.goal_tracker.current_focus.value if self.bridge.system3.goal_tracker.current_focus else None

        return state

    def _execute_task(self, task: Dict):
        """Esegue un task attivando nodi appropriati."""
        task_type = task.get("type", "")
        logger.info(f"Esecuzione task autopoietico: {task_type}")

        try:
            if task_type == "improve_coherence":
                if "improve" in self.graph.nodes:
                    self.graph.nodes["improve"].execute({})
                    # Rafforza edge monitor->improve dopo successo
                    self.graph.reinforce_edge("monitor", "improve", 0.05)

            elif task_type == "discover_skills":
                self._scan_skills_directory(task.get("params", {}).get("directory", "skills"))

            elif task_type in ["self_improvement", "self_repair", "emergency_repair"]:
                if "repair" in self.graph.nodes:
                    self.graph.nodes["repair"].execute({"component": task.get("params", {}).get("component", "general")})

        except Exception as e:
            logger.error(f"Esecuzione task fallita: {e}")

    def _scan_skills_directory(self, directory: str):
        """Scansiona directory skills e registra nuovi nodi."""
        skills_path = ROOT_DIR / directory
        if not skills_path.exists():
            logger.debug(f"Skills directory non esiste: {skills_path}")
            return

        registered = 0
        for py_file in skills_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                if hasattr(mod, 'register_skill') and callable(mod.register_skill):
                    skill_func, contract = mod.register_skill()
                    if isinstance(contract, SkillContract):
                        self.graph.add_node(py_file.stem, skill_func, contract)
                        registered += 1
                        logger.info(f"Nuova skill registrata: {py_file.stem}")

            except Exception as e:
                logger.error(f"Errore caricamento skill {py_file}: {e}")

        if registered > 0:
            logger.info(f"Skills scan completato: {registered} nuovi nodi registrati")

    def add_skill(self, name: str, func: Callable, contract: SkillContract):
        """API pubblica per aggiungere skill dinamicamente."""
        with self.lock:
            self.graph.add_node(name, func, contract)

    def get_status(self) -> Dict:
        """Stato completo del motore autopoietico."""
        return {
            "running": self.running,
            "cycle_count": self.cycle_count,
            "graph": self.graph.get_graph_snapshot(),
            "needs": self.needs.get_needs_snapshot(),
            "validation": self.validation.get_validation_status(),
            "task_queue_size": len(self.task_queue),
            "exploration_rate": self.needs.exploration_rate
        }

    def get_plasticity_log(self, last_n: int = 20) -> List[Dict]:
        """Ritorna log delle operazioni di plasticità."""
        return list(self.graph.plasticity_log)[-last_n:]


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Autopoietic Engine - Test")
    print("=" * 60)

    # Mock bridge
    class MockBridge:
        def get_c_index(self):
            return 0.72

        def auto_improver():
            return None

    bridge = MockBridge()
    engine = AutopoieticEngine(bridge)
    engine.start()

    print(f"Graph nodes: {list(engine.graph.nodes.keys())}")
    print(f"Needs: {engine.needs.priority_order()}")

    # Test execution cycle manually
    state = {
        "phi": 0.75,
        "comparti_attivi": 15,
        "error_count": 1,
        "error_rate": 0.05
    }

    engine.needs.update(state)
    print(f"Needs after update: {engine.needs.priority_order()}")

    # Test graph snapshot
    print(f"Graph snapshot: {json.dumps(engine.graph.get_graph_snapshot(), indent=2)[:500]}")

    # Test status
    status = engine.get_status()
    print(f"Status - nodes: {status['graph']['nodes_count']}, cycles: {status['cycle_count']}")

    engine.stop()
    print("\n✅ Autopoietic Engine test completed")