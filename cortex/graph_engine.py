"""
SPEACE Graph Compute Engine - Rete neurale di script con plasticità strutturale
Il grafo connette i "neuroni funzionali" (script/algoritmi) con sinapsi pesate.
La plasticità modifica i pesi delle sinapsi basandosi sulla fitness.
Versione: 1.0
Data: 24 Aprile 2026
"""

import networkx as nx
from typing import Dict, Any, Callable, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger("GraphEngine")


@dataclass
class FunctionalNeuron:
    """Neurone funzionale - un componente SPEACE registrato nel grafo"""
    name: str
    execute: Callable
    input_signature: Dict[str, str]
    output_signature: Dict[str, str]
    priority: float = 0.5
    description: str = ""
    metadata: Dict = field(default_factory=dict)

    async def run(self, input_data: Dict) -> Dict[str, Any]:
        """Esegue il neurone con i dati di input"""
        return await self.execute(input_data)


@dataclass
class Synapse:
    """Sinapsi tra neuroni con peso plastico"""
    from_neuron: str
    to_neuron: str
    weight: float = 1.0
    last_activation: Optional[datetime] = None
    activation_count: int = 0

    def strengthen(self, delta: float = 0.1):
        """Rafforza la sinapsi"""
        self.weight = min(2.0, self.weight + delta)
        self.activation_count += 1
        self.last_activation = datetime.now()

    def weaken(self, delta: float = 0.05):
        """ indebolisce la sinapsi"""
        self.weight = max(0.1, self.weight - delta)


