"""
SPEACE Neural Bridge – Integrazione tra Neural Engine e componenti SPEACE esistenti
Coordinatore del grafo computazionale che mappa i componenti SPEACE su neuroni funzionali.
Versione: 1.3 – Digital Brain Integration
Data: 25 aprile 2026
"""

from __future__ import annotations

import sys
import time
import threading
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import sicuro del Neural Engine (opzionale)
# ---------------------------------------------------------------------------
try:
    from neural_engine import (
        ComputationalGraph,
        InteropProtocol,
        create_protocol,
        SynapseManager,
        SynapticPlasticity,
        StructuralPlasticity,
        ExecutionEngine,
        EvolutionEngine,
        EnvironmentSensor,
        LoadBalancer,
        NeuronType,
        ExecutionContext,
        SignalType,
        BaseNeuron,
        NeuronFactory,
    )
    from neural_engine.graph_core import EdgeType
    from neural_engine.wrappers.speace_neurons import (
        SafeProactiveNeuron,
        SMFOIKerneNeuron,
        WorldModelNeuron,
        ScientificTeamNeuron,
        DigitalDNANeuron,
        MemoryNeuron,
        StatusMonitorNeuron,
        AGPTNeuron,
        HermesAgentNeuron,
    )
    NEURAL_ENGINE_AVAILABLE = True
except ImportError:
    NEURAL_ENGINE_AVAILABLE = False
    logger.warning("neural_engine non disponibile, funzionalità del grafo neurale disattivate")

# Import 9 Comparti Cerebrali (sempre richiesti)
from .comparti import COMPARTI_REGISTRY, COMPARTI_LAZY
from .world_model.knowledge_graph import KnowledgeGraph
from .cortex_orchestrator import CortexOrchestrator
from .graph_engine import GraphEngine
from .swarm.swarm_node import SwarmNode, SwarmOrchestrator
from .agente_organismo.device_discovery import OrganismDeviceDiscovery, DeviceRegistry


