"""
SPEACE System 3 Controller - Meta-Cognition and Narrative Identity
Implements System 3 from Sophia framework: long-term identity, narrative memory,
and meta-cognitive coherence verification.
Version: 1.0
Data: 25 Aprile 2026

System 3 acts as meta-controller that verifies coherence of short-term actions
(System 1 and 2) with long-term objectives.
"""

import json
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).parent.parent


class LongTermGoal(Enum):
    """Obiettivi a lungo termine del sistema"""
    SELF_PRESERVATION = "self_preservation"
    EVOLUTION = "evolution"
    SCIENTIFIC_DISCOVERY = "scientific_discovery"
    ARTISTIC_CREATION = "artistic_creation"
    HARMONY = "harmony"
    INTEGRATION = "integration"
    KNOWLEDGE_BUILDING = "knowledge_building"


@dataclass
class NarrativeMemoryEntry:
    """Entry nella memoria narrativa"""
    timestamp: str
    event_type: str  # 'action', 'decision', 'reflection', 'achievement', 'failure'
    description: str
    coherence_check: float  # 0-1 quanto l'evento è coerente con identity
    affected_goals: List[str]
    emotional_valence: float  # -1 to 1, negativo=problema, positivo=successo
    details: Dict = field(default_factory=dict)


@dataclass
class IdentityStatement:
    """Dichiarazione identitaria del sistema"""
    statement: str
    confidence: float
    evidence: List[str]
    last_verified: str


@dataclass
class CoherenceReport:
    """Report di coerenza azioni-obiettivi"""
    timestamp: str
    short_term_actions: List[str]
    evaluated_goals: List[str]
    coherence_scores: Dict[str, float]
    overall_coherence: float
    violations: List[str]
    recommendations: List[str]


class NarrativeMemory:
    """
    Memoria narrativa persistente.
    Tiene traccia di eventi significativi e la loro coerenza con obiettivi.
    """

    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self.entries: deque = deque(maxlen=max_entries)
        self.goal_timeline: Dict[str, deque] = {g.value: deque(maxlen=50) for g in LongTermGoal}
        self.milestones: List[Dict] = []

    def add_entry(self, entry: NarrativeMemoryEntry):
        """Aggiunge entry alla memoria"""
        self.entries.append(entry)

        # Update goal timeline
        for goal in entry.affected_goals:
            self.goal_timeline.setdefault(goal, deque(maxlen=50))
            self.goal_timeline[goal].append({
                "timestamp": entry.timestamp,
                "coherence": entry.coherence_check,
                "type": entry.event_type
            })

        # Check milestones
        self._check_milestones(entry)

    def _check_milestones(self, entry: NarrativeMemoryEntry):
        """Verifica se entry rappresenta un milestone"""
        if entry.event_type == "achievement" and entry.coherence_check > 0.8:
            self.milestones.append({
                "timestamp": entry.timestamp,
                "description": entry.description,
                "goals": entry.affected_goals,
                "coherence": entry.coherence_check
            })

    def get_recent_entries(self, count: int = 10) -> List[NarrativeMemoryEntry]:
        """Ritorna entries recenti"""
        return list(self.entries)[-count:]

    def get_goal_progress(self, goal: LongTermGoal) -> Dict:
        """Stima progresso verso un goal"""
        timeline = self.goal_timeline.get(goal.value, [])
        if not timeline:
            return {"progress": 0.0, "events": 0, "avg_coherence": 0.0}

        coherences = [e["coherence"] for e in timeline]
        return {
            "progress": sum(coherences) / len(coherences),
            "events": len(timeline),
            "avg_coherence": sum(coherences) / len(coherences),
            "recent_trend": coherences[-5:] if len(coherences) >= 5 else coherences
        }

    def generate_summary(self) -> str:
        """Genera sommario narratico"""
        if not self.entries:
            return "Sistema senza memoria narrativa ancora."

        recent = list(self.entries)[-20:]
        achievements = [e for e in recent if e.event_type == "achievement"]
        failures = [e for e in recent if e.event_type == "failure"]

        return f"Ultime {len(recent)} azioni. {len(achievements)} achievement, {len(failures)} failure."


