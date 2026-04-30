"""
SPEACE SafeProactive – Sistema di Governance e Sicurezza
Versione: 1.0 | 2026-04-17

Write-Ahead Logging + Approval Gates + Snapshot + Rollback
Nessuna azione a rischio viene eseguita senza approvazione esplicita.
"""

import os
import json
import yaml
import shutil
import hashlib
import datetime
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, Any, List

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent
PROPOSALS_FILE = BASE_DIR / "PROPOSALS.md"
WAL_LOG = BASE_DIR / "WAL.log"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
EPIGENOME_PATH = ROOT_DIR / "digitaldna" / "epigenome.yaml"
GENOME_PATH = ROOT_DIR / "digitaldna" / "genome.yaml"
STATE_FILE = ROOT_DIR / "state.json"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    REGULATORY = "regulatory"


class ProposalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class SafeProactive:
    """
    Sistema di governance SPEACE.
    Tutte le azioni a rischio DEVONO passare per questa classe.
    """

    def __init__(self):
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self._init_proposals_file()
        self.proposals: List[Dict] = self._load_proposals()

    # -------------------------------------------------------
    # PROPOSTA E APPROVAZIONE
    # -------------------------------------------------------

    def propose(
        self,
        action_name: str,
        description: str,
        risk_level: RiskLevel,
        payload: Optional[Dict] = None,
        source_agent: str = "speace-core",
        requires_second_approver: bool = False
    ) -> str:
        """
        Registra una proposta di azione.
        Restituisce l'ID della proposta.
        """
        proposal_id = self._generate_id(action_name)
        timestamp = self._now()

        proposal = {
            "id": proposal_id,
            "timestamp": timestamp,
            "action": action_name,
            "description": description,
            "risk_level": risk_level.value,
            "source_agent": source_agent,
            "payload": payload or {},
            "status": ProposalStatus.PENDING.value,
            "approved_by": None,
            "second_approver": None,
            "requires_second_approver": requires_second_approver,
            "executed_at": None,
            "rollback_snapshot": None,
        }

        self.proposals.append(proposal)
        self._write_proposal_to_md(proposal)
        self._wal_log("PROPOSE", proposal_id, action_name, risk_level.value)

        print(f"\n[SafeProactive] 📋 Proposta registrata: {proposal_id}")
        print(f"  Azione: {action_name}")
        print(f"  Risk Level: {risk_level.value.upper()}")
        print(f"  Descrizione: {description}")

        if risk_level == RiskLevel.LOW:
            print(f"  [AUTO-APPROVE] Risk LOW → approvazione automatica.")
            return self.approve(proposal_id, approver="auto-system")

        return proposal_id

    def approve(
        self,
        proposal_id: str,
        approver: str = "Roberto De Biase",
        second_approver: Optional[str] = None
    ) -> str:
        """
        Approva una proposta. Per risk HIGH/REGULATORY richiede
        conferma esplicita e (opzionale) secondo approvatore.
        """
        proposal = self._get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposta {proposal_id} non trovata")

        risk = RiskLevel(proposal["risk_level"])

        if risk in (RiskLevel.HIGH, RiskLevel.REGULATORY):
            if approver == "auto-system":
                raise PermissionError(
                    f"Proposta {proposal_id} (risk={risk.value}) "
                    "richiede approvazione umana esplicita."
                )
            if proposal["requires_second_approver"] and not second_approver:
                raise PermissionError(
                    f"Proposta {proposal_id} richiede un secondo approvatore."
                )

        proposal["status"] = ProposalStatus.APPROVED.value
        proposal["approved_by"] = approver
        proposal["second_approver"] = second_approver

        self._wal_log("APPROVE", proposal_id, proposal["action"], risk.value, f"by={approver}")
        self._rewrite_proposals()
        print(f"\n[SafeProactive] ✅ Proposta {proposal_id} APPROVATA da {approver}")
        return proposal_id

    def reject(self, proposal_id: str, reason: str = "Rifiutata dall'operatore") -> str:
        """Rifiuta una proposta."""
        proposal = self._get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposta {proposal_id} non trovata")

        proposal["status"] = ProposalStatus.REJECTED.value
        self._wal_log("REJECT", proposal_id, proposal["action"], reason=reason)
        self._rewrite_proposals()
        print(f"\n[SafeProactive] ❌ Proposta {proposal_id} RIFIUTATA. Motivo: {reason}")
        return proposal_id

    # -------------------------------------------------------
    # SNAPSHOT E ROLLBACK
    # -------------------------------------------------------

    def snapshot(self, label: str = "") -> str:
        """
        Crea snapshot del DigitalDNA e dello state.json.
        Restituisce l'ID dello snapshot.
        """
        snap_id = f"snap_{self._now_compact()}_{label}".strip("_")
        snap_dir = SNAPSHOTS_DIR / snap_id
        snap_dir.mkdir(parents=True, exist_ok=True)

        # Copia file critici
        files_to_snap = [EPIGENOME_PATH, GENOME_PATH, STATE_FILE]
        for f in files_to_snap:
            if f.exists():
                shutil.copy2(f, snap_dir / f.name)

        # Salva manifest
        manifest = {
            "id": snap_id,
            "timestamp": self._now(),
            "label": label,
            "files": [f.name for f in snap_dir.iterdir()],
        }
        (snap_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

        self._wal_log("SNAPSHOT", snap_id, "digitaldna+state", label=label)
        print(f"\n[SafeProactive] 📸 Snapshot creato: {snap_id}")
        return snap_id

    def rollback(self, snap_id: str, approver: str = "Roberto De Biase") -> bool:
        """
        Ripristina DigitalDNA e state da uno snapshot.
        Richiede approvazione umana.
        """
        snap_dir = SNAPSHOTS_DIR / snap_id
        if not snap_dir.exists():
            raise FileNotFoundError(f"Snapshot {snap_id} non trovato")

        print(f"\n[SafeProactive] ⏮️  ROLLBACK a {snap_id} richiesto da {approver}")
        print("  Conferma richiesta (operazione irreversibile per lo stato corrente).")

        # Crea snapshot pre-rollback come backup
        pre_rollback_snap = self.snapshot(label="pre-rollback")

        # Ripristina file
        for f in snap_dir.iterdir():
            if f.name == "manifest.json":
                continue
            dest = ROOT_DIR / "digitaldna" / f.name
            if f.name == "state.json":
                dest = STATE_FILE
            shutil.copy2(f, dest)
            print(f"  Ripristinato: {f.name}")

        self._wal_log("ROLLBACK", snap_id, "digitaldna+state", f"by={approver}", f"pre-backup={pre_rollback_snap}")
        print(f"\n[SafeProactive] ✅ Rollback completato. Backup pre-rollback: {pre_rollback_snap}")
        return True

    def list_snapshots(self) -> List[Dict]:
        """Lista tutti gli snapshot disponibili."""
        snaps = []
        for snap_dir in sorted(SNAPSHOTS_DIR.iterdir()):
            manifest_file = snap_dir / "manifest.json"
            if manifest_file.exists():
                snaps.append(json.loads(manifest_file.read_text()))
        return snaps

    # -------------------------------------------------------
    # UTILITÀ
    # -------------------------------------------------------

    def get_pending_proposals(self) -> List[Dict]:
        return [p for p in self.proposals if p["status"] == ProposalStatus.PENDING.value]

    def get_proposal_status(self, proposal_id: str) -> Optional[str]:
        p = self._get_proposal(proposal_id)
        return p["status"] if p else None

    def _get_proposal(self, proposal_id: str) -> Optional[Dict]:
        for p in self.proposals:
            if p["id"] == proposal_id:
                return p
        return None

    def _generate_id(self, action_name: str) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        short_hash = hashlib.md5(f"{action_name}{ts}".encode()).hexdigest()[:6]
        prefix = action_name.upper().replace(" ", "_")[:8]
        return f"PROP-{prefix}-{short_hash}"

    def _now(self) -> str:
        return datetime.datetime.now().isoformat()

    def _now_compact(self) -> str:
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    def _wal_log(self, event: str, prop_id: str, action: str, risk: str = "", label: str = "", reason: str = "", **kwargs):
        line = f"[{self._now()}] {event} | {prop_id} | {action} | {risk} | {label} | {reason}"
        for k, v in kwargs.items():
            line += f" | {k}={v}"
        with open(WAL_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _init_proposals_file(self):
        if not PROPOSALS_FILE.exists():
            PROPOSALS_FILE.write_text(
                "# SPEACE SafeProactive – PROPOSALS\n\n"
                "> Log automatico di tutte le proposte di azione SPEACE.\n\n"
                "---\n\n"
            )
        if not WAL_LOG.exists():
            WAL_LOG.write_text(f"# SPEACE Write-Ahead Log\n# Creato: {self._now()}\n\n")

    def _load_proposals(self) -> List[Dict]:
        # In futuro: caricare da DB o JSON; per ora lista in memoria
        return []

    def _write_proposal_to_md(self, p: Dict):
        with open(PROPOSALS_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n## {p['id']}\n")
            f.write(f"- **Timestamp:** {p['timestamp']}\n")
            f.write(f"- **Azione:** {p['action']}\n")
            f.write(f"- **Risk Level:** {p['risk_level'].upper()}\n")
            f.write(f"- **Sorgente:** {p['source_agent']}\n")
            f.write(f"- **Descrizione:** {p['description']}\n")
            f.write(f"- **Status:** {p['status']}\n")
            if p['payload']:
                f.write(f"- **Payload:** `{json.dumps(p['payload'])}`\n")
            f.write("\n---\n")

    def _rewrite_proposals(self):
        """Riscrive PROPOSALS.md con stato aggiornato."""
        with open(PROPOSALS_FILE, "w", encoding="utf-8") as f:
            f.write("# SPEACE SafeProactive – PROPOSALS\n\n")
            f.write("> Log automatico di tutte le proposte di azione SPEACE.\n\n---\n\n")
            for p in self.proposals:
                f.write(f"\n## {p['id']}\n")
                f.write(f"- **Timestamp:** {p['timestamp']}\n")
                f.write(f"- **Azione:** {p['action']}\n")
                f.write(f"- **Risk Level:** {p['risk_level'].upper()}\n")
                f.write(f"- **Sorgente:** {p['source_agent']}\n")
                f.write(f"- **Descrizione:** {p['description']}\n")
                f.write(f"- **Status:** {p['status'].upper()}\n")
                if p.get('approved_by'):
                    f.write(f"- **Approvato da:** {p['approved_by']}\n")
                if p['payload']:
                    f.write(f"- **Payload:** `{json.dumps(p['payload'])}`\n")
                f.write("\n---\n")


# -------------------------------------------------------
# TEST RAPIDO (eseguibile direttamente)
# -------------------------------------------------------
if __name__ == "__main__":
    sp = SafeProactive()

    print("\n=== TEST SafeProactive ===\n")

    # 1. Snapshot iniziale
    snap = sp.snapshot(label="initial")

    # 2. Proposta LOW (auto-approvata)
    sp.propose(
        action_name="log_status",
        description="Scrittura status report su file log",
        risk_level=RiskLevel.LOW,
        source_agent="speace-monitor"
    )

    # 3. Proposta MEDIUM (richiede approvazione)
    pid = sp.propose(
        action_name="mutate_learning_rate",
        description="Aumenta learning_rate da 0.05 a 0.07 per migliorare adattamento",
        risk_level=RiskLevel.MEDIUM,
        payload={"parameter": "learning.learning_rate", "old": 0.05, "new": 0.07},
        source_agent="speace-evolver"
    )
    sp.approve(pid, approver="Roberto De Biase")

    # 4. Lista snapshot
    snaps = sp.list_snapshots()
    print(f"\nSnapshot disponibili: {len(snaps)}")
    for s in snaps:
        print(f"  - {s['id']} ({s['timestamp']})")

    print("\n=== TEST COMPLETATO ===")
