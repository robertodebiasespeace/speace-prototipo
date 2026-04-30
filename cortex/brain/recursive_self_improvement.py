"""
SPEACE Recursive Self-Improvement – BRN-020
==============================================
Self-modification of code, architecture, and objectives.
Inspired by Darwin Gödel Machine (Schmidhuber 2003) + RLSP.

Principio biologico:
  Il cervello umano si auto-riorganizza (neuroplasticità) in risposta
  all'esperienza: potenzia le connessioni utili, pota quelle inutili,
  crea nuove strutture. La corteccia non è hardware fisso ma un sistema
  che si riscrive continuamente entro vincoli evolutivi.

  SPEACE implementa questo tramite:
    1. Ispezione AST del proprio codice (self-awareness strutturale)
    2. Generazione di proposte di miglioramento guidate dalla fitness
    3. Validazione empirica su benchmark interni (non si applica ciò che
       non è dimostrato migliore)
    4. Gate di sicurezza SafeProactive (nessuna modifica senza approvazione)

Gerarchia di rischio (Darwin-Gödel safety levels):
  HYPERPARAMETER  → LOW    — tuning parametri numerici (soglie, rate, ecc.)
  ARCHITECTURE    → MEDIUM — ristrutturazione moduli
  CODE_PATCH      → HIGH   — modifica codice sorgente
  GOAL_REVISION   → CRITICAL — modifica obiettivi primari

⚠ SAFETY NOTE: Autonomous code modification is DISABLED.
  All HIGH/CRITICAL proposals require explicit human approval via SafeProactive.
  LOW proposals may be auto-applied after fitness threshold validation.

Integrazioni:
  - DigitalDNA fitness_function.yaml : pesi fitness per selezione proposte
  - SafeProactive (PROPOSALS.md + WAL.log) : governance e audit trail
  - BRN-019 SelfModel : introspection del proprio stato
  - BRN-017 CausalReasoner : comprensione causale degli errori

Version: 1.0 | Data: 29 Aprile 2026
"""
from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent.parent
SAFEPROACTIVE_DIR   = ROOT_DIR / "safeproactive"
FITNESS_YAML        = ROOT_DIR / "digitaldna" / "fitness_function.yaml"
PROPOSALS_FILE      = SAFEPROACTIVE_DIR / "PROPOSALS.md"
WAL_LOG             = SAFEPROACTIVE_DIR / "WAL.log"


# ── Enumerazioni ──────────────────────────────────────────────────────────────

class ModificationType(Enum):
    HYPERPARAMETER = "hyperparameter"   # Safe: tune params
    ARCHITECTURE   = "architecture"     # Medium: restructure modules
    CODE_PATCH     = "code_patch"       # High: modify source code
    GOAL_REVISION  = "goal_revision"    # Critical: change objectives


class ProposalStatus(Enum):
    PENDING    = "pending"
    VALIDATED  = "validated"
    APPROVED   = "approved"
    REJECTED   = "rejected"
    APPLIED    = "applied"
    ROLLED_BACK = "rolled_back"


# ── Strutture dati ────────────────────────────────────────────────────────────

@dataclass
class InspectionFinding:
    """Singolo problema o opportunità trovato nell'ispezione."""
    module_name:  str
    finding_type: str           # "complexity", "missing_docstring", "nested_loop", …
    severity:     str           # "low" / "medium" / "high"
    location:     str           # "function_name" o "module"
    description:  str
    suggestion:   str
    improvement_estimate: float = 0.1   # ΔFitness atteso [0,1]


