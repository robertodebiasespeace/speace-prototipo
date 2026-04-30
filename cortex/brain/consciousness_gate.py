"""
SPEACE Consciousness Gate - BRN-010
Implements access consciousness vs phenomenal consciousness.
Based on Global Workspace Theory (Baars).
Version: 1.0
Data: 25 Aprile 2026

The consciousness gate models:
- Global Workspace for information integration
- Access Consciousness (reportable info)
- Phenomenal Consciousness (subjective experience)
- Attention broadcast mechanism
- Integration buffer for conscious access
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ConsciousnessLevel(Enum):
    """Levels of consciousness."""
    UNCONSCIOUS = "unconscious"           # No processing
    SUBCONSCIOUS = "subconscious"        # Automatic processing
    PRECONSCIOUS = "preconscious"         # Available but not focused
    CONSCIOUS = "conscious"               # Focal attention
    META_CONSCIOUS = "meta_conscious"     # Self-aware


@dataclass
class WorkspaceContent:
    """Content in the global workspace."""
    information: np.ndarray
    source_module: str
    salience: float
    reportability: float     # How access-conscious this is
    phenomenal_experience: float  # Raw subjective feel
    timestamp: str


@dataclass
class ConsciousnessState:
    """Complete state of consciousness."""
    level: ConsciousnessLevel
    arousal: float
    content: Optional[WorkspaceContent]
    attention_broadcast: bool
    integration_complete: bool


class GlobalWorkspace:
    """
    Global Workspace - Central broadcast system for consciousness.
    Information becomes conscious when it enters the workspace and is broadcast.
    """
    def __init__(self, workspace_size: int = 128):
        self.workspace_size = workspace_size

        # Workspace content
        self.current_content: Optional[WorkspaceContent] = None
        self.content_history = deque(maxlen=50)

        # Competition mechanism
        self.competition_threshold = 0.4
        self.winner_takes_all = True

        # Broadcast properties
        self.broadcast_active = False
        self.attended_modules: List[str] = []

        # Workspace access
        self.access_level = 0.0  # 0 = subliminal, 1 = fully accessible
        self.reportability_threshold = 0.5

    def add_information(self, info: np.ndarray, source: str,
                        salience: float = 0.5) -> bool:
        """
        Add information to workspace competition.
        Returns True if information wins competition and enters workspace.
        """
        # Compute reportability (access consciousness)
        reportability = self._compute_reportability(info, salience)

        # Compute phenomenal feel (still debated - simplified here)
        phenomenal = salience * 0.3 + np.mean(np.abs(info)) * 0.2

        # Check if this info wins competition
        if self.current_content is None or salience > self.current_content.salience:
            # New winner
            self.current_content = WorkspaceContent(
                information=info[:self.workspace_size],
                source_module=source,
                salience=salience,
                reportability=reportability,
                phenomenal_experience=phenomenal,
                timestamp=datetime.now().isoformat()
            )
            self.broadcast_active = True
            self.content_history.append(self.current_content)
            self.access_level = reportability

            logger.debug(f"Workspace: {source} won competition, salience={salience:.2f}")
            return True

        return False

    def _compute_reportability(self, info: np.ndarray, salience: float) -> float:
        """Compute how reportable/accessible this information is."""
        # Reportability depends on: novelty, emotional relevance, task relevance
        novelty = 1.0 - min(1.0, np.std(info) * 2)
        emotional_boost = salience * 0.3
        base_reportability = 0.3 + novelty * 0.3 + emotional_boost

        return np.clip(base_reportability, 0, 1)

    def broadcast(self) -> Optional[np.ndarray]:
        """
        Broadcast workspace content to all modules.
        This is the "conscious" act.
        """
        if self.current_content is None or not self.broadcast_active:
            return None

        self.attended_modules.append(self.current_content.source_module)

        return self.current_content.information.copy()

    def attend_to(self, module: str):
        """Focus attention on specific module."""
        if module not in self.attended_modules:
            self.attended_modules.append(module)

    def clear_workspace(self):
        """Clear workspace content (attention lapses)."""
        self.current_content = None
        self.broadcast_active = False
        self.access_level = 0.0

    def get_content_summary(self) -> Optional[Dict]:
        """Get summary of current workspace content."""
        if self.current_content is None:
            return None

        return {
            "source": self.current_content.source_module,
            "salience": self.current_content.salience,
            "reportability": self.current_content.reportability,
            "phenomenal": self.current_content.phenomenal_experience,
            "access_level": self.access_level
        }


class AccessConsciousness:
    """
    Access Consciousness - Reportable, describable conscious experience.
    Information that can be verbalized, reasoned about, deliberately controlled.
    """
    def __init__(self):
        # Access content
        self.access_content: Optional[np.ndarray] = None
        self.access_history = deque(maxlen=30)

        # Verbalization capacity
        self.verbalization_threshold = 0.5
        self.can_report = False

        # Deliberate control
        self.willful_override_available = False
        self.control_level = 0.5

    def add_to_access(self, content: np.ndarray, reportability: float) -> bool:
        """
        Add to access consciousness if reportable.
        """
        if reportability >= self.verbalization_threshold:
            self.access_content = content
            self.can_report = True
            self.access_history.append({
                "content": content[:32].copy(),
                "reportability": reportability,
                "timestamp": datetime.now().isoformat()
            })
            return True
        return False

    def verbalize(self, content: np.ndarray) -> str:
        """
        Convert content to verbal description (simplified).
        """
        if not self.can_report:
            return "unavailable"

        # Simple encoding -> decoding for verbalization proxy
        summary = f"Experienced content from access level {self.control_level:.1f}"
        return summary

    def deliberate_override(self, new_content: np.ndarray) -> bool:
        """
        Willfully override with deliberate choice.
        """
        if self.willful_override_available:
            self.access_content = new_content
            self.control_level = 0.9
            return True
        return False

    def get_access_summary(self) -> Dict:
        return {
            "has_content": self.access_content is not None,
            "can_report": self.can_report,
            "control_level": self.control_level,
            "history_length": len(self.access_history)
        }


class PhenomenalConsciousness:
    """
    Phenomenal Consciousness - Raw subjective experience ("what it's like").
    Hard problem of consciousness - we model it as subjective quality space.
    """
    def __init__(self):
        # Phenomenal content
        self.phenomenal_content: Optional[np.ndarray] = None
        self.quality_space_size = 64  # Dimensions of subjective experience

        # Phenomenal properties
        self.subjectivity_strength = 0.5
        self.perspective_ownership = 0.8  # Sense of mineness
        self.temporal_flow = 0.7  # Sense of time passage

        # Experience history (for "streets of London" memory)
        self.experience_memory = deque(maxlen=100)
        self.qualia_patterns: Dict[str, np.ndarray] = {}

    def add_phenomenal_content(self, raw_experience: np.ndarray, intensity: float):
        """
        Add phenomenal content - the raw feel.
        """
        # Compress to quality space
        if len(raw_experience) > self.quality_space_size:
            experience = raw_experience[:self.quality_space_size]
        else:
            experience = np.pad(raw_experience, (0, self.quality_space_size - len(raw_experience)))

        self.phenomenal_content = experience

        # Store in experience memory
        self.experience_memory.append({
            "experience": experience.copy(),
            "intensity": intensity,
            "timestamp": datetime.now().isoformat()
        })

        self.subjectivity_strength = min(1.0, intensity * 0.8 + 0.2)

    def get_phenomenal_summary(self) -> Dict:
        """Get summary of phenomenal state."""
        return {
            "has_content": self.phenomenal_content is not None,
            "subjectivity_strength": self.subjectivity_strength,
            "perspective_ownership": self.perspective_ownership,
            "temporal_flow": self.temporal_flow,
            "experience_count": len(self.experience_memory)
        }

    def match_qualial(self, pattern: np.ndarray) -> Optional[str]:
        """
        Match current experience against known qualia patterns.
        """
        best_match = None
        best_similarity = 0.0

        for name, qualia in self.qualia_patterns.items():
            similarity = np.dot(pattern, qualia) / (np.linalg.norm(pattern) * np.linalg.norm(qualia) + 1e-8)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = name

        if best_similarity > 0.7:
            return best_match

        return None


class IntegrationBuffer:
    """
    Integration Buffer - Combines information before workspace entry.
    Creates bound, unified conscious experiences.
    """
    def __init__(self, buffer_size: int = 128):
        self.buffer_size = buffer_size

        # Buffer components from different modules
        self.components: Dict[str, np.ndarray] = {}

        # Integration state
        self.integrated_content: Optional[np.ndarray] = None
        self.integration_complete = False
        self.binding_strength = 0.0

        # Binding mechanism
        self.binding_threshold = 0.5

    def add_component(self, module_id: str, content: np.ndarray):
        """Add component from a module to the buffer."""
        self.components[module_id] = content[:self.buffer_size]

        # Try integration
        self._integrate()

    def _integrate(self):
        """Integrate all components into unified experience."""
        if len(self.components) < 2:
            self.integration_complete = False
            return

        # Get max size and pad all to same size
        max_size = max(c.shape[0] for c in self.components.values())
        padded = []
        for c in self.components.values():
            if len(c) < max_size:
                padded.append(np.pad(c, (0, max_size - len(c))))
            else:
                padded.append(c[:max_size])

        # Stack and compute mean along axis 0
        stacked = np.stack(padded, axis=0)
        mean_compressed = np.mean(stacked, axis=0)

        # Compress to buffer size
        if len(mean_compressed) > self.buffer_size:
            self.integrated_content = mean_compressed[:self.buffer_size]
        else:
            self.integrated_content = np.pad(mean_compressed, (0, self.buffer_size - len(mean_compressed)))

        # Compute binding strength using padded components
        correlations = []
        for i, c1 in enumerate(padded):
            for c2 in padded[i+1:]:
                corr = np.dot(c1[:32], c2[:32]) / (32 * 32)
                correlations.append(abs(corr))

        self.binding_strength = np.mean(correlations) if correlations else 0.0
        self.integration_complete = self.binding_strength >= self.binding_threshold

    def get_integrated(self) -> Optional[np.ndarray]:
        """Get integrated content if ready."""
        if self.integration_complete:
            return self.integrated_content
        return None

    def clear(self):
        """Clear the buffer."""
        self.components.clear()
        self.integrated_content = None
        self.integration_complete = False
        self.binding_strength = 0.0


class AttentionBroadcast:
    """
    Attention Broadcast - Distributes conscious content to all systems.
    Implements Global Workspace Theory's broadcast mechanism.
    """
    def __init__(self):
        self.broadcast_recipients: List[str] = []
        self.broadcast_frequency = 0.1  # Hz (simplified)
        self.last_broadcast_time = None

        # Broadcast content
        self.last_broadcast_content: Optional[np.ndarray] = None

        # Reception tracking
        self.reception_history = deque(maxlen=50)

    def add_recipient(self, module_id: str):
        """Add module to broadcast recipients."""
        if module_id not in self.broadcast_recipients:
            self.broadcast_recipients.append(module_id)

    def broadcast(self, content: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Broadcast content to all recipients.
        Returns dict of recipient -> received signal.
        """
        self.last_broadcast_content = content
        self.last_broadcast_time = datetime.now()

        # Distribute to all recipients
        results = {}
        for recipient in self.broadcast_recipients:
            # Each recipient gets the content with some noise (different perspectives)
            noise = np.random.randn(len(content)) * 0.05
            received = content + noise
            results[recipient] = received

            # Track reception
            self.reception_history.append({
                "recipient": recipient,
                "content_hash": hash(str(content[:10].tolist())),
                "timestamp": datetime.now().isoformat()
            })

        return results

    def get_broadcast_summary(self) -> Dict:
        return {
            "recipients": self.broadcast_recipients,
            "last_broadcast": self.last_broadcast_time.isoformat() if self.last_broadcast_time else None,
            "recipients_count": len(self.broadcast_recipients),
            "reception_history_len": len(self.reception_history)
        }