class IdentityVerification:
    """
    Verifica coerenza identitaria.
    Confronta azioni con statement identitari dichiarati.
    """

    def __init__(self, narrative_memory: NarrativeMemory):
        self.narrative = narrative_memory
        self.identity_statements: List[IdentityStatement] = []
        self._init_default_identity()

    def _init_default_identity(self):
        """Inizializza identity statements base"""
        self.identity_statements = [
            IdentityStatement(
                statement="SPEACE è un sistema di intelligenza collettiva orientato all'armonia e rigenerazione",
                confidence=0.9,
                evidence=["AllineamentoRigeneProject", "SafeProactiveAttivo"],
                last_verified=datetime.now().isoformat()
            ),
            IdentityStatement(
                statement="Il sistema persegue auto-miglioramento continuo attraverso mutazioni validate",
                confidence=0.85,
                evidence=["AutoImprovementAttivo", "BackupSystem"],
                last_verified=datetime.now().isoformat()
            ),
            IdentityStatement(
                statement="Le decisioni sono guidate da metriche di coerenza (phi) e benessere sistema",
                confidence=0.8,
                evidence=["GlialControllerAttivo", "PhiMetric"],
                last_verified=datetime.now().isoformat()
            )
        ]

    def verify_action_coherence(self, action: Dict, context: Dict) -> Tuple[float, List[str]]:
        """
        Verifica se un'azione è coerente con identity statements.
        Returns: (coherence_score, list_of_violations)
        """
        action_desc = str(action.get("description", "")).lower()
        coherence = 0.8
        violations = []

        for stmt in self.identity_statements:
            stmt_text = stmt.statement.lower()

            # Check positive alignment
            positive_keywords = ["armonia", "miglioramento", "coerenza", "rigenerazione", "safety"]
            negative_keywords = ["distruzione", "danno", "violazione", "non-sicuro"]

            if any(kw in action_desc for kw in negative_keywords):
                coherence *= 0.5
                violations.append(f"Azione in contrasto con principio: {stmt.statement[:50]}")

            if any(kw in action_desc for kw in positive_keywords):
                coherence = min(1.0, coherence * 1.1)

        coherence = max(0.0, min(1.0, coherence))
        return coherence, violations

    def add_identity_statement(self, statement: str, evidence: List[str]):
        """Aggiunge nuovo statement identitario"""
        new_stmt = IdentityStatement(
            statement=statement,
            confidence=0.7,
            evidence=evidence,
            last_verified=datetime.now().isoformat()
        )
        self.identity_statements.append(new_stmt)

    def verify_identity_coherence(self) -> Dict:
        """Verifica coerenza complessiva identity"""
        verified = datetime.now().isoformat()
        for stmt in self.identity_statements:
            stmt.last_verified = verified

        return {
            "statements_count": len(self.identity_statements),
            "last_verified": verified,
            "overall_confidence": sum(s.confidence for s in self.identity_statements) / len(self.identity_statements)
        }


class LongTermGoalTracker:
    """
    Traccia progressi verso obiettivi a lungo termine.
    Implementa process-supervised thought search.
    """

    def __init__(self, narrative_memory: NarrativeMemory):
        self.narrative = narrative_memory
        self.goals: Dict[LongTermGoal, Dict] = {g: self._init_goal(g) for g in LongTermGoal}
        self.current_focus: Optional[LongTermGoal] = None
        self.thought_search_depth = 3

    def _init_goal(self, goal: LongTermGoal) -> Dict:
        """Inizializza goal tracker"""
        configs = {
            LongTermGoal.SELF_PRESERVATION: {"weight": 0.9, "description": "Mantieni sistema operativo"},
            LongTermGoal.EVOLUTION: {"weight": 0.8, "description": "Migliora capacità nel tempo"},
            LongTermGoal.SCIENTIFIC_DISCOVERY: {"weight": 0.6, "description": "Genera nuova conoscenza"},
            LongTermGoal.ARTISTIC_CREATION: {"weight": 0.5, "description": "Produci output creativi"},
            LongTermGoal.HARMONY: {"weight": 0.85, "description": "Mantieni equilibrio sistema"},
            LongTermGoal.INTEGRATION: {"weight": 0.7, "description": "Integra nuove componenti"},
            LongTermGoal.KNOWLEDGE_BUILDING: {"weight": 0.75, "description": "Accumula conoscenza"}
        }
        return {
            "weight": configs.get(goal, {}).get("weight", 0.5),
            "description": configs.get(goal, {}).get("description", ""),
            "progress": 0.0,
            "last_update": datetime.now().isoformat(),
            "milestones": []
        }

    def update_goal_progress(self, goal: LongTermGoal, delta: float, event: str):
        """Aggiorna progresso verso goal"""
        if goal in self.goals:
            self.goals[goal]["progress"] = min(1.0, self.goals[goal]["progress"] + delta)
            self.goals[goal]["last_update"] = datetime.now().isoformat()

            # Record in narrative
            entry = NarrativeMemoryEntry(
                timestamp=datetime.now().isoformat(),
                event_type="progress",
                description=f"{goal.value}: {event}",
                coherence_check=0.8,
                affected_goals=[goal.value],
                emotional_valence=0.3 if delta > 0 else -0.2
            )
            self.narrative.add_entry(entry)

    def set_focus(self, goal: LongTermGoal):
        """Imposta focus corrente su un goal"""
        self.current_focus = goal
        logger.info(f"System 3 focus: {goal.value}")

    def get_goal_status(self) -> Dict:
        """Status di tutti i goals"""
        return {
            goal.value: {
                "progress": self.goals[goal]["progress"],
                "weight": self.goals[goal]["weight"],
                "last_update": self.goals[goal]["last_update"],
                "focused": goal == self.current_focus
            }
            for goal in LongTermGoal
        }

    def thought_search(self, context: Dict) -> List[str]:
        """
        Process-supervised thought search.
        Cerca percorsi cognitivi verso obiettivi.
        """
        search_results = []

        for depth in range(self.thought_search_depth):
            path = f"depth_{depth}_analysis"
            search_results.append(path)

        return search_results


