"""
SPEACE Team Scientifico – Orchestrator
Coordina i 10 agenti specializzati e produce il Daily Planetary Health Brief.

Versione: 1.0 | 2026-04-17
"""

import os
import sys
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
_THIS_DIR = Path(__file__).parent

# La cartella "scientific-team" contiene un trattino e non può essere
# importata come package. Registriamo un alias "scientific_team" che
# punta al filesystem reale, così da preservare gli import relativi degli
# agenti (`from .base_agent import BaseAgent`).
import importlib.util
import types as _types
if "scientific_team" not in sys.modules:
    _pkg = _types.ModuleType("scientific_team")
    _pkg.__path__ = [str(_THIS_DIR)]
    sys.modules["scientific_team"] = _pkg
if "scientific_team.agents" not in sys.modules:
    _agents_pkg = _types.ModuleType("scientific_team.agents")
    _agents_pkg.__path__ = [str(_THIS_DIR / "agents")]
    sys.modules["scientific_team.agents"] = _agents_pkg

OUTPUTS_DIR = _THIS_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# Import agenti tramite il package alias
from scientific_team.agents.climate_agent import ClimateAgent
from scientific_team.agents.economics_agent import EconomicsAgent
from scientific_team.agents.governance_agent import GovernanceAgent
from scientific_team.agents.technology_agent import TechnologyAgent
from scientific_team.agents.health_agent import HealthAgent
from scientific_team.agents.social_agent import SocialAgent
from scientific_team.agents.space_agent import SpaceAgent
from scientific_team.agents.regulatory_agent import RegulatoryAgent
from scientific_team.agents.adversarial_agent import AdversarialAgent
from scientific_team.agents.evidence_agent import EvidenceAgent