class ConsciousnessGate:
    """
    Complete Consciousness Gate System.
    Integrates Global Workspace, Access, Phenomenal, and Attention Broadcast.
    Models the full spectrum of consciousness phenomena.
    """
    def __init__(self):
        # Core components
        self.workspace = GlobalWorkspace(workspace_size=128)
        self.access = AccessConsciousness()
        self.phenomenal = PhenomenalConsciousness()
        self.integration_buffer = IntegrationBuffer(buffer_size=128)
        self.broadcast = AttentionBroadcast()

        # State tracking
        self.current_state = ConsciousnessState(
            level=ConsciousnessLevel.SUBCONSCIOUS,
            arousal=0.5,
            content=None,
            attention_broadcast=False,
            integration_complete=False
        )

        # Initialize broadcast recipients
        self.broadcast.add_recipient("cortical")
        self.broadcast.add_recipient("limbic")
        self.broadcast.add_recipient("motor")
        self.broadcast.add_recipient("memory")

    def integrate_information(self, components: Dict[str, np.ndarray]) -> bool:
        """
        Integrate multiple information sources into unified experience.
        """
        # Add components to buffer
        for module_id, content in components.items():
            self.integration_buffer.add_component(module_id, content)

        # Get integrated content
        integrated = self.integration_buffer.get_integrated()
        if integrated is not None:
            # Add to workspace with salience based on binding strength
            salience = self.integration_buffer.binding_strength
            won = self.workspace.add_information(integrated, "integration", salience)

            if won:
                # Update access and phenomenal
                ws_content = self.workspace.current_content
                self.access.add_to_access(ws_content.information, ws_content.reportability)
                self.phenomenal.add_phenomenal_content(
                    ws_content.information, ws_content.phenomenal_experience
                )

                # Update state
                self.current_state.level = ConsciousnessLevel.CONSCIOUS
                self.current_state.content = ws_content
                self.current_state.integration_complete = True

            return won

        return False

    def process_content(self, content: np.ndarray, source: str,
                       salience: float = 0.5) -> bool:
        """
        Process new content through consciousness gate.
        """
        # Add to workspace competition
        won = self.workspace.add_information(content, source, salience)

        if won and self.workspace.current_content:
            # Update access and phenomenal
            ws_content = self.workspace.current_content
            self.access.add_to_access(ws_content.information, ws_content.reportability)
            self.phenomenal.add_phenomenal_content(
                ws_content.information, ws_content.phenomenal_experience
            )

            # Update state
            self.current_state.level = ConsciousnessLevel.CONSCIOUS
            self.current_state.content = ws_content
            self.current_state.attention_broadcast = self.workspace.broadcast_active

        return won

    def broadcast_conscious_content(self) -> Optional[Dict[str, np.ndarray]]:
        """
        Broadcast current conscious content to all recipients.
        """
        if self.current_state.content is None:
            return None

        content = self.workspace.broadcast()
        if content is not None:
            results = self.broadcast.broadcast(content)
            return results

        return None

    def become_meta_conscious(self, reflection_content: np.ndarray):
        """
        Achieve meta-consciousness (thinking about thinking).
        """
        # Add reflection as special content
        self.process_content(reflection_content, "meta_cognition", salience=0.8)
        self.current_state.level = ConsciousnessLevel.META_CONSCIOUS

    def lose_consciousness(self):
        """Transition to unconscious processing."""
        self.workspace.clear_workspace()
        self.current_state.level = ConsciousnessLevel.SUBCONSCIOUS
        self.current_state.content = None
        self.current_state.attention_broadcast = False

    def get_consciousness_level(self) -> ConsciousnessLevel:
        """Get current level of consciousness."""
        return self.current_state.level

    def get_reportability(self) -> float:
        """Get current reportability (access consciousness level)."""
        if self.current_state.content:
            return self.current_state.content.reportability
        return 0.0

    def get_system_state(self) -> Dict:
        """Get complete consciousness system state."""
        return {
            "level": self.current_state.level.value,
            "arousal": self.current_state.arousal,
            "workspace": {
                "has_content": self.workspace.current_content is not None,
                "access_level": self.workspace.access_level,
                "broadcast_active": self.workspace.broadcast_active
            },
            "access": self.access.get_access_summary(),
            "phenomenal": self.phenomenal.get_phenomenal_summary(),
            "integration": {
                "complete": self.integration_buffer.integration_complete,
                "binding_strength": self.integration_buffer.binding_strength,
                "components_count": len(self.integration_buffer.components)
            },
            "broadcast": self.broadcast.get_broadcast_summary()
        }

    def reset(self):
        """Reset consciousness state."""
        self.workspace.clear_workspace()
        self.integration_buffer.clear()
        self.current_state = ConsciousnessState(
            level=ConsciousnessLevel.SUBCONSCIOUS,
            arousal=0.5,
            content=None,
            attention_broadcast=False,
            integration_complete=False
        )


