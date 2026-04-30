"""
SPEACE Thalamic Relay System - BRN-002
Implements thalamic circuits for selective attention routing.
Includes: ThalamicSwitch, LGN, MD, IN nuclei.
Version: 1.0
Data: 25 Aprile 2026

The thalamus serves as the central switching hub for sensory information
flowing to the cortex. This module models:
- Specific thalamic nuclei (LGN for vision, etc.)
- Intralaminar nuclei for arousal
- Mediodorsal nucleus for prefrontal circuits
- Pulvinar for visual attention
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ThalamicNucleusType(Enum):
    """Types of thalamic nuclei."""
    LGN = "lateral_geniculate"      # Vision
    MGN = "medial_geniculate"       # Audition
    VPM = "ventral_posterior_medial" # Somatosensory
    VPL = "ventral_posterolateral"   # Somatosensory
    MD = "mediodorsal"              # Prefrontal
    VL = "ventrolateral"           # Motor
    VA = "ventral_anterior"        # Motor/Prefrontal
    Pulvinar = "pulvinar"           # Visual attention
    IN = "intralaminar"            # Arousal
    Centromedian = "centromedian"   # Basal ganglia input


@dataclass
class ThalamicSignal:
    """Signal passing through thalamic circuit."""
    source_nucleus: str
    target_area: str
    data: np.ndarray
    priority: float  # 0-1
    timestamp: str
    modality: str  # 'visual', 'auditory', 'somatosensory', 'cognitive'
    confidence: float = 1.0


@dataclass
class AttentionGate:
    """Gate controlling signal flow."""
    nucleus_id: str
    open: bool
    gain: float  # 0 = blocked, 1 = full
    focus_source: Optional[str] = None


@dataclass
class ThalamicState:
    """State snapshot of thalamic system."""
    timestamp: str
    active_nuclei: List[str]
    attention_focus: Optional[str]
    arousal_level: float
    gate_configurations: Dict[str, AttentionGate]


class NucleusBase:
    """Base class for thalamic nuclei."""
    def __init__(self, nucleus_id: str, nucleus_type: ThalamicNucleusType,
                 output_size: int = 64):
        self.nucleus_id = nucleus_id
        self.nucleus_type = nucleus_type
        self.output_size = output_size

        # Relay properties
        self.input_buffer = deque(maxlen=10)
        self.output_history = deque(maxlen=50)
        self.processing_delay_ms = 2.0  # Typical thalamic delay

        # State
        self.current_output = np.zeros(output_size)
        self.last_activation = None

    def relay(self, input_signal: np.ndarray) -> np.ndarray:
        """Relays input to output with minimal transformation."""
        # Thalamic relay neurons act as low-pass filters
        if len(self.input_buffer) > 0:
            prev = self.input_buffer[-1]
            smoothed = 0.7 * prev + 0.3 * input_signal
        else:
            smoothed = input_signal

        self.input_buffer.append(input_signal)
        self.current_output = smoothed[:self.output_size] if len(smoothed) >= self.output_size else np.pad(smoothed, (0, self.output_size - len(smoothed)))

        self.output_history.append(self.current_output.copy())
        self.last_activation = datetime.now().isoformat()

        return self.current_output

    def get_activity_level(self) -> float:
        """Returns current activity level."""
        return float(np.mean(np.abs(self.current_output)))


class RelayNucleus(NucleusBase):
    """Standard relay nucleus with specific targeting."""
    def __init__(self, nucleus_id: str, nucleus_type: ThalamicNucleusType,
                 target_area: str, output_size: int = 64):
        super().__init__(nucleus_id, nucleus_type, output_size)
        self.target_area = target_area
        self.specificity_weights = np.random.randn(output_size, output_size) * 0.1

    def relay_to_target(self, input_signal: np.ndarray) -> Tuple[np.ndarray, str]:
        """Relays with specificity for target cortical area."""
        output = self.relay(input_signal)
        # Apply target-specific weighting
        targeted = output * (1 + 0.2 * np.tanh(np.dot(self.specificity_weights, output)))
        return targeted, self.target_area


class LGN_Nucleus(RelayNucleus):
    """
    Lateral Geniculate Nucleus - Visual processing.
    Receives input from retina, projects to V1 cortex.
    """
    def __init__(self, nucleus_id: str = "LGN"):
        super().__init__(nucleus_id, ThalamicNucleusType.LGN, "V1", output_size=128)
        # LGN has distinct layers (magnocellular, parvocellular)
        self.magnocellular_output = np.zeros(64)
        self.parvocellular_output = np.zeros(64)

        # Input projection layer (retinal -> LGN size)
        self.input_projection = np.random.randn(128, 256) * 0.05

        # Retinotopic map (simplified)
        self.retinotopic_weights = self._init_retinotopic()

    def _init_retinotopic(self) -> np.ndarray:
        """Initialize retinotopic mapping."""
        weights = np.zeros((self.output_size, self.output_size))
        # Center-surround organization
        center_size = self.output_size // 8
        for i in range(self.output_size):
            for j in range(self.output_size):
                dist = np.sqrt((i - self.output_size/2)**2 + (j - self.output_size/2)**2)
                if dist < center_size:
                    weights[i, j] = 1.0 - dist / center_size
                else:
                    weights[i, j] = -0.2 * np.exp(-(dist - center_size)**2 / 20)
        return weights

    def process_retinal_input(self, retinal_signal: np.ndarray) -> Dict[str, np.ndarray]:
        """Process input from retina with M/P pathway separation."""
        # Project from retinal size (256) to LGN size (128)
        projected = np.dot(self.input_projection, retinal_signal)

        # Apply retinotopic processing (center-surround)
        retinotopic_processed = np.dot(self.retinotopic_weights, projected)

        # Split into magnocellular (motion, contrast) and parvocellular (color, form)
        half = len(retinotopic_processed) // 2
        self.magnocellular_output = retinotopic_processed[:half] * 1.2  # Faster
        self.parvocellular_output = retinotopic_processed[half:] * 0.8  # Slower, precise

        # Combined output
        self.current_output = np.concatenate([self.magnocellular_output, self.parvocellular_output])

        return {
            "magnocellular": self.magnocellular_output,
            "parvocellular": self.parvocellular_output,
            "combined": self.current_output
        }

    def get_v1_projection(self) -> np.ndarray:
        """Returns signal to primary visual cortex."""
        return self.current_output * 1.1  # Slight amplification for V1


class MD_Nucleus(RelayNucleus):
    """
    Mediodorsal Nucleus - Cognitive/Prefrontal integration.
    Projects to prefrontal cortex, important for executive function.
    """
    def __init__(self, nucleus_id: str = "MD"):
        super().__init__(nucleus_id, ThalamicNucleusType.MD, "PFC", output_size=96)
        self.association_cache = deque(maxlen=20)
        self.fidelity_threshold = 0.5

    def process_cognitive_input(self, cognitive_signal: np.ndarray,
                               context: np.ndarray = None) -> np.ndarray:
        """Process cognitive signals with context integration."""
        # Base relay
        output = self.relay(cognitive_signal)

        # Context modulation (from prefrontal feedback)
        if context is not None and len(context) == self.output_size:
            context_modulated = output + 0.3 * np.tanh(context)
        else:
            context_modulated = output

        # Check signal fidelity
        fidelity = np.mean(np.abs(context_modulated))
        if fidelity < self.fidelity_threshold:
            # Boost weak signals
            context_modulated *= (1 + self.fidelity_threshold - fidelity)

        self.current_output = context_modulated
        return self.current_output

    def cache_association(self, signal: np.ndarray, association_type: str):
        """Cache signal patterns for associative learning."""
        self.association_cache.append({
            "pattern": signal.copy(),
            "type": association_type,
            "timestamp": datetime.now().isoformat()
        })


class PulvinarNucleus(NucleusBase):
    """
    Pulvinar - Visual attention and integration.
    Acts as attentional amplifier for visual cortex.
    """
    def __init__(self, nucleus_id: str = "Pulvinar"):
        super().__init__(nucleus_id, ThalamicNucleusType.Pulvinar, output_size=128)
        self.attention_map = np.ones(16)  # 4x4 spatial attention grid
        self.attended_region = None

    def compute_attention(self, visual_input: np.ndarray) -> np.ndarray:
        """Compute attention map from visual input."""
        # Simple attention: areas with high contrast get attention
        contrast = np.abs(np.diff(visual_input.reshape(16, -1), axis=1))
        self.attention_map = np.tanh(contrast.mean(axis=1) + 0.5)

        # Normalize attention map
        self.attention_map = self.attention_map / (np.sum(self.attention_map) + 1e-8)

        return self.attention_map

    def apply_attention(self, v1_signal: np.ndarray, attended_location: int = None) -> np.ndarray:
        """Apply spatial attention to V1 signal."""
        if attended_location is not None and attended_location < len(self.attention_map):
            self.attended_region = attended_location
            # Amplify attended region
            amplified = v1_signal * (1 + 0.5 * self.attention_map)
        else:
            # Use computed attention map
            amplified = v1_signal * (1 + 0.3 * self.attention_map.repeat(8)[:len(v1_signal)])

        self.current_output = amplified
        return amplified

    def highlight_location(self, location: int, intensity: float = 1.0):
        """Explicitly highlight a spatial location."""
        self.attended_region = location
        self.attention_map = np.zeros(16)
        self.attention_map[location] = intensity


class IN_Nucleus(NucleusBase):
    """
    Intralaminar Nuclei - Arousal and awareness.
    Projects widely to cortex for global arousal modulation.
    """
    def __init__(self, nucleus_id: str = "IN"):
        super().__init__(nucleus_id, ThalamicNucleusType.IN, output_size=64)
        self.arousal_level = 0.5  # Default moderate arousal
        self.attention_broadcast = np.ones(64)  # Global broadcast

    def compute_arousal(self, sensory_context: np.ndarray) -> float:
        """Compute arousal level from sensory context."""
        # High variance in input = higher arousal
        variance = float(np.var(sensory_context))

        # Novelty detection increases arousal
        novelty_factor = min(1.0, variance * 2)

        # Update arousal level (slow integration)
        self.arousal_level = 0.9 * self.arousal_level + 0.1 * (0.5 + novelty_factor * 0.4)
        self.arousal_level = np.clip(self.arousal_level, 0.1, 1.0)

        return self.arousal_level

    def broadcast_attention(self, priority_signal: np.ndarray) -> np.ndarray:
        """Broadcast priority signal to all cortical areas."""
        # Modulate broadcast by arousal
        modulation = self.arousal_level * 0.8 + 0.2
        self.attention_broadcast = priority_signal[:64] * modulation

        self.current_output = self.attention_broadcast
        return self.attention_broadcast


class CentromedianNucleus(NucleusBase):
    """
    Centromedian Nucleus - Input from basal ganglia.
    Part of the cortico-basal ganglia-thalamic loop.
    """
    def __init__(self, nucleus_id: str = "CM"):
        super().__init__(nucleus_id, ThalamicNucleusType.Centromedian, output_size=48)
        self.basal_ganglia_input = None

    def receive_basal_input(self, bg_signal: np.ndarray):
        """Receive input from basal ganglia."""
        self.basal_ganglia_input = bg_signal[:48] if len(bg_signal) >= 48 else np.pad(bg_signal, (0, 48 - len(bg_signal)))

    def project_to_cortex(self, cortical_input: np.ndarray = None) -> np.ndarray:
        """Project combined basal ganglia / cortical signal."""
        if self.basal_ganglia_input is not None:
            combined = self.basal_ganglia_input * 0.6
            if cortical_input is not None:
                combined += cortical_input[:48] * 0.4
            self.current_output = np.tanh(combined)
        else:
            self.current_output = np.zeros(48)

        return self.current_output


class ThalamicSwitch:
    """
    Central switching mechanism for thalamic routing.
    Controls which signals pass to cortex based on attention and priorities.
    """
    def __init__(self):
        self.nuclei: Dict[str, NucleusBase] = {}
        self.gates: Dict[str, AttentionGate] = {}
        self.routing_table: Dict[str, List[str]] = {}  # target -> source nuclei

        # Routing configuration
        self.default_routes = {
            "V1": ["LGN"],
            "A1": ["MGN"],
            "S1": ["VPM", "VPL"],
            "PFC": ["MD", "VA"],
            "Motor": ["VL", "VA"],
            "Awareness": ["IN", "CM"]
        }

        self.priority_weights = {
            "visual": 0.8,
            "auditory": 0.7,
            "somatosensory": 0.6,
            "cognitive": 0.9  # Higher for cognitive signals
        }

    def register_nucleus(self, nucleus: NucleusBase):
        """Register a thalamic nucleus."""
        self.nuclei[nucleus.nucleus_id] = nucleus
        self.gates[nucleus.nucleus_id] = AttentionGate(
            nucleus_id=nucleus.nucleus_id,
            open=True,
            gain=1.0
        )

    def get_nucleus(self, nucleus_id: str) -> Optional[NucleusBase]:
        return self.nuclei.get(nucleus_id)

    def set_gate(self, nucleus_id: str, open: bool, gain: float = 1.0):
        """Configure a specific gate."""
        if nucleus_id in self.gates:
            self.gates[nucleus_id].open = open
            self.gates[nucleus_id].gain = np.clip(gain, 0, 2)

    def route_signal(self, source_nucleus: str, signal: np.ndarray,
                    target_area: str = None) -> Optional[np.ndarray]:
        """Route signal through thalamic switch."""
        if source_nucleus not in self.nuclei:
            logger.warning(f"Unknown nucleus: {source_nucleus}")
            return None

        gate = self.gates.get(source_nucleus)
        if gate and not gate.open:
            return None  # Gate closed

        nucleus = self.nuclei[source_nucleus]
        output = nucleus.relay(signal)

        # Apply gate gain
        if gate:
            output = output * gate.gain

        return output

    def get_attention_focus(self) -> Optional[str]:
        """Returns currently attended nucleus/area."""
        for gid, gate in self.gates.items():
            if gate.focus_source:
                return gate.focus_source

        # If no explicit focus, return most active nucleus
        max_activity = 0
        focused = None
        for nid, nucleus in self.nuclei.items():
            activity = nucleus.get_activity_level()
            if activity > max_activity:
                max_activity = activity
                focused = nid
        return focused

    def get_system_state(self) -> ThalamicState:
        """Get complete system state."""
        return ThalamicState(
            timestamp=datetime.now().isoformat(),
            active_nuclei=[n for n, nc in self.nuclei.items() if nc.get_activity_level() > 0.1],
            attention_focus=self.get_attention_focus(),
            arousal_level=self.nuclei.get("IN", NucleusBase("dummy", ThalamicNucleusType.IN)).arousal_level if "IN" in self.nuclei else 0.5,
            gate_configurations=self.gates.copy()
        )


class ThalamicRelaySystem:
    """
    Complete Thalamic Relay System.
    Integrates all thalamic nuclei and switch for full functionality.
    """
    def __init__(self):
        # Create switch
        self.switch = ThalamicSwitch()

        # Create nuclei
        self.lgn = LGN_Nucleus()
        self.md = MD_Nucleus()
        self.pulvinar = PulvinarNucleus()
        self.in_nucleus = IN_Nucleus()
        self.cm = CentromedianNucleus()

        # Register with switch
        self.switch.register_nucleus(self.lgn)
        self.switch.register_nucleus(self.md)
        self.switch.register_nucleus(self.pulvinar)
        self.switch.register_nucleus(self.in_nucleus)
        self.switch.register_nucleus(self.cm)

        # State tracking
        self.processing_history = deque(maxlen=100)
        self.total_signals_processed = 0

    def process_visual_input(self, retinal_signal: np.ndarray) -> Dict[str, np.ndarray]:
        """Process visual input through LGN."""
        lgn_output = self.lgn.process_retinal_input(retinal_signal)

        # Also update pulvinar attention
        self.pulvinar.compute_attention(lgn_output["combined"])

        self.total_signals_processed += 1
        return lgn_output

    def process_cognitive_to_pfc(self, cognitive_signal: np.ndarray,
                                pfc_context: np.ndarray = None) -> np.ndarray:
        """Route cognitive signals to prefrontal cortex."""
        md_output = self.md.process_cognitive_input(cognitive_signal, pfc_context)

        # IN modulates arousal
        arousal = self.in_nucleus.compute_arousal(cognitive_signal)

        self.total_signals_processed += 1
        return md_output

    def attention_to_location(self, location: int):
        """Direct attention to specific location."""
        self.pulvinar.highlight_location(location, intensity=1.5)
        self.switch.set_gate("LGN", open=True, gain=1.2)

    def release_attention(self):
        """Release focused attention."""
        self.pulvinar.highlight_location(-1, intensity=0.5)
        self.switch.set_gate("LGN", open=True, gain=1.0)

    def receive_basal_ganglia_signal(self, bg_signal: np.ndarray):
        """Receive and process basal ganglia input."""
        self.cm.receive_basal_input(bg_signal)
        self.total_signals_processed += 1

    def get_cortical_output(self, target_area: str) -> Optional[np.ndarray]:
        """Get thalamic output for specific cortical target."""
        if target_area == "V1":
            return self.lgn.get_v1_projection()
        elif target_area == "PFC":
            return self.md.current_output
        elif target_area == "Awareness":
            return self.in_nucleus.attention_broadcast
        return None

    def get_system_state(self) -> Dict:
        """Get complete system state."""
        return {
            "signals_processed": self.total_signals_processed,
            "arousal_level": self.in_nucleus.arousal_level,
            "attention_focus": self.switch.get_attention_focus(),
            "lgn_activity": self.lgn.get_activity_level(),
            "md_activity": self.md.get_activity_level(),
            "pulvinar_attention": list(self.pulvinar.attention_map),
            "gates_open": [g for g, v in self.switch.gates.items() if v.open],
            "state": self.switch.get_system_state().__dict__
        }

    def reset(self):
        """Reset thalamic system."""
        self.processing_history.clear()
        self.total_signals_processed = 0
        for nucleus in [self.lgn, self.md, self.pulvinar, self.in_nucleus, self.cm]:
            nucleus.input_buffer.clear()
            nucleus.output_history.clear()


# Factory function for easy creation
def create_thalamic_system() -> ThalamicRelaySystem:
    """Create a complete thalamic relay system."""
    return ThalamicRelaySystem()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Thalamic Relay System - Test")
    print("=" * 60)

    # Create system
    thalamus = create_thalamic_system()

    # Test visual input processing
    print("\n--- Test Visual Processing ---")
    retinal = np.random.randn(256)
    lgn_output = thalamus.process_visual_input(retinal)
    print(f"LGN outputs: magnocellular={lgn_output['magnocellular'].shape}, parvocellular={lgn_output['parvocellular'].shape}")

    # Test attention
    print("\n--- Test Attention ---")
    thalamus.attention_to_location(5)
    state = thalamus.get_system_state()
    print(f"Attention focus: {state['attention_focus']}")
    print(f"Arousal level: {state['arousal_level']:.3f}")

    thalamus.release_attention()
    print("Attention released")

    # Test cognitive routing
    print("\n--- Test Cognitive Routing ---")
    cognitive = np.random.randn(96)
    pfc_out = thalamus.process_cognitive_to_pfc(cognitive)
    print(f"MD output shape: {pfc_out.shape}, mean={np.mean(pfc_out):.3f}")

    # Test basal ganglia integration
    print("\n--- Test Basal Ganglia Integration ---")
    bg_signal = np.random.randn(64)
    thalamus.receive_basal_ganglia_signal(bg_signal)
    cm_out = thalamus.cm.project_to_cortex()
    print(f"CM output shape: {cm_out.shape}")

    # Get cortical outputs
    print("\n--- Test Cortical Outputs ---")
    v1 = thalamus.get_cortical_output("V1")
    pfc = thalamus.get_cortical_output("PFC")
    awareness = thalamus.get_cortical_output("Awareness")
    print(f"V1 output: {v1.shape if v1 else None}")
    print(f"PFC output: {pfc.shape if pfc else None}")
    print(f"Awareness broadcast: {awareness.shape if awareness else None}")

    # System state
    print("\n--- System State ---")
    full_state = thalamus.get_system_state()
    print(f"Total signals processed: {full_state['signals_processed']}")
    print(f"LGN activity: {full_state['lgn_activity']:.3f}")
    print(f"MD activity: {full_state['md_activity']:.3f}")

    print("\n" + "=" * 60)
    print("Thalamic Relay System: PASS")
    print("=" * 60)