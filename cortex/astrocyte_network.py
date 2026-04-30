"""
SPEACE Astrocyte Network – Reti astrocitarie plastiche a lunga distanza.
Basato sulla scoperta Nature 2026: gli astrociti formano reti selettive
che connettono regioni cerebrali specifiche, distinte dalle reti neuronali.
Version: 1.0
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).parent.parent


class GapJunction:
    """
    Giunzione gap digitale: canale di comunicazione diretta tra due astrociti.
    Permette il passaggio di: segnali di coerenza (Φ), alert metabolici,
    pattern di attivazione, e richieste di risorse.
    """
    
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
        self.flux_rate = 0.1           # Tasso di trasferimento
        self.permeability = 0.5        # Permeabilità (0=chiuso, 1=completamente aperto)
        self.last_flux_time = time.time()
        self.total_fluxed = 0
        self.created_at = datetime.now().isoformat()
        
    def flux(self, signal: Dict) -> Dict:
        """Trasferisce un segnale attraverso la giunzione."""
        self.last_flux_time = time.time()
        self.total_fluxed += 1
        
        # La permeabilità modula l'intensità del segnale
        attenuated = {}
        for k, v in signal.items():
            if isinstance(v, (int, float)):
                attenuated[k] = v * self.permeability
            else:
                attenuated[k] = v
        
        return attenuated
    
    def modulate_permeability(self, delta: float):
        """Modula la permeabilità (plasticità della giunzione)."""
        self.permeability = max(0.05, min(1.0, self.permeability + delta))
    
    def get_status(self) -> Dict:
        return {
            "source": self.source,
            "target": self.target,
            "permeability": round(self.permeability, 3),
            "total_fluxed": self.total_fluxed,
        }


class Astrocyte:
    """
    Astrocita digitale: nodo di una rete astrocitaria.
    Può connettersi ad altri astrociti via gap junctions.
    Coordina risorse, segnali di coerenza, e risposte metaboliche.
    """
    
    def __init__(self, name: str, region: str):
        self.name = name
        self.region = region          # Regione cerebrale di appartenenza
        self.gap_junctions: Dict[str, GapJunction] = {}
        self.calcium_signal = 0.0     # Segnale di attivazione (equivalente digitale del Ca²⁺)
        self.metabolic_reserve = 1.0  # Riserva energetica
        self.coherence_local = 0.7    # Φ locale
        self.activation_history: List[float] = []
        
    def connect_to(self, other_astrocyte: 'Astrocyte') -> GapJunction:
        """Crea una gap junction con un altro astrocita."""
        junction_id = f"{self.name}↔{other_astrocyte.name}"
        if junction_id not in self.gap_junctions:
            gj = GapJunction(self.name, other_astrocyte.name)
            self.gap_junctions[junction_id] = gj
            # Connessione bidirezionale
            other_astrocyte.gap_junctions[junction_id] = gj
            logger.debug(f"Gap junction creata: {junction_id}")
        return self.gap_junctions[junction_id]
    
    def activate(self, signal_strength: float):
        """Attiva l'astrocita (aumenta il segnale di calcio)."""
        self.calcium_signal = min(1.0, self.calcium_signal + signal_strength)
        self.activation_history.append(self.calcium_signal)
        if len(self.activation_history) > 100:
            self.activation_history = self.activation_history[-100:]
    
    def propagate_wave(self) -> Dict[str, Dict]:
        """Propaga un'onda di calcio attraverso le gap junctions."""
        propagated = {}
        for junction_id, gj in self.gap_junctions.items():
            target_name = gj.target if gj.source == self.name else gj.source
            signal = {
                "calcium": self.calcium_signal * 0.8,  # attenuazione
                "coherence": self.coherence_local,
                "metabolic_alert": 1.0 - self.metabolic_reserve,
                "timestamp": datetime.now().isoformat(),
            }
            attenuated = gj.flux(signal)
            propagated[target_name] = attenuated
        return propagated
    
    def consume_energy(self, amount: float):
        """Consuma riserva metabolica."""
        self.metabolic_reserve = max(0.0, self.metabolic_reserve - amount)
    
    def receive_resources(self, amount: float):
        """Riceve risorse metaboliche da altri astrociti."""
        self.metabolic_reserve = min(1.0, self.metabolic_reserve + amount)
    
    def get_status(self) -> Dict:
        return {
            "name": self.name,
            "region": self.region,
            "calcium": round(self.calcium_signal, 3),
            "metabolic_reserve": round(self.metabolic_reserve, 3),
            "coherence": round(self.coherence_local, 3),
            "gap_junctions": len(self.gap_junctions),
        }