class GraphEngine:
    """
    Grafo computazionale dinamico con plasticità strutturale.
    Gestisce l'esecuzione ordinata dei neuroni e la plasticità delle sinapsi.
    """

    def __init__(self, name: str = "speace_graph"):
        self.name = name
        self.graph = nx.DiGraph()
        self.neurons: Dict[str, FunctionalNeuron] = {}
        self.synapses: Dict[str, Synapse] = {}
        self.execution_history: List[Dict] = []
        self.max_history = 200

    def register_neuron(self, neuron: FunctionalNeuron) -> bool:
        """
        Registra un neurone nel grafo.
        Returns True se registrato, False se già esistente.
        """
        if neuron.name in self.neurons:
            logger.warning(f"Neurone {neuron.name} già registrato, skipping")
            return False

        self.neurons[neuron.name] = neuron
        self.graph.add_node(
            neuron.name,
            priority=neuron.priority,
            description=neuron.description,
            **neuron.metadata
        )
        logger.info(f"✅ Neurone registrato: {neuron.name} (priority={neuron.priority})")
        return True

    def add_synapse(self, from_neuron: str, to_neuron: str, weight: float = 1.0) -> bool:
        """
        Aggiunge una sinapsi tra due neuroni.
        Returns True se aggiunta, False se i neuroni non esistono.
        """
        if from_neuron not in self.neurons:
            logger.error(f"Neurone sorgente {from_neuron} non trovato")
            return False
        if to_neuron not in self.neurons:
            logger.error(f"Neurone destinazione {to_neuron} non trovato")
            return False

        synapse_key = f"{from_neuron}->{to_neuron}"
        self.synapses[synapse_key] = Synapse(from_neuron, to_neuron, weight)
        self.graph.add_edge(from_neuron, to_neuron, weight=weight, key=synapse_key)
        logger.info(f"🔗 Sinapsi creata: {from_neuron} → {to_neuron} (weight={weight})")
        return True

    def remove_synapse(self, from_neuron: str, to_neuron: str) -> bool:
        """Rimuove una sinapsi"""
        synapse_key = f"{from_neuron}->{to_neuron}"
        if synapse_key in self.synapses:
            del self.synapses[synapse_key]
            self.graph.remove_edge(from_neuron, to_neuron)
            return True
        return False

    async def execute_graph(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Esegue il grafo in ordine topologico.
        L'output di ogni neurone diventa input per il successivo.
        """
        if not self.neurons:
            return {"status": "empty_graph", "results": {}}

        results = {}
        context = dict(input_data)

        try:
            # Esecuzione in ordine topologico
            for node in nx.topological_sort(self.graph):
                if node not in self.neurons:
                    continue

                neuron = self.neurons[node]

                # Verifica che tutti gli input richiesti siano disponibili
                required_inputs = set(neuron.input_signature.keys())
                available_inputs = set(context.keys())
                if not required_inputs.issubset(available_inputs):
                    logger.warning(f"Neurone {node}: input mancanti {required_inputs - available_inputs}")
                    results[node] = {"status": "skipped", "reason": "missing_inputs"}
                    continue

                # Esegui neurone
                logger.debug(f"Executing neuron: {node}")
                try:
                    result = await neuron.run(context)
                    results[node] = result

                    # Propaga output come input per prossimo neurone
                    if isinstance(result, dict):
                        context.update(result)

                except Exception as e:
                    logger.error(f"Errore esecuzione neurone {node}: {e}")
                    results[node] = {"status": "error", "error": str(e)}

            # Registra in history
            self._add_execution_history(input_data, results, context)

            return {
                "status": "completed",
                "results": results,
                "final_context": context
            }

        except nx.NetworkXError as e:
            logger.error(f"Graph error (possibly cycle): {e}")
            return {"status": "error", "error": str(e), "results": results}

    def _add_execution_history(self, input_data: Dict, results: Dict, final_context: Dict):
        """Aggiunge l'esecuzione allo storico"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "input_keys": list(input_data.keys()),
            "neurons_executed": len([r for r in results.values() if r.get("status") == "completed"]),
            "results_keys": list(results.keys()),
            "final_c_index": final_context.get("c_index", 0)
        }
        self.execution_history.append(entry)
        if len(self.execution_history) > self.max_history:
            self.execution_history = self.execution_history[-self.max_history:]

    def apply_plasticity(self, fitness_delta: float, cycle_c_index: float = 0.0):
        """
        Applica plasticità strutturale basata su fitness delta.
        - Fitness positiva: rafforza sinapsi
        - Fitness negativa: indebolisce sinapsi
        - C-index alto: consolida pesi
        """
        if fitness_delta > 0.05:
            # Rafforza tutte le sinapsi
            for synapse in self.synapses.values():
                synapse.strengthen(delta=fitness_delta * 0.2)
            logger.info(f"🧬 Plasticity: sinapsi rafforzate (fitness_delta={fitness_delta:.3f})")

        elif fitness_delta < -0.03:
            # Indebolisce sinapsi
            for synapse in self.synapses.values():
                synapse.weaken(delta=abs(fitness_delta) * 0.1)
            logger.info(f"🧬 Plasticity: sinapsi indebolite (fitness_delta={fitness_delta:.3f})")

        if cycle_c_index > 0.82:
            # Consolidamento: rafforza ancora di più le sinapsi attive
            for synapse in self.synapses.values():
                if synapse.activation_count > 5:
                    synapse.strengthen(delta=0.05)
            logger.info(f"🧬 Plasticity: consolidamento sinapsi attive (C-index={cycle_c_index:.3f})")

    def get_synapse_weights(self) -> Dict[str, float]:
        """Ritorna i pesi attuali di tutte le sinapsi"""
        return {key: syn.weight for key, syn in self.synapses.items()}

    def get_graph_snapshot(self) -> Dict[str, Any]:
        """Ritorna snapshot del grafo per debugging"""
        return {
            "name": self.name,
            "neurons_count": len(self.neurons),
            "synapses_count": len(self.synapses),
            "neuron_names": list(self.neurons.keys()),
            "synapse_weights": self.get_synapse_weights(),
            "execution_history_size": len(self.execution_history)
        }

    def get_active_path(self) -> List[str]:
        """Ritorna il percorso di esecuzione più attivo (basato su activation_count)"""
        sorted_synapses = sorted(
            self.synapses.values(),
            key=lambda s: s.activation_count,
            reverse=True
        )
        return [f"{s.from_neuron}→{s.to_neuron}" for s in sorted_synapses[:5]]

    def reset_weights(self, default_weight: float = 1.0):
        """Resetta tutti i pesi delle sinapsi al valore default"""
        for synapse in self.synapses.values():
            synapse.weight = default_weight
        logger.info(f"🔄 Pesi sinapsi resettati a {default_weight}")