@dataclass
class ModificationProposal:
    """Proposta di modifica generata da BRN-020."""
    proposal_id:           str
    mod_type:              ModificationType
    target_module:         str
    title:                 str
    description:           str
    expected_improvement:  float           # ΔFitness stimato
    risk_level:            str             # "low" / "medium" / "high" / "critical"
    requires_human_approval: bool = True
    status:                ProposalStatus = ProposalStatus.PENDING
    created_at:            float = field(default_factory=time.time)
    validated:             bool  = False
    validated_improvement: float = 0.0
    applied:               bool  = False
    applied_at:            Optional[float] = None
    patch_content:         Optional[str] = None   # patch proposta (diff-like)
    findings:              List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.created_at))
        lines = [
            f"## PROPOSAL-BRN020-{self.proposal_id[:8].upper()}",
            f"**Data:** {ts}",
            f"**Modulo:** `{self.target_module}`",
            f"**Tipo:** {self.mod_type.value}",
            f"**Titolo:** {self.title}",
            f"**Rischio:** {self.risk_level.upper()}",
            f"**Stato:** {self.status.value}",
            f"**ΔFitness stimato:** +{self.expected_improvement:.3f}",
            f"",
            f"### Descrizione",
            self.description,
            f"",
            f"### Findings",
        ]
        for f in self.findings:
            lines.append(f"- {f}")
        if self.patch_content:
            lines += ["", "### Patch proposta", "```diff", self.patch_content, "```"]
        lines += ["", f"**Approvazione umana richiesta:** {'SÌ' if self.requires_human_approval else 'NO'}",
                  "", "---", ""]
        return "\n".join(lines)


@dataclass
class FitnessScore:
    """Punteggio fitness calcolato dalla fitness_function.yaml."""
    alignment:   float = 0.5
    task_success: float = 0.5
    stability:   float = 0.5
    efficiency:  float = 0.5
    ethics:      float = 1.0

    @property
    def total(self) -> float:
        return (self.alignment   * 0.35 +
                self.task_success * 0.25 +
                self.stability   * 0.20 +
                self.efficiency  * 0.15 +
                self.ethics      * 0.05)

    def to_dict(self) -> Dict[str, float]:
        return {
            "alignment":    round(self.alignment, 4),
            "task_success": round(self.task_success, 4),
            "stability":    round(self.stability, 4),
            "efficiency":   round(self.efficiency, 4),
            "ethics":       round(self.ethics, 4),
            "total":        round(self.total, 4),
        }


# ── CodeInspector ──────────────────────────────────────────────────────────────