class AstrocyteNetwork:
    """
    Rete astrocitaria plastica che connette selettivamente regioni cerebrali.
    
    Basato sulla scoperta Nature 2026:
    - Reti locali (confinati a singole regioni)
    - Reti a lunga distanza (attraversano emisferi)
    - Plasticità strutturale (riorganizzazione dopo deprivazione)
    """
    
    def __init__(self, network_id: str, network_type: str = "local"):
        self.network_id = network_id
        self.network_type = network_type  # "local" o "long_range"
        self.astrocytes: Dict[str, Astrocyte] = {}
        self.topology: Dict[str, List[str]] = defaultdict(list)
        self.plasticity_log: List[Dict] = []
        
        logger.info(f"Rete astrocitaria '{network_id}' ({network_type}) inizializzata")
    
    def add_astrocyte(self, name: str, region: str) -> Astrocyte:
        """Aggiunge un astrocita alla rete."""
        astrocyte = Astrocyte(name, region)
        self.astrocytes[name] = astrocyte
        return astrocyte
    
    def connect(self, source_name: str, target_name: str):
        """Connette due astrociti via gap junction."""
        if source_name not in self.astrocytes or target_name not in self.astrocytes:
            logger.warning(f"Astrociti non trovati: {source_name} o {target_name}")
            return
        
        source = self.astrocytes[source_name]
        target = self.astrocytes[target_name]
        source.connect_to(target)
        
        self.topology[source_name].append(target_name)
        self.topology[target_name].append(source_name)
    
    def propagate_global_wave(self, origin: str, phi: float) -> Dict:
        """
        Propaga un'onda di calcio globale a partire da un astrocita di origine.
        Simula la comunicazione astrocitaria a lunga distanza.
        """
        if origin not in self.astrocytes:
            return {}
        
        # Attiva l'astrocita di origine
        self.astrocytes[origin].activate(phi)
        self.astrocytes[origin].coherence_local = phi
        
        # Propaga attraverso la rete (BFS)
        visited = {origin}
        wave_results = {origin: {"calcium": self.astrocytes[origin].calcium_signal}}
        
        current_layer = [origin]
        while current_layer:
            next_layer = []
            for node in current_layer:
                for neighbor in self.topology.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        # Propaga segnale
                        source = self.astrocytes[node]
                        propagated = source.propagate_wave()
                        if neighbor in propagated:
                            self.astrocytes[neighbor].activate(
                                propagated[neighbor].get("calcium", 0.0)
                            )
                            self.astrocytes[neighbor].coherence_local = (
                                self.astrocytes[neighbor].coherence_local * 0.7 +
                                propagated[neighbor].get("coherence", 0.7) * 0.3
                            )
                            wave_results[neighbor] = {
                                "calcium": self.astrocytes[neighbor].calcium_signal,
                                "coherence": self.astrocytes[neighbor].coherence_local,
                            }
                        next_layer.append(neighbor)
            current_layer = next_layer
        
        return wave_results
    
    def redistribute_resources(self, needy_regions: List[str], donor_regions: List[str]):
        """
        Ridistribuisce risorse metaboliche da regioni donatrici a regioni in bisogno.
        Simula la funzione protettiva astrocitaria scoperta nell'articolo.
        """
        for needy in needy_regions:
            if needy not in self.astrocytes:
                continue
            needed = 1.0 - self.astrocytes[needy].metabolic_reserve
            if needed <= 0:
                continue
            
            for donor in donor_regions:
                if donor not in self.astrocytes or donor == needy:
                    continue
                available = self.astrocytes[donor].metabolic_reserve - 0.3
                if available <= 0:
                    continue
                
                transfer = min(needed, available * 0.5)
                self.astrocytes[donor].consume_energy(transfer)
                self.astrocytes[needy].receive_resources(transfer)
                needed -= transfer
                
                if needed <= 0:
                    break
    
    def reorganize(self, phi_history: List[float]) -> Dict:
        """
        Riorganizzazione plastica della rete in base all'esperienza (Φ).
        Rafforza connessioni tra regioni che mostrano alta coerenza,
        indebolisce connessioni tra regioni con bassa coerenza.
        """
        changes = {"strengthened": [], "weakened": [], "pruned": []}
        
        for astrocyte_name, astrocyte in self.astrocytes.items():
            for junction_id, gj in list(astrocyte.gap_junctions.items()):
                # Determina la coerenza media recente
                avg_phi = sum(phi_history[-10:]) / len(phi_history[-10:]) if phi_history else 0.5
                
                if avg_phi > 0.7:
                    # Rafforza connessioni
                    gj.modulate_permeability(+0.05)
                    changes["strengthened"].append(junction_id)
                elif avg_phi < 0.4:
                    # Indebolisci
                    gj.modulate_permeability(-0.05)
                    if gj.permeability < 0.1:
                        # Pruning: rimuovi connessione
                        del astrocyte.gap_junctions[junction_id]
                        changes["pruned"].append(junction_id)
                    else:
                        changes["weakened"].append(junction_id)
        
        if changes["strengthened"] or changes["weakened"] or changes["pruned"]:
            self.plasticity_log.append({
                "timestamp": datetime.now().isoformat(),
                "changes": changes,
            })
            logger.info(f"Rete '{self.network_id}' riorganizzata: "
                       f"+{len(changes['strengthened'])} -{len(changes['weakened'])} "
                       f"✂️{len(changes['pruned'])}")
        
        return changes
    
    def get_network_map(self) -> Dict:
        """Mappa completa della rete astrocitaria."""
        return {
            "network_id": self.network_id,
            "type": self.network_type,
            "astrocytes": {
                name: a.get_status() for name, a in self.astrocytes.items()
            },
            "topology": dict(self.topology),
            "total_gap_junctions": sum(
                len(a.gap_junctions) for a in self.astrocytes.values()
            ) // 2,  # Diviso 2 perché ogni giunzione è contata due volte
            "plasticity_events": len(self.plasticity_log),
        }


