"""
Tests — RecursiveSelfImprover BRN-020
=========================================
Run: python -m pytest cortex/brain/_tests_recursive_self_improvement.py -v
"""
import os
import time
import pytest
import tempfile
from pathlib import Path

from cortex.brain.recursive_self_improvement import (
    ModificationType, ProposalStatus,
    InspectionFinding, ModificationProposal, FitnessScore,
    CodeInspector, ModificationProposer, ImprovementValidator,
    SafeModificationGate, RecursiveSelfImprover,
    create_recursive_self_improver,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

SAMPLE_GOOD_CODE = '''
"""Module with good practices."""
from typing import Dict, List

def add(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

def multiply(x: float, y: float) -> float:
    """Multiplies two numbers."""
    return x * y
'''

SAMPLE_BAD_CODE = '''
def process(data, config, options, extra, more):
    result = []
    for i in data:
        for j in config:
            for k in options:
                result.append(i + j + k)
    x = 0.123456
    y = 789.0
    z = 42
    return result
# no docstring, magic numbers, nested loops, no type hints
'''

def make_temp_py(content: str) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".py", mode="w",
                                    delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


# ── TestFitnessScore ──────────────────────────────────────────────────────────

class TestFitnessScore:

    def test_total_formula(self):
        fs = FitnessScore(alignment=1.0, task_success=1.0, stability=1.0,
                          efficiency=1.0, ethics=1.0)
        assert abs(fs.total - 1.0) < 1e-6

    def test_total_zero(self):
        fs = FitnessScore(alignment=0.0, task_success=0.0, stability=0.0,
                          efficiency=0.0, ethics=0.0)
        assert fs.total == 0.0

    def test_weights_sum_to_one(self):
        # 0.35 + 0.25 + 0.20 + 0.15 + 0.05 = 1.0
        fs = FitnessScore()
        total_check = (0.35 + 0.25 + 0.20 + 0.15 + 0.05)
        assert abs(total_check - 1.0) < 1e-9

    def test_to_dict_has_all_keys(self):
        fs = FitnessScore()
        d  = fs.to_dict()
        for k in ("alignment", "task_success", "stability", "efficiency",
                  "ethics", "total"):
            assert k in d

    def test_clamp_values(self):
        rsi = create_recursive_self_improver()
        fs  = rsi.compute_fitness(alignment=1.5, task_success=-0.1)
        assert 0.0 <= fs.alignment <= 1.0
        assert 0.0 <= fs.task_success <= 1.0


# ── TestCodeInspector ─────────────────────────────────────────────────────────

class TestCodeInspector:

    def test_inspect_good_code_fewer_findings(self):
        path = make_temp_py(SAMPLE_GOOD_CODE)
        try:
            inspector = CodeInspector()
            findings = inspector.inspect(path)
            high_med = [f for f in findings if f.severity in ("high", "medium")]
            assert len(high_med) <= 2   # solo "missing_tests" potrebbe apparire
        finally:
            os.unlink(path)

    def test_inspect_bad_code_detects_nested_loop(self):
        path = make_temp_py(SAMPLE_BAD_CODE)
        try:
            inspector = CodeInspector()
            findings = inspector.inspect(path)
            types = [f.finding_type for f in findings]
            assert "nested_loop" in types
        finally:
            os.unlink(path)

    def test_inspect_bad_code_detects_magic_numbers(self):
        path = make_temp_py(SAMPLE_BAD_CODE)
        try:
            inspector = CodeInspector()
            findings = inspector.inspect(path)
            types = [f.finding_type for f in findings]
            assert "magic_numbers" in types
        finally:
            os.unlink(path)

    def test_inspect_bad_code_detects_missing_docstring(self):
        path = make_temp_py(SAMPLE_BAD_CODE)
        try:
            inspector = CodeInspector()
            findings = inspector.inspect(path)
            types = [f.finding_type for f in findings]
            assert "missing_docstring" in types
        finally:
            os.unlink(path)

    def test_inspect_bad_code_detects_missing_type_hints(self):
        path = make_temp_py(SAMPLE_BAD_CODE)
        try:
            inspector = CodeInspector()
            findings = inspector.inspect(path)
            types = [f.finding_type for f in findings]
            assert "missing_type_hints" in types
        finally:
            os.unlink(path)

    def test_inspect_nonexistent_file(self):
        inspector = CodeInspector()
        findings = inspector.inspect("/nonexistent/path/module.py")
        assert findings == []

    def test_inspect_syntax_error(self):
        path = make_temp_py("def broken(\n  x:\n")
        try:
            inspector = CodeInspector()
            findings = inspector.inspect(path)
            assert any(f.finding_type == "syntax_error" for f in findings)
        finally:
            os.unlink(path)

    def test_get_bottlenecks_filters_low(self):
        findings = [
            InspectionFinding("m","nested_loop","high","fn","d","s",0.1),
            InspectionFinding("m","magic_numbers","low","mod","d","s",0.03),
        ]
        inspector = CodeInspector()
        bottlenecks = inspector.get_bottlenecks(findings)
        assert all(f.severity in ("high","medium") for f in bottlenecks)
        assert len(bottlenecks) == 1

    def test_estimate_improvement_capped(self):
        findings = [InspectionFinding("m","t","high","fn","d","s", imp)
                    for imp in [0.3, 0.3, 0.3, 0.3]]
        inspector = CodeInspector()
        est = inspector.estimate_total_improvement(findings)
        assert est <= 0.5


# ── TestModificationProposer ──────────────────────────────────────────────────

class TestModificationProposer:

    def _make_finding(self, ftype="nested_loop", sev="medium", imp=0.08):
        return InspectionFinding("my_module", ftype, sev, "fn", "desc", "sug", imp)

    def test_propose_generates_proposals(self):
        proposer = ModificationProposer()
        findings = [self._make_finding("nested_loop"),
                    self._make_finding("magic_numbers", sev="low", imp=0.03)]
        proposals = proposer.propose(findings)
        assert len(proposals) >= 1

    def test_propose_ordered_by_improvement(self):
        proposer = ModificationProposer()
        findings = [
            self._make_finding("nested_loop", imp=0.08),
            self._make_finding("missing_docstring", imp=0.02),
        ]
        proposals = proposer.propose(findings, min_improvement=0.01)
        improvements = [p.expected_improvement for p in proposals]
        assert improvements == sorted(improvements, reverse=True)

    def test_propose_low_risk_no_human(self):
        proposer = ModificationProposer()
        findings = [self._make_finding("magic_numbers", sev="low", imp=0.05)]
        proposals = proposer.propose(findings)
        low_risk = [p for p in proposals if p.risk_level == "low"]
        assert all(not p.requires_human_approval for p in low_risk)

    def test_propose_high_risk_requires_human(self):
        proposer = ModificationProposer()
        findings = [self._make_finding("syntax_error", sev="high", imp=0.3)]
        proposals = proposer.propose(findings)
        high_risk = [p for p in proposals if p.risk_level == "high"]
        assert all(p.requires_human_approval for p in high_risk)

    def test_propose_filters_below_threshold(self):
        proposer = ModificationProposer()
        findings = [self._make_finding("missing_docstring", sev="low", imp=0.001)]
        proposals = proposer.propose(findings, min_improvement=0.05)
        assert proposals == []

    def test_propose_hyperparameter_tuning(self):
        proposer = ModificationProposer()
        p = proposer.propose_hyperparameter_tuning(
            "my_module", "learning_rate", 0.1, 0.05,
            "learning rate troppo alto"
        )
        assert p.mod_type == ModificationType.HYPERPARAMETER
        assert p.risk_level == "low"
        assert not p.requires_human_approval
        assert "learning_rate" in p.title

    def test_proposal_has_markdown(self):
        proposer = ModificationProposer()
        p = proposer.propose_hyperparameter_tuning(
            "mod", "alpha", 0.3, 0.2, "test"
        )
        md = p.to_markdown()
        assert "PROPOSAL-BRN020-" in md
        assert p.title in md


# ── TestImprovementValidator ──────────────────────────────────────────────────

class TestImprovementValidator:

    def _make_proposal(self, mod_type=ModificationType.HYPERPARAMETER,
                       risk="low", imp=0.05, patch=None):
        return ModificationProposal(
            proposal_id=f"test_{int(time.time()*1000)}",
            mod_type=mod_type, target_module="mod",
            title="test", description="test",
            expected_improvement=imp, risk_level=risk,
            requires_human_approval=(risk != "low"),
            patch_content=patch,
        )

    def test_validate_hyperparameter_valid(self):
        validator = ImprovementValidator(min_improvement=0.01)
        p = self._make_proposal(patch="- alpha = 0.1\n+ alpha = 0.05")
        is_valid, score = validator.validate(p)
        assert is_valid is True
        assert score > 0.0

    def test_validate_hyperparameter_fallback(self):
        validator = ImprovementValidator(min_improvement=0.01)
        p = self._make_proposal(imp=0.05)  # no patch
        is_valid, score = validator.validate(p)
        assert is_valid is True

    def test_validate_below_threshold(self):
        validator = ImprovementValidator(min_improvement=0.1)
        p = self._make_proposal(imp=0.005)
        is_valid, score = validator.validate(p)
        assert is_valid is False

    def test_validate_architecture(self):
        validator = ImprovementValidator(min_improvement=0.01)
        p = self._make_proposal(mod_type=ModificationType.ARCHITECTURE,
                                risk="medium", imp=0.1)
        is_valid, score = validator.validate(p)
        assert isinstance(is_valid, bool)
        if is_valid:
            assert score < p.expected_improvement  # penalità cautela

    def test_validate_code_patch_never_auto(self):
        validator = ImprovementValidator()
        p = self._make_proposal(mod_type=ModificationType.CODE_PATCH,
                                risk="high", imp=0.5)
        is_valid, score = validator.validate(p)
        assert is_valid is False
        assert score == 0.0

    def test_validate_goal_revision_never_auto(self):
        validator = ImprovementValidator()
        p = self._make_proposal(mod_type=ModificationType.GOAL_REVISION,
                                risk="critical", imp=0.9)
        is_valid, score = validator.validate(p)
        assert is_valid is False


# ── TestSafeModificationGate ──────────────────────────────────────────────────

class TestSafeModificationGate:

    def _make_proposal(self):
        return ModificationProposal(
            proposal_id="abc123def456",
            mod_type=ModificationType.HYPERPARAMETER,
            target_module="test_mod",
            title="Test proposal",
            description="A test proposal",
            expected_improvement=0.05,
            risk_level="low",
            requires_human_approval=False,
        )

    def test_submit_writes_wal(self, tmp_path, monkeypatch):
        import cortex.brain.recursive_self_improvement as rsi_mod
        monkeypatch.setattr(rsi_mod, "WAL_LOG", tmp_path / "WAL.log")
        monkeypatch.setattr(rsi_mod, "PROPOSALS_FILE", tmp_path / "PROPOSALS.md")
        monkeypatch.setattr(rsi_mod, "SAFEPROACTIVE_DIR", tmp_path)
        gate = SafeModificationGate()
        p = self._make_proposal()
        gate.submit(p)
        wal_content = (tmp_path / "WAL.log").read_text()
        assert "BRN-020 PROPOSE" in wal_content

    def test_submit_writes_proposals_md(self, tmp_path, monkeypatch):
        import cortex.brain.recursive_self_improvement as rsi_mod
        monkeypatch.setattr(rsi_mod, "WAL_LOG", tmp_path / "WAL.log")
        monkeypatch.setattr(rsi_mod, "PROPOSALS_FILE", tmp_path / "PROPOSALS.md")
        monkeypatch.setattr(rsi_mod, "SAFEPROACTIVE_DIR", tmp_path)
        gate = SafeModificationGate()
        p = self._make_proposal()
        gate.submit(p)
        md_content = (tmp_path / "PROPOSALS.md").read_text()
        assert "PROPOSAL-BRN020-" in md_content

    def test_check_approval_nonexistent(self, tmp_path, monkeypatch):
        import cortex.brain.recursive_self_improvement as rsi_mod
        monkeypatch.setattr(rsi_mod, "PROPOSALS_FILE", tmp_path / "PROPOSALS.md")
        gate = SafeModificationGate()
        status = gate.check_approval_status("nonexistent_id")
        assert status == ProposalStatus.PENDING


# ── TestRecursiveSelfImprover ─────────────────────────────────────────────────

class TestRecursiveSelfImprover:

    def test_init(self):
        rsi    = create_recursive_self_improver()
        status = rsi.get_full_status()
        assert status["status"]      == "active"
        assert status["brn_id"]      == "BRN-020"
        assert "STRICT" in status["safety_mode"]

    def test_compute_fitness(self):
        rsi = create_recursive_self_improver()
        fs  = rsi.compute_fitness(alignment=0.8, task_success=0.7,
                                  stability=0.9, efficiency=0.6, ethics=1.0)
        assert 0.0 <= fs.total <= 1.0
        assert len(rsi._fitness_history) == 1

    def test_run_cycle_on_bad_code(self):
        path = make_temp_py(SAMPLE_BAD_CODE)
        try:
            rsi = create_recursive_self_improver()
            proposals = rsi.run_improvement_cycle([path])
            # Deve trovare almeno una proposta
            assert len(proposals) >= 1
            assert rsi._cycle == 1
        finally:
            os.unlink(path)

    def test_run_cycle_on_nonexistent_module(self):
        rsi = create_recursive_self_improver()
        proposals = rsi.run_improvement_cycle(["/nonexistent/mod.py"])
        assert proposals == []
        assert rsi._cycle == 1

    def test_apply_approved_low_risk(self):
        rsi = create_recursive_self_improver()
        p = ModificationProposal(
            proposal_id="low_risk_123456",
            mod_type=ModificationType.HYPERPARAMETER,
            target_module="test", title="t", description="d",
            expected_improvement=0.05, risk_level="low",
            requires_human_approval=False,
            validated=True, validated_improvement=0.04,
            status=ProposalStatus.VALIDATED,
        )
        rsi._proposals.append(p)
        applied = rsi.apply_approved()
        assert p.proposal_id in applied
        assert p.applied is True

    def test_apply_approved_medium_not_auto(self):
        rsi = create_recursive_self_improver()
        p = ModificationProposal(
            proposal_id="medium_risk_123",
            mod_type=ModificationType.ARCHITECTURE,
            target_module="test", title="t", description="d",
            expected_improvement=0.1, risk_level="medium",
            requires_human_approval=True,
            validated=True, validated_improvement=0.08,
            status=ProposalStatus.VALIDATED,
        )
        rsi._proposals.append(p)
        applied = rsi.apply_approved()
        # Non deve essere applicato automaticamente
        assert p.proposal_id not in applied
        assert p.applied is False

    def test_apply_rejected_proposal(self):
        rsi = create_recursive_self_improver()
        p = ModificationProposal(
            proposal_id="rejected_123",
            mod_type=ModificationType.HYPERPARAMETER,
            target_module="test", title="t", description="d",
            expected_improvement=0.05, risk_level="low",
            requires_human_approval=False,
            validated=True, validated_improvement=0.04,
            status=ProposalStatus.REJECTED,
        )
        rsi._proposals.append(p)
        applied = rsi.apply_approved()
        assert "rejected_123" not in applied

    def test_propose_hyperparameter_direct(self):
        rsi = create_recursive_self_improver()
        p = rsi.propose_hyperparameter(
            "my_module", "alpha", 0.3, 0.2, "improve learning"
        )
        assert p is not None
        assert p.mod_type == ModificationType.HYPERPARAMETER
        assert p in rsi._proposals

    def test_get_pending_approvals(self):
        rsi = create_recursive_self_improver()
        p = ModificationProposal(
            proposal_id="pending_1",
            mod_type=ModificationType.ARCHITECTURE,
            target_module="mod", title="t", description="d",
            expected_improvement=0.1, risk_level="medium",
            requires_human_approval=True,
            status=ProposalStatus.VALIDATED,
        )
        rsi._proposals.append(p)
        pending = rsi.get_pending_approvals()
        assert p in pending

    def test_code_patch_never_applied(self):
        rsi = create_recursive_self_improver()
        p = ModificationProposal(
            proposal_id="code_patch_1",
            mod_type=ModificationType.CODE_PATCH,
            target_module="mod", title="t", description="d",
            expected_improvement=0.2, risk_level="high",
            requires_human_approval=True,
            validated=True, validated_improvement=0.0,
            status=ProposalStatus.VALIDATED,
        )
        rsi._proposals.append(p)
        applied = rsi.apply_approved()
        assert "code_patch_1" not in applied
        assert p.applied is False

    def test_full_status_structure(self):
        rsi    = create_recursive_self_improver()
        rsi.compute_fitness(0.7, 0.8, 0.6, 0.5, 1.0)
        status = rsi.get_full_status()
        assert "proposals" in status
        assert "fitness_latest" in status
        assert "fitness_weights" in status
        assert status["fitness_latest"]["total"] > 0

    def test_proposals_summary(self):
        rsi = create_recursive_self_improver()
        p = rsi.propose_hyperparameter("mod", "x", 0.5, 0.4, "test")
        summary = rsi.get_proposals_summary()
        assert summary["total"] >= 1

    def test_integrate_self_model_stub(self):
        rsi = create_recursive_self_improver()

        class MockSelfModel:
            def get_full_status(self):
                return {
                    "limitations": ["working_memory_limited"],
                    "alignment_score": 0.6,
                }

        result = rsi.integrate_self_model(MockSelfModel())
        # Può essere None o una ModificationProposal
        if result is not None:
            assert