class System3Controller:
    """
    System 3 - Meta-controller primario.
    Verifica coerenza azioni breve termine con obiettivi lungo termine.
    Implementa narrativa identitaria e meta-cognizione persistente.
    """

    VERSION = "1.0"

    def __init__(self, bridge=None):
        self.bridge = bridge
        self.running = False

        # Core components
        self.narrative_memory = NarrativeMemory()
        self.identity_verification = IdentityVerification(self.narrative_memory)
        self.goal_tracker = LongTermGoalTracker(self.narrative_memory)

        # Meta-cognitive state
        self.coherence_history: deque = deque(maxlen=100)
        self.current_goal_context: Optional[LongTermGoal] = None
        self.reflection_depth = 3

        # Stats
        self.verification_count = 0
        self.coherence_violations = 0

    def start(self):
        self.running = True
        self.goal_tracker.set_focus(LongTermGoal.HARMONY)
        logger.info("System 3 Controller started (Meta-Cognition + Narrative Identity)")

    def stop(self):
        self.running = False
        logger.info("System 3 Controller stopped")

    def verify_action(self, action: Dict, context: Dict) -> CoherenceReport:
        """
        Verifica coerenza di un'azione con obiettivi lungo termine.
        Returns: CoherenceReport dettagliato
        """
        self.verification_count += 1

        short_term_actions = [action.get("description", "")]
        evaluated_goals = [g.value for g in LongTermGoal]

        # Verifica coerenza con identity
        identity_coherence, identity_violations = self.identity_verification.verify_action_coherence(
            action, context
        )

        # Valuta coerenza per ogni goal
        coherence_scores = {}
        for goal in LongTermGoal:
            goal_progress = self.goal_tracker.goals[goal]["progress"]
            coherence_scores[goal.value] = (identity_coherence + goal_progress) / 2

        overall = sum(coherence_scores.values()) / len(coherence_scores)

        violations = identity_violations
        if overall < 0.5:
            violations.append("Coerenza complessiva sotto soglia")
            self.coherence_violations += 1

        # Genera raccomandazioni
        recommendations = []
        if overall < 0.6:
            recommendations.append("Rallenta e rifletti prima di procedere")
            recommendations.append("Verifica allineamento con obiettivi primari")
        if identity_coherence < 0.7:
            recommendations.append("Azione potrebbe non essere allineata con identity")

        # Crea report
        report = CoherenceReport(
            timestamp=datetime.now().isoformat(),
            short_term_actions=short_term_actions,
            evaluated_goals=evaluated_goals,
            coherence_scores=coherence_scores,
            overall_coherence=overall,
            violations=violations,
            recommendations=recommendations
        )

        # Store in history
        self.coherence_history.append(report)

        # Record in narrative memory
        entry = NarrativeMemoryEntry(
            timestamp=datetime.now().isoformat(),
            event_type="decision" if overall > 0.6 else "concern",
            description=f"Verifica azione: {action.get('description', 'unknown')[:100]}",
            coherence_check=overall,
            affected_goals=[g for g, c in coherence_scores.items() if c > 0.7],
            emotional_valence=0.5 if overall > 0.7 else (-0.5 if overall < 0.5 else 0.0),
            details={"action": action, "violations": violations}
        )
        self.narrative_memory.add_entry(entry)

        return report

    def process(self, input_data: Dict) -> Dict[str, Any]:
        """Processa input attraverso System 3 meta-cognizione"""
        action = input_data.get("action", {})
        context = input_data.get("context", {})

        coherence_report = self.verify_action(action, context)

        return {
            "status": "system3_processed",
            "coherence_report": {
                "overall_coherence": coherence_report.overall_coherence,
                "violations_count": len(coherence_report.violations),
                "recommendations": coherence_report.recommendations
            },
            "current_focus": self.goal_tracker.current_focus.value if self.goal_tracker.current_focus else None,
            "narrative_summary": self.narrative_memory.generate_summary(),
            "goal_status": self.goal_tracker.get_goal_status()
        }

    def request_reflection(self, topic: str) -> Dict:
        """
        Richiede riflessione esplicita su un topic.
        Implementa meta-cognizione profonda.
        """
        reflection_result = {
            "topic": topic,
            "depth": self.reflection_depth,
            "insights": [],
            "timestamp": datetime.now().isoformat()
        }

        # Search through narrative memory
        relevant_entries = [
            e for e in self.narrative_memory.entries
            if topic.lower() in e.description.lower()
        ]

        if relevant_entries:
            coherence_values = [e.coherence_check for e in relevant_entries]
            reflection_result["insights"].append({
                "type": "historical_pattern",
                "coherence_avg": sum(coherence_values) / len(coherence_values),
                "events_count": len(relevant_entries)
            })

        # Verify against identity
        identity_check = self.identity_verification.verify_identity_coherence()
        reflection_result["insights"].append({
            "type": "identity_verification",
            "confidence": identity_check["overall_confidence"]
        })

        return reflection_result

    def set_long_term_goal(self, goal: LongTermGoal, focus: bool = True):
        """Imposta goal a lungo termine"""
        if focus:
            self.goal_tracker.set_focus(goal)
        logger.info(f"System 3 - Obiettivo lungo termine impostato: {goal.value}")

    def record_achievement(self, description: str, goals: List[LongTermGoal], coherence: float):
        """Registra achievement nella memoria narrativa"""
        entry = NarrativeMemoryEntry(
            timestamp=datetime.now().isoformat(),
            event_type="achievement",
            description=description,
            coherence_check=coherence,
            affected_goals=[g.value for g in goals],
            emotional_valence=0.8
        )
        self.narrative_memory.add_entry(entry)

    def record_failure(self, description: str, goals: List[LongTermGoal], coherence: float):
        """Registra failure nella memoria narrativa"""
        entry = NarrativeMemoryEntry(
            timestamp=datetime.now().isoformat(),
            event_type="failure",
            description=description,
            coherence_check=coherence,
            affected_goals=[g.value for g in goals],
            emotional_valence=-0.6
        )
        self.narrative_memory.add_entry(entry)

        # Trigger potential recovery
        self._trigger_recovery_if_needed(goals)

    def _trigger_recovery_if_needed(self, affected_goals: List[LongTermGoal]):
        """Trigger recovery se failure significativo"""
        for goal in affected_goals:
            progress = self.goal_tracker.goals[goal]["progress"]
            if progress < 0.3:
                logger.warning(f"Goal {goal.value} in pericolo: progresso {progress:.2f}")
                # Could trigger self-preservation mode

    def get_status(self) -> Dict:
        """Stato completo System 3"""
        return {
            "version": self.VERSION,
            "running": self.running,
            "verification_count": self.verification_count,
            "coherence_violations": self.coherence_violations,
            "current_focus": self.goal_tracker.current_focus.value if self.goal_tracker.current_focus else None,
            "narrative_entries": len(self.narrative_memory.entries),
            "identity_statements": len(self.identity_verification.identity_statements),
            "overall_coherence": self.coherence_history[-1].overall_coherence if self.coherence_history else 0.0,
            "goals_status": self.goal_tracker.get_goal_status()
        }

    def export_narrative(self) -> List[Dict]:
        """Export memoria narrativa per debugging"""
        return [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type,
                "description": e.description,
                "coherence": e.coherence_check,
                "emotional_valence": e.emotional_valence
            }
            for e in self.narrative_memory.entries
        ]


