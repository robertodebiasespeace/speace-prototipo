"""
cortex.governance.neural_parliament
=====================================
M14.4 — NeuralParliament: governance autonoma con voto ponderato.

Funzionamento:
  - 5 delegate con ruoli e pesi diversi votano su ogni proposta.
  - Consensus score = somma pesi favorevoli / somma pesi totali.
  - Risk Level LOW  + consensus >= threshold → AUTO-APPROVE.
  - Risk Level LOW  + consensus <  threshold → ESCALATE TO HUMAN.
  - Risk Level MEDIUM/HIGH                  → SEMPRE escalate.
  - Voto determinato da regole euristiche sul campo della proposta
    (no Ollama richiesto — funziona offline).

Integrazione SafeProactive:
  - vote_on_proposal(proposal_dict) → VoteResult con status APPROVED/ESCALATED.
  - Proposta compatibile con formato propose_best() di EvolutionaryAlgorithm.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Costanti ─────────────────────────────────────────────────────────────────

CONSENSUS_THRESHOLD_LOW    = 0.80   # auto-approve LOW se consenso >= 80%
CONSENSUS_THRESHOLD_MEDIUM = 0.90   # auto-approve MEDIUM (mai raggiunto automaticamente)
MIN_QUORUM                 = 3      # minimo delegate che devono votare


class RiskLevel(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


class VoteChoice(str, Enum):
    APPROVE = "APPROVE"
    REJECT  = "REJECT"
    ABSTAIN = "ABSTAIN"


class ParliamentStatus(str, Enum):
    APPROVED        = "APPROVED"
    REJECTED        = "REJECTED"
    ESCALATED       = "ESCALATED"   # consensus < threshold → human review
    QUORUM_FAILED   = "QUORUM_FAILED"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class Delegate:
    """Membro del parlamento con ruolo e peso di voto."""
    name: str
    role: str
    weight: float            # 0.0 – 1.0 (normalizzato esternamente)
    description: str = ""


@dataclass
class DelegateVote:
    delegate: Delegate
    choice: VoteChoice
    rationale: str = ""
    confidence: float = 1.0  # 0.0 – 1.0


@dataclass
class VoteResult:
    proposal_id: str
    status: ParliamentStatus
    consensus_score: float          # 0.0 – 1.0
    votes: List[DelegateVote]
    risk_level: RiskLevel
    threshold_used: float
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id":    self.proposal_id,
            "status":         self.status.value,
            "consensus_score": round(self.consensus_score, 4),
            "risk_level":     self.risk_level.value,
            "threshold_used": self.threshold_used,
            "timestamp":      self.timestamp,
            "notes":          self.notes,
            "votes": [
                {
                    "delegate": v.delegate.name,
                    "role":     v.delegate.role,
                    "weight":   v.delegate.weight,
                    "choice":   v.choice.value,
                    "rationale": v.rationale,
                    "confidence": v.confidence,
                }
                for v in self.votes
            ],
        }


# ── Delegate predefiniti ──────────────────────────────────────────────────────

DEFAULT_DELEGATES: List[Delegate] = [
    Delegate("SafetyGuard",   "safety",     0.30, "Valuta rischi etici e di sicurezza"),
    Delegate("EvolutionVoice","evolution",  0.25, "Valuta potenziale evolutivo"),
    Delegate("Critic",        "critic",     0.20, "Verifica coerenza e robustezza"),
    Delegate("Executor",      "executor",   0.15, "Valuta fattibilità tecnica"),
    Delegate("Ethicist",      "ethics",     0.10, "Allineamento con valori Rigene Project"),
]


# ── NeuralParliament ──────────────────────────────────────────────────────────

class NeuralParliament:
    """
    Governance autonoma per micro-decisioni di SPEACE.

    Flusso principale:
      result = parliament.vote_on_proposal(proposal)
      if result.status == ParliamentStatus.APPROVED:
          # esegui autonomamente
      elif result.status == ParliamentStatus.ESCALATED:
          # richiedi approvazione umana (SafeProactive)
    """

    def __init__(
        self,
        delegates: Optional[List[Delegate]] = None,
        consensus_threshold_low: float = CONSENSUS_THRESHOLD_LOW,
        consensus_threshold_medium: float = CONSENSUS_THRESHOLD_MEDIUM,
        min_quorum: int = MIN_QUORUM,
    ):
        self.delegates = delegates or list(DEFAULT_DELEGATES)
        self._normalize_weights()
        self.consensus_threshold_low    = consensus_threshold_low
        self.consensus_threshold_medium = consensus_threshold_medium
        self.min_quorum                 = min_quorum
        self.vote_history: List[VoteResult] = []

    # ── Normalizzazione pesi ─────────────────────────────────────────────────

    def _normalize_weights(self) -> None:
        total = sum(d.weight for d in self.delegates)
        if total > 0:
            for d in self.delegates:
                d.weight = d.weight / total

    # ── Voto principale ──────────────────────────────────────────────────────

    def vote_on_proposal(self, proposal: Dict[str, Any]) -> VoteResult:
        """
        Vota su una proposta SafeProactive-compatible.

        proposal deve contenere almeno:
          - 'id' o 'proposal_id'
          - 'risk_level': "LOW" / "MEDIUM" / "HIGH"
          - Qualsiasi campo descrittivo (best_genome, description, ecc.)

        Ritorna VoteResult con status APPROVED / ESCALATED / REJECTED.
        """
        prop_id    = proposal.get("id") or proposal.get("proposal_id", "UNKNOWN")
        risk_str   = str(proposal.get("risk_level", "LOW")).upper()
        try:
            risk = RiskLevel(risk_str)
        except ValueError:
            risk = RiskLevel.LOW

        # MEDIUM / HIGH → sempre escalate senza delibera
        if risk in (RiskLevel.MEDIUM, RiskLevel.HIGH):
            result = VoteResult(
                proposal_id    = prop_id,
                status         = ParliamentStatus.ESCALATED,
                consensus_score= 0.0,
                votes          = [],
                risk_level     = risk,
                threshold_used = self.consensus_threshold_medium,
                notes          = f"Risk Level {risk.value} → escalation automatica a revisione umana.",
            )
            self.vote_history.append(result)
            logger.info(f"[Parliament] {prop_id} ESCALATED (risk={risk.value})")
            return result

        # LOW → delibera con voto ponderato
        votes = [self._delegate_vote(d, proposal) for d in self.delegates]
        consensus = self._compute_consensus(votes)

        # Quorum check
        actual_voters = sum(1 for v in votes if v.choice != VoteChoice.ABSTAIN)
        if actual_voters < self.min_quorum:
            status = ParliamentStatus.QUORUM_FAILED
            notes  = f"Quorum non raggiunto: {actual_voters}/{self.min_quorum} delegate hanno votato."
        elif consensus >= self.consensus_threshold_low:
            status = ParliamentStatus.APPROVED
            notes  = f"Consensus {consensus:.1%} >= soglia {self.consensus_threshold_low:.0%} → AUTO-APPROVE."
        else:
            status = ParliamentStatus.ESCALATED
            notes  = f"Consensus {consensus:.1%} < soglia {self.consensus_threshold_low:.0%} → escalation umana."

        result = VoteResult(
            proposal_id    = prop_id,
            status         = status,
            consensus_score= consensus,
            votes          = votes,
            risk_level     = risk,
            threshold_used = self.consensus_threshold_low,
            notes          = notes,
        )
        self.vote_history.append(result)
        logger.info(f"[Parliament] {prop_id} {status.value} (consensus={consensus:.1%})")
        return result

    # ── Logica di voto per singolo delegate ──────────────────────────────────

    def _delegate_vote(self, delegate: Delegate, proposal: Dict[str, Any]) -> DelegateVote:
        """
        Voto euristico basato sul ruolo del delegate e sui campi della proposta.
        Non richiede Ollama — opera offline su regole deterministiche.
        """
        role   = delegate.role
        choice = VoteChoice.APPROVE
        rationale = ""
        confidence = 0.9

        # ── SafetyGuard: approva se nessun campo di rischio elevato ─────────
        if role == "safety":
            unsafe_keywords = ["HIGH", "CRITICAL", "DANGER", "UNSAFE", "EXPLOIT"]
            desc = str(proposal.get("description", "")) + str(proposal.get("notes", ""))
            if any(kw in desc.upper() for kw in unsafe_keywords):
                choice    = VoteChoice.REJECT
                rationale = "Rilevati segnali di rischio elevato nella descrizione."
                confidence = 0.85
            else:
                rationale = "Nessun segnale di rischio elevato rilevato."
                confidence = 0.90

        # ── EvolutionVoice: approva se c'è fitness o improvement ─────────────
        elif role == "evolution":
            fitness = proposal.get("best_fitness") or proposal.get("fitness_score") or 0.0
            if isinstance(fitness, (int, float)) and fitness >= 0.5:
                rationale  = f"Fitness {fitness:.3f} ≥ 0.5 → potenziale evolutivo positivo."
                confidence = min(1.0, fitness)
            else:
                choice     = VoteChoice.ABSTAIN
                rationale  = f"Fitness {fitness} insufficiente o non disponibile."
                confidence = 0.5

        # ── Critic: approva se ha id e descrizione non vuoti ─────────────────
        elif role == "critic":
            has_id   = bool(proposal.get("id") or proposal.get("proposal_id"))
            has_desc = bool(proposal.get("description") or proposal.get("genome_update"))
            if has_id and has_desc:
                rationale  = "Struttura proposta coerente (id + descrizione presenti)."
                confidence = 0.85
            else:
                choice     = VoteChoice.REJECT
                rationale  = "Proposta malformata: mancano id o descrizione."
                confidence = 0.80

        # ── Executor: approva se c'è un genome_update o azione concreta ──────
        elif role == "executor":
            has_action = bool(
                proposal.get("genome_update") or
                proposal.get("action") or
                proposal.get("file_target") or
                proposal.get("best_genome")
            )
            if has_action:
                rationale  = "Azione concreta definita nella proposta."
                confidence = 0.88
            else:
                choice     = VoteChoice.ABSTAIN
                rationale  = "Nessuna azione esplicita trovata nella proposta."
                confidence = 0.6

        # ── Ethicist: approva se allineata a valori Rigene / TINA ────────────
        elif role == "ethics":
            ethical_terms = [
                "alignment", "ethical", "tina", "rigene", "harmony",
                "sustainability", "peace", "evolution", "safe"
            ]
            all_text = " ".join(str(v) for v in proposal.values()).lower()
            hits = sum(1 for t in ethical_terms if t in all_text)
            if hits >= 1:
                rationale  = f"Trovati {hits} indicatori etici positivi nel testo."
                confidence = min(1.0, 0.70 + hits * 0.05)
            else:
                choice     = VoteChoice.ABSTAIN
                rationale  = "Nessun indicatore etico rilevato."
                confidence = 0.5

        return DelegateVote(
            delegate   = delegate,
            choice     = choice,
            rationale  = rationale,
            confidence = confidence,
        )

    # ── Calcolo consensus ────────────────────────────────────────────────────

    def _compute_consensus(self, votes: List[DelegateVote]) -> float:
        """
        Consensus = somma(peso * confidence) degli APPROVE
                  / somma(peso) dei votanti (esclusi ABSTAIN).
        """
        weight_approve = sum(
            v.delegate.weight * v.confidence
            for v in votes if v.choice == VoteChoice.APPROVE
        )
        weight_total = sum(
            v.delegate.weight
            for v in votes if v.choice != VoteChoice.ABSTAIN
        )
        return weight_approve / weight_total if weight_total > 0 else 0.0

    # ── Statistiche ──────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        total    = len(self.vote_history)
        approved = sum(1 for r in self.vote_history if r.status == ParliamentStatus.APPROVED)
        escalated= sum(1 for r in self.vote_history if r.status == ParliamentStatus.ESCALATED)
        rejected = sum(1 for r in self.vote_history if r.status == ParliamentStatus.REJECTED)
        avg_cons = (
            sum(r.consensus_score for r in self.vote_history) / total
            if total > 0 else 0.0
        )
        return {
            "delegates":           len(self.delegates),
            "total_votes":         total,
            "approved":            approved,
            "escalated":           escalated,
            "rejected":            rejected,
            "avg_consensus":       round(avg_cons, 4),
            "threshold_low":       self.consensus_threshold_low,
            "min_quorum":          self.min_quorum,
        }

    def format_result_markdown(self, result: VoteResult) -> str:
        """Formatta VoteResult per PROPOSALS.md / log."""
        lines = [
            f"## Parliament Vote — {result.proposal_id}",
            f"- **Timestamp:** {result.timestamp}",
            f"- **Risk Level:** {result.risk_level.value}",
            f"- **Consensus:** {result.consensus_score:.1%}",
            f"- **Status:** {result.status.value}",
            f"- **Notes:** {result.notes}",
            "",
            "| Delegate | Role | Weight | Vote | Confidence | Rationale |",
            "|----------|------|--------|------|------------|-----------|",
        ]
        for v in result.votes:
            lines.append(
                f"| {v.delegate.name} | {v.delegate.role} | "
                f"{v.delegate.weight:.2f} | {v.choice.value} | "
                f"{v.confidence:.2f} | {v.rationale} |"
            )
        return "\n".join(lines)