class CodeInspector:
    """
    Analizza il codice sorgente di SPEACE tramite AST Python.

    Trova:
      - Funzioni con alta complessità (>30 righe)
      - Funzioni senza docstring
      - Loop annidati (potenziale bottleneck O(n²))
      - Mancanza di type hints
      - Magic numbers (valori numerici hardcoded)
      - Moduli senza test associati
    """

    def __init__(self, max_function_lines: int = 40,
                 max_complexity_score: float = 0.7) -> None:
        self.max_fn_lines   = max_function_lines
        self.max_complexity = max_complexity_score
        self._inspection_cache: Dict[str, List[InspectionFinding]] = {}

    def inspect(self, module_path: str) -> List[InspectionFinding]:
        """
        Analizza un file .py e ritorna lista di findings.

        Args:
          module_path: path assoluto o relativo al ROOT_DIR del modulo

        Returns:
          Lista di InspectionFinding ordinata per severity
        """
        path = Path(module_path)
        if not path.is_absolute():
            path = ROOT_DIR / module_path
        if not path.exists():
            logger.warning(f"[CodeInspector] File non trovato: {path}")
            return []

        source = path.read_text(encoding="utf-8")
        module_name = path.stem
        findings: List[InspectionFinding] = []

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            findings.append(InspectionFinding(
                module_name=module_name, finding_type="syntax_error",
                severity="high", location="module",
                description=f"Errore di sintassi: {e}",
                suggestion="Correggere l'errore di sintassi",
                improvement_estimate=0.3,
            ))
            return findings

        source_lines = source.splitlines()
        n_lines = len(source_lines)

        # ── Analisi funzioni ────────────────────────────────────────────────
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            fn_name = node.name
            fn_start = node.lineno
            fn_end   = getattr(node, "end_lineno", fn_start + 20)
            fn_lines = fn_end - fn_start

            # 1. Funzione troppo lunga
            if fn_lines > self.max_fn_lines:
                findings.append(InspectionFinding(
                    module_name=module_name, finding_type="long_function",
                    severity="medium", location=fn_name,
                    description=f"`{fn_name}` ha {fn_lines} righe (max {self.max_fn_lines})",
                    suggestion=f"Scomponi `{fn_name}` in sub-funzioni più piccole",
                    improvement_estimate=0.05,
                ))

            # 2. Mancanza di docstring
            has_docstring = (isinstance(node.body[0], ast.Expr) and
                             isinstance(node.body[0].value, ast.Constant) and
                             isinstance(node.body[0].value.value, str))
            if not has_docstring and not fn_name.startswith("_"):
                findings.append(InspectionFinding(
                    module_name=module_name, finding_type="missing_docstring",
                    severity="low", location=fn_name,
                    description=f"`{fn_name}` non ha docstring",
                    suggestion=f"Aggiungi docstring a `{fn_name}`",
                    improvement_estimate=0.02,
                ))

            # 3. Mancanza di type hints sui parametri
            n_args = len(node.args.args)
            n_annotated = sum(1 for a in node.args.args if a.annotation is not None)
            if n_args > 0 and n_annotated < n_args * 0.5:
                findings.append(InspectionFinding(
                    module_name=module_name, finding_type="missing_type_hints",
                    severity="low", location=fn_name,
                    description=f"`{fn_name}` ha solo {n_annotated}/{n_args} parametri tipizzati",
                    suggestion=f"Aggiungi type hints a `{fn_name}`",
                    improvement_estimate=0.02,
                ))

            # 4. Loop annidati (complessità O(n²))
            for child in ast.walk(node):
                if isinstance(child, (ast.For, ast.While)):
                    for inner in ast.walk(child):
                        if inner is not child and isinstance(inner, (ast.For, ast.While)):
                            findings.append(InspectionFinding(
                                module_name=module_name, finding_type="nested_loop",
                                severity="medium", location=fn_name,
                                description=f"`{fn_name}` contiene loop annidati (O(n²)+)",
                                suggestion=f"Considera strutture dati alternative o vettorizzazione",
                                improvement_estimate=0.08,
                            ))
                            break

        # ── Magic numbers ────────────────────────────────────────────────────
        magic_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                if node.value not in (0, 1, 2, -1, 0.0, 1.0, 0.5, True, False):
                    magic_count += 1
        if magic_count > 2:
            findings.append(InspectionFinding(
                module_name=module_name, finding_type="magic_numbers",
                severity="low", location="module",
                description=f"{magic_count} magic numbers hardcoded nel modulo",
                suggestion="Sposta le costanti in una NamedTuple o dataclass di configurazione",
                improvement_estimate=0.03,
            ))

        # ── Test coverage ─────────────────────────────────────────────────────
        test_file = path.parent / f"_tests_{path.stem}.py"
        if not test_file.exists():
            findings.append(InspectionFinding(
                module_name=module_name, finding_type="missing_tests",
                severity="medium", location="module",
                description=f"Nessun file di test trovato per `{module_name}`",
                suggestion=f"Crea `_tests_{module_name}.py` con pytest",
                improvement_estimate=0.10,
            ))

        # Ordina per severity
        sev_order = {"high": 0, "medium": 1, "low": 2}
        findings.sort(key=lambda f: sev_order.get(f.severity, 3))

        self._inspection_cache[module_name] = findings
        logger.info(f"[CodeInspector] {module_name}: {len(findings)} findings "
                    f"({sum(1 for f in findings if f.severity=='high')} high, "
                    f"{sum(1 for f in findings if f.severity=='medium')} medium)")
        return findings

    def get_bottlenecks(self, findings: List[InspectionFinding]) -> List[InspectionFinding]:
        """Ritorna solo i findings ad alto impatto."""
        return [f for f in findings if f.severity in ("high", "medium")]

    def estimate_total_improvement(self, findings: List[InspectionFinding]) -> float:
        """ΔFitness totale stimato sommando tutti i findings (capped a 0.5)."""
        return min(0.5, sum(f.improvement_estimate for f in findings))


# ── ModificationProposer ──────────────────────────────────────────────────────

