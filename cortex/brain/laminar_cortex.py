"""
SPEACE Laminar Cortical Model - Bio-inspired Neocortical Column
Implements 6-layer neocortex with feedforward/feedback/lateral connectivity.
Version: 1.0
Data: 25 Aprile 2026

This is the foundational component for all higher brain functions.
Each column contains specialized layers mirroring biological neocortex.
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)


# -----------------------------------------------
# Data Classes for Layer Communication
# -----------------------------------------------

@dataclass
class LayerActivation:
    """Activation from a cortical layer."""
    layer_id: int
    neurons: np.ndarray
    timestamp: str
    attention_weight: float = 1.0
    prediction_error: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "layer_id": self.layer_id,
            "mean_activation": float(np.mean(self.neurons)),
            "timestamp": self.timestamp,
            "attention_weight": self.attention_weight,
            "prediction_error": self.prediction_error
        }


@dataclass
class ColumnState:
    """Full state of a cortical column."""
    column_id: str
    layer_activations: Dict[int, LayerActivation]
    feedforward_output: Optional[np.ndarray] = None
    feedback_input: Optional[np.ndarray] = None
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "column_id": self.column_id,
            "layers": {k: v.to_dict() for k, v in self.layer_activations.items()},
            "processing_time_ms": self.processing_time_ms
        }


@dataclass
class CorticalRegion:
    """Collection of columns forming a cortical region."""
    region_id: str
    columns: Dict[str, 'CorticalColumn']
    region_type: str  # 'sensory', 'association', 'motor'
    topologically_organized: bool = True


# -----------------------------------------------
# Neuron Models
# -----------------------------------------------

def sigmoid(x):
    """Numerically stable sigmoid function."""
    return np.where(x >= 0,
                    1 / (1 + np.exp(-x)),
                    np.exp(x) / (1 + np.exp(x)))


class LIF_Neuron:
    """Leaky Integrate-and-Fire neuron model."""
    def __init__(self, tau_mem: float = 20.0, v_thresh: float = 1.0,
                 v_rest: float = 0.0, dt: float = 1.0):
        self.tau_mem = tau_mem
        self.v_thresh = v_thresh
        self.v_rest = v_rest
        self.dt = dt
        self.v_membrane = v_rest

    def step(self, input_current: float) -> Tuple[float, bool]:
        """Process one timestep."""
        # Leaky integration
        self.v_membrane += (-(self.v_membrane - self.v_rest) + input_current) / self.tau_mem * self.dt

        # Spike generation
        spiked = self.v_membrane >= self.v_thresh
        if spiked:
            self.v_membrane = self.v_rest

        return self.v_membrane, spiked


class NeuralPopulation:
    """Population of neurons with shared parameters."""
    def __init__(self, size: int, neuron_type: str = "lif", **kwargs):
        self.size = size
        self.neuron_type = neuron_type

        if neuron_type == "lif":
            self.neurons = [LIF_Neuron(**kwargs) for _ in range(size)]
        elif neuron_type == "rate":
            self.neurons = None  # Rate-based, no individual neurons
            self.gain = kwargs.get('gain', 1.0)
            self.bias = kwargs.get('bias', 0.0)

        # Population activity
        self.activity = np.zeros(size)
        self.firing_rate = np.zeros(size)

    def process(self, inputs: np.ndarray) -> np.ndarray:
        """Process input through population."""
        if self.neuron_type == "lif":
            outputs = []
            for i, neuron in enumerate(self.neurons):
                if i < len(inputs):
                    v_m, spiked = neuron.step(inputs[i])
                    outputs.append(1.0 if spiked else 0.0)
                else:
                    outputs.append(0.0)
            self.activity = np.array(outputs)
        elif self.neuron_type == "rate":
            # Rate-based: activation = gain * input + bias, passed through nonlinearity
            self.activity = np.tanh(self.gain * inputs + self.bias)

        self.firing_rate = self.activity  # For rate neurons
        return self.activity

    def get_mean_activity(self) -> float:
        return float(np.mean(self.activity))


# -----------------------------------------------
# Synaptic Weights and Plasticity
# -----------------------------------------------

class SynapticWeights:
    """Manages synaptic weights with Hebbian plasticity."""
    def __init__(self, input_size: int, output_size: int,
                 initialization: str = "xavier"):
        self.input_size = input_size
        self.output_size = output_size

        # Initialize weights
        if initialization == "xavier":
            scale = np.sqrt(2.0 / (input_size + output_size))
            self.weights = np.random.randn(output_size, input_size) * scale
        elif initialization == "uniform":
            self.weights = np.random.uniform(-0.1, 0.1, (output_size, input_size))
        else:
            self.weights = np.random.randn(output_size, input_size) * 0.01

        # Plasticity parameters
        self.learning_rate = 0.01
        self.hebbian_factor = 0.9
        self.decay_rate = 0.001

        # Weight history for analysis
        self.history = deque(maxlen=1000)

    def forward(self, inputs: np.ndarray) -> np.ndarray:
        """Forward pass."""
        return np.dot(self.weights, inputs)

    def hebbian_update(self, pre_activity: np.ndarray, post_activity: np.ndarray):
        """Hebbian weight update: ΔW = η * pre * post * W"""
        delta_w = self.learning_rate * np.outer(post_activity, pre_activity)
        self.weights += delta_w

        # Normalize to prevent runaway weights
        row_norms = np.linalg.norm(self.weights, axis=1, keepdims=True)
        row_norms[row_norms == 0] = 1
        self.weights = self.weights / row_norms * np.sqrt(self.input_size)

        # Apply decay
        self.weights *= (1 - self.decay_rate)

    def apply_stdp(self, pre_spikes: np.ndarray, post_spikes: np.ndarray,
                   timing_diff: float):
        """
        Spike-Timing Dependent Plasticity.
        timing_diff > 0 means pre before post (LTP)
        timing_diff < 0 means post before pre (LTD)
        """
        if timing_diff > 0:  # LTP: pre before post
            delta = self.learning_rate * np.outer(post_spikes, pre_spikes) * 0.1
        else:  # LTD: post before pre
            delta = -self.learning_rate * np.outer(post_spikes, pre_spikes) * 0.05

        self.weights += delta
        self.weights = np.clip(self.weights, -2, 2)

    def get_weight_stats(self) -> Dict:
        return {
            "mean": float(np.mean(self.weights)),
            "std": float(np.std(self.weights)),
            "max": float(np.max(self.weights)),
            "min": float(np.min(self.weights)),
            "sparsity": float(np.sum(np.abs(self.weights) < 0.01) / self.weights.size)
        }


# -----------------------------------------------
# Cortical Layers
# -----------------------------------------------

class Layer1_SensoryInput:
    """
    L1: Sensory Input Layer
    Receives direct sensory input from thalamus and environment.
    Creates initial encoding of stimuli.
    """
    def __init__(self, column_id: str, input_size: int, neuron_count: int = 64):
        self.column_id = column_id
        self.layer_id = 1
        self.neuron_count = neuron_count
        self.input_size = input_size

        # Input processing
        self.encoding_weights = SynapticWeights(input_size, neuron_count, "xavier")
        self.excitatory_gain = 2.0

        # Lateral connections (same-layer)
        self.lateral_weights = SynapticWeights(neuron_count, neuron_count, "uniform")
        self.lateral_inhibition_strength = 0.3

        self.output = np.zeros(neuron_count)

    def encode(self, sensory_input: np.ndarray) -> np.ndarray:
        """Encode sensory input into neural pattern."""
        # Validate input size
        if len(sensory_input) != self.input_size:
            # Pad or truncate
            if len(sensory_input) < self.input_size:
                sensory_input = np.pad(sensory_input, (0, self.input_size - len(sensory_input)))
            else:
                sensory_input = sensory_input[:self.input_size]

        # Feedforward encoding
        ff_output = self.encoding_weights.forward(sensory_input) * self.excitatory_gain

        # Lateral interactions (competitive learning)
        lateral_excitation = np.dot(self.lateral_weights.weights, self.output)
        lateral_inhibition = self.lateral_inhibition_strength * np.mean(self.output)

        self.output = np.tanh(ff_output + lateral_excitation - lateral_inhibition)
        self.output = np.clip(self.output, -1, 1)

        return self.output

    def hebbian_learn(self, input_pattern: np.ndarray):
        """Hebbian learning between input and output."""
        self.encoding_weights.hebbian_update(input_pattern, self.output)


class Layer2_3_Association:
    """
    L2/3: Association Layer
    Local association and recurrent excitation.
    Processes Feedforward input and creates higher-order representations.
    """
    def __init__(self, column_id: str, input_size: int, neuron_count: int = 128):
        self.column_id = column_id
        self.layer_id = 2  # Layer 2/3
        self.neuron_count = neuron_count

        # Input from L4
        self.input_weights = SynapticWeights(input_size, neuron_count, "xavier")

        # Recurrent connections (memory)
        self.recurrent_weights = SynapticWeights(neuron_count, neuron_count, "xavier")
        self.recurrent_gain = 0.8

        # Output projection to L5
        self.output_weights = SynapticWeights(neuron_count, neuron_count, "xavier")

        # Inhibition for competition
        self.k_winner = 15  # Number of winners in k-winner-take-all
        self.inhibition_strength = 0.5

        self.output = np.zeros(neuron_count)
        self.recurrent_context = deque(maxlen=5)

    def process(self, l4_input: np.ndarray, feedback_from_l6: np.ndarray = None) -> np.ndarray:
        """Process L4 input through association computation."""
        # Feedforward drive
        ff_drive = self.input_weights.forward(l4_input)

        # Recurrent context integration
        recurrent_drive = np.zeros(self.neuron_count)
        if self.recurrent_context:
            context = np.mean(list(self.recurrent_context), axis=0)
            recurrent_drive = self.recurrent_weights.forward(context) * self.recurrent_gain

        # Combine inputs
        total_input = ff_drive + recurrent_drive

        # Add feedback if available
        if feedback_from_l6 is not None and len(feedback_from_l6) == self.neuron_count:
            total_input += 0.3 * feedback_from_l6

        # Apply nonlinearity
        self.output = np.tanh(total_input)

        # K-winner-take-all inhibition (sparse coding)
        if self.k_winner < self.neuron_count:
            threshold = np.sort(self.output)[-self.k_winner]
            self.output = np.where(self.output >= threshold, self.output, 0)

        # Normalize
        self.output = self.output / (np.linalg.norm(self.output) + 1e-8)

        # Update recurrent memory
        self.recurrent_context.append(self.output.copy())

        return self.output

    def get_sparse_code(self) -> np.ndarray:
        """Returns sparse representation (only active neurons)."""
        return np.where(self.output > 0.2, self.output, 0)


class Layer4_ThalamicInput:
    """
    L4: Thalamic Input Reception
    Receives specific thalamic inputs.
    Primary receptor for feedforward sensory information.
    """
    def __init__(self, column_id: str, input_size: int, neuron_count: int = 64):
        self.column_id = column_id
        self.layer_id = 4
        self.neuron_count = neuron_count

        # Thalamic input weights
        self.thalamic_weights = SynapticWeights(input_size, neuron_count, "xavier")
        self.amplification_gain = 2.5

        # Non-specific (matrix) inputs
        self.matrix_input_size = 32
        self.matrix_weights = SynapticWeights(self.matrix_input_size, neuron_count, "uniform")
        self.matrix_gain = 0.5

        self.output = np.zeros(neuron_count)

    def integrate(self, sensory_input: np.ndarray, matrix_input: np.ndarray = None) -> np.ndarray:
        """Integrate thalamic and matrix inputs."""
        # Specific thalamic input
        thalamic = self.thalamic_weights.forward(sensory_input) * self.amplification_gain

        # Non-specific/matrix input (from other cortical areas)
        matrix = np.zeros(self.neuron_count)
        if matrix_input is not None and len(matrix_input) == self.matrix_input_size:
            matrix = self.matrix_weights.forward(matrix_input) * self.matrix_gain

        self.output = np.tanh(thalamic + matrix)

        return self.output

    def get_integration_summary(self) -> Dict:
        return {
            "thalamic_strength": float(np.mean(np.abs(self.thalamic_weights.weights))),
            "matrix_strength": float(np.mean(np.abs(self.matrix_weights.weights)))
        }


class Layer5_OutputGeneration:
    """
    L5: Output Generation
    Generates output signals to subcortical structures and other areas.
    Contains pyramidal tract neurons.
    """
    def __init__(self, column_id: str, input_size: int, neuron_count: int = 96):
        self.column_id = column_id
        self.layer_id = 5
        self.neuron_count = neuron_count

        # Input from L2/3
        self.input_weights = SynapticWeights(input_size, neuron_count, "xavier")

        # Subcortical projection weights
        self.subcortical_weights = SynapticWeights(neuron_count, neuron_count, "xavier")

        # Output neurons (pyramidal tract)
        self.pyramidal_neurons = NeuralPopulation(neuron_count, "rate", gain=1.5)

        self.output = np.zeros(neuron_count)
        self.subcortical_output = np.zeros(neuron_count)

    def generate(self, l2_3_output: np.ndarray, prediction_error: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        """Generate outputs to cortical and subcortical targets."""
        # Input processing
        input_drive = self.input_weights.forward(l2_3_output)

        # Modulate by prediction error (higher error = stronger output)
        error_modulation = 1.0 + np.abs(prediction_error) * 0.5
        input_drive *= error_modulation

        # Generate cortical output
        self.output = self.pyramidal_neurons.process(input_drive)

        # Generate subcortical output (motor commands, etc.)
        self.subcortical_output = self.subcortical_weights.forward(self.output)

        return self.output, self.subcortical_output

    def get_output_summary(self) -> Dict:
        return {
            "cortical_output_mean": float(np.mean(self.output)),
            "subcortical_output_mean": float(np.mean(self.subcortical_output)),
            "active_fraction": float(np.sum(self.output > 0.1) / self.neuron_count)
        }


class Layer6_FeedbackProjection:
    """
    L6: Feedback Projection
    Projects feedback to lower cortical areas and thalamus.
    Contains corticothalamic neurons.
    """
    def __init__(self, column_id: str, input_size: int, neuron_count: int = 64):
        self.column_id = column_id
        self.layer_id = 6
        self.neuron_count = neuron_count

        # Input from L5
        self.input_weights = SynapticWeights(input_size, neuron_count, "xavier")

        # Feedback to L2/3
        self.feedback_to_l23 = SynapticWeights(neuron_count, neuron_count, "xavier")
        self.feedback_gain = 0.4

        # Feedback to thalamus (corticothalamic)
        self.thalamic_feedback_size = 32
        self.feedback_to_thalamus = SynapticWeights(neuron_count, self.thalamic_feedback_size, "xavier")
        self.thalamic_gain = 0.3

        # Inactivating interneurons (feedback control)
        self.interneuron_weights = SynapticWeights(neuron_count, neuron_count, "uniform")
        self.interneuron_gain = 0.2

        self.output = np.zeros(neuron_count)
        self.l23_feedback = np.zeros(neuron_count)
        self.thalamic_feedback = np.zeros(self.thalamic_feedback_size)

    def project(self, l5_output: np.ndarray) -> np.ndarray:
        """Project feedback signals to lower areas."""
        # Input processing
        input_drive = self.input_weights.forward(l5_output)

        # Generate interneuron inhibition (controls feedback magnitude)
        interneuron_activity = np.dot(self.interneuron_weights.weights, input_drive)
        gating_scalar = float(np.mean(sigmoid(interneuron_activity * self.interneuron_gain)))

        # Compute feedback to L2/3 (contextual prediction)
        self.l23_feedback = self.feedback_to_l23.forward(input_drive) * self.feedback_gain * (1 - gating_scalar)

        # Compute feedback to thalamus
        self.thalamic_feedback = self.feedback_to_thalamus.forward(input_drive) * self.thalamic_gain * (1 - gating_scalar)

        # Combined output for L6 activation
        self.output = input_drive

        return self.l23_feedback

    def get_thalamic_feedback(self) -> np.ndarray:
        """Get feedback signal for thalamus."""
        return self.thalamic_feedback

    def get_feedback_summary(self) -> Dict:
        return {
            "l23_feedback_mean": float(np.mean(np.abs(self.l23_feedback))),
            "thalamic_feedback_mean": float(np.mean(np.abs(self.thalamic_feedback))),
            "gate_openness": float(np.mean(sigmoid(np.dot(self.interneuron_weights.weights, self.output))))
        }


# -----------------------------------------------
# Cortical Column (Main Class)
# -----------------------------------------------

class CorticalColumn:
    """
    Cortical Column with 6-layer neocortical architecture.
    Processes information through laminar processing with recurrent connectivity.
    """
    def __init__(self, column_id: str, input_size: int = 256,
                 l1_neurons: int = 64, l23_neurons: int = 128,
                 l4_neurons: int = 64, l5_neurons: int = 96, l6_neurons: int = 64):
        self.column_id = column_id
        self.input_size = input_size

        # Initialize layers
        self.layer1 = Layer1_SensoryInput(column_id, input_size, l1_neurons)
        self.layer2_3 = Layer2_3_Association(column_id, l1_neurons, l23_neurons)
        self.layer4 = Layer4_ThalamicInput(column_id, input_size, l4_neurons)
        self.layer5 = Layer5_OutputGeneration(column_id, l23_neurons, l5_neurons)
        self.layer6 = Layer6_FeedbackProjection(column_id, l5_neurons, l6_neurons)

        # State tracking
        self.processing_history = deque(maxlen=100)
        self.prediction_errors = deque(maxlen=50)

        # Column parameters
        self.location = (0, 0)  # For topographic organization
        self.region_type = "association"  # 'sensory', 'association', 'motor'

        # Performance metrics
        self.activation_count = 0
        self.last_processing_time = 0.0

    def process_column(self, sensory_input: np.ndarray,
                      thalamic_input: np.ndarray = None,
                      context: np.ndarray = None) -> Dict[str, np.ndarray]:
        """
        Process input through all 6 layers.
        Returns outputs from different layers for analysis/debugging.
        """
        import time
        start_time = time.time()

        outputs = {}

        # === LAYER 1: Sensory Encoding ===
        l1_out = self.layer1.encode(sensory_input)
        outputs['L1_sensory'] = l1_out.copy()

        # === LAYER 4: Thalamic Integration (parallel to L1) ===
        if thalamic_input is not None:
            l4_out = self.layer4.integrate(sensory_input, thalamic_input)
        else:
            l4_out = self.layer4.integrate(sensory_input)
        outputs['L4_thalamic'] = l4_out.copy()

        # === LAYER 2/3: Association ===
        # L2/3 receives from L4 (feedforward) and L6 (feedback)
        l6_feedback = context if context is not None else None
        l23_out = self.layer2_3.process(l4_out, l6_feedback)
        outputs['L2_3_association'] = l23_out.copy()
        outputs['L2_3_sparse'] = self.layer2_3.get_sparse_code()

        # === LAYER 5: Output Generation ===
        # Calculate prediction error for modulation
        if len(self.prediction_errors) > 0:
            pred_error = np.mean(self.prediction_errors)
        else:
            pred_error = 0.0

        l5_out, subcortical = self.layer5.generate(l23_out, pred_error)
        outputs['L5_cortical'] = l5_out.copy()
        outputs['L5_subcortical'] = subcortical.copy()

        # === LAYER 6: Feedback Projection ===
        l6_out = self.layer6.project(l5_out)
        outputs['L6_feedback'] = l6_out.copy()
        outputs['L6_thalamic'] = self.layer6.get_thalamic_feedback()

        # Update processing stats
        self.last_processing_time = time.time() - start_time
        self.activation_count += 1

        # Store in history
        self.processing_history.append({
            "timestamp": datetime.now().isoformat(),
            "processing_time_ms": self.last_processing_time * 1000,
            "l2_3_activity": float(np.mean(l23_out)),
            "l5_output": float(np.mean(l5_out))
        })

        return outputs

    def compute_prediction_error(self, observed: np.ndarray, predicted: np.ndarray) -> float:
        """Compute prediction error for a layer."""
        error = np.mean(np.abs(observed - predicted))
        self.prediction_errors.append(error)
        return error

    def get_column_state(self) -> Dict:
        """Get complete state of the column."""
        return {
            "column_id": self.column_id,
            "activation_count": self.activation_count,
            "avg_processing_time_ms": self.last_processing_time * 1000,
            "prediction_error_recent": float(np.mean(list(self.prediction_errors))) if self.prediction_errors else 0.0,
            "layer_stats": {
                "L4_thalamic_integration": self.layer4.get_integration_summary(),
                "L5_output": self.layer5.get_output_summary(),
                "L6_feedback": self.layer6.get_feedback_summary()
            },
            "location": self.location,
            "region_type": self.region_type
        }

    def hebbian_learn_all(self, sensory_input: np.ndarray):
        """Apply Hebbian learning across layers."""
        l1_out = self.layer1.encode(sensory_input)
        self.layer1.hebbian_learn(sensory_input)


class CorticalRegionManager:
    """
    Manages multiple cortical columns organized by region.
    Coordinates inter-column communication and region-wide processing.
    """
    def __init__(self, region_id: str, region_type: str, columns_per_row: int = 4, rows: int = 4):
        self.region_id = region_id
        self.region_type = region_type
        self.columns: Dict[str, CorticalColumn] = {}
        self.grid_size = (columns_per_row, rows)

        # Inter-column connections (lateral)
        self.lateral_connection_strength = 0.15

        # Region-level output aggregation
        self.region_output = None

    def add_column(self, column_id: str, **kwargs) -> CorticalColumn:
        """Add a column to the region."""
        column = CorticalColumn(column_id, **kwargs)
        column.region_type = self.region_type

        # Assign location in grid
        idx = len(self.columns)
        row = idx // self.grid_size[0]
        col = idx % self.grid_size[0]
        column.location = (row, col)

        self.columns[column_id] = column
        return column

    def process_region(self, inputs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """Process inputs through all columns in the region."""
        outputs = {}

        for col_id, column in self.columns.items():
            if col_id in inputs:
                col_input = inputs[col_id]
            else:
                # Use first available input for all if no specific mapping
                col_input = list(inputs.values())[0] if inputs else np.zeros(256)

            outputs[col_id] = column.process_column(col_input)

        # Aggregate region output
        self._aggregate_region_output(outputs)

        return outputs

    def _aggregate_region_output(self, column_outputs: Dict):
        """Aggregate outputs from all columns."""
        l5_outputs = []
        for col_id, outputs in column_outputs.items():
            if 'L5_cortical' in outputs:
                l5_outputs.append(outputs['L5_cortical'])

        if l5_outputs:
            self.region_output = np.mean(l5_outputs, axis=0)
        else:
            self.region_output = None

    def get_region_summary(self) -> Dict:
        """Get summary statistics for the region."""
        if not self.columns:
            return {"column_count": 0}

        return {
            "region_id": self.region_id,
            "region_type": self.region_type,
            "column_count": len(self.columns),
            "grid_size": self.grid_size,
            "columns": {col_id: col.get_column_state() for col_id, col in self.columns.items()}
        }


# -----------------------------------------------
# Hierarchical Cortical Network (Top Level)
# -----------------------------------------------

class HierarchicalCorticalNetwork:
    """
    Top-level manager for multiple cortical regions in hierarchy.
    Implements feedforward/feedback processing across regions.
    """
    def __init__(self, num_levels: int = 3):
        self.num_levels = num_levels
        self.regions: Dict[str, CorticalRegionManager] = {}
        self.inter_region_weights = {}

        # Hierarchy configuration
        self.level_sizes = {
            1: {"columns": 16, "neurons_per_column": 32},
            2: {"columns": 8, "neurons_per_column": 64},
            3: {"columns": 4, "neurons_per_column": 128}
        }

        # Initialize regions
        self._setup_hierarchy()

    def _setup_hierarchy(self):
        """Set up hierarchical region structure."""
        for level in range(1, self.num_levels + 1):
            config = self.level_sizes.get(level, {"columns": 4, "neurons_per_column": 64})

            region = CorticalRegionManager(
                region_id=f"level_{level}",
                region_type="sensory" if level == 1 else "association",
                columns_per_row=4,
                rows=config["columns"] // 4
            )

            # Add columns
            for i in range(config["columns"]):
                col_id = f"L{level}_col_{i}"
                region.add_column(
                    col_id,
                    input_size=256,
                    l1_neurons=config["neurons_per_column"] // 4,
                    l23_neurons=config["neurons_per_column"] // 2,
                    l4_neurons=config["neurons_per_column"] // 4,
                    l5_neurons=config["neurons_per_column"] // 3,
                    l6_neurons=config["neurons_per_column"] // 4
                )

            self.regions[f"level_{level}"] = region

        logger.info(f"HierarchicalCorticalNetwork initialized with {self.num_levels} levels")

    def process_hierarchy(self, sensory_input: np.ndarray,
                         target_level: int = 1) -> Dict:
        """
        Process input through hierarchical network.
        Returns outputs and state from all levels.
        """
        results = {}

        # Process from bottom up
        for level in range(1, self.num_levels + 1):
            region = self.regions[f"level_{level}"]

            if level == 1:
                # Level 1 receives external input
                inputs = {col_id: sensory_input for col_id in region.columns.keys()}
            else:
                # Higher levels receive from level below
                lower_region = self.regions[f"level_{level - 1}"]
                lower_output = lower_region.region_output
                if lower_output is None:
                    lower_output = sensory_input  # Fallback

                # Ensure lower_output has correct size for next level (256)
                # Pad or truncate as needed
                if len(lower_output) < 256:
                    lower_output = np.pad(lower_output, (0, 256 - len(lower_output)))
                elif len(lower_output) > 256:
                    lower_output = lower_output[:256]

                inputs = {col_id: lower_output for col_id in region.columns.keys()}

            outputs = region.process_region(inputs)
            results[f"level_{level}"] = outputs

        return results

    def get_network_summary(self) -> Dict:
        """Get summary of entire network."""
        return {
            "num_levels": self.num_levels,
            "total_columns": sum(len(r.columns) for r in self.regions.values()),
            "regions": {rid: r.get_region_summary() for rid, r in self.regions.items()}
        }


# -----------------------------------------------
# Factory and Registry
# -----------------------------------------------

class CorticalColumnFactory:
    """Factory for creating and managing cortical columns."""
    _columns: Dict[str, CorticalColumn] = {}
    _regions: Dict[str, CorticalRegionManager] = {}

    @classmethod
    def create_column(cls, column_id: str, **kwargs) -> CorticalColumn:
        """Create a new cortical column."""
        if column_id in cls._columns:
            logger.warning(f"Column {column_id} already exists, returning existing")
            return cls._columns[column_id]

        column = CorticalColumn(column_id, **kwargs)
        cls._columns[column_id] = column
        return column

    @classmethod
    def get_column(cls, column_id: str) -> Optional[CorticalColumn]:
        return cls._columns.get(column_id)

    @classmethod
    def list_columns(cls) -> List[str]:
        return list(cls._columns.keys())

    @classmethod
    def create_region(cls, region_id: str, region_type: str = "association") -> CorticalRegionManager:
        """Create a new cortical region."""
        region = CorticalRegionManager(region_id, region_type)
        cls._regions[region_id] = region
        return region

    @classmethod
    def get_network_summary(cls) -> Dict:
        return {
            "total_columns": len(cls._columns),
            "total_regions": len(cls._regions),
            "columns": list(cls._columns.keys()),
            "regions": {rid: r.get_region_summary() for rid, r in cls._regions.items()}
        }


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Laminar Cortical Model - Test")
    print("=" * 60)

    # Test single column
    print("\n--- Test Single Column ---")
    column = CorticalColumn("test_column_1", input_size=256)
    print(f"Column created: {column.column_id}")

    # Generate test input
    test_input = np.random.randn(256)
    thalamic_input = np.random.randn(64)

    # Process
    outputs = column.process_column(test_input, thalamic_input)

    print("\nLayer outputs:")
    for layer_name, output in outputs.items():
        print(f"  {layer_name}: shape={output.shape}, mean={np.mean(output):.3f}")

    # Get state
    state = column.get_column_state()
    print(f"\nColumn state:")
    print(f"  Processing time: {state['avg_processing_time_ms']:.2f}ms")
    print(f"  Prediction error: {state['prediction_error_recent']:.3f}")

    # Test hierarchy
    print("\n--- Test Hierarchical Network ---")
    network = HierarchicalCorticalNetwork(num_levels=3)
    print(f"Network created with {network.num_levels} levels")

    # Process through hierarchy
    sensory = np.random.randn(256)
    results = network.process_hierarchy(sensory)

    print("\nHierarchical processing results:")
    for level_name, level_outputs in results.items():
        print(f"  {level_name}: {len(level_outputs)} columns processed")

    # Summary
    summary = network.get_network_summary()
    print(f"\nNetwork summary: {summary['total_columns']} columns total")

    print("\n" + "=" * 60)
    print("✅ Laminar Cortical Model test completed")
    print("=" * 60)