class SPEACENeuralBridge:
    """
    Bridge principale che integra il Neural Engine nell'architettura SPEACE.
    Crea un grafo computazionale dove ogni componente è un neurone funzionale.
    Gestisce ora anche il cervello a 6 livelli (L1-L6), l'auto-miglioramento,
    e il Digital Brain biologicamente ispirato.
    """

    VERSION = "1.3.0"

    def __init__(
        self,
        safe_proactive=None,
        smfoi_kernel=None,
        world_model=None,
        scientific_team=None,
        status_monitor=None,
    ):
        self.running = False
        self.cycle_count = 0
        self.start_time = 0.0
        self._lock = threading.RLock()

        # Core Neural Engine (solo se disponibile)
        self.graph = None
        self.protocol = None
        self.synapse_manager = None
        self.plasticity = None
        self.execution_engine = None
        self.evolution_engine = None
        self.environment_sensor = None
        self.load_balancer = None

        if NEURAL_ENGINE_AVAILABLE:
            self.graph = ComputationalGraph(name="SPEACE_Neural_Graph")
            self.protocol = create_protocol()
            self.synapse_manager = SynapseManager()
            self.plasticity = StructuralPlasticity(self.graph, self.synapse_manager)
            self.execution_engine = ExecutionEngine(self.graph, self.synapse_manager, self.protocol)
            self.evolution_engine = EvolutionEngine(self.graph, self.synapse_manager, self.plasticity)
            self.environment_sensor = EnvironmentSensor()
            self.load_balancer = LoadBalancer()

        # Riferimenti ai componenti SPEACE esistenti
        self.sp = safe_proactive
        self.kernel = smfoi_kernel
        self.wm = world_model
        self.team = scientific_team
        self.monitor = status_monitor

        # Neuroni wrapper
        self.neurons: Dict[str, BaseNeuron] = {}

        # 9 Comparti Cerebrali
        self.compartments: Dict[str, Any] = {}
        self.knowledge_graph = KnowledgeGraph()
        self.orchestrator: Optional[CortexOrchestrator] = None

        # Componenti avanzati
        self.learning_core = None
        self.graph_engine: Optional[GraphEngine] = None
        self.swarm_node: Optional[SwarmNode] = None
        self.swarm_orchestrator: Optional[SwarmOrchestrator] = None
        self.device_registry: Optional[DeviceRegistry] = None

        # Layer cerebrali L3-L6
        self.glia = None
        self.myelin = None
        self.field = None
        self.resources = None
        self.epigenetic_mod = None
        self.speace_node = None
        self.parliament = None
        self.auto_improver = None

        # Digital Brain (architettura biologica completa)
        self.digital_brain = None

        # Threading
        self._background_thread: Optional[threading.Thread] = None
        self._evolution_thread: Optional[threading.Thread] = None
        self._init_flags = {
            "compartments": False,
            "advanced": False,
        }

    # -----------------------------------------------------------------------
    # Inizializzazione UNIFICATA
    # -----------------------------------------------------------------------
    def initialize(self):
        """Percorso legacy: inizializza il grafo neurale e tutti i layer cerebrali."""
        if NEURAL_ENGINE_AVAILABLE:
            print(f"[NeuralBridge] Inizializzazione grafo v{self.VERSION}...")
            self._create_neurons()
            self._create_synapses()
            self.evolution_engine.initialize()
            print(f"[NeuralBridge] Neurons: {len(self.graph._neurons)}")
            print(f"[NeuralBridge] Synapses: {len(self.synapse_manager._synapses)}")
        self._init_cortex_complete()
        print("[NeuralBridge] Ready")

    def initialize_full_cortex(self):
        """Percorso moderno: inizializza direttamente tutti i layer cerebrali."""
        self._init_cortex_complete()
        return self.compartments

    def _init_cortex_complete(self):
        """Inizializzazione unificata di tutti i componenti SPEACE."""
        print("[NeuralBridge] Inizializzazione completa del Cortex SPEACE...")

        self._init_compartments()
        self.orchestrator = CortexOrchestrator(self)
        self._init_advanced_base()
        self._init_brain_layers()

        comp_count = len(self.compartments)
        print(
            f"[NeuralBridge] Cortex attivato: {comp_count} comparti + Orchestrator + "
            f"Swarm + GraphEngine + Glia + Myelin + EpigeneticMod + Node + Parliament + "
            f"AutoImprover + DigitalBrain"
        )

    # -----------------------------------------------------------------------
    # Inizializzazione Comparti
    # -----------------------------------------------------------------------
    def initialize_compartments(self):
        self._init_compartments()

    def _init_compartments(self):
        if self._init_flags["compartments"]:
            return
        print("[NeuralBridge] Inizializzazione comparti cerebrali...")
        for name, CompartmentClass in COMPARTI_REGISTRY.items():
            try:
                instance = CompartmentClass()
                instance.set_bridge(self)
                self.compartments[name] = instance
            except Exception as e:
                logger.error(f"  [!!] Errore caricamento {name}: {e}")

        for name, factory_fn in COMPARTI_LAZY.items():
            try:
                CompartmentClass = factory_fn()
                instance = CompartmentClass()
                instance.set_bridge(self)
                self.compartments[name] = instance
            except Exception as e:
                logger.error(f"  [!!] Errore lazy {name}: {e}")

        print(f"[NeuralBridge] Comparti attivati: {len(self.compartments)}")
        self._init_flags["compartments"] = True

    def _init_advanced_base(self):
        """Inizializza componenti base aggiuntivi."""
        try:
            from .learning_core.online_learner import SPEACEOnlineLearner
            self.learning_core = SPEACEOnlineLearner()
            print("  [OK] Learning Core initialized")
        except ImportError as e:
            print(f"  [!!] Learning Core not available: {e}")

        try:
            self.graph_engine = GraphEngine(name="SPEACE_Structural_Graph")
            print("  [OK] Graph Engine initialized")
        except Exception as e:
            print(f"  [!!] Graph Engine not available: {e}")

        try:
            self.swarm_node = SwarmNode(role="cortex", node_id=f"cortex_{self.cycle_count}")
            self.swarm_orchestrator = SwarmOrchestrator(local_node=self.swarm_node)
            print("  [OK] Swarm Node initialized")
        except Exception as e:
            print(f"  [!!] Swarm Node not available: {e}")

        try:
            self.device_registry = DeviceRegistry()
            print(f"  [OK] Device Registry loaded: {self.device_registry.get_active_count()} devices")
        except Exception as e:
            print(f"  [!!] Device Registry not available: {e}")

    def _init_brain_layers(self):
        """Inizializza i layer L3-L6, la rete Ψ, il Parlamento, l'Auto-Miglioramento e il Digital Brain."""
        # Glial Controller (L3)
        try:
            from .glial_controller import GlialController
            self.glia = GlialController()
            self.field = self.glia.field
            self.resources = self.glia.resources
            print("  [OK] Glial Controller (L3)")
        except Exception as e:
            print(f"  [!!] Glial Controller not available: {e}")

        # Myelination Engine (L3)
        try:
            from .myelination_engine import MyelinationEngine
            self.myelin = MyelinationEngine()
            print("  [OK] Myelination Engine (oligodendrocytes)")
        except Exception as e:
            print(f"  [!!] Myelination Engine not available: {e}")

        # Epigenetic Modulator (L6→L2)
        try:
            from .epigenetic_modulator import EpigeneticModulator
            self.epigenetic_mod = EpigeneticModulator()
            print("  [OK] Epigenetic Modulator (L6->L2)")
        except Exception as e:
            print(f"  [!!] Epigenetic Modulator not available: {e}")

        # SPEACE Node (rete Ψ)
        try:
            from .speace_node import SPEACE_Node
            self.speace_node = SPEACE_Node()
            print(f"  [OK] SPEACE Node (Psi network) - ID: {self.speace_node.node_id}")
        except Exception as e:
            print(f"  [!!] SPEACE Node not available: {e}")

        # Neural Parliament (orchestratore neuroni L2)
        try:
            from .neural_parliament import NeuralParliament
            self.parliament = NeuralParliament(bridge=self)
            print(f"  [OK] Neural Parliament ({len(self.parliament.neurons)} neuroni)")
        except Exception as e:
            print(f"  [!!] Neural Parliament error: {e}")

        # Auto-Improvement Engine
        try:
            from .auto_improvement import AutoImprovementEngine
            self.auto_improver = AutoImprovementEngine(bridge=self)
            print(f"  [OK] Auto-Improvement Engine (ogni {self.auto_improver.improvement_interval} cicli)")
        except Exception as e:
            print(f"  [!!] Auto-Improvement Engine not available: {e}")

        # Digital Brain (architettura biologica completa)
        try:
            from .digital_brain import DigitalBrain
            self.digital_brain = DigitalBrain(bridge=self)
            print("  [OK] Digital Brain (biologically-inspired)")
        except Exception as e:
            print(f"  [!!] Digital Brain not available: {e}")

        # Morphogenesis Engine (Homeodyna + Kinetica + Hebbian)
        try:
            from .morphogenesis_engine import MorphogenesisEngine
            self.morphogenesis = MorphogenesisEngine(bridge=self)
            self.morphogenesis.start()
            print("  [OK] Morphogenesis Engine (Homeodyna + Kinetica + Hebbian)")
        except Exception as e:
            print(f"  [!!] Morphogenesis Engine not available: {e}")

        # System 3 Controller (Meta-cognition + Narrative Identity)
        try:
            from .system3_controller import System3Controller
            self.system3 = System3Controller(bridge=self)
            self.system3.start()
            print("  [OK] System 3 Controller (Meta-Cognition + Narrative Identity)")
        except Exception as e:
            print(f"  [!!] System 3 Controller not available: {e}")

        # Autopoietic Engine (grafo adattivo, bisogni dinamici, evoluzione 24/7)
        try:
            from .autopoietic_engine import AutopoieticEngine
            self.autopoietic = AutopoieticEngine(bridge=self)
            self.autopoietic.start()
            print("  [OK] Autopoietic Engine (auto-poiesi 24/7)")
        except Exception as e:
            print(f"  [!!] Autopoietic Engine not available: {e}")
            self.autopoietic = None

        self._init_flags["advanced"] = True

    # -----------------------------------------------------------------------
    # Creazione neuroni wrapper (Neural Engine)
    # -----------------------------------------------------------------------
    def _create_neurons(self):
        if not NEURAL_ENGINE_AVAILABLE:
            return
        n_sp = SafeProactiveNeuron(safe_proactive_instance=self.sp)
        self.graph.add_neuron(n_sp)
        self.neurons["safeproactive"] = n_sp

        n_smfoi = SMFOIKerneNeuron(kernel_instance=self.kernel)
        self.graph.add_neuron(n_smfoi)
        self.neurons["smfoi"] = n_smfoi

        n_wm = WorldModelNeuron(wm_instance=self.wm)
        self.graph.add_neuron(n_wm)
        self.neurons["worldmodel"] = n_wm

        n_team = ScientificTeamNeuron(orchestrator_instance=self.team)
        self.graph.add_neuron(n_team)
        self.neurons["scientificteam"] = n_team

        n_dna = DigitalDNANeuron()
        self.graph.add_neuron(n_dna)
        self.neurons["digitaldna"] = n_dna

        n_mem = MemoryNeuron()
        self.graph.add_neuron(n_mem)
        self.neurons["memory"] = n_mem

        n_mon = StatusMonitorNeuron(monitor_instance=self.monitor)
        self.graph.add_neuron(n_mon)
        self.neurons["statusmonitor"] = n_mon

        def _tool_calculator(goal, ctx):
            expr = ctx.get("expression", "")
            try:
                return {"result": eval(expr, {"__builtins__": {}}, {})}
            except Exception as e:
                return {"error": str(e)}

        def _tool_file_ops(goal, ctx):
            path = ctx.get("path", "")
            operation = ctx.get("operation", "read")
            try:
                p = Path(path)
                if operation == "read" and p.exists():
                    return {"content": p.read_text(encoding="utf-8", errors="ignore")[:2000]}
                elif operation == "list" and p.exists():
                    return {"entries": [str(x) for x in p.iterdir()][:50]}
                return {"error": "Unsupported file operation or path not found"}
            except Exception as e:
                return {"error": str(e)}

        n_agpt = AGPTNeuron(local_tools={"calculator": _tool_calculator, "file_ops": _tool_file_ops})
        self.graph.add_neuron(n_agpt)
        self.neurons["agpt"] = n_agpt

        n_hermes = HermesAgentNeuron()
        self.graph.add_neuron(n_hermes)
        self.neurons["hermes"] = n_hermes

    def _create_synapses(self):
        if not NEURAL_ENGINE_AVAILABLE:
            return
        conn = [
            ("digitaldna", "safeproactive", EdgeType.DATA, 1.0),
            ("digitaldna", "smfoi", EdgeType.DATA, 1.0),
            ("digitaldna", "worldmodel", EdgeType.DATA, 0.9),
            ("digitaldna", "scientificteam", EdgeType.DATA, 0.8),
            ("digitaldna", "statusmonitor", EdgeType.DATA, 0.7),
            ("safeproactive", "smfoi", EdgeType.CONTROL, 1.0),
            ("smfoi", "worldmodel", EdgeType.BIDIRECTIONAL, 0.9),
            ("worldmodel", "scientificteam", EdgeType.DATA, 0.7),
            ("scientificteam", "safeproactive", EdgeType.FEEDBACK, 0.8),
            ("statusmonitor", "safeproactive", EdgeType.FEEDBACK, 0.5),
            ("statusmonitor", "smfoi", EdgeType.FEEDBACK, 0.5),
            ("statusmonitor", "worldmodel", EdgeType.FEEDBACK, 0.5),
            ("memory", "smfoi", EdgeType.DATA, 0.6),
            ("memory", "worldmodel", EdgeType.DATA, 0.6),
            ("memory", "scientificteam", EdgeType.DATA, 0.5),
            ("agpt", "smfoi", EdgeType.DATA, 0.7),
            ("agpt", "worldmodel", EdgeType.DATA, 0.6),
            ("hermes", "scientificteam", EdgeType.DATA, 0.8),
            ("hermes", "memory", EdgeType.BIDIRECTIONAL, 0.7),
            ("digitaldna", "agpt", EdgeType.DATA, 0.5),
            ("digitaldna", "hermes", EdgeType.DATA, 0.5),
        ]
        for src, tgt, etype, weight in conn:
            sid = self._neuron_id(src)
            tid = self._neuron_id(tgt)
            if sid and tid:
                self.graph.connect(sid, tid, edge_type=etype, weight=weight)
                self.synapse_manager.create_synapse(sid, tid, edge_type=etype, initial_weight=weight)
            else:
                logger.warning(f"Saltata sinapsi {src}→{tgt}: neurone mancante")

    def _neuron_id(self, name: str) -> Optional[str]:
        n = self.neurons.get(name)
        if n is None:
            logger.warning(f"Neurone '{name}' non trovato nel registry")
            return None
        return n.id

    # -----------------------------------------------------------------------
    # Ciclo cognitivo principale
    # -----------------------------------------------------------------------
    async def run_full_cognitive_cycle(self, input_data: dict):
        if not self.orchestrator:
            self._init_cortex_complete()
        return await self.orchestrator.run_cycle(input_data)

    async def process(self, context: dict):
        return await self.run_full_cognitive_cycle(context)

    async def process_cortex(self, input_data: dict) -> Dict[str, Any]:
        return self._process_cortex_impl(input_data)

    def process_cortex_sync(self, input_data: dict) -> Dict[str, Any]:
        return self._process_cortex_impl(input_data)

    def _process_cortex_impl(self, input_data: dict) -> Dict[str, Any]:
        results = {}
        if "prefrontal" in self.compartments:
            comp = self.compartments["prefrontal"]
            results["prefrontal"] = comp.process(input_data) if hasattr(comp, "process") else {"status": "no_process"}
        if "safety" in self.compartments:
            comp = self.compartments["safety"]
            results["safety"] = comp.process({"operation": "assess_risk", "action": "cortex_process"})
        for name, comp in self.compartments.items():
            if name in ("prefrontal", "safety"):
                continue
            try:
                results[name] = comp.process(input_data) if hasattr(comp, "process") else {"status": "no_process"}
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)}
        return results

    # -----------------------------------------------------------------------
    # Neural Engine cycle
    # -----------------------------------------------------------------------
    def run_cycle(self, cycle_context: Optional[Dict] = None) -> Dict[str, Any]:
        if not NEURAL_ENGINE_AVAILABLE:
            return {"cycle": self.cycle_count, "warning": "neural_engine non disponibile"}

        with self._lock:
            self.cycle_count += 1
            ctx = cycle_context or {}

            if "digitaldna" not in self.neurons:
                raise RuntimeError("Graph neurale non inizializzato: chiamare initialize() prima.")

            dna_ctx = ExecutionContext(
                execution_id=f"cycle_{self.cycle_count}_dna",
                neuron_id=self.neurons["digitaldna"].id,
                inputs={"operation": "read", "file": "epigenome.yaml"},
            )
            dna_result = self.neurons["digitaldna"].execute(dna_ctx)

            smfoi_ctx = ExecutionContext(
                execution_id=f"cycle_{self.cycle_count}_smfoi",
                neuron_id=self.neurons["smfoi"].id,
                inputs={
                    "mode": ctx.get("mode", "single"),
                    "cycle": self.cycle_count,
                    "context": {**ctx, "dna_state": dna_result.get("result", {})},
                },
            )
            smfoi_result = self.neurons["smfoi"].execute(smfoi_ctx)

            self.synapse_manager.propagate_signal(
                self.neurons["smfoi"].id,
                SignalType.RESULT,
                smfoi_result,
            )
            self._update_plasticity(smfoi_result)

            mon_ctx = ExecutionContext(
                execution_id=f"cycle_{self.cycle_count}_mon",
                neuron_id=self.neurons["statusmonitor"].id,
                inputs={"action": "heartbeat"},
            )
            mon_result = self.neurons["statusmonitor"].execute(mon_ctx)

            return {
                "cycle": self.cycle_count,
                "dna_result": dna_result,
                "smfoi_result": smfoi_result,
                "monitor_result": mon_result,
                "synapse_stats": self.synapse_manager.get_synapse_stats(),
                "plasticity_report": self.plasticity.get_plasticity_report(),
            }

    def _update_plasticity(self, smfoi_result: Dict):
        success = smfoi_result.get("status") != "error"
        outcome = 1.0 if success else 0.0
        synapses = {}
        if hasattr(self.synapse_manager, "get_all_synapses"):
            synapses = self.synapse_manager.get_all_synapses()
        else:
            synapses = self.synapse_manager._synapses
        for synapse_id in synapses:
            self.synapse_manager.update_from_outcome(
                synapse_id,
                execution_success=success,
                outcome_metric=outcome,
            )

    # -----------------------------------------------------------------------
    # Background loop
    # -----------------------------------------------------------------------
    def start_background(self, interval: float = 60.0):
        if self.running:
            return
        self.running = True
        self.start_time = time.time()
        self._background_thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._background_thread.start()
        print(f"[NeuralBridge] Background loop avviato (interval={interval}s)")

    def stop_background(self):
        self.running = False
        if self._background_thread:
            self._background_thread.join(timeout=5)
        if self.autopoietic:
            self.autopoietic.stop()
        print("[NeuralBridge] Background loop fermato")

    def _loop(self, interval: float):
        while self.running:
            try:
                result = self.run_cycle({"mode": "continuous"})
                stats = result.get("synapse_stats", {})
                plast = result.get("plasticity_report", {})
                print(
                    f"[NeuralBridge] Ciclo #{result['cycle']} | "
                    f"Sinapsi: {stats.get('total_synapses', 0)} | "
                    f"Fitness avg: {plast.get('average_fitness', 0):.3f}"
                )
            except Exception as e:
                print(f"[NeuralBridge] Errore ciclo: {e}")
            time.sleep(interval)

    # -----------------------------------------------------------------------
    # Stato e reporting
    # -----------------------------------------------------------------------
    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            state = {
                "version": self.VERSION,
                "running": self.running,
                "cycle_count": self.cycle_count,
                "uptime": time.time() - self.start_time if self.start_time else 0,
                "neurons": {},
                "compartments": {},
                "cortex_compartments_initialized": len(self.compartments),
                "graph": self.graph.get_state() if self.graph else {},
                "synapses": self.synapse_manager.get_synapse_stats() if self.synapse_manager else {},
                "plasticity": self.plasticity.get_plasticity_report() if self.plasticity else {},
                "phi": self.get_c_index(),
                "digital_brain": self.digital_brain.get_brain_state() if self.digital_brain else {},
            }
            for k, v in self.neurons.items():
                try:
                    state["neurons"][k] = v.get_status() if hasattr(v, "get_status") else "no_status"
                except Exception:
                    state["neurons"][k] = "error"
            for k, v in self.compartments.items():
                try:
                    state["compartments"][k] = v.get_status() if hasattr(v, "get_status") else "no_status"
                except Exception:
                    state["compartments"][k] = "error"
            return state

    def export_graph(self) -> Dict[str, Any]:
        if self.graph:
            return self.graph.export_to_dict()
        return {}

    def get_c_index(self) -> float:
        if hasattr(self, 'glia') and self.glia and self.glia.phi_history:
            return self.glia.phi_history[-1]["phi"]
        if not self.compartments:
            return 0.0
        success_count = 0
        for comp in self.compartments.values():
            if hasattr(comp, "get_status"):
                try:
                    status = comp.get_status()
                    if isinstance(status, dict) and (
                        status.get("status") == "success" or status.get("activation_count", 0) > 0
                    ):
                        success_count += 1
                except Exception:
                    pass
        base = 0.65
        factor = success_count / max(len(self.compartments), 1) * 0.15
        return min(0.95, base + factor)

    def get_cortex_status(self) -> Dict[str, Any]:
        status = {
            "compartments_initialized": len(self.compartments),
            "knowledge_graph_stats": self.knowledge_graph.get_stats() if self.knowledge_graph else {},
            "graph_engine": self.get_graph_engine_status(),
            "swarm": self.get_swarm_status(),
            "device_registry": self.get_device_registry_status(),
        }
        for name, comp in self.compartments.items():
            if hasattr(comp, "get_status"):
                try:
                    status[name] = comp.get_status()
                except Exception:
                    status[name] = "error"
        return status

    def get_graph_engine_status(self) -> Dict:
        return self.graph_engine.get_graph_snapshot() if self.graph_engine else {"status": "not_initialized"}

    def get_swarm_status(self) -> Dict:
        return self.swarm_node.get_swarm_status() if self.swarm_node else {"status": "not_initialized"}

    def get_device_registry_status(self) -> Dict:
        if not self.device_registry:
            return {"status": "not_initialized"}
        return {
            "total_devices": len(self.device_registry.devices),
            "active_count": self.device_registry.get_active_count(),
            "types": list(set(d.get("type") for d in self.device_registry.devices.values())),
        }

    def get_neurochem_status(self) -> Dict:
        """Stato neurochimico del Digital Brain."""
        if self.digital_brain:
            return self.digital_brain.get_brain_state().get("neurochemistry", {})
        return {}


__all__ = ["SPEACENeuralBridge"]
