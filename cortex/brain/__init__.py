"""
SPEACE Brain Module - Complete Biological Brain Emulation
BRN-001 to BRN-020 implementations

Modules:
- BRN-001: Laminar Cortical Model (6-layer neocortex)           implemented
- BRN-002: Thalamic Relay System                                implemented
- BRN-003: Amygdala Module                                      implemented
- BRN-004: Basal Ganglia System                                 implemented
- BRN-005: Dopaminergic System                                  implemented
- BRN-006: Working Memory Module                                implemented
- BRN-007: Affective Computing Layer                            implemented
- BRN-008: Motivational Engine (SDT-based)                      implemented
- BRN-009: Social Cognition Module (ToM, empathy)               implemented
- BRN-010: Consciousness Gate (Global Workspace)                implemented
- BRN-011: STDP Learning (synaptic plasticity)                  implemented
- BRN-012: Episodic Memory (hippocampal system)                 implemented
- BRN-013: Metalearning System (learning-to-learn)              implemented
- BRN-014: Attention System (selective/divided/executive)       implemented
- BRN-015: Predictive Coding (Free Energy Principle)            implemented
- BRN-016: Language Acquisition                                 stub
- BRN-017: Causal Reasoning (Pearl hierarchy)                   stub
- BRN-018: Abstraction Layer (conceptual blending)              stub
- BRN-019: Self-Model (body schema, metacognition)              stub
- BRN-020: Recursive Self-Improvement (Darwin Godel)            stub

Version: 2.0
Data: 26 Aprile 2026
"""

# BRN-001
from .laminar_cortex import (
    CorticalColumn, CorticalRegionManager, HierarchicalCorticalNetwork,
    CorticalColumnFactory, Layer1_SensoryInput, Layer2_3_Association,
    Layer4_ThalamicInput, Layer5_OutputGeneration, Layer6_FeedbackProjection,
    SynapticWeights, NeuralPopulation, LIF_Neuron,
)
# BRN-002
from .thalamic_system import (
    ThalamicRelaySystem, ThalamicSwitch, ThalamicNucleusType, ThalamicSignal,
    AttentionGate, LGN_Nucleus, MD_Nucleus, PulvinarNucleus, IN_Nucleus,
    CentromedianNucleus, create_thalamic_system,
)
# BRN-003
from .amygdala_module import (
    Amygdala, EmotionalValence, EmotionalState, LateralNucleus,
    BasolateralComplex, CentromedialNucleus, CentralNucleus, create_amygdala,
)
# BRN-004
from .basal_ganglia import (
    BasalGanglia, ActionSelectionPolicy, Striatum, GlobusPallidusInterna,
    SubthalamicNucleus, SubstantiaNigra, GlobusPallidusExterna,
    Action, SelectionResult, create_basal_ganglia,
)
# BRN-005
from .dopaminergic_system import (
    DopaminergicSystem, VTA_Dopamine, SNc_Dopamine, MotivationCalculator,
    CuriositySignal, RewardOutcome, MotivationSignal, create_dopaminergic_system,
)
# BRN-006
from .working_memory import (
    WorkingMemory, WMRegion, WMItem, WMState, DLPFC_Module, VLPFC_Module,
    ACC_Module, create_working_memory,
)
# BRN-007
from .affective_layer import (
    AffectiveComputing, AffectiveLayer, EmotionalDimension, MoodState,
    EmotionCategory, create_affective_layer,
)
# BRN-008
from .motivational_engine import (
    MotivationalEngine, AutonomyNeed, CompetenceNeed, RelatednessNeed,
    NeedSatisfaction, Drive, MotivationState, MotivationType,
    create_motivational_engine,
)
# BRN-009
from .social_cognition import (
    SocialCognition, TheoryOfMind, EmpathyModule, SocialLearning,
    JointAttention, IntentDecoding, MentalState, EmpathyResponse,
    SocialLearningResult, SocialSignalType, create_social_cognition,
)
# BRN-010
from .consciousness_gate import (
    ConsciousnessGate, GlobalWorkspace, AccessConsciousness,
    PhenomenalConsciousness, IntegrationBuffer, AttentionBroadcast,
    ConsciousnessLevel, WorkspaceContent, ConsciousnessState,
    create_consciousness_gate,
)
# BRN-011
from .stdp_learning import (
    STDPNetwork, STDPPlasticity, STDPWindow, SynapticTrace,
    HomeostaticScaling, Metaplasticity, PlasticityType, SynapseState,
    STDPResult, create_stdp_network,
)
# BRN-012
from .episodic_memory import (
    HippocampalSystem, DentateGyrus, CA3Region, CA1Region,
    EntorhinalCortex, EpisodicMemory, MemoryPhase, MemoryResult,
    create_hippocampal_system,
)
# BRN-013
from .metalearner import (
    MetaLearner, StrategySelector, HyperparameterOptimizer,
    TransferLearningEngine, ExperienceBuffer,
    LearningStrategy, TaskDomain, Task, LearningEpisode,
    create_metalearner,
)
# BRN-014
from .attention_system import (
    AttentionSystem, SelectiveAttention, DividedAttention, ExecutiveAttention,
    AttentionMode, AttentionSignal, AttentionSignalType, AttentionFocus,
    create_attention_system,
)
# BRN-015
from .predictive_coding import (
    PredictiveCodingEngine, HierarchicalPredictor, PrecisionWeighting,
    GenerativeModel, FreeEnergyMinimizer,
    CorticalLevel, Belief, PredictionError, InferenceMode,
    create_predictive_coding_engine,
)
# BRN-016 stub
from .language_acquisition import LanguageAcquisition, create_language_acquisition
# BRN-017 stub
from .causal_reasoning import CausalReasoner, CausalGraph, create_causal_reasoner
# BRN-018 stub
from .abstraction_layer import AbstractionLayer, Concept, create_abstraction_layer
# BRN-019 stub
from .self_model import (
    SelfModel, BodySchema, SelfNarrative, MetacognitiveMonitor, create_self_model,
)
# BRN-020 stub
from .recursive_self_improvement import (
    RecursiveSelfImprover, ModificationProposal, SafeModificationGate,
    create_recursive_self_improver,
)
# Brain Integration
from .brain_integration import BrainIntegration, BrainSignal, CognitiveResult, create_brain

__version__ = "2.0"
__date__ = "26 Aprile 2026"
__brain_modules__ = "BRN-001 to BRN-015 fully implemented | BRN-016 to BRN-020 stub"
__implemented__ = [f"BRN-{i:03d}" for i in range(1, 16)]
__stub__ = [f"BRN-{i:03d}" for i in range(16, 21)]
