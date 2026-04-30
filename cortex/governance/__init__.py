"""
cortex.governance
==================
M14.4 — Governance autonoma di SPEACE.

Espone:
  NeuralParliament  — voto ponderato su proposte (LOW risk auto-approve)
  Delegate          — membro del parlamento con ruolo e peso
  VoteResult        — risultato della delibera
  DelegateVote      — voto singolo delegate
  VoteChoice        — APPROVE / REJECT / ABSTAIN
  ParliamentStatus  — APPROVED / ESCALATED / REJECTED / QUORUM_FAILED
  RiskLevel         — LOW / MEDIUM / HIGH
  DEFAULT_DELEGATES — 5 delegate predefiniti
  CONSENSUS_THRESHOLD_LOW — soglia default 0.80
"""

from .neural_parliament import (
    NeuralParliament,
    Delegate,
    VoteResult,
    DelegateVote,
    VoteChoice,
    ParliamentStatus,
    RiskLevel,
    DEFAULT_DELEGATES,
    CONSENSUS_THRESHOLD_LOW,
    CONSENSUS_THRESHOLD_MEDIUM,
    MIN_QUORUM,
)

__all__ = [
    "NeuralParliament",
    "Delegate",
    "VoteResult",
    "DelegateVote",
    "VoteChoice",
    "ParliamentStatus",
    "RiskLevel",
    "DEFAULT_DELEGATES",
    "CONSENSUS_THRESHOLD_LOW",
    "CONSENSUS_THRESHOLD_MEDIUM",
    "MIN_QUORUM",
]
