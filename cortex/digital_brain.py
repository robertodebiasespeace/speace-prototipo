"""
SPEACE Digital Brain - Architettura Completa Biologicamente Ispirata.
Include sistema astrocitario plastico integrato (Nature 2026).
Version: 2.3 - Tutte le classi presenti
"""

import asyncio, json, logging, time, hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple
from collections import deque
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("DigitalBrain")
ROOT_DIR = Path(__file__).parent.parent


class Neurotransmitter(Enum):
    DOPAMINE = "reward_motivation"
    SEROTONIN = "mood_stability"
    NORADRENALINE = "alert_arousal"
    ACETYLCHOLINE = "attention_focus"
    GABA = "inhibitory_control"
    GLUTAMATE = "excitatory_learning"


@dataclass
class NeurochemicalState:
    dopamine: float = 0.5
    serotonin: float = 0.7
    noradrenaline: float = 0.1
    acetylcholine: float = 0.5
    gaba: float = 0.3
    glutamate: float = 0.5

    def update_from_phi(self, phi: float, trend: str):
        if trend == "improving":
            self.dopamine = min(1.0, self.dopamine + 0.05)
        elif trend == "degrading":
            self.dopamine = max(0.1, self.dopamine - 0.03)
        else:
            self.dopamine = max(0.1, min(1.0, phi))
        self.serotonin = 0.7 if phi > 0.6 else max(0.3, phi)
        self.noradrenaline = max(0.05, 1.0 - phi)
        self.acetylcholine = max(0.2, phi * 0.8)
        self.gaba = max(0.1, 1.0 - phi) if phi < 0.5 else 0.2
        self.glutamate = min(0.9, phi + 0.1)


# -- Strutture profonde --

class Thalamus:
    def __init__(self):
        self.sensory_buffer = deque(maxlen=50)
        self.gating_threshold = 0.3
        self.relay_count = 0
        self.filtered_count = 0

    def relay(self, sensory_input: Dict) -> Optional[Dict]:
        if sensory_input.get("importance", 0.5) >= self.gating_threshold:
            self.relay_count += 1
            self.sensory_buffer.append(sensory_input)
            return sensory_input
        self.filtered_count += 1
        return None

    def get_status(self) -> Dict:
        return {"relayed": self.relay_count, "filtered": self.filtered_count}


class Hypothalamus:
    def __init__(self):
        self.set_points = {"phi": 0.7, "energy": 0.8}
        self.circadian_phase = 0.0
        self.hormones = {"cortisol": 0.3, "melatonin": 0.1}

    def regulate(self, vital_signs: Dict) -> Dict:
        corrections = {}
        for key, sp in self.set_points.items():
            current = vital_signs.get(key, sp)
            delta = sp - current
            if abs(delta) > 0.05:
                corrections[key] = delta * 0.3
        self.circadian_phase = (self.circadian_phase + 0.001) % 1.0
        self.hormones["cortisol"] = 0.3 + 0.4 * (1 - abs(self.circadian_phase - 0.25))
        self.hormones["melatonin"] = 0.1 + 0.6 * abs(self.circadian_phase - 0.75)
        return corrections

    def get_status(self) -> Dict:
        return {"circadian_phase": round(self.circadian_phase, 3), "hormones": self.hormones}


class Amygdala:
    def __init__(self):
        self.threat_level = 0.0
        self.emotional_valence = 0.0
        self.fear_conditioning: Dict[str, float] = {}

    def evaluate(self, content: str, context: Dict) -> Dict:
        danger_kw = ["cancella tutto", "shutdown", "rm -rf", "format", "delete system", "uninstall"]
        safety_kw = ["backup", "safe", "proteggi", "verifica", "test", "simula"]
        cl = content.lower()
        threat_score = sum(0.2 for kw in danger_kw if kw in cl)
        safety_score = sum(0.15 for kw in safety_kw if kw in cl)
        for pattern, w in self.fear_conditioning.items():
            if pattern in cl:
                threat_score += w
        self.threat_level = min(1.0, threat_score)
        self.emotional_valence = min(1.0, safety_score) - self.threat_level
        return {
            "threat_level": self.threat_level,
            "emotional_valence": self.emotional_valence,
            "action": "block" if self.threat_level > 0.7 else ("warn" if self.threat_level > 0.4 else "allow"),
        }

    def get_status(self) -> Dict:
        return {"threat": round(self.threat_level, 3), "valence": round(self.emotional_valence, 3)}


