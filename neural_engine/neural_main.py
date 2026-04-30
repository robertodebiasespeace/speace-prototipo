"""
SPEACE Neural Engine - Main Entry Point
Motore neurale per automazione processi cerebrali SPEACE.
Funziona continuamente in background come sistema distribuito.
"""

import sys
import os
import time
import json
import threading
import signal
import argparse
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

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
    Priority,
    NeuronType,
    BaseNeuron,
    Contract,
    Port,
    ExecutionContext,
    SPEACEObjectives,
    NeedCategory
)


BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║   SPEACE NEURAL ENGINE – Grafo Computazionale Adattivo         ║
║   Versione 1.0 | Background Process                            ║
║   Coordinate: Cortex + DigitalDNA + Memory + Environment       ║
╚══════════════════════════════════════════════════════════════════╝
"""


class SPEACENeuralEngine:
    VERSION = "1.0.0"

    def __init__(self, config_path: Optional[str] = None):
        self.running = False
        self.cycle_count = 0
        self.start_time = 0

        self.graph = ComputationalGraph(name="SPEACE_Main_Graph")
        self.protocol = create_protocol()
        self.synapse_manager = SynapseManager()
        self.plasticity = StructuralPlasticity(self.graph, self.synapse_manager)
        self.execution_engine = ExecutionEngine(
            self.graph, self.synapse_manager, self.protocol
        )
        self.evolution_engine = EvolutionEngine(
            self.graph, self.synapse_manager, self.plasticity
        )
        self.environment_sensor = EnvironmentSensor()
        self.load_balancer = LoadBalancer()

        self._background_thread: Optional[threading.Thread] = None
        self._evolution_thread: Optional[threading.Thread] = None
        self._monitor_thread: Optional[threading.Thread] = None

        self._neurons_registry: Dict[str, BaseNeuron] = {}
        self._cycle_interval = 60
        self._evolution_interval = 300
        self._environment_scan_interval = 600

        self._lock = threading.RLock()

    def initialize(self):
        print("[NeuralEngine] Inizializzazione...")

        self.evolution_engine.initialize()

        self._register_default_neurons()
        self._setup_connections()
        self._load_balancer.start_monitoring()
        self.execution_engine.start()

        print(f"[NeuralEngine] ✅ Inizializzato")
        print(f"[NeuralEngine]   - Neuroni registrati: {len(self._neurons_registry)}")
        print(f"[NeuralEngine]   - Grafi: {len(self.graph._neurons)}")
        print(f"[NeuralEngine]   - Sinapsi: {len(self.synapse_manager._synapses)}")

    def _register_default_neurons(self):
        from neural_engine.neuron_base import (
            NeuronMetadata, Port, Contract
        )

        class CortexNeuron(BaseNeuron):
            def _default_contract(self):
                return Contract(
                    input_ports=[
                        Port("data", "object", "input", {"type": "object"}),
                        Port("operation", "string", "input")
                    ],
                    output_ports=[
                        Port("result", "object", "output"),
                        Port("metrics", "object", "output")
                    ]
                )

            def _execute(self, context: ExecutionContext) -> Dict[str, Any]:
                return {
                    "result": {"status": "processed", "source": "cortex"},
                    "metrics": {"cycles": self.cycle_count}
                }

        class DigitalDNANeuron(BaseNeuron):
            def _default_contract(self):
                return Contract(
                    input_ports=[
                        Port("dna_data", "object", "input"),
                        Port("operation", "string", "input")
                    ],
                    output_ports=[
                        Port("mutation_result", "object", "output"),
                        Port("fitness", "number", "output")
                    ]
                )

            def _execute(self, context: ExecutionContext) -> Dict[str, Any]:
                return {
                    "mutation_result": {"applied": True, "generation": 1},
                    "fitness": 0.75
                }

        class MemoryNeuron(BaseNeuron):
            def _default_contract(self):
                return Contract(
                    input_ports=[
                        Port("memory_op", "string", "input"),
                        Port("key", "string", "input"),
                        Port("value", "object", "input")
                    ],
                    output_ports=[
                        Port("success", "boolean", "output"),
                        Port("data", "object", "output")
                    ]
                )

            def _execute(self, context: ExecutionContext) -> Dict[str, Any]:
                return {
                    "success": True,
                    "data": {"memory_used": 1024}
                }

        class EnvironmentNeuron(BaseNeuron):
            def _default_contract(self):
                return Contract(
                    input_ports=[
                        Port("domain", "string", "input"),
                        Port("scan_type", "string", "input")
                    ],
                    output_ports=[
                        Port("factors", "array", "output"),
                        Port("constraints", "array", "output")
                    ]
                )

            def _execute(self, context: ExecutionContext) -> Dict[str, Any]:
                report = self._env_sensor.scan_environment() if hasattr(self, '_env_sensor') else None
                return {
                    "factors": [],
                    "constraints": []
                }

        cortex_neuron = CortexNeuron(
            neuron_id="cortex_main",
            name="Cortex Main Processor",
            neuron_type=NeuronType.CORTEX_MODULE
        )
        cortex_neuron.metadata = NeuronMetadata(
            version="1.0.0",
            category="cortex",
            tags=["brain", "processing", "coordination"]
        )
        cortex_neuron._env_sensor = self.environment_sensor

        dna_neuron = DigitalDNANeuron(
            neuron_id="digitaldna_main",
            name="DigitalDNA Operator",
            neuron_type=NeuronType.DNA_OPERATOR
        )
        dna_neuron.metadata = NeuronMetadata(
            version="1.0.0",
            category="dna",
            tags=["genome", "evolution", "mutation"]
        )

        memory_neuron = MemoryNeuron(
            neuron_id="memory_main",
            name="Memory Manager",
            neuron_type=NeuronType.MEMORY_UNIT
        )
        memory_neuron.metadata = NeuronMetadata(
            version="1.0.0",
            category="memory",
            tags=["storage", "consolidation"]
        )

        env_neuron = EnvironmentNeuron(
            neuron_id="environment_main",
            name="Environment Sensor",
            neuron_type=NeuronType.SENSOR
        )
        env_neuron._env_sensor = self.environment_sensor

        self.graph.add_neuron(cortex_neuron)
        self.graph.add_neuron(dna_neuron)
        self.graph.add_neuron(memory_neuron)
        self.graph.add_neuron(env_neuron)

        self._neurons_registry["cortex_main"] = cortex_neuron
        self._neurons_registry["digitaldna_main"] = dna_neuron
        self._neurons_registry["memory_main"] = memory_neuron
        self._neurons_registry["environment_main"] = env_neuron

        self.synapse_manager.create_synapse(
            "cortex_main", "digitaldna_main",
            weight=0.8
        )
        self.synapse_manager.create_synapse(
            "digitaldna_main", "cortex_main",
            weight=0.6
        )
        self.synapse_manager.create_synapse(
            "cortex_main", "memory_main",
            weight=0.7
        )
        self.synapse_manager.create_synapse(
            "memory_main", "cortex_main",
            weight=0.5
        )
        self.synapse_manager.create_synapse(
            "environment_main", "cortex_main",
            weight=0.9
        )

    def _setup_connections(self):
        pass

    def start_background(self):
        if self.running:
            print("[NeuralEngine] ⚠️  Già in esecuzione")
            return

        print("[NeuralEngine] Avvio background process...")

        self.running = True
        self.start_time = time.time()

        self._background_thread = threading.Thread(
            target=self._background_loop,
            daemon=True,
            name="NeuralEngine_Background"
        )
        self._background_thread.start()

        self._evolution_thread = threading.Thread(
            target=self._evolution_loop,
            daemon=True,
            name="NeuralEngine_Evolution"
        )
        self._evolution_thread.start()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="NeuralEngine_Monitor"
        )
        self._monitor_thread.start()

        print(f"[NeuralEngine] ✅ Background process avviato")
        print(f"[NeuralEngine]   - Ciclo ogni {self._cycle_interval}s")
        print(f"[NeuralEngine]   - Evoluzione ogni {self._evolution_interval}s")

    def stop_background(self):
        if not self.running:
            return

        print("[NeuralEngine] Arresto background process...")
        self.running = False

        self.execution_engine.stop()
        self.load_balancer.stop_monitoring()

        if self._background_thread:
            self._background_thread.join(timeout=5)
        if self._evolution_thread:
            self._evolution_thread.join(timeout=5)
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

        print("[NeuralEngine] ✅ Arresto completato")

    def _background_loop(self):
        while self.running:
            try:
                self._execute_neural_cycle()
            except Exception as e:
                print(f"[NeuralEngine] ❌ Errore ciclo: {e}")
            time.sleep(self._cycle_interval)

    def _evolution_loop(self):
        while self.running:
            time.sleep(self._evolution_interval)
            try:
                self._execute_evolution_cycle()
            except Exception as e:
                print(f"[NeuralEngine] ❌ Errore evoluzione: {e}")

    def _monitor_loop(self):
        while self.running:
            time.sleep(30)
            try:
                self._print_status()
            except Exception as e:
                print(f"[NeuralEngine] ❌ Errore monitor: {e}")

    def _execute_neural_cycle(self):
        with self._lock:
            self.cycle_count += 1
            cycle_id = f"CYCLE-{self.cycle_count:04d}"

        print(f"\n[NeuralEngine] {'='*50}")
        print(f"[NeuralEngine] {cycle_id} | {datetime.now().isoformat()}")

        load_report = self.load_balancer.get_load_report()
        print(f"[NeuralEngine] Load: {load_report['current_load']['level']} | "
              f"CPU: {load_report['current_load']['cpu']:.1%} | "
              f"Balance: {load_report['current_load']['balance_score']:.2f}")

        balance_report = self.evolution_engine.get_balance_report()
        critical_needs = balance_report['critical_count']
        if critical_needs > 0:
            print(f"[NeuralEngine] ⚠️  {critical_needs} bisogni critici")

        for neuron_id, neuron in self._neurons_registry.items():
            job_id = self.execution_engine.submit(
                neuron_id,
                {"cycle": self.cycle_count, "timestamp": time.time()},
                priority=Priority.NORMAL
            )
            if job_id:
                print(f"[NeuralEngine]   → {neuron.name}: job {job_id[:12]}")

        self.plasticity.update_fitness_batch(list(self._neurons_registry.keys()))

        synapse_stats = self.synapse_manager.get_synapse_stats()
        print(f"[NeuralEngine] Sinapsi: {synapse_stats['total_synapses']} | "
              f"Attivazioni: {synapse_stats['total_activations']}")

    def _execute_evolution_cycle(self):
        print(f"\n[NeuralEngine] --- EVOLUTION CYCLE ---")

        env_report = self.environment_sensor.scan_environment()
        print(f"[NeuralEngine] Ambiente: {env_report.overall_impact:.2f} impatto")

        planned_tasks = self.evolution_engine.evaluate_and_plan()
        print(f"[NeuralEngine] Task pianificati: {len(planned_tasks)}")

        obj_progress = self.evolution_engine.check_objective_progress()
        for obj_id, progress in obj_progress.items():
            status = "✅" if progress > 0.7 else "⚡" if progress > 0.4 else "❌"
            print(f"[NeuralEngine]   {status} {obj_id}: {progress:.1%}")

        self.plasticity.apply_pruning()

        if self.plasticity._enabled_rules:
            rules = [r.name for r in self.plasticity._enabled_rules]
            print(f"[NeuralEngine] Plasticity rules: {', '.join(rules)}")

    def _print_status(self):
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)

        load_report = self.load_balancer.get_load_report()
        balance = self.evolution_engine.get_system_balance()

        print(f"\n[NeuralEngine] STATUS | Uptime: {hours}h {minutes}m | Cycle: {self.cycle_count}")
        print(f"[NeuralEngine]   Load: {load_report['current_load']['utilization_ratio']:.1%} | "
              f"Sustainability: {load_report['current_load']['sustainability_index']:.2f}")
        print(f"[NeuralEngine]   Balance: {balance:.2f} | "
              f"Neurons: {len(self._neurons_registry)} | "
              f"Synapses: {len(self.synapse_manager._synapses)}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "version": self.VERSION,
            "running": self.running,
            "cycle_count": self.cycle_count,
            "uptime": time.time() - self.start_time if self.running else 0,
            "graph": self.graph.get_state(),
            "evolution": {
                "needs_count": len(self.evolution_engine._needs),
                "tasks_running": len(self.evolution_engine._running_tasks),
                "balance": self.evolution_engine.get_system_balance()
            },
            "load": self.load_balancer.get_load_report()["current_load"],
            "synapses": self.synapse_manager.get_synapse_stats()
        }

    def execute_once(self) -> Dict[str, Any]:
        self._execute_neural_cycle()
        return self.get_status()


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description="SPEACE Neural Engine")
    parser.add_argument("--background", "-b", action="store_true", help="Esegui in background")
    parser.add_argument("--once", action="store_true", help="Esegui un ciclo singolo")
    parser.add_argument("--interval", type=int, default=60, help="Intervallo cicli (secondi)")
    parser.add_argument("--status", action="store_true", help="Mostra status e esci")
    args = parser.parse_args()

    engine = SPEACENeuralEngine()
    engine._cycle_interval = args.interval
    engine._evolution_interval = args.interval * 5

    engine.initialize()

    if args.status:
        status = engine.get_status()
        print(json.dumps(status, indent=2, default=str))
        return

    if args.once:
        print("[NeuralEngine] Esecuzione ciclo singolo...")
        engine.execute_once()
        return

    if args.background:
        def signal_handler(sig, frame):
            print("\n[NeuralEngine] Ricevuto signal di terminazione...")
            engine.stop_background()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        engine.start_background()

        print("[NeuralEngine] ⏳ In esecuzione in background (Ctrl+C per terminare)...")
        try:
            while engine.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            engine.stop_background()
    else:
        print("[NeuralEngine] Modalità interattiva - uso --background per esecuzione continua")


if __name__ == "__main__":
    main()