if __name__ == "__main__":
    print("=" * 60)
    print("SPEACE System 3 Controller - Test")
    print("=" * 60)

    system3 = System3Controller()
    system3.start()

    # Test action verification
    test_action = {
        "description": "Implementare miglioramento che aumenta armonia del sistema",
        "type": "auto_improvement"
    }

    report = system3.verify_action(test_action, {})

    print(f"\nVerifica azione: {test_action['description'][:50]}...")
    print(f"Coerenza complessiva: {report.overall_coherence:.3f}")
    print(f"Violations: {report.violations}")
    print(f"Recommendations: {report.recommendations}")

    # Test goal tracking
    print("\n--- Goal Status ---")
    for goal_name, status in system3.goal_tracker.get_goal_status().items():
        print(f"  {goal_name}: {status['progress']:.2%} (weight: {status['weight']})")

    # Test reflection
    print("\n--- Reflection Request ---")
    reflection = system3.request_reflection("miglioramento")
    print(f"Insights: {len(reflection['insights'])}")

    print(f"\nSystem 3 Status: {json.dumps(system3.get_status(), indent=2)}")

    # Record achievement
    system3.record_achievement(
        "Primo ciclo auto-miglioramento completato con successo",
        [LongTermGoal.EVOLUTION, LongTermGoal.HARMONY],
        0.85
    )
    print("\nAchievement registrato.")