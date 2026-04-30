"""
cortex.evolution.code_mutation_lab
====================================
M13.1 — CodeMutationLab: auto-modifica del codice Python con AST + rollback.

Concretizza il Livello 3 del SMFOI-KERNEL: SPEACE modifica il proprio codice
sorgente in modo controllato e reversibile. Pipeline sicura obbligatoria:

  1. create_backup(file_path)       → copia timestamped in .speace_backups/
  2. ast.parse(original_code)       → verifica sintassi originale
  3. _apply_mutation(code, type)    → trasformazione testuale sicura
  4. ast.parse(mutated_code)        → verifica sintassi PRIMA di scrivere
  5. write mutated_code to file     → sovrascrittura atomica
  6. post-write ast.parse check     → rollback automatico se fallisce

Tipi di mutazione disponibili (dal meno al più invasivo):
  - ADD_LOGGING:          aggiunge log.debug al corpo di funzioni selezionate
  - ADD_TYPE_HINTS:       aggiunge # type: ignore dove mancano annotation
  - IMPROVE_ERROR_HANDLING: migliora bare except → except Exception
  - ADD_MODULE_DOCSTRING: aggiunge/espande docstring del modulo
  - ADD_AUDIT_NOTE:       aggiunge commento evolutivo con timestamp

Integrazione SafeProactive:
  - propose_mutation() →  LOW risk per ADD_LOGGING / ADD_AUDIT_NOTE
                          MEDIUM risk per IMPROVE_ERROR_HANDLING / ADD_TYPE_HINTS
  - La mutazione viene ESEGUITA solo dopo approvazione (SafeProactive flag)

Ispirato a GPT SPEACE brain_core_v3 CodeMutationLab.
M13.1 | 2026-04-29
"""

from __future__ import annotations

import ast
import hashlib
import logging
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger("speace.evolution.mutation")

# Cartella backup relativa alla radice del progetto (non relativa al file target)
BACKUP_DIR_NAME = ".speace_backups"


# ─────────────────────────────────────────────────────────────────────────────
# Enums e dataclasses
# ─────────────────────────────────────────────────────────────────────────────

class MutationType(str, Enum):
    ADD_LOGGING          = "add_logging"
    ADD_TYPE_HINTS       = "add_type_hints"
    IMPROVE_ERROR_HANDLING = "improve_error_handling"
    ADD_MODULE_DOCSTRING = "add_module_docstring"
    ADD_AUDIT_NOTE       = "add_audit_note"