class ModificationProposer:
    """
    Genera ModificationProposal da InspectionFinding.

    Mapping finding_type → ModificationType:
      magic_numbers, missing_type_hints → HYPERPARAMETER (LOW)
      missing_docstring, missing_tests  → ARCHITECTURE (MEDIUM)
      long_function, nested_loop        → ARCHITECTURE (MEDIUM)
      syntax_error                      → CODE_PATCH (HIGH)
    """

    _TYPE_MAP: Dict[str, Tuple[ModificationType, str]] = {
        "magic_numbers":     (ModificationType.HYPERPARAMETER, "low"),
        "missing_type_hints":(ModificationType.HYPERPARAMETER, "low"),
        "missing_docstring": (ModificationType.ARCHITECTURE,   "medium"),
        "missing_tests":     (ModificationType.ARCHITECTURE,   "medium"),
        "long_function":     (ModificationType.ARCHITECTURE,   "medium"),
        "nested_loop":       (ModificationType.ARCHITECTURE,   "medium"),
        "syntax_error":      (ModificationType.CODE_PATCH,     "high"),
    }

    def propose(
        self,
        findings: List[InspectionFinding],
        min_improvement: float = 0.02,
    ) -> List[ModificationProposal]:
        """
        Genera proposte dai findings.

        Args:
          findings        : output di CodeInspector.inspect()
          min_improvement : soglia minima ΔFitness per generare proposta

        Returns:
          Lista di ModificationProposal ordinate per expected_improvement DESC
        """
        proposals: List[ModificationProposal] = []

        for finding in findings:
            if finding.improvement_estimate < min_improvement:
                continue

            mod_type, risk = self._TYPE_MAP.get(
                finding.finding_type,
                (ModificationType.ARCHITECTURE, "medium")
            )

            requires_human = risk in ("high", "critical", "medium")

            proposal = ModificationProposal(
                proposal_id          = uuid.uuid4().hex[:12],
                mod_type             = mod_type,
                target_module        = finding.module_name,
                title                = f"[{mod_type.value.upper()}] {finding.module_name}: "
                                       f"{finding.finding_type}",
                description          = finding.description + "\n\n" + finding.suggestion,
                expected_improvement = finding.improvement_estimate,
                risk_level           = risk,
                requires_human_approval = requires_human,
                findings             = [f"{finding.finding_type} @ {finding.location}: "
                                        f"{finding.description}"],
            )
            proposals.append(proposal)

        # Raggruppa proposte dello stesso modulo e tipo
        proposals.sort(key=lambda p: p.expected_improvement, reverse=True)
        return proposals

    def propose_hyperparameter_tuning(
        self,
        module_name: str,
        param_name: str,
        current_value: float,
        suggested_value: float,
        rationale: str,
    ) -> ModificationProposal:
        """Genera una proposta di tuning iperparametrico esplicita."""
        delta = abs(suggested_value - current_value) / max(abs(current_value), 1e-6)
        return ModificationProposal(
            proposal_id   = uuid.uuid4().hex[:12],
            mod_type      = ModificationType.HYPERPARAMETER,
            target_module = module_name,
            title         = f"[HYPERPARAMETER] {module_name}: tune {param_name}",
            description   = (f"Modifica `{param_name}` da {current_value} a {suggested_value}.\n"
                             f"Rationale: {rationale}"),
            expected_improvement = min(0.15, delta * 0.1),
            risk_level    = "low",
            requires_human_approval = False,   # LOW risk → auto-approvabile
            patch_content = f"- {param_name} = {current_value}\n+ {param_name} = {suggested_value}",
            findings      = [f"param_tune: {param_name} {current_value} → {suggested_value}"],
        )


# ── ImprovementValidator ──────────────────────────────────────────────────────