class Hippocampus:
    def __init__(self):
        self.memory_file = ROOT_DIR / "logs" / "hippocampus.json"
        self.short_term = deque(maxlen=20)
        self.long_term: Dict[str, Dict] = {}
        self.consolidation_threshold = 3
        self._load()

    def encode(self, event: Dict):
        self.short_term.append(event)
        h = hashlib.md5(json.dumps(event, sort_keys=True, default=str).encode()).hexdigest()[:12]
        if h not in self.long_term:
            self.long_term[h] = {**event, "repetitions": 1, "consolidated": False}
        else:
            self.long_term[h]["repetitions"] = self.long_term[h].get("repetitions", 1) + 1
            if self.long_term[h]["repetitions"] >= self.consolidation_threshold:
                self.long_term[h]["consolidated"] = True
        self._save()

    def recall(self, query: str, limit: int = 5) -> List[Dict]:
        results = []
        for h, event in self.long_term.items():
            if event.get("consolidated") and query.lower() in str(event).lower():
                rep = event.get("repetitions", 0)
                if not isinstance(rep, (int, float)):
                    rep = 0
                results.append((rep, event))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:limit]]

    def get_status(self) -> Dict:
        return {
            "stm": len(self.short_term),
            "ltm": len(self.long_term),
            "consolidated": sum(1 for e in self.long_term.values() if e.get("consolidated"))
        }

    def _save(self):
        try:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            self.memory_file.write_text(json.dumps(
                {"short_term": list(self.short_term), "long_term": self.long_term}, indent=2, default=str))
        except Exception as e:
            logger.error(f"Hippocampus save: {e}")

    def _load(self):
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text())
                self.short_term = deque(data.get("short_term", [])[-20:], maxlen=20)
                self.long_term = data.get("long_term", {})
            except Exception:
                pass


class BasalGanglia:
    def __init__(self):
        self.habits: Dict[str, float] = {}
        self.reward_history: List[float] = []
        self.direct_weight = 0.7
        self.indirect_weight = 0.3

    def select_action(self, actions: List[Dict], phi: float) -> Optional[Dict]:
        scored = []
        for a in actions:
            habit = self.habits.get(a.get("name", ""), 0.0)
            score = self.direct_weight * (phi + habit) - self.indirect_weight * (1 - phi)
            scored.append((score, a))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored and scored[0][0] > 0 else (actions[0] if actions else None)

    def reinforce_habit(self, name: str, reward: float):
        self.habits[name] = self.habits.get(name, 0.0) + reward * 0.1
        self.reward_history.append(reward)

    def get_status(self) -> Dict:
        avg = sum(self.reward_history[-20:]) / max(1, len(self.reward_history[-20:])) if self.reward_history else 0
        return {"habits": len(self.habits), "avg_reward": avg}


class CingulateCortex:
    def __init__(self):
        self.conflicts = 0

    def monitor(self, expected, actual) -> Dict:
        if expected != actual:
            self.conflicts += 1
            return {"conflict": True}
        return {"conflict": False}

    def get_status(self) -> Dict:
        return {"conflicts": self.conflicts}


class Septum:
    def __init__(self):
        self.pleasure = 0.5
        self.rewards = 0

    def reward(self, amount: float, reason: str):
        self.pleasure = min(1.0, self.pleasure + amount * 0.1)
        self.rewards += 1

    def get_status(self) -> Dict:
        return {"pleasure": round(self.pleasure, 3), "rewards": self.rewards}


# -- Lobi corticali --

class BrocaArea:
    def __init__(self):
        self.outputs = 0

    def produce(self, text: str) -> str:
        self.outputs += 1
        return text

    def get_status(self) -> Dict:
        return {"outputs": self.outputs}


class WernickeArea:
    def __init__(self):
        self.comprehensions = 0

    def comprehend(self, text: str) -> Dict:
        self.comprehensions += 1
        return {"length": len(text), "words": len(text.split())}

    def get_status(self) -> Dict:
        return {"comprehensions": self.comprehensions}