class ScientificTeamOrchestrator:
    """
    Orchestra il Team Scientifico SPEACE.
    Produce Daily Planetary Health Brief e proposte evolutive.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.agents = {
            "climate": ClimateAgent(self.api_key),
            "economics": EconomicsAgent(self.api_key),
            "governance": GovernanceAgent(self.api_key),
            "technology": TechnologyAgent(self.api_key),
            "health": HealthAgent(self.api_key),
            "social": SocialAgent(self.api_key),
            "space": SpaceAgent(self.api_key),
            "regulatory": RegulatoryAgent(self.api_key),
        }
        # Agenti speciali (eseguiti DOPO gli altri)
        self.adversarial = AdversarialAgent(self.api_key)
        self.evidence = EvidenceAgent(self.api_key)

    # M3L.5 — Gate di qualità pre-output
    # Soglie oltre le quali un brief è "rilasciabile" vs "degradato".
    GATE_THRESHOLDS = {
        "min_reliability_score":   0.40,  # sotto: degrade
        "min_adversarial_conf":    0.30,  # sotto: degrade
        "min_agents_ok_ratio":     0.60,  # <60% agenti OK → degrade
    }

    def run_daily_brief(self, world_model_summary: Optional[Dict] = None) -> str:
        """
        Esegue tutti gli agenti in parallelo e produce il Daily Brief.
        Include pre-output gate (Adversarial + Evidence) prima dell'emissione.
        """
        print("\n[ScientificTeam] 🔬 Avvio Daily Planetary Health Brief...")
        start = datetime.datetime.now()

        # Step 1: Esegui agenti principali in parallelo
        reports = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(agent.analyze, world_model_summary): name
                for name, agent in self.agents.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    reports[name] = future.result()
                    print(f"  ✓ {name.capitalize()} Agent completato")
                except Exception as e:
                    reports[name] = {"error": str(e), "status": "failed"}
                    print(f"  ✗ {name.capitalize()} Agent ERRORE: {e}")

        # Step 2: Adversarial Agent critica le proposte (GATE #1)
        print("\n  🔴 Adversarial Agent in analisi critica...")
        adversarial_review = self.adversarial.critique(reports)

        # Step 3: Evidence Agent verifica le fonti (GATE #2)
        print("  🔍 Evidence Agent in verifica fonti...")
        evidence_check = self.evidence.verify(reports)

        # Step 3.bis: Valuta il gate di qualità PRIMA di emettere il brief
        gate_result = self._evaluate_gate(reports, adversarial_review, evidence_check)
        status_icon = "🟢" if gate_result["passed"] else "🟡"
        print(f"  {status_icon} Quality Gate: {gate_result['status']} "
              f"(score={gate_result['score']:.2f})")
        for issue in gate_result.get("issues", []):
            print(f"     ⚠ {issue}")

        # Step 4: Compila il brief (con header gate)
        brief = self._compile_brief(
            reports, adversarial_review, evidence_check, start, gate_result
        )

        # Salva output
        self._save_brief(brief)
        # Salva anche i dati strutturati del gate per audit
        self._save_gate_audit(gate_result, start)
        print(f"\n[ScientificTeam] ✅ Brief completato in "
              f"{(datetime.datetime.now()-start).seconds}s")
        return brief

    def _evaluate_gate(self, reports: Dict,
                       adversarial: Dict, evidence: Dict) -> Dict:
        """
        Valuta il gate di qualità: unisce reliability (Evidence), confidence
        (Adversarial) e ratio agenti OK. Ritorna status + issues + score.
        Il gate NON blocca la pubblicazione ma la marca come degraded quando
        le soglie non sono rispettate (Fase 1: human-in-the-loop review).
        """
        issues: List[str] = []

        reliability = float(evidence.get("reliability_score", 0.0) or 0.0)
        adv_conf = float(adversarial.get("confidence", 0.0) or 0.0)
        total = max(len(reports), 1)
        # Un agente è "OK" se NON ha un error non-null. Alcuni agenti
        # ritornano {"error": None} in successo: non contarli come falliti.
        ok = sum(1 for r in reports.values() if not r.get("error"))
        ok_ratio = ok / total

        if reliability < self.GATE_THRESHOLDS["min_reliability_score"]:
            issues.append(
                f"Reliability score basso ({reliability:.2f} < "
                f"{self.GATE_THRESHOLDS['min_reliability_score']:.2f})"
            )
        if adv_conf < self.GATE_THRESHOLDS["min_adversarial_conf"]:
            issues.append(
                f"Adversarial confidence bassa ({adv_conf:.2f} < "
                f"{self.GATE_THRESHOLDS['min_adversarial_conf']:.2f})"
            )
        if ok_ratio < self.GATE_THRESHOLDS["min_agents_ok_ratio"]:
            issues.append(
                f"Solo {ok}/{total} agenti hanno risposto correttamente "
                f"(ratio {ok_ratio:.2f} < "
                f"{self.GATE_THRESHOLDS['min_agents_ok_ratio']:.2f})"
            )

        # Score aggregato (media pesata)
        score = (reliability * 0.45) + (adv_conf * 0.30) + (ok_ratio * 0.25)
        passed = len(issues) == 0

        return {
            "passed": passed,
            "status": "PASS" if passed else "DEGRADED",
            "score": round(score, 3),
            "reliability": round(reliability, 3),
            "adversarial_confidence": round(adv_conf, 3),
            "agents_ok_ratio": round(ok_ratio, 3),
            "agents_ok": ok,
            "agents_total": total,
            "issues": issues,
            "thresholds": dict(self.GATE_THRESHOLDS),
        }

    def _save_gate_audit(self, gate_result: Dict,
                          start: datetime.datetime) -> None:
        """Salva su file JSON l'esito del gate per audit/compliance."""
        date_str = start.strftime("%Y-%m-%d")
        audit_file = OUTPUTS_DIR / f"gate_audit_{date_str}.json"
        payload = {
            "timestamp": start.isoformat(),
            "gate": gate_result,
        }
        audit_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _compile_brief(self, reports: Dict, adversarial: Dict, evidence: Dict,
                       start: datetime.datetime,
                       gate_result: Optional[Dict] = None) -> str:
        """Compila il Daily Planetary Health Brief in Markdown."""
        date_str = start.strftime("%Y-%m-%d %H:%M")
        gate_result = gate_result or {}

        status_badge = "🟢 PASS" if gate_result.get("passed") else "🟡 DEGRADED"
        lines = [
            f"# 🌍 SPEACE Daily Planetary Health Brief",
            f"**Data:** {date_str}  ",
            f"**Generato da:** SPEACE Scientific Team (10 agenti)  ",
            f"**Quality Gate:** {status_badge} "
            f"(score={gate_result.get('score', 0):.2f} — "
            f"reliability={gate_result.get('reliability', 0):.2f}, "
            f"adv_conf={gate_result.get('adversarial_confidence', 0):.2f}, "
            f"agents_ok={gate_result.get('agents_ok', 0)}/"
            f"{gate_result.get('agents_total', 0)})  ",
            "",
        ]
        issues = gate_result.get("issues") or []
        if issues:
            lines.append("> **⚠ Avvertenze di qualità (pre-output gate):**")
            for iss in issues:
                lines.append(f"> - {iss}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 📊 Sintesi Planetaria",
            "",
        ])

        # Sezioni per ogni agente
        agent_labels = {
            "climate": "🌡️ Clima & Ecosistemi",
            "economics": "💹 Economia & Risorse",
            "governance": "⚖️ Governance & Etica",
            "technology": "🔬 Tecnologia (TFT)",
            "health": "🏥 Salute Globale",
            "social": "🤝 Coesione Sociale",
            "space": "🚀 Spazio & Espansione",
            "regulatory": "📋 Compliance & Regolatorio",
        }

        for key, label in agent_labels.items():
            report = reports.get(key, {})
            lines.append(f"### {label}")
            err = report.get("error")
            if err:  # Solo errori reali (non None/empty)
                lines.append(f"⚠️ *Agente non disponibile: {err}*")
            else:
                lines.append(report.get("summary", "*Nessun dato disponibile*"))
                if report.get("alerts"):
                    lines.append("\n**⚠️ Alert:**")
                    for alert in report["alerts"][:3]:
                        lines.append(f"- {alert}")
                if report.get("proposals"):
                    lines.append("\n**💡 Proposte:**")
                    for prop in report["proposals"][:2]:
                        lines.append(f"- {prop}")
            lines.append("")

        # Sezione critica Adversarial
        lines.extend([
            "---",
            "## 🔴 Revisione Critica (Adversarial Agent)",
            "",
            adversarial.get("critique", "*Nessuna critica generata*"),
            "",
        ])

        # Sezione verifica Evidence
        lines.extend([
            "---",
            "## 🔍 Verifica Fonti (Evidence Agent)",
            "",
            evidence.get("verification", "*Nessuna verifica eseguita*"),
            "",
        ])

        # Footer
        lines.extend([
            "---",
            f"*Generato automaticamente da SPEACE Cortex | {date_str}*",
        ])

        return "\n".join(lines)

    def _save_brief(self, brief: str):
        """Salva il brief su file."""
        date_str = datetime.date.today().isoformat()
        brief_file = OUTPUTS_DIR / f"daily_brief_{date_str}.md"
        brief_file.write_text(brief, encoding="utf-8")

        # Aggiorna anche il file principale
        (OUTPUTS_DIR / "daily_brief.md").write_text(brief, encoding="utf-8")
        print(f"  💾 Brief salvato: {brief_file.name}")