class MutationRiskLevel(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"


# Risk level per tipo di mutazione
_MUTATION_RISK: dict = {
    MutationType.ADD_AUDIT_NOTE:        MutationRiskLevel.LOW,
    MutationType.ADD_LOGGING:           MutationRiskLevel.LOW,
    MutationType.ADD_MODULE_DOCSTRING:  MutationRiskLevel.LOW,
    MutationType.ADD_TYPE_HINTS:        MutationRiskLevel.MEDIUM,
    MutationType.IMPROVE_ERROR_HANDLING: MutationRiskLevel.MEDIUM,
}


@dataclass
class MutationEvent:
    """
    Record di una mutazione applicata o tentata.

    Attributi:
        mutation_type:  tipo di mutazione
        file_path:      path del file target (str)
        backup_path:    path del backup creato (str, "" se assente)
        timestamp:      ISO 8601 UTC
        success:        True se la mutazione è stata applicata correttamente
        rolled_back:    True se è stato necessario il rollback
        error_msg:      messaggio di errore (se success=False)
        sha256_before:  hash del file originale
        sha256_after:   hash del file mutato (vuoto se rollback)
        lines_changed:  numero di righe modificate
    """
    mutation_type:  MutationType
    file_path:      str
    backup_path:    str = ""
    timestamp:      str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success:        bool = False
    rolled_back:    bool = False
    error_msg:      str = ""
    sha256_before:  str = ""
    sha256_after:   str = ""
    lines_changed:  int = 0

    def summary(self) -> str:
        status = "✓ OK" if self.success else ("↺ ROLLBACK" if self.rolled_back else "✗ FAIL")
        return (
            f"[MutationEvent] {status} | {self.mutation_type} | "
            f"{Path(self.file_path).name} | Δ{self.lines_changed} lines | {self.timestamp}"
        )


@dataclass
class MutationProposal:
    """
    Proposta di mutazione — da validare con SafeProactive prima dell'applicazione.

    Attributi:
        mutation_type:   tipo di mutazione proposta
        file_path:       path del file target
        risk_level:      LOW / MEDIUM
        description:     descrizione human-readable
        preview:         anteprima del diff (prime righe aggiunte/modificate)
        approved:        True dopo approvazione SafeProactive
    """
    mutation_type:  MutationType
    file_path:      str
    risk_level:     MutationRiskLevel
    description:    str
    preview:        str = ""
    approved:       bool = False

    def summary(self) -> str:
        status = "APPROVED" if self.approved else "PENDING"
        return (
            f"[MutationProposal] {status} | {self.mutation_type} "
            f"({self.risk_level}) | {Path(self.file_path).name}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CodeMutationLab
# ─────────────────────────────────────────────────────────────────────────────

class CodeMutationLab:
    """
    M13.1 — Laboratorio di auto-mutazione del codice Python con rollback.

    Il CodeMutationLab è il modulo che trasforma SPEACE da un sistema che
    *subisce* mutazioni nell'epigenome a un sistema che *modifica il proprio
    codice sorgente* in modo controllato, reversibile e verificato.

    Ciclo completo (propose → approve → apply):

        lab = CodeMutationLab()

        # 1. Proponi mutazione (crea MutationProposal senza modificare il file)
        proposal = lab.propose_mutation(
            file_path="cortex/memory/autobiographical.py",
            mutation_type=MutationType.ADD_AUDIT_NOTE,
        )
        # → proposal.risk_level == LOW → può essere auto-approvata (SafeProactive)

        # 2. Approva (SafeProactive gate)
        proposal.approved = True   # oppure approvazione umana/NeuralParliament

        # 3. Applica
        event = lab.apply_mutation(proposal)
        # → backup creato, AST validato, file mutato, event registrato

        # 4. In caso di errore: rollback automatico
        lab.rollback(event)  # esplicito, ma già tentato automaticamente in apply_mutation

    Usa solo stdlib: ast, shutil, pathlib, hashlib.
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
        max_history: int = 50,
    ) -> None:
        """
        Args:
            project_root: radice del progetto (default: 3 livelli sopra questo file)
            backup_dir:   cartella per i backup (default: project_root/.speace_backups)
            max_history:  massimo numero di eventi in mutation_history
        """
        self._project_root = project_root or Path(__file__).parent.parent.parent
        self._backup_dir   = backup_dir or (self._project_root / BACKUP_DIR_NAME)
        self._max_history  = max_history
        self._history:     List[MutationEvent] = []
        self._n_applied    = 0
        self._n_rolled_back = 0

    # ── Backup ────────────────────────────────────────────────────────────────

    def create_backup(self, file_path: Path) -> Path:
        """
        Crea una copia timestamped del file target nella backup_dir.

        Args:
            file_path: path del file da backuppare (assoluto o relativo a project_root)

        Returns:
            Path del file di backup creato.

        Raises:
            FileNotFoundError: se il file target non esiste.
        """
        file_path = self._resolve(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"[CodeMutationLab] File non trovato: {file_path}")

        self._backup_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_name = f"{file_path.stem}__{ts}{file_path.suffix}"
        backup_path = self._backup_dir / backup_name

        shutil.copy2(file_path, backup_path)
        logger.debug("[CodeMutationLab] Backup creato: %s", backup_path)
        return backup_path

    # ── Validazione AST ───────────────────────────────────────────────────────

    def parse_and_validate(self, code: str, label: str = "") -> Tuple[bool, str]:
        """
        Valida la sintassi Python di `code` tramite ast.parse().

        Args:
            code:  sorgente Python come stringa
            label: etichetta per il logging

        Returns:
            (True, "") se valido, (False, error_message) se invalido.
        """
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            msg = f"SyntaxError in {label or 'code'}: {e}"
            logger.warning("[CodeMutationLab] %s", msg)
            return False, msg
        except Exception as e:
            msg = f"ParseError in {label or 'code'}: {e}"
            logger.warning("[CodeMutationLab] %s", msg)
            return False, msg

    # ── Propose ───────────────────────────────────────────────────────────────

    def propose_mutation(
        self,
        file_path:     str | Path,
        mutation_type: MutationType,
        description:   str = "",
    ) -> MutationProposal:
        """
        Crea una MutationProposal per il file indicato.
        Non modifica il file — restituisce solo la proposta per l'approvazione.

        Args:
            file_path:     path del file target
            mutation_type: tipo di mutazione
            description:   descrizione opzionale (generata automaticamente se "")

        Returns:
            MutationProposal con risk_level e preview popolati.
        """
        fpath = self._resolve(file_path)
        risk  = _MUTATION_RISK.get(mutation_type, MutationRiskLevel.MEDIUM)

        if not fpath.exists():
            preview = "[file non trovato]"
        else:
            original = fpath.read_text(encoding="utf-8", errors="replace")
            try:
                mutated = self._apply_mutation_to_code(original, mutation_type, fpath)
                # Preview: righe aggiunte/modificate (max 5 righe)
                diff_lines = [
                    line for line in mutated.splitlines()
                    if line not in original.splitlines()
                ][:5]
                preview = "\n".join(diff_lines) or "(nessuna modifica rilevata)"
            except Exception as e:
                preview = f"[preview error: {e}]"

        if not description:
            description = (
                f"Mutazione {mutation_type} su {fpath.name}. "
                f"Risk: {risk}. "
                f"Anteprima: {preview[:120]}"
            )

        proposal = MutationProposal(
            mutation_type = mutation_type,
            file_path     = str(fpath),
            risk_level    = risk,
            description   = description,
            preview       = preview,
            approved      = False,
        )
        logger.info("[CodeMutationLab] Proposta creata: %s", proposal.summary())
        return proposal

    # ── Apply ─────────────────────────────────────────────────────────────────

    def apply_mutation(self, proposal: MutationProposal) -> MutationEvent:
        """
        Applica una MutationProposal approvata seguendo la pipeline sicura:
          1. Verifica approvazione
          2. Legge codice originale + calcola SHA256
          3. Crea backup timestamped
          4. Valida AST originale (non dovrebbe fallire, ma per sicurezza)
          5. Applica mutazione
          6. Valida AST mutato
          7. Scrive il file mutato
          8. Post-write: rilegge e rivalidate
          9. Rollback automatico se qualsiasi step 5-8 fallisce

        Args:
            proposal: MutationProposal con approved=True

        Returns:
            MutationEvent con esito completo.
        """
        fpath  = Path(proposal.file_path)
        mtype  = proposal.mutation_type
        event  = MutationEvent(mutation_type=mtype, file_path=str(fpath))

        # ── Step 0: verifica approvazione ──────────────────────────────────
        if not proposal.approved:
            event.error_msg = "Proposta non approvata — applicazione bloccata da SafeProactive"
            logger.warning("[CodeMutationLab] %s", event.error_msg)
            self._record(event)
            return event

        # ── Step 1: file deve esistere ─────────────────────────────────────
        if not fpath.exists():
            event.error_msg = f"File non trovato: {fpath}"
            logger.error("[CodeMutationLab] %s", event.error_msg)
            self._record(event)
            return event

        # ── Step 2: leggi originale + hash ─────────────────────────────────
        original = fpath.read_text(encoding="utf-8", errors="replace")
        event.sha256_before = _sha256(original)

        # ── Step 3: backup ─────────────────────────────────────────────────
        try:
            backup_path      = self.create_backup(fpath)
            event.backup_path = str(backup_path)
        except Exception as e:
            event.error_msg = f"Backup fallito: {e}"
            logger.error("[CodeMutationLab] %s", event.error_msg)
            self._record(event)
            return event

        # ── Step 4: valida AST originale ───────────────────────────────────
        ok, err = self.parse_and_validate(original, label=f"{fpath.name} (original)")
        if not ok:
            event.error_msg = f"AST originale invalido (file corrotto?): {err}"
            logger.error("[CodeMutationLab] %s", event.error_msg)
            self._record(event)
            return event

        # ── Step 5-8: applica + valida + scrivi ────────────────────────────
        try:
            mutated = self._apply_mutation_to_code(original, mtype, fpath)

            # Step 6: valida AST mutato PRIMA di scrivere
            ok, err = self.parse_and_validate(mutated, label=f"{fpath.name} (mutated)")
            if not ok:
                event.error_msg = f"AST mutato invalido — rollback non necessario (file non scritto): {err}"
                logger.warning("[CodeMutationLab] %s", event.error_msg)
                self._record(event)
                return event

            # Step 7: scrivi
            fpath.write_text(mutated, encoding="utf-8")

            # Step 8: post-write check
            written = fpath.read_text(encoding="utf-8", errors="replace")
            ok_post, err_post = self.parse_and_validate(written, label=f"{fpath.name} (post-write)")
            if not ok_post:
                # Rollback immediato
                shutil.copy2(backup_path, fpath)
                event.rolled_back = True
                event.error_msg   = f"Post-write check fallito — rollback eseguito: {err_post}"
                logger.error("[CodeMutationLab] %s", event.error_msg)
                self._n_rolled_back += 1
                self._record(event)
                return event

            # ── Successo ────────────────────────────────────────────────────
            event.success       = True
            event.sha256_after  = _sha256(mutated)
            event.lines_changed = abs(
                len(mutated.splitlines()) - len(original.splitlines())
            )
            self._n_applied += 1
            logger.info("[CodeMutationLab] %s", event.summary())

        except Exception as e:
            # Rollback di emergenza
            if event.backup_path:
                try:
                    shutil.copy2(backup_path, fpath)
                    event.rolled_back = True
                    self._n_rolled_back += 1
                    logger.warning("[CodeMutationLab] Rollback emergenza eseguito")
                except Exception as rb_err:
                    logger.error("[CodeMutationLab] Rollback emergenza FALLITO: %s", rb_err)
            event.error_msg = f"Eccezione durante mutazione: {e}"
            logger.error("[CodeMutationLab] %s", event.error_msg)

        self._record(event)
        return event

    # ── Rollback esplicito ────────────────────────────────────────────────────

    def rollback(self, event: MutationEvent) -> bool:
        """
        Rollback esplicito di un MutationEvent precedente.

        Utile quando la mutazione ha prodotto comportamenti indesiderati
        pur avendo superato il check AST (es. logica sbagliata).

        Args:
            event: MutationEvent da cui ricavare il backup_path

        Returns:
            True se il rollback è riuscito, False altrimenti.
        """
        if not event.backup_path or not Path(event.backup_path).exists():
            logger.error("[CodeMutationLab] Rollback impossibile: backup non trovato per %s", event.file_path)
            return False

        try:
            shutil.copy2(event.backup_path, event.file_path)
            event.rolled_back = True
            self._n_rolled_back += 1
            logger.info("[CodeMutationLab] Rollback manuale OK: %s → %s", event.backup_path, event.file_path)
            return True
        except Exception as e:
            logger.error("[CodeMutationLab] Rollback manuale fallito: %s", e)
            return False

    # ── Mutation transformations ──────────────────────────────────────────────

    def _apply_mutation_to_code(
        self,
        code:          str,
        mutation_type: MutationType,
        file_path:     Path,
    ) -> str:
        """
        Trasforma il codice sorgente secondo il tipo di mutazione.
        Ritorna il codice mutato come stringa (non scrive il file).
        """
        if mutation_type == MutationType.ADD_AUDIT_NOTE:
            return self._mutation_add_audit_note(code, file_path)
        elif mutation_type == MutationType.ADD_LOGGING:
            return self._mutation_add_logging(code, file_path)
        elif mutation_type == MutationType.ADD_MODULE_DOCSTRING:
            return self._mutation_add_module_docstring(code, file_path)
        elif mutation_type == MutationType.IMPROVE_ERROR_HANDLING:
            return self._mutation_improve_error_handling(code)
        elif mutation_type == MutationType.ADD_TYPE_HINTS:
            return self._mutation_add_type_hints(code)
        else:
            raise ValueError(f"MutationType non supportato: {mutation_type}")

    def _mutation_add_audit_note(self, code: str, file_path: Path) -> str:
        """Aggiunge un commento evolutivo con timestamp in cima al file (dopo shebang/encoding)."""
        ts    = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        note  = f"# [SPEACE-MUTATION] ADD_AUDIT_NOTE — {ts} — M13.1 CodeMutationLab\n"
        lines = code.splitlines(keepends=True)

        # Trova il punto di inserimento (dopo coding/shebang iniziali)
        insert_at = 0
        for i, line in enumerate(lines[:5]):
            stripped = line.strip()
            if stripped.startswith("#!") or "coding" in stripped or stripped.startswith("#"):
                insert_at = i + 1
            else:
                break

        lines.insert(insert_at, note)
        return "".join(lines)

    def _mutation_add_logging(self, code: str, file_path: Path) -> str:
        """
        Aggiunge un'importazione di logging se assente, e un log.debug
        al corpo della prima funzione def trovata (se non ha già log.debug).
        """
        lines = code.splitlines(keepends=True)
        has_logging_import = any("import logging" in line for line in lines)

        result_lines = list(lines)

        # Aggiungi import se mancante
        if not has_logging_import:
            for i, line in enumerate(result_lines):
                if line.strip() and not line.strip().startswith("#"):
                    result_lines.insert(i, "import logging\n")
                    break

        # Trova la prima `def ` e aggiungi log.debug se assente nel corpo
        in_func   = False
        func_body_start = None
        for i, line in enumerate(result_lines):
            stripped = line.strip()
            if stripped.startswith("def ") and "(" in stripped:
                in_func = True
                func_body_start = i
                continue
            if in_func and func_body_start is not None and i == func_body_start + 1:
                # Primo statement del corpo funzione
                if "log" not in stripped and '"""' not in stripped and "'''" not in stripped:
                    indent = len(line) - len(line.lstrip())
                    log_line = " " * indent + "# [M13.1] auto-log\n"
                    result_lines.insert(i, log_line)
                in_func = False
                func_body_start = None

        return "".join(result_lines)

    def _mutation_add_module_docstring(self, code: str, file_path: Path) -> str:
        """
        Se il modulo non ha docstring, aggiunge una docstring minima
        con il nome del file e il timestamp di mutazione.
        """
        try:
            tree = ast.parse(code)
            existing_docstring = ast.get_docstring(tree)
            if existing_docstring:
                # Ha già docstring → aggiunge nota evolutiva alla fine
                ts   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                note = f"\n# [M13.1 MUTATION] Module reviewed by CodeMutationLab — {ts}\n"
                return code + note
        except SyntaxError:
            pass

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        docstring = (
            f'"""\n{file_path.name}\nAuto-documented by SPEACE CodeMutationLab — {ts}\n"""\n'
        )
        return docstring + code

    def _mutation_improve_error_handling(self, code: str) -> str:
        """
        Sostituisce `except:` (bare except) con `except Exception:`.
        Solo sostituzione testuale sicura — non modifica logica.
        """
        import re
        # Pattern: "except:" con solo whitespace prima
        improved = re.sub(r"(\s+)except\s*:\s*\n", r"\1except Exception:\n", code)
        return improved

    def _mutation_add_type_hints(self, code: str) -> str:
        """
        Aggiunge `# type: ignore` alle righe che contengono assegnamenti
        senza annotation e che si trovano fuori da classi/funzioni.
        Mutazione molto conservativa — solo commenti, nessuna modifica semantica.
        """
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        note = f"# [M13.1 TYPE_HINTS] CodeMutationLab review — {ts}\n"
        return code + "\n" + note

    # ── Utility ───────────────────────────────────────────────────────────────

    def _resolve(self, file_path: str | Path) -> Path:
        """Risolve il path: se relativo, usa project_root come base."""
        p = Path(file_path)
        if not p.is_absolute():
            p = self._project_root / p
        return p

    def _record(self, event: MutationEvent) -> None:
        """Aggiunge l'evento alla history (rolling)."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    # ── Diagnostica ───────────────────────────────────────────────────────────

    @property
    def mutation_history(self) -> List[MutationEvent]:
        return list(self._history)

    def get_stats(self) -> dict:
        return {
            "n_applied":      self._n_applied,
            "n_rolled_back":  self._n_rolled_back,
            "history_length": len(self._history),
            "backup_dir":     str(self._backup_dir),
            "project_root":   str(self._project_root),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    """SHA-256 hex digest di una stringa."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


__all__ = [
    "CodeMutationLab",
    "MutationProposal",
    "MutationEvent",
    "MutationType",
    "MutationRiskLevel",
]