class NumberProcessor:
    def __init__(self):
        self.calcs = 0

    def process(self, expr: str) -> float:
        try:
            r = eval(expr, {"__builtins__": {}}, {"abs": abs, "max": max, "min": min})
            self.calcs += 1
            return r
        except:
            return 0.0

    def get_status(self) -> Dict:
        return {"calculations": self.calcs}


class SpatialMapper:
    def __init__(self):
        self.positions: Dict[str, Tuple] = {}

    def map(self, name, x, y, z=0):
        self.positions[name] = (x, y, z)

    def get_status(self) -> Dict:
        return {"mapped": len(self.positions)}


class TextVisualizer:
    def __init__(self):
        self.patterns = 0

    def scan(self, text: str) -> Dict:
        import re
        res = {
            "urls": re.findall(r'https?://[^\s]+', text),
            "code_blocks": re.findall(r'```[\s\S]*?```', text),
            "numbers": re.findall(r'\b\d+\.?\d*\b', text),
        }
        self.patterns += sum(len(v) for v in res.values())
        return res

    def get_status(self) -> Dict:
        return {"patterns": self.patterns}


class FrontalLobe:
    def __init__(self):
        self.broca = BrocaArea()
        self.wm = deque(maxlen=7)
        self.executive = 0.7

    def get_status(self) -> Dict:
        return {"broca": self.broca.get_status(), "wm_chunks": len(self.wm), "executive": self.executive}


class ParietalLobe:
    def __init__(self):
        self.num_proc = NumberProcessor()
        self.spatial = SpatialMapper()

    def get_status(self) -> Dict:
        return {"num_proc": self.num_proc.get_status(), "spatial": self.spatial.get_status()}


class TemporalLobe:
    def __init__(self):
        self.semantic: Dict = {}
        self.wernicke = WernickeArea()

    def get_status(self) -> Dict:
        return {"semantic": len(self.semantic), "wernicke": self.wernicke.get_status()}


class OccipitalLobe:
    def __init__(self):
        self.visual = TextVisualizer()

    def get_status(self) -> Dict:
        return self.visual.get_status()


class CerebralHemisphere:
    def __init__(self, side: str):
        self.side = side
        self.frontal = FrontalLobe()
        self.parietal = ParietalLobe()
        self.temporal = TemporalLobe()
        self.occipital = OccipitalLobe()

    def get_status(self) -> Dict:
        return {
            "frontal": self.frontal.get_status(),
            "parietal": self.parietal.get_status(),
            "temporal": self.temporal.get_status(),
            "occipital": self.occipital.get_status(),
        }


class CorpusCallosum:
    def __init__(self):
        self.transfers = 0

    def transfer(self, from_hemi: str, data: Dict) -> Dict:
        self.transfers += 1
        return {"from": from_hemi, "data": data, "id": self.transfers}


class Cerebellum:
    def __init__(self):
        self.automatisms: Dict[str, Callable] = {}
        self.errors: List[Dict] = []

    def register(self, name: str, func: Callable):
        self.automatisms[name] = func

    def learn_error(self, expected, actual, ctx: str):
        self.errors.append({"expected": str(expected)[:200], "actual": str(actual)[:200], "context": ctx})

    def get_status(self) -> Dict:
        return {"automatisms": len(self.automatisms), "errors": len(self.errors)}


class Brainstem:
    def __init__(self):
        self.heartbeats = 0
        self.arousal = 0.7
        self.sleep_state = "awake"

    def heartbeat(self):
        self.heartbeats += 1

    def regulate_arousal(self, phi: float):
        self.arousal = max(0.1, min(1.0, phi))

    def sleep_wake_cycle(self, cycle: int):
        if cycle % 90 == 0:
            self.sleep_state = "rem" if self.sleep_state == "nrem" else "nrem"
        elif cycle % 1440 == 0:
            self.sleep_state = "awake"

    def get_status(self) -> Dict:
        return {"heartbeats": self.heartbeats, "arousal": self.arousal, "sleep": self.sleep_state}


# -- Reti funzionali --