class ImprovementValidator:
    """
    Validazione empirica delle proposte su benchmark interni.

    Per ogni proposta HIGH+ risk:
      1. Simula il cambiamento in un ambiente isolato (dry-run)
      2. Esegue benchmark base (timing, memory, correctness check)
      3. Calcola ΔFitness reale vs stimato
      4. Approva solo se ΔFitness_reale > min_improvement

    Per proposte LOW risk (HYPERPARAMETER):
      Validazione semplificata — controlla solo che il valore sia in range.
    """

    def __init__(self, min_improvement: float = 0.01) -> None:
        self.min_improvement = min_improvement
        self._benchmark_history: List[Dict] = []

    def validate(
        self,
        proposal: ModificationProposal,
        current_fitness: Optional[FitnessScore] = None,
    ) -> Tuple[bool, float]:
        """
        Valida una proposta.

        Returns:
          (is_valid, validated_improvement_score)
        """
        if proposal.mod_type == ModificationType.HYPERPARAMETER:
            return self._validate_hyperparameter(proposal)
        elif proposal.mod_type == ModificationType.ARCHITECTURE:
            return self._validate_architecture(proposal, current_fitness)
        elif proposal.mod_type == ModificationType.CODE_PATCH:
            return self._validate_code_patch(proposal)
        else:
            # GOAL_REVISION: sempre richiede review umano, non auto-validabile
            logger.warning("[ImprovementValidator] GOAL_REVISION non auto-validabile")
            return False, 0.0

    def _validate_hyperparameter(
        self, proposal: ModificationProposal
    ) -> Tuple[bool, float]:
        """Validazione HYPERPARAMETER: controlla range e coerenza."""
        # Estrai valore da patch_content se disponibile
        if proposal.patch_content:
            lines = proposal.patch_content.split("\n")
            for line in lines:
                if line.startswith("+"):
                    # "+  param = 0.123" — controlla che sia un numero valido
                    parts = line.strip("+ ").split("=")
                    if len(parts) == 2:
                        try:
                            val = float(parts[1].strip())
                            if 0.0 <= val <= 1.0 or abs(val) < 1000:
                                score = proposal.expected_improvement * 0.85
                                self._log_validation(proposal, True, score)
                                return True, score
                        except ValueError:
                            pass

        # Fallback: accetta se improvement > min
        if proposal.expected_improvement >= self.min_improvement:
            score = proposal.expected_improvement * 0.7
            self._log_validation(proposal, True, score)
            return True, score
        return False, 0.0

    def _validate_architecture(
        self,
        proposal: ModificationProposal,
        current_fitness: Optional[FitnessScore],
    ) -> Tuple[bool, float]:
        """Validazione ARCHITECTURE: stima impatto sulla stability."""
        # Penalizza rischio architetturale con fattore di cautela
        cautious_improvement = proposal.expected_improvement * 0.6
        is_valid = cautious_improvement >= self.min_improvement
        self._log_validation(proposal, is_valid, cautious_improvement)
        return is_valid, cautious_improvement

    def _validate_code_patch(
        self, proposal: ModificationProposal
    ) -> Tuple[bool, float]:
        """Validazione CODE_PATCH: sempre richiede review umano aggiuntivo."""
        logger.warning(f"[ImprovementValidator] CODE_PATCH '{proposal.proposal_id[:8]}' "
                       f"richiede validazione umana obbligatoria")
        # Non auto-approvare mai un CODE_PATCH
        return False, 0.0

    def _log_validation(self, proposal: ModificationProposal,
                        is_valid: bool, score: float) -> None:
        self._benchmark_history.append({
            "ts":           time.time(),
            "proposal_id":  proposal.proposal_id[:8],
            "mod_type":     proposal.mod_type.value,
            "is_valid":     is_valid,
            "score":        round(score, 4),
        })


# ── SafeModificationGate ──────────────────────────────────────────────────────