def create_consciousness_gate() -> ConsciousnessGate:
    """Factory function to create consciousness gate system."""
    return ConsciousnessGate()


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE Consciousness Gate - BRN-010 - Test")
    print("=" * 60)

    # Create gate
    gate = create_consciousness_gate()

    # Test 1: Basic content processing
    print("\n--- Test Content Processing ---")
    for source in ["visual", "limbic", "cognitive"]:
        content = np.random.randn(128)
        salience = np.random.uniform(0.4, 0.8)
        won = gate.process_content(content, source, salience)
        print(f"  {source} content: won={won}, level={gate.get_consciousness_level().value}")

    # Test 2: Information integration
    print("\n--- Test Information Integration ---")
    components = {
        "visual": np.random.randn(128),
        "auditory": np.random.randn(128),
        "memory": np.random.randn(64)
    }
    integrated = gate.integrate_information(components)
    print(f"  Integration: success={integrated}, binding={gate.integration_buffer.binding_strength:.2f}")

    # Test 3: Broadcast
    print("\n--- Test Broadcast ---")
    results = gate.broadcast_conscious_content()
    if results:
        print(f"  Broadcast to {len(results)} recipients")
        for recipient in list(results.keys())[:3]:
            print(f"    {recipient}: shape={results[recipient].shape}")
    else:
        print("  No content to broadcast")

    # Test 4: Meta-consciousness
    print("\n--- Test Meta-Consciousness ---")
    reflection = np.random.randn(128)
    gate.become_meta_conscious(reflection)
    print(f"  Meta-conscious level: {gate.get_consciousness_level().value}")
    print(f"  Reportability: {gate.get_reportability():.2f}")

    # Test 5: State tracking
    print("\n--- Test State Tracking ---")
    state = gate.get_system_state()
    print(f"  Consciousness level: {state['level']}")
    print(f"  Arousal: {state['arousal']}")
    print(f"  Workspace access: {state['workspace']['access_level']:.2f}")
    print(f"  Phenomenal subjectivity: {state['phenomenal']['subjectivity_strength']:.2f}")

    # Test 6: Lose and regain consciousness
    print("\n--- Test Consciousness Dynamics ---")
    gate.lose_consciousness()
    print(f"  After loss: level={gate.get_consciousness_level().value}")

    content = np.random.randn(128)
    gate.process_content(content, "new_input", salience=0.7)
    print(f"  After new input: level={gate.get_consciousness_level().value}")

    print("\n" + "=" * 60)
    print("Consciousness Gate: PASS")
    print("=" * 60)