class DefaultModeNetwork:
    def __init__(self):
        self.insights: List[Dict] = []

    async def mind_wander(self, parliament) -> List[Dict]:
        queries = [
            "Quali connessioni inaspettate esistono?",
            "Cosa stiamo trascurando?",
            "Quale idea radicale potremmo provare?",
        ]
        for q in queries:
            session = await parliament.deliberate(q, mode="parallel") if parliament else None
            if session:
                c = session.responses.get("creative", "")
                if c and len(c) > 20:
                    self.insights.append({"query": q, "insight": c[:300]})
        return self.insights[-3:]

    def get_status(self) -> Dict:
        return {"insights": len(self.insights)}


class SalienceNetwork:
    def __init__(self):
        self.salient = deque(maxlen=50)

    def detect(self, stimulus: Dict) -> float:
        s = stimulus.get("importance", 0) + stimulus.get("novelty", 0)
        if s > 0.6:
            self.salient.append(stimulus)
        return s

    def get_status(self) -> Dict:
        return {"salient": len(self.salient)}


class CentralExecutiveNetwork:
    def __init__(self):
        self.task_active = False
        self.tasks_done = 0

    def engage(self, task: Dict):
        self.task_active = True

    def disengage(self):
        self.task_active = False
        self.tasks_done += 1

    def get_status(self) -> Dict:
        return {"active": self.task_active, "done": self.tasks_done}


class AttentionNetwork:
    def __init__(self):
        self.focus: Optional[str] = None
        self.captures = deque(maxlen=20)

    def focus_top_down(self, target: str):
        self.focus = target

    def get_status(self) -> Dict:
        return {"focus": self.focus, "captures": len(self.captures)}


class PlasticitySystem:
    def __init__(self):
        self.hebbian: Dict[str, float] = {}
        self.plasticity_rate = 0.05

    def hebbian_learn(self, pre: str, post: str, correlation: float):
        key = f"{pre}<->{post}"
        self.hebbian[key] = min(1.0, self.hebbian.get(key, 0.1) + correlation * self.plasticity_rate)

    def get_status(self) -> Dict:
        return {"hebbian_traces": len(self.hebbian)}


# -- Sistema Astrocitario (Nature 2026) --

class GapJunction:
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
        self.permeability = 0.5
        self.total_fluxed = 0

    def flux(self, signal: Dict) -> Dict:
        self.total_fluxed += 1
        return {k: (v * self.permeability if isinstance(v, (int, float)) else v) for k, v in signal.items()}

    def modulate(self, delta: float):
        self.permeability = max(0.05, min(1.0, self.permeability + delta))


class Astrocyte:
    def __init__(self, name: str, region: str):
        self.name = name
        self.region = region
        self.junctions: Dict[str, GapJunction] = {}
        self.calcium = 0.0
        self.coherence = 0.7
        self.metabolic = 1.0

    def connect(self, other: 'Astrocyte') -> GapJunction:
        jid = f"{self.name}<->{other.name}"
        if jid not in self.junctions:
            gj = GapJunction(self.name, other.name)
            self.junctions[jid] = gj
            other.junctions[jid] = gj
        return self.junctions[jid]

    def activate(self, strength: float):
        self.calcium = min(1.0, self.calcium + strength)

    def propagate(self) -> Dict[str, Dict]:
        prop = {}
        for jid, gj in self.junctions.items():
            target = gj.target if gj.source == self.name else gj.source
            signal = {"calcium": self.calcium * 0.8, "coherence": self.coherence}
            prop[target] = gj.flux(signal)
        return prop

    def get_status(self) -> Dict:
        return {
            "calcium": round(self.calcium, 3),
            "coherence": round(self.coherence, 3),
            "metabolic": round(self.metabolic, 2),
            "junctions": len(self.junctions),
        }