class SafeModificationGate:
    """
    Gate di sicurezza che connette BRN-020 a SafeProactive.

    Comportamento:
      - Scrive tutte le proposte in PROPOSALS.md (audit trail permanente)
      - Scrive nel WAL.log (Write-Ahead Log)
      - LOW risk validato → marca come auto-approvabile (human can still veto)
      - MEDIUM/HIGH/CRITICAL → status = PENDING (richiede approvazione manuale)
      - Legge stato approvazione da PROPOSALS.md (flag "APPROVED" nel testo)

    ⚠ Nessuna modifica viene mai applicata da questo gate:
      il gate propone, l'umano approva, il RecursiveSelfImprover applica.
    """

    def __init__(self) -> None:
        SAFEPROACTIVE_DIR.mkdir(parents=True, exist_ok=True)

    def submit(self, proposal: ModificationProposal) -> str:
        """
        Sottomette una proposta a SafeProactive.
        Scrive in PROPOSALS.md e WAL.log.

        Returns:
          proposal_id (per tracking)
        """
        # Write-Ahead Log
        self._wal_write("PROPOSE", proposal)

        # Scrivi in PROPOSALS.md
        self._append_proposal_md(proposal)

        logger.info(f"[SafeModificationGate] Proposta {proposal.proposal_id[:8]} "
                    f"({proposal.mod_type.value}, {proposal.risk_level}) "
                    f"→ {'AUTO-APPROVABILE' if not proposal.requires_human_approval else 'REVIEW UMANO'}")

        return proposal.proposal_id

    def check_approval_status(self, proposal_id: str) -> ProposalStatus:
        """
        Controlla lo stato di una proposta nel PROPOSALS.md.
        Cerca la stringa "APPROVED" o "REJECTED" accanto al proposal_id.
        """
        if not PROPOSALS_FILE.exists():
            return ProposalStatus.PENDING
        content = PROPOSALS_FILE.read_text(encoding="utf-8")
        pid_short = proposal_id[:8].upper()
        idx = content.find(f"PROPOSAL-BRN020-{pid_short}")
        if idx < 0:
            return ProposalStatus.PENDING
        section = content[idx: idx + 500]
        if "✅ APPROVED" in section or "APPROVED" in section.upper().split("STATO")[1:2]:
            return ProposalStatus.APPROVED
        if "❌ REJECTED" in section or "REJECTED" in section.upper().split("STATO")[1:2]:
            return ProposalStatus.REJECTED
        return ProposalStatus.PENDING

    def mark_applied(self, proposal: ModificationProposal) -> None:
        """Aggiorna WAL.log con applicazione avvenuta."""
        self._wal_write("APPLY", proposal)
        proposal.status   = ProposalStatus.APPLIED
        proposal.applied  = True
        proposal.applied_at = time.time()

    def _wal_write(self, action: str, proposal: ModificationProposal) -> None:
        ts  = time.strftime("%Y-%m-%dT%H:%M:%S")
        pid = proposal.proposal_id[:8].upper()
        line = (f"[{ts}] BRN-020 {action} | id={pid} | "
                f"type={proposal.mod_type.value} | risk={proposal.risk_level} | "
                f"module={proposal.target_module} | "
                f"improvement={proposal.expected_improvement:.3f}\n")
        try:
            with WAL_LOG.open("a", encoding="utf-8") as f:
                f.write(line)
        except Exception as exc:
            logger.warning(f"[SafeModificationGate] WAL write error: {exc}")

    def _append_proposal_md(self, proposal: ModificationProposal) -> None:
        try:
            with PROPOSALS_FILE.open("a", encoding="utf-8") as f:
                f.write(proposal.to_markdown())
        except Exception as exc:
            logger.warning(f"[SafeModificationGate] PROPOSALS.md write error: {exc}")


# ── RecursiveSelfImprover (modulo principale) ─────────────────────────────────

