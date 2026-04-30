"""
cortex.cognitive_autonomy.swarm
================================
M8 — Swarm Agentic Layer: 10° comparto SPEACE Cortex.

Risolve EM-03: PFC integra feedback cross-modulo (loop riflessivo).

Componenti:
  NeuronBase        — classe base per tutti i neuroni Ollama
  PlannerNeuron     — decomposizione task e pianificazione
  CriticNeuron      — validazione output e anti-groupthink
  ExecutorNeuron    — esecuzione step-by-step di subtask
  ResearcherNeuron  — ricerca info e arricchimento WorldModel
  SwarmOrchestrator — pipeline Researcher→Planner→Executor→Critic

EPI-010: cognitive_autonomy.swarm.enabled = true
"""

from .neuron_base  import NeuronBase, NeuronResult
from .planner      import PlannerNeuron
from .critic       import CriticNeuron
from .executor     import ExecutorNeuron
from .researcher   import ResearcherNeuron
from .orchestrator import SwarmOrchestrator, SwarmResult

__all__ = [
    "NeuronBase",
    "NeuronResult",
    "PlannerNeuron",
    "CriticNeuron",
    "ExecutorNeuron",
    "ResearcherNeuron",
    "SwarmOrchestrator",
    "SwarmResult",
]