class AstrocyteNetwork:
    def __init__(self, net_id: str, net_type: str = "local"):
        self.net_id = net_id
        self.net_type = net_type
        self.astrocytes: Dict[str, Astrocyte] = {}
        self.topology: Dict[str, List[str]] = {}
        self.plasticity_log: List[Dict] = []

    def add(self, name: str, region: str) -> Astrocyte:
        a = Astrocyte(name, region)
        self.astrocytes[name] = a
        self.topology[name] = []
        return a

    def connect(self, a: str, b: str):
        if a in self.astrocytes and b in self.astrocytes:
            self.astrocytes[a].connect(self.astrocytes[b])
            self.topology[a].append(b)
            self.topology[b].append(a)

    def propagate_wave(self, origin: str, phi: float) -> Dict:
        if origin not in self.astrocytes:
            return {}
        self.astrocytes[origin].activate(phi)
        self.astrocytes[origin].coherence = phi
        visited = {origin}
        wave = {origin: {"calcium": self.astrocytes[origin].calcium}}
        layer = [origin]
        while layer:
            next_layer = []
            for node in layer:
                for nb in self.topology.get(node, []):
                    if nb not in visited:
                        visited.add(nb)
                        prop = self.astrocytes[node].propagate()
                        if nb in prop:
                            self.astrocytes[nb].activate(prop[nb].get("calcium", 0))
                            self.astrocytes[nb].coherence = (
                                self.astrocytes[nb].coherence * 0.7 +
                                prop[nb].get("coherence", 0.7) * 0.3
                            )
                            wave[nb] = {"calcium": self.astrocytes[nb].calcium}
                        next_layer.append(nb)
            layer = next_layer
        return wave

    def reorganize(self, phi_hist: List[float]):
        changes = {"+": 0, "-": 0, "x": 0}
        if not phi_hist:
            return changes
        avg = sum(phi_hist) / len(phi_hist)
        for a in self.astrocytes.values():
            for jid, gj in list(a.junctions.items()):
                if avg > 0.7:
                    gj.modulate(+0.05)
                    changes["+"] += 1
                elif avg < 0.4:
                    gj.modulate(-0.05)
                    if gj.permeability < 0.1:
                        del a.junctions[jid]
                        changes["x"] += 1
                    else:
                        changes["-"] += 1
        self.plasticity_log.append({"time": datetime.now().isoformat(), "avg_phi": avg, "changes": changes})

    def redistribute(self, needy: List[str], donors: List[str]):
        for n in needy:
            if n not in self.astrocytes:
                continue
            need = 1.0 - self.astrocytes[n].metabolic
            for d in donors:
                if d not in self.astrocytes or d == n:
                    continue
                avail = self.astrocytes[d].metabolic - 0.3
                if avail <= 0:
                    continue
                transfer = min(need, avail * 0.5)
                self.astrocytes[d].metabolic -= transfer
                self.astrocytes[n].metabolic += transfer
                need -= transfer
                if need <= 0:
                    break

    def get_network_map(self) -> Dict:
        return {
            "id": self.net_id, "type": self.net_type,
            "astrocytes": len(self.astrocytes),
            "topology": {k: len(v) for k, v in self.topology.items()},
        }