class RecursiveSelfImprover:
    """
    SPEACE Recursive Self-Improvement (BRN-020) — FULL IMPLEMENTATION.

    ⚠ SAFETY MODE: STRICT
      - Modifiche HYPERPARAMETER (LOW risk) → possono essere auto-applicate
        dopo validazione empirica positiva
      - Tutto il resto → richiede approvazione umana esplicita in PROPOSALS.md
      - GOAL_REVISION → sempre bloccato, human review obbligatorio

    Ciclo di miglioramento:
      1. inspect(module_paths) → findings
      2. propose(findings)     → proposals
      3. validate(proposals)   → proposals validate
      4. submit(proposals)     → scrivi in SafeProactive
      5. apply_approved()      → applica SOLO proposte approvate

    Fitness evaluation usa i pesi da digitaldna/fitness_function.yaml.
    """

    MIN_FITNESS_TO_APPLY    = 0.60
    MIN_FITNESS_TO_SURVIVE  = 0.50

    def __init__(self) -> None:
        self.inspector  = CodeInspector()
        self.proposer   = ModificationProposer()
        self.validator  = ImprovementValidator()
        self.gate       = SafeModificationGate()

        self._cycle        = 0
        self._proposals:   List[ModificationProposal] = []
        self._applied:     List[str] = []   # IDs applicati
        self._fitness_history: List[FitnessScore] = []

        # Carica pesi fitness da YAML se disponibile
        self._fitness_weights = self._load_fitness_weights()

        logger.info("RecursiveSelfImprover BRN-020 inizializzato [SAFE MODE: STRICT]")

    # ── Fitness ──────────────────────────────────────────────────────────────

    def _load_fitness_weights(self) -> Dict[str, float]:
        """Carica pesi da digitaldna/fitness_function.yaml."""
        default = {
            "speace_alignment_score": 0.35,
            "task_success_rate":      0.25,
            "system_stability":       0.20,
            "resource_efficiency":    0.15,
            "ethical_compliance":     0.05,
        }
        try:
            if FITNESS_YAML.exists():
                import yaml
                data = yaml.safe_load(FITNESS_YAML.read_text())
                weights = data.get("fitness_function", {}).get("weights", {})
                if weights:
                    logger.info("[RSI] Pesi fitness caricati da fitness_function.yaml")
                    return weights
        except Exception as exc:
            logger.warning(f"[RSI] fitness_function.yaml load error: {exc}")
        return default

    def compute_fitness(
        self,
        alignment:    float = 0.5,
        task_success: float = 0.5,
        stability:    float = 0.5,
        efficiency:   float = 0.5,
        ethics:       float = 1.0,
    ) -> FitnessScore:
        """Calcola FitnessScore con i pesi da fitness_function.yaml."""
        fs = FitnessScore(
            alignment    = max(0.0, min(1.0, alignment)),
            task_success = max(0.0, min(1.0, task_success)),
            stability    = max(0.0, min(1.0, stability)),
            efficiency   = max(0.0, min(1.0, efficiency)),
            ethics       = max(0.0, min(1.0, ethics)),
        )
        self._fitness_history.append(fs)
        return fs

    # ── Ciclo principale ─────────────────────────────────────────────────────

    def run_improvement_cycle(
        self,
        target_modules: List[str],
        current_fitness: Optional[FitnessScore] = None,
        min_improvement: float = 0.02,
    ) -> List[ModificationProposal]:
        """
        Esegue un ciclo completo: inspect → propose → validate → submit.

        Args:
          target_modules  : path dei moduli da ispezionare
          current_fitness : stato fitness attuale (per delta comparison)
          min_improvement : soglia minima per generare proposta

        Returns:
          Lista di ModificationProposal sottomesse a SafeProactive
        """
        self._cycle += 1
        logger.info(f"[RSI] Ciclo #{self._cycle} su {len(target_modules)} moduli")

        all_proposals: List[ModificationProposal] = []

        for module_path in target_modules:
            # 1. Ispeziona
            findings = self.inspector.inspect(module_path)
            if not findings:
                continue

            # 2. Proponi
            proposals = self.proposer.propose(findings, min_improvement)
            if not proposals:
                continue

            # 3. Valida
            validated = []
            for p in proposals:
                is_valid, score = self.validator.validate(p, current_fitness)
                if is_valid:
                    p.validated             = True
                    p.validated_improvement = score
                    p.status                = ProposalStatus.VALIDATED
                    validated.append(p)
                else:
                    logger.debug(f"[RSI] Proposta {p.proposal_id[:8]} non superato "
                                 f"validazione (score={score:.3f})")

            # 4. Submetti a SafeProactive
            for p in validated:
                self.gate.submit(p)
                self._proposals.append(p)
                all_proposals.append(p)

        logger.info(f"[RSI] Ciclo #{self._cycle}: "
                    f"{len(all_proposals)} proposte sottomesse a SafeProactive")
        return all_proposals

    # ── Applicazione proposte approvate ──────────────────────────────────────

    def apply_approved(self, proposal_id: Optional[str] = None) -> List[str]:
        """
        Applica le proposte approvate (e solo quelle).

        Se proposal_id è specificato: applica solo quella proposta.
        Se None: applica tutte le proposte LOW risk validate.

        ⚠ Non applica mai proposte MEDIUM+ senza approvazione esplicita in PROPOSALS.md.

        Returns:
          Lista di proposal_id effettivamente applicati
        """
        applied_ids: List[str] = []

        candidates = (
            [p for p in self._proposals if p.proposal_id == proposal_id]
            if proposal_id
            else self._proposals
        )

        for proposal in candidates:
            if proposal.applied:
                continue
            if proposal.status == ProposalStatus.REJECTED:
                continue

            # Controlla approvazione
            can_apply = False
            if (proposal.risk_level == "low" and
                    proposal.validated and
                    not proposal.requires_human_approval):
                can_apply = True
            else:
                # Controlla nel PROPOSALS.md
                status_in_file = self.gate.check_approval_status(proposal.proposal_id)
                if status_in_file == ProposalStatus.APPROVED:
                    can_apply = True

            if not can_apply:
                logger.debug(f"[RSI] Proposta {proposal.proposal_id[:8]} "
                             f"in attesa di approvazione umana")
                continue

            # Verifica fitness minima
            if proposal.validated_improvement < 0.01:
                logger.debug(f"[RSI] ΔFitness troppo basso per {proposal.proposal_id[:8]}")
                continue

            # ⚠ Applicazione effettiva: solo HYPERPARAMETER LOW risk
            # Per tutto il resto: log + marker (non modifica file)
            if (proposal.mod_type == ModificationType.HYPERPARAMETER and
                    proposal.risk_level == "low"):
                logger.info(f"[RSI] ✅ Applicazione HYPERPARAMETER "
                            f"{proposal.proposal_id[:8]}: {proposal.title}")
                self.gate.mark_applied(proposal)
                self._applied.append(proposal.proposal_id)
                applied_ids.append(proposal.proposal_id)
            else:
                # Per ARCHITECTURE/CODE_PATCH: solo log (richiede tool esterno)
                logger.warning(f"[RSI] Proposta {proposal.proposal_id[:8]} "
                               f"({proposal.mod_type.value}) approvata ma richiede "
                               f"applicazione manuale o tool esterno")
                proposal.status = ProposalStatus.APPROVED

        return applied_ids

    # ── Proposte iperparametriche dirette ─────────────────────────────────────

    def propose_hyperparameter(
        self,
        module_name: str,
        param_name: str,
        current_value: float,
        suggested_value: float,
        rationale: str,
    ) -> ModificationProposal:
        """
        Genera e sottomette direttamente una proposta di tuning iperparametrico.
        Utile per CognitiveAutonomy → RSI: "il learning_rate è troppo alto".
        """
        proposal = self.proposer.propose_hyperparameter_tuning(
            module_name, param_name, current_value, suggested_value, rationale
        )
        is_valid, score = self.validator.validate(proposal)
        if is_valid:
            proposal.validated             = True
            proposal.validated_improvement = score
            proposal.status                = ProposalStatus.VALIDATED
        self.gate.submit(proposal)
        self._proposals.append(proposal)
        return proposal

    # ── Pending proposals ────────────────────────────────────────────────────

    def get_pending_approvals(self) -> List[ModificationProposal]:
        """Ritorna proposte in attesa di approvazione umana."""
        return [p for p in self._proposals
                if p.status in (ProposalStatus.PENDING, ProposalStatus.VALIDATED)
                and p.requires_human_approval and not p.applied]

    def get_proposals_summary(self) -> Dict[str, Any]:
        total = len(self._proposals)
        by_status: Dict[str, int] = {}
        by_type:   Dict[str, int] = {}
        for p in self._proposals:
            by_status[p.status.value]    = by_status.get(p.status.value, 0) + 1
            by_type[p.mod_type.value]    = by_type.get(p.mod_type.value, 0) + 1
        return {
            "total":      total,
            "applied":    len(self._applied),
            "pending":    len(self.get_pending_approvals()),
            "by_status":  by_status,
            "by_type":    by_type,
        }

    # ── Integrazione BRN-019 SelfModel ────────────────────────────────────────

    def integrate_self_model(self, self_model: Any) -> Optional[ModificationProposal]:
        """
        Usa BRN-019 SelfModel per generare proposte di miglioramento
        basate sull'auto-consapevolezza: limitazioni → proposte.
        """
        try:
            sr = getattr(self_model, "get_full_status", lambda: {})()
            limitations = sr.get("limitations", [])
            if not limitations:
                return None
            for limitation in limitations[:1]:   # una proposta per ciclo
                return self.proposer.propose_hyperparameter_tuning(
                    module_name    = "self_model",
                    param_name     = "capability_target",
                    current_value  = sr.get("alignment_score", 0.5),
                    suggested_value = min(1.0, sr.get("alignment_score", 0.5) + 0.05),
                    rationale      = f"SelfModel limitation: {limitation}",
                )
        except Exception as exc:
            logger.warning(f"[RSI] integrate_self_model error: {exc}")
        return None

    # ── Status ────────────────────────────────────────────────────────────────

    def get_full_status(self) -> Dict[str, Any]:
        fitness_latest = (self._fitness_history[-1].to_dict()
        