class AstrocyteSystem:
    """
    Sistema astrocitario completo di SPEACE.
    Gestisce multiple reti astrocitarie (locali e a lunga distanza)
    e coordina la comunicazione gliale globale.
    """
    
    def __init__(self, bridge=None):
        self.bridge = bridge
        self.networks: Dict[str, AstrocyteNetwork] = {}
        
        # Crea reti predefinite
        self._create_default_networks()
        
        logger.info(f"🧠 AstrocyteSystem: {len(self.networks)} reti astrocitarie inizializzate")
    
    def _create_default_networks(self):
        """Crea le reti astrocitarie predefinite basate sulla scoperta Nature 2026."""
        
        # Rete locale: coordina i neuroni del parlamento
        local = AstrocyteNetwork("neural_parliament_local", "local")
        for name in ["planner", "critic", "creative", "researcher", "executor"]:
            local.add_astrocyte(f"astro_{name}", f"cortex_{name}")
        # Connessioni a maglia completa (tutti connessi a tutti)
        names = ["astro_planner", "astro_critic", "astro_creative", "astro_researcher", "astro_executor"]
        for i, n1 in enumerate(names):
            for n2 in names[i+1:]:
                local.connect(n1, n2)
        self.networks["parliament_local"] = local
        
        # Rete a lunga distanza: connette emisferi e regioni distanti
        long_range = AstrocyteNetwork("inter_hemispheric_long_range", "long_range")
        regions = [
            ("astro_left_frontal", "left_frontal"),
            ("astro_right_frontal", "right_frontal"),
            ("astro_left_temporal", "left_temporal"),
            ("astro_right_temporal", "right_temporal"),
            ("astro_hippocampus", "hippocampus"),
            ("astro_amygdala", "amygdala"),
            ("astro_cerebellum", "cerebellum"),
            ("astro_brainstem", "brainstem"),
        ]
        for name, region in regions:
            long_range.add_astrocyte(name, region)
        # Connessioni cross-emisferiche
        long_range.connect("astro_left_frontal", "astro_right_frontal")
        long_range.connect("astro_left_frontal", "astro_hippocampus")
        long_range.connect("astro_right_frontal", "astro_hippocampus")
        long_range.connect("astro_left_temporal", "astro_right_temporal")
        long_range.connect("astro_hippocampus", "astro_amygdala")
        long_range.connect("astro_amygdala", "astro_brainstem")
        long_range.connect("astro_cerebellum", "astro_brainstem")
        long_range.connect("astro_left_frontal", "astro_left_temporal")
        long_range.connect("astro_right_frontal", "astro_right_temporal")
        self.networks["inter_hemispheric"] = long_range
        
        # Rete metabolica: gestione risorse
        metabolic = AstrocyteNetwork("metabolic_resource", "local")
        for region in ["cortex", "hippocampus", "brainstem", "cerebellum"]:
            metabolic.add_astrocyte(f"astro_meta_{region}", region)
        for i, (n1, _) in enumerate([("astro_meta_cortex", ""), ("astro_meta_hippocampus", ""), 
                                       ("astro_meta_brainstem", ""), ("astro_meta_cerebellum", "")]):
            for j, (n2, _) in enumerate([("astro_meta_cortex", ""), ("astro_meta_hippocampus", ""), 
                                           ("astro_meta_brainstem", ""), ("astro_meta_cerebellum", "")]):
                if i < j:
                    metabolic.connect(n1, n2)
        self.networks["metabolic"] = metabolic
    
    async def cycle(self, phi: float, phi_history: List[float], active_regions: List[str]):
        """
        Ciclo astrocitario completo.
        1. Propaga onde di calcio in base a Φ
        2. Ridistribuisce risorse metaboliche
        3. Riorganizza plasticamente le reti
        """
        results = {}
        
        for network_id, network in self.networks.items():
            # Propaga onda di calcio da un astrocita random nella rete
            if network.astrocytes:
                origin = list(network.astrocytes.keys())[0]
                wave = network.propagate_global_wave(origin, phi)
                results[network_id] = {
                    "wave_reached": len(wave),
                    "astrocytes_activated": sum(1 for v in wave.values() if v.get("calcium", 0) > 0.3),
                }
            
            # Riorganizzazione plastica ogni 10 cicli
            if self.bridge and self.bridge.cycle_count % 10 == 0:
                network.reorganize(phi_history)
            
            # Ridistribuzione risorse se Φ è basso (funzione protettiva)
            if phi < 0.5:
                needy = [name for name, a in network.astrocytes.items() if a.metabolic_reserve < 0.5]
                donors = [name for name, a in network.astrocytes.items() if a.metabolic_reserve > 0.7]
                if needy and donors:
                    network.redistribute_resources(needy, donors)
        
        return results
    
    def get_status(self) -> Dict:
        return {
            "networks": {
                net_id: net.get_network_map() for net_id, net in self.networks.items()
            },
            "total_astrocytes": sum(len(n.astrocytes) for n in self.networks.values()),
            "total_gap_junctions": sum(
                sum(len(a.gap_junctions) for a in n.astrocytes.values()) // 2
                for n in self.networks.values()
            ),
        }