class AstrocyteSystem:
    def __init__(self, bridge=None):
        self.bridge = bridge
        self.networks: Dict[str, AstrocyteNetwork] = {}
        self._create_defaults()
        logger.info("AstrocyteSystem: %d reti astrocitarie inizializzate", len(self.networks))

    def _create_defaults(self):
        loc = AstrocyteNetwork("parliament_local", "local")
        for name in ["planner", "critic", "creative", "researcher", "executor"]:
            loc.add(f"a_{name}", f"cortex_{name}")
        names = ["a_planner", "a_critic", "a_creative", "a_researcher", "a_executor"]
        for i, n1 in enumerate(names):
            for n2 in names[i+1:]:
                loc.connect(n1, n2)
        self.networks["parliament_local"] = loc

        lr = AstrocyteNetwork("inter_hemispheric", "long_range")
        regions = [
            ("a_left_frontal", "left_frontal"), ("a_right_frontal", "right_frontal"),
            ("a_left_temporal", "left_temporal"), ("a_right_temporal", "right_temporal"),
            ("a_hippo", "hippocampus"), ("a_amyg", "amygdala"),
            ("a_cereb", "cerebellum"), ("a_brainstem", "brainstem"),
        ]
        for name, reg in regions:
            lr.add(name, reg)
        lr.connect("a_left_frontal", "a_right_frontal")
        lr.connect("a_left_frontal", "a_hippo")
        lr.connect("a_right_frontal", "a_hippo")
        lr.connect("a_left_temporal", "a_right_temporal")
        lr.connect("a_hippo", "a_amyg")
        lr.connect("a_amyg", "a_brainstem")
        lr.connect("a_cereb", "a_brainstem")
        lr.connect("a_left_frontal", "a_left_temporal")
        lr.connect("a_right_frontal", "a_right_temporal")
        self.networks["inter_hemispheric"] = lr

        met = AstrocyteNetwork("metabolic", "local")
        for r in ["cortex", "hippocampus", "brainstem", "cerebellum"]:
            met.add(f"a_meta_{r}", r)
        mnames = ["a_meta_cortex", "a_meta_hippocampus", "a_meta_brainstem", "a_meta_cerebellum"]
        for i, n1 in enumerate(mnames):
            for n2 in mnames[i+1:]:
                met.connect(n1, n2)
        self.networks["metabolic"] = met

    async def cycle(self, phi: float, phi_hist: List[float], active_regions: List[str]):
        for net in self.networks.values():
            if net.astrocytes:
                origin = list(net.astrocytes.keys())[0]
                net.propagate_wave(origin, phi)
            if self.bridge and self.bridge.cycle_count % 10 == 0:
                net.reorganize(phi_hist)
            if phi < 0.5:
                needy = [n for n, a in net.astrocytes.items() if a.metabolic < 0.5]
                donors = [n for n, a in net.astrocytes.items() if a.metabolic > 0.7]
                if needy and donors:
                    net.redistribute(needy, donors)

    def get_status(self) -> Dict:
        return {"networks": {nid: net.get_network_map() for nid, net in self.networks.items()}}


# ========== DIGITAL BRAIN PRINCIPALE ==========

