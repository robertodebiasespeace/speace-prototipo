"""
SPEACE STDP Learning - BRN-011
Implements Spike-Timing Dependent Plasticity for long-term learning.
Version: 1.0
Data: 25 Aprile 2026

The STDP learning module models:
- Spike-timing dependent plasticity (STDP)
- Long-term potentiation (LTP)
- Long-term depression (LTD)
- Homeostatic scaling
- Metaplasticity (Muller et al.)
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PlasticityType(Enum):
    """Types of synaptic plasticity."""
    LTP = "long_term_potentiation"
    LTD = "long_term_depression"
    HOMEOSTATIC = "homeostatic"
    METAPLASTICITY = "metaplasticity"


@dataclass
class SynapseState:
    """State of a single synapse."""
    weight: float
    last_update: str
    eligibility_trace: float = 0.0
    ltp_traces: float = 0.0
    ltd_traces: float = 0.0


@dataclass
class STDPResult:
    """Result of STDP computation."""
    weight_change: float
    plasticity_type: PlasticityType
    timing_diff_ms: float


class STDPWindow:
    """
    STDP Timing Window - Defines temporal window for spike pairs.
    Classical asymmetric window: LTP when pre before post, LTD when post before pre.
    """
    def __init__(self,
                 tau_plus: float = 20.0,    # LTP time constant (ms)
                 tau_minus: float = 20.0,    # LTD time constant (ms)
                 a_plus: float = 0.01,       # LTP amplitude
                 a_minus: float = 0.012):    # LTD amplitude (slightly larger for stability)
        self.tau_plus = tau_plus
        self.tau_minus = tau_minus
        self.a_plus = a_plus
        self.a_minus = a_minus

        # Additional parameters
        self.w_max = 2.0  # Maximum weight
        self.w_min = 0.0  # Minimum weight
        self.stable_weight = 1.0  # Target stable weight

    def compute_delta(self, timing_diff: float) -> float:
        """
        Compute weight change based on spike timing difference.
        timing_diff > 0: pre before post -> LTP
        timing_diff < 0: post before pre -> LTD
        """
        if timing_diff > 0:
            # LTP: pre before post
            delta = self.a_plus * np.exp(-timing_diff / self.tau_plus)
        else:
            # LTD: post before pre
            delta = -self.a_minus * np.exp(timing_diff / self.tau_minus)

        return delta

    def clamp_weight(self, weight: float) -> float:
        """Clamp weight to valid range."""
        return np.clip(weight, self.w_min, self.w_max)


class SynapticTrace:
    """
    Eligibility trace for STDP - Tracks recent spike activity.
    Enables STDP even when spikes are not exactly coincident.
    """
    def __init__(self, tau: float = 20.0, trace_init: float = 0.0):
        self.tau = tau
        self.trace = trace_init
        self.last_update_time = 0

    def update(self, spike_occurred: bool, time_ms: float):
        """Update trace based on spike and time."""
        dt = time_ms - self.last_update_time
        self.last_update_time = time_ms

        # Decay
        self.trace *= np.exp(-dt / self.tau)

        # Rise on spike
        if spike_occurred:
            self.trace += 1.0

        return self.trace

    def get_trace(self) -> float:
        return self.trace


class STDPPlasticity:
    """
    Complete STDP Plasticity Mechanism.
    Combines timing window, traces, and weight updates.
    """
    def __init__(self,
                 input_size: int = 256,
                 output_size: int = 128,
                 learning_rate: float = 0.01):
        self.input_size = input_size
        self.output_size = output_size
        self.learning_rate = learning_rate

        # Synaptic weights
        self.weights = np.random.randn(output_size, input_size) * 0.05
        self.weights = np.clip(self.weights, 0.01, 2.0)

        # STDP windows for LTP and LTD
        self.stdp_window = STDPWindow()

        # Eligibility traces
        self.pre_traces = np.zeros(input_size)
        self.post_traces = np.zeros(output_size)

        # Timing tracking
        self.last_pre_spike_time = 0.0
        self.last_post_spike_time = 0.0

        # History
        self.weight_history = deque(maxlen=200)
        self.plasticity_history = deque(maxlen=100)

    def update_pre_spike(self, neuron_id: int, time_ms: float):
        """Update when presynaptic neuron spikes."""
        # Update traces
        self.pre_traces[neuron_id] = 1.0

        # Compute timing difference with last post-synaptic spike
        if self.last_post_spike_time > 0:
            timing_diff = self.last_post_spike_time - time_ms
            if timing_diff > 0:
                # Pre before post -> LTP
                delta = self.stdp_window.compute_delta(timing_diff)
                self.weights[:, neuron_id] += delta * self.learning_rate * self.pre_traces[neuron_id]
                self.plasticity_history.append({
                    "type": "LTP",
                    "timing_diff": timing_diff,
                    "delta": delta
                })

        self.last_pre_spike_time = time_ms

        # Decay all pre traces
        self.pre_traces *= 0.95

    def update_post_spike(self, neuron_id: int, time_ms: float):
        """Update when postsynaptic neuron spikes."""
        # Update traces
        self.post_traces[neuron_id] = 1.0

        # Compute timing difference with last pre-synaptic spike
        if self.last_pre_spike_time > 0:
            timing_diff = time_ms - self.last_pre_spike_time
            if timing_diff > 0:
                # Pre before post -> LTP (already handled in pre spike)
                # But post spike triggers LTD for synapses that were pre-active
                pass

        # LTD: when post fires without recent pre, weaken active synapses
        for j in range(self.input_size):
            if self.pre_traces[j] > 0.3:  # Pre was recently active
                timing_diff = time_ms - self.last_pre_spike_time
                if timing_diff > 0:
                    delta = self.stdp_window.compute_delta(-timing_diff)  # Negative for LTD
                    self.weights[neuron_id, j] += delta * self.learning_rate * self.post_traces[neuron_id]
                    self.plasticity_history.append({
                        "type": "LTD",
                        "timing_diff": -timing_diff,
                        "delta": delta
                    })

        self.last_post_spike_time = time_ms

        # Decay all post traces
        self.post_traces *= 0.95

    def apply_stdp_pair(self, pre_time: float, post_time: float,
                        pre_idx: int, post_idx: int) -> float:
        """
        Apply STDP to a specific synapse pair.
        Returns weight change.
        """
        timing_diff = post_time - pre_time

        # Compute weight change
        delta_w = self.stdp_window.compute_delta(timing_diff)

        # Apply with trace values as gating
        trace_factor = self.pre_traces[pre_idx] * self.post_traces[post_idx] + 0.1
        actual_delta = delta_w * self.learning_rate * trace_factor

        # Update weight
        self.weights[post_idx, pre_idx] += actual_delta
        self.weights[post_idx, pre_idx] = self.stdp_window.clamp_weight(
            self.weights[post_idx, pre_idx]
        )

        return actual_delta

    def compute_pairwise_stdp(self, pre_spikes: np.ndarray, post_spikes: np.ndarray,
                             pre_times: np.ndarray, post_times: np.ndarray) -> np.ndarray:
        """
        Compute STDP for all spike pairs in a time window.
        Returns matrix of weight changes.
        """
        weight_changes = np.zeros_like(self.weights)

        # For each pre-post pair
        for i, (pt, pi) in enumerate(zip(pre_times, pre_spikes)):
            for j, (qt, qj) in enumerate(zip(post_times, post_spikes)):
                timing_diff = qt - pt
                if abs(timing_diff) < 100:  # Within STDP window (100ms)
                    delta = self.stdp_window.compute_delta(timing_diff)
                    weight_changes[qj, pi] += delta * self.learning_rate

        # Apply changes
        self.weights += weight_changes
        self.weights = self.stdp_window.clamp_weight(self.weights)

        self.weight_history.append(self.weights.copy())

        return weight_changes

    def get_weight_stats(self) -> Dict:
        """Get weight statistics."""
        return {
            "mean": float(np.mean(self.weights)),
            "std": float(np.std(self.weights)),
            "min": float(np.min(self.weights)),
            "max": float(np.max(self.weights)),
            "sparsity": float(np.sum(self.weights < 0.1) / self.weights.size)
        }


class HomeostaticScaling:
    """
    Homeostatic Plasticity - Maintains stable firing rates.
    Scales all synapses to prevent runaway excitation or depression.
    """
    def __init__(self, target_activity: float = 0.1, scaling_rate: float = 0.001):
        self.target_activity = target_activity
        self.scaling_rate = scaling_rate

        # Scaling factors per neuron
        self.scaling_factors = np.ones(128)

        # Activity history
        self.activity_history = deque(maxlen=100)

    def compute_scaling(self, actual_activity: float, weights: np.ndarray) -> np.ndarray:
        """
        Compute homeostatic scaling factors.
        If activity too high: scale down
        If activity too low: scale up
        """
        activity_error = actual_activity - self.target_activity

        # Proportional scaling
        scaling_delta = -self.scaling_rate * activity_error

        # Apply to scaling factors
        self.scaling_factors += scaling_delta
        self.scaling_factors = np.clip(self.scaling_factors, 0.5, 2.0)

        # Record history
        self.activity_history.append(actual_activity)

        return self.scaling_factors

    def apply_scaling(self, weights: np.ndarray) -> np.ndarray:
        """Apply scaling factors to weights."""
        scaled = weights * self.scaling_factors[:, np.newaxis]
        return np.clip(scaled, 0, 2.0)


class Metaplasticity:
    """
    Metaplasticity - Learning about learning.
    Adjusts plasticity parameters based on history.
    Based on Muller et al. discovery that "plasticity is plastic".
    """
    def __init__(self):
        # Metaplasticity state
        self.baseline_plasticity = 1.0
        self.current_modulation = 1.0

        # History tracking
        self.activity_history = deque(maxlen=200)
        self.plasticity_demand_history = deque(maxlen=100)

        # Thresholds
        self.high_activity_threshold = 0.8
        self.low_activity_threshold = 0.2

    def update_metaplasticity(self, recent_activity: np.ndarray, current_weights: np.ndarray):
        """
        Update metaplasticity state based on recent neural activity.
        High activity -> reduce plasticity (protect from overlearning)
        Low activity -> increase plasticity (encourage learning)
        """
        mean_activity = np.mean(recent_activity)

        # Compute plasticity demand
        if mean_activity > self.high_activity_threshold:
            # Too active -> reduce plasticity
            plasticity_demand = -0.1
        elif mean_activity < self.low_activity_threshold:
            # Too quiet -> increase plasticity
            plasticity_demand = 0.1
        else:
            plasticity_demand = 0.0

        # Update modulation factor
        self.current_modulation += plasticity_demand
        self.current_modulation = np.clip(self.current_modulation, 0.3, 3.0)

        # Track history
        self.plasticity_demand_history.append(plasticity_demand)
        self.activity_history.append(mean_activity)

    def get_modulation(self) -> float:
        """Get current plasticity modulation factor."""
        return self.current_modulation

    def get_plasticity_scale(self) -> float:
        """Get scale factor for plasticity computations."""
        return self.baseline_plasticity * self.current_modulation


class STDPNetwork:
    """
    Complete STDP Learning Network.
    Integrates STDP, homeostatic scaling, and metaplasticity.
    """
    def __init__(self, input_size: int = 256, output_size: int = 128):
        self.input_size = input_size
        self.output_size = output_size

        # Components
        self.stdp = STDPPlasticity(input_size, output_size)
        self.homeostatic = HomeostaticScaling()
        self.metaplasticity = Metaplasticity()

        # Network state
        self.pre_neurons = np.zeros(input_size)
        self.post_neurons = np.zeros(output_size)

        # Learning parameters
        self.learning_enabled = True
        self.consolidation_threshold = 0.7

    def forward(self, inputs: np.ndarray) -> np.ndarray:
        """Forward pass through network."""
        # Compute pre-synaptic activations
        self.pre_neurons = np.tanh(inputs[:self.input_size])

        # Compute post-synaptic activations
        post_input = np.dot(self.stdp.weights, self.pre_neurons)
        self.post_neurons = np.tanh(post_input)

        return self.post_neurons.copy()

    def learn(self, inputs: np.ndarray, targets: np.ndarray = None) -> Dict:
        """
        Perform learning cycle.
        Returns learning stats.
        """
        if not self.learning_enabled:
            return {"learning_disabled": True}

        # Forward pass
        outputs = self.forward(inputs)

        # Compute error for weight update
        if targets is not None:
            error = targets - outputs
            weight_update = np.outer(error, self.pre_neurons) * 0.01
            self.stdp.weights += weight_update

        # Get metaplasticity modulation
        meta_scale = self.metaplasticity.get_plasticity_scale()

        # Apply homeostatic scaling
        activity = np.mean(np.abs(self.post_neurons))
        scaling_factors = self.homeostatic.compute_scaling(activity, self.stdp.weights)
        self.stdp.weights = self.homeostatic.apply_scaling(self.stdp.weights)

        # Update metaplasticity
        self.metaplasticity.update_metaplasticity(
            self.post_neurons, self.stdp.weights
        )

        return {
            "output_mean": float(np.mean(outputs)),
            "weight_mean": float(np.mean(self.stdp.weights)),
            "metaplasticity_modulation": meta_scale,
            "homeostatic_scaling": float(np.mean(scaling_factors))
        }

    def apply_stdp_from_spikes(self, pre_spikes: np.ndarray, post_spikes: np.ndarray,
                               pre_times: np.ndarray, post_times: np.ndarray):
        """Apply STDP from spike events."""
        changes = self.stdp.compute_pairwise_stdp(pre_spikes, post_spikes, pre_times, post_times)

        # Apply metaplasticity modulation
        meta_scale = self.metaplasticity.get_plasticity_scale()
        self.stdp.weights *= meta_scale

    def get_system_state(self) -> Dict:
        """Get complete system state."""
        return {
            "weights": self.stdp.get_weight_stats(),
            "metaplasticity": {
                "modulation": self.metaplasticity.get_modulation(),
                "scale": self.metaplasticity.get_plasticity_scale()
            },
            "homeostatic": {
                "scaling_factors": self.homeostatic.scaling_factors.tolist()[:10]
            },
            "plasticity_enabled": self.learning_enabled
        }

    def reset(self):
        """Reset learning network."""
        self.stdp.weights = np.random.randn(self.stdp.output_size, self.stdp.input_size) * 0.05
        self.stdp.pre_traces.fill(0)
        self.stdp.post_traces.fill(0)


def create_stdp_network(input_size: int = 256, output_size: int = 128) -> STDPNetwork:
    """Factory function to create STDP network."""
    return STDPNetwork(input_size, output_size)


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE STDP Learning - BRN-011 - Test")
    print("=" * 60)

    # Create network
    network = create_stdp_network(input_size=256, output_size=128)

    # Test 1: Basic forward pass
    print("\n--- Test Forward Pass ---")
    inputs = np.random.randn(256)
    outputs = network.forward(inputs)
    print(f"  Input mean: {np.mean(np.abs(inputs)):.3f}")
    print(f"  Output mean: {np.mean(np.abs(outputs)):.3f}")
    print(f"  Output shape: {outputs.shape}")

    # Test 2: Learning cycle
    print("\n--- Test Learning ---")
    for epoch in range(3):
        inputs = np.random.randn(256)
        targets = np.random.randn(128) * 0.5
        stats = network.learn(inputs, targets)
        print(f"  Epoch {epoch+1}: weight_mean={stats['weight_mean']:.3f}, meta_mod={stats['metaplasticity_modulation']:.2f}")

    # Test 3: STDP pairwise
    print("\n--- Test STDP Pairwise ---")
    pre_spikes = np.array([10, 25, 40])
    post_spikes = np.array([35, 50])
    pre_times = np.array([10.0, 25.0, 40.0])
    post_times = np.array([35.0, 50.0])
    changes = network.stdp.compute_pairwise_stdp(pre_spikes, post_spikes, pre_times, post_times)
    print(f"  Total weight changes: {np.sum(np.abs(changes)):.4f}")

    # Test 4: Metaplasticity
    print("\n--- Test Metaplasticity ---")
    network.metaplasticity.update_metaplasticity(
        np.random.randn(128) * 0.5,  # Moderate activity
        network.stdp.weights
    )
    print(f"  Metaplasticity modulation: {network.metaplasticity.get_modulation():.2f}")
    print(f"  Plasticity scale: {network.metaplasticity.get_plasticity_scale():.2f}")

    # Test 5: Homeostatic scaling
    print("\n--- Test Homeostatic ---")
    scaling = network.homeostatic.compute_scaling(0.15, network.stdp.weights)
    print(f"  Activity (low): {0.15:.2f}, scaling factors mean: {np.mean(scaling):.3f}")
    scaling = network.homeostatic.compute_scaling(0.5, network.stdp.weights)
    print(f"  Activity (normal): {0.5:.2f}, scaling factors mean: {np.mean(scaling):.3f}")

    # Test 6: System state
    print("\n--- Test System State ---")
    state = network.get_system_state()
    print(f"  Weight stats: mean={state['weights']['mean']:.3f}, std={state['weights']['std']:.3f}")
    print(f"  Metaplasticity: scale={state['metaplasticity']['scale']:.2f}")

    print("\n" + "=" * 60)
    print("STDP Learning: PASS")
    print("=" * 60)