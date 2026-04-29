"""
cortex.cognitive_autonomy.executive
=====================================
M7.0 — DriveExecutive: ponte causale Drive → Comportamento.

Componenti:
  DriveExecutive  — legge drive omeostatici → produce BehavioralState
  TaskSelector    — usa BehavioralState per filtrare/prioritizzare task
  SelfRepairTrigger — attiva modalità riparazione quando viability < 0.4

EPI-008: cognitive_autonomy.executive.enabled = true (attivato al completamento M7.0)
"""

from .drive_executive import DriveExecutive, BehavioralState, DriveSnapshot
from .task_selector import TaskSelector, Task, TaskPriority
from .self_repair import SelfRepairTrigger, RepairAction

__all__ = [
    "DriveExecutive",
    "BehavioralState",
    "DriveSnapshot",
    "TaskSelector",
    "Task",
    "TaskPriority",
    "SelfRepairTrigger",
    "RepairAction",
]