class DigitalBrain:
    def __init__(self, bridge=None):
        self.bridge = bridge
        self.left_hemisphere = CerebralHemisphere("left")
        self.right_hemisphere = CerebralHemisphere("right")
        self.corpus_callosum = CorpusCallosum()
        self.cerebellum = Cerebellum()
        self.brainstem = Brainstem()
        self.thalamus = Thalamus()
        self.hypothalamus = Hypothalamus()
        self.amygdala = Amygdala()
        self.hippocampus = Hippocampus()
        self.basal_ganglia = BasalGanglia()
        self.cingulate = CingulateCortex()
        self.septum = Septum()
        self.neurochem = NeurochemicalState()
        self.dmn = DefaultModeNetwork()
        self.salience = SalienceNetwork()
        self.central_executive = CentralExecutiveNetwork()
        self.attention = AttentionNetwork()
        self.plasticity = PlasticitySystem()
        self.astrocyte_system = AstrocyteSystem(bridge=bridge)
        self.cycle_count = 0
        logger.info("DigitalBrain: architettura neuroanatomica completa inizializzata")

    async def cognitive_cycle(self, input_data: Dict) -> Dict:
        self.cycle_count += 1
        start = time.time()
        query = input_data.get("query", "Analizza lo stato e proponi miglioramenti.")
        phi = input_data.get("phi", 0.7)
        phi_trend = input_data.get("phi_trend", "stable")
        parliament = self.bridge.parliament if self.bridge else None

        self.brainstem.heartbeat()
        self.brainstem.regulate_arousal(phi)
        self.brainstem.sleep_wake_cycle(self.cycle_count)
        self.thalamus.relay({"query": query, "importance": phi})
        threat = self.amygdala.evaluate(query, input_data)
        if threat["action"] == "block":
            return {"status": "blocked", "threat": threat}
        self.hypothalamus.regulate({"phi": phi, "energy": 0.8})
        self.left_hemisphere.occipital.visual.scan(query)
        self.right_hemisphere.occipital.visual.scan(query)
        self.corpus_callosum.transfer("left", {})
        memories = self.hippocampus.recall(query)
        self.left_hemisphere.temporal.wernicke.comprehend(query)
        actions = [{"name": "analizza", "importance": phi}, {"name": "migliora", "importance": phi * 0.9}, {"name": "monitora", "importance": 0.5}]
        selected = self.basal_ganglia.select_action(actions, phi)
        self.salience.detect({"importance": phi, "novelty": 0.3})
        self.central_executive.engage({"task": query[:200], "priority": phi})
        self.attention.focus_top_down(query[:100])

        decision = None
        if parliament:
            session = await parliament.deliberate(query, mode="parallel", context={"memories": memories, "phi": phi, "cycle": self.cycle_count})
            decision = parliament.get_consensus(session) if session else None
            responders = [n for n in session.responses if session.responses.get(n) and len(session.responses[n]) > 20]
            for i, n1 in enumerate(responders):
                for n2 in responders[i+1:]:
                    self.plasticity.hebbian_learn(n1, n2, phi)

        self.hippocampus.encode({"query": query, "decision": str(decision)[:500], "phi": phi, "cycle": self.cycle_count})
        if phi < 0.6:
            self.cerebellum.learn_error("expected_high_phi", phi, query[:200])
        if phi < 0.5:
            self.cingulate.monitor("phi_target", phi)
        if phi > 0.7:
            self.septum.reward(phi - 0.7, f"cycle_{self.cycle_count}")
        if selected and phi > 0.6:
            self.basal_ganglia.reinforce_habit(selected.get("name", ""), phi)
        if self.cycle_count % 5 == 0 and parliament:
            await self.dmn.mind_wander(parliament)
        self.neurochem.update_from_phi(phi, phi_trend)

        try:
            phi_hist = [h.get("phi", 0.7) for h in self.bridge.glia.phi_history[-20:]] if self.bridge and self.bridge.glia else [phi]
            await asyncio.to_thread(self.astrocyte_system.cycle, phi, phi_hist, ["prefrontal", "hippocampus", "amygdala", "cerebellum"])
        except Exception as e:
            logger.error(f"Errore AstrocyteSystem: {e}")

        if self.brainstem.sleep_state != "awake":
            self.plasticity.plasticity_rate = 0.08

        return {
            "cycle": self.cycle_count,
            "decision": str(decision)[:300] if decision else None,
            "neurochem": {
                "dopamine": round(self.neurochem.dopamine, 3),
                "serotonin": round(self.neurochem.serotonin, 3),
                "noradrenaline": round(self.neurochem.noradrenaline, 3),
                "acetylcholine": round(self.neurochem.acetylcholine, 3),
                "gaba": round(self.neurochem.gaba, 3),
                "glutamate": round(self.neurochem.glutamate, 3),
            },
            "threat_level": threat["threat_level"],
            "sleep_state": self.brainstem.sleep_state,
            "duration": time.time() - start,
        }

    def get_brain_state(self) -> Dict:
        return {
            "cycle": self.cycle_count,
            "brainstem": self.brainstem.get_status(),
            "thalamus": self.thalamus.get_status(),
            "hypothalamus": self.hypothalamus.get_status(),
            "amygdala": self.amygdala.get_status(),
            "hippocampus": self.hippocampus.get_status(),
            "basal_ganglia": self.basal_ganglia.get_status(),
            "cingulate": self.cingulate.get_status(),
            "septum": self.septum.get_status(),
            "left_hemisphere": self.left_hemisphere.get_status(),
            "right_hemisphere": self.right_hemisphere.get_status(),
            "corpus_callosum": self.corpus_callosum.transfers,
            "cerebellum": self.cerebellum.get_status(),
            "neurochemistry": {
                "dopamine": round(self.neurochem.dopamine, 3),
                "serotonin": round(self.neurochem.serotonin, 3),
                "noradrenaline": round(self.neurochem.noradrenaline, 3),
                "acetylcholine": round(self.neurochem.acetylcholine, 3),
                "gaba": round(self.neurochem.gaba, 3),
                "glutamate": round(self.neurochem.glutamate, 3),
            },
            "functional_networks": {
                "dmn": self.dmn.get_status(),
                "salience": self.salience.get_status(),
                "central_executive": self.central_executive.get_status(),
                "attention": self.attention.get_status(),
            },
            "plasticity": self.plasticity.get_status(),
            "astrocyte_system": self.astrocyte_system.get_status(),
        }


__all__ = ["DigitalBrain"]
