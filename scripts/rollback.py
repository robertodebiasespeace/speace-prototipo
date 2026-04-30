"""
SPEACE Rollback – CLI Standalone
Versione: 1.0 | M2 – PROP-BENCHMARK-ROLLBACK-M2

Riusa le primitive di SafeProactive (snapshot/rollback/list_snapshots) e
aggiunge:
  - --list         : elenca snapshot disponibili
  - --dry-run      : mostra cosa ripristinerebbe (NESSUNA modifica)
  - --restore ID   : rollback effettivo, con conferma esplicita
  - --help         : help testuale

Safety:
  - --dry-run è sempre sicuro (read-only).
  - --restore richiede --yes oppure risposta interattiva "YES".
  - Prima di ogni restore viene creato uno snapshot "pre-rollback"
    tramite SafeProactive.rollback().
  - Non è prevista forzatura di override: i file ripristinati sono
    solo quelli presenti nello snapshot (digitaldna/ + state.json).
"""

import argparse
import json
import sys
from pathlib import Path

# --- Path setup ---------------------------------------------------------
_THIS = Path(__file__).resolve()
_ROOT = _THIS.parent.parent
sys.path.insert(0, str(_ROOT))

from safeproactive.safeproactive import SafeProactive, SNAPSHOTS_DIR  # noqa: E402


EXIT_OK = 0
EXIT_USER_ABORT = 2
EXIT_NOT_FOUND = 3
EXIT_ERROR = 4


def cmd_list() -> int:
    sp = SafeProactive()
    snaps = sp.list_snapshots()
    if not snaps:
        print("Nessuno snapshot disponibile.")
        return EXIT_OK

    print(f"Snapshot disponibili ({len(snaps)}):\n")
    print(f"{'ID':50s} {'Timestamp':26s} Label")
    print("-" * 100)
    for s in snaps:
        sid = s.get("id", "?")
        ts = s.get("timestamp", "?")
        lbl = s.get("label", "") or ""
        print(f"{sid:50s} {ts:26s} {lbl}")
    return EXIT_OK


def cmd_dry_run(snap_id: str) -> int:
    snap_dir = SNAPSHOTS_DIR / snap_id
    if not snap_dir.exists():
        print(f"[ERRORE] Snapshot '{snap_id}' non trovato in {SNAPSHOTS_DIR}")
        return EXIT_NOT_FOUND

    manifest_file = snap_dir / "manifest.json"
    if not manifest_file.exists():
        print(f"[ATTENZIONE] Manifest mancante in {snap_dir}")
    else:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        print(f"Snapshot: {manifest.get('id')}")
        print(f"Timestamp: {manifest.get('timestamp')}")
        print(f"Label: {manifest.get('label')}")
        print(f"Files: {manifest.get('files')}")

    print("\n[DRY-RUN] Il seguente contenuto VERREBBE ripristinato:")
    print("-" * 60)
    for f in sorted(snap_dir.iterdir()):
        if f.name == "manifest.json":
            continue
        dest_hint = "digitaldna/" + f.name if f.name != "state.json" else "state.json"
        size = f.stat().st_size
        print(f"  {f.name:40s} → {dest_hint:30s} ({size} bytes)")
    print("-" * 60)
    print("[DRY-RUN] Nessuna modifica effettuata. Per eseguire: --restore <ID> --yes")
    return EXIT_OK


def cmd_restore(snap_id: str, approver: str, auto_yes: bool) -> int:
    sp = SafeProactive()
    snap_dir = SNAPSHOTS_DIR / snap_id
    if not snap_dir.exists():
        print(f"[ERRORE] Snapshot '{snap_id}' non trovato.")
        return EXIT_NOT_FOUND

    print(f"\n⚠️  ROLLBACK a snapshot: {snap_id}")
    print(f"    Approver: {approver}")
    print("    Verranno sovrascritti: digitaldna/genome.yaml, digitaldna/epigenome.yaml, state.json")
    print("    Uno snapshot 'pre-rollback' verrà creato automaticamente prima.\n")

    if not auto_yes:
        try:
            resp = input("Digita 'YES' per confermare: ").strip()
        except EOFError:
            print("[ABORT] Input non interattivo e --yes non specificato.")
            return EXIT_USER_ABORT
        if resp != "YES":
            print("[ABORT] Rollback annullato dall'utente.")
            return EXIT_USER_ABORT

    try:
        sp.rollback(snap_id, approver=approver)
    except Exception as e:
        print(f"[ERRORE] Rollback fallito: {e}")
        return EXIT_ERROR

    print("\n[OK] Rollback completato.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="speace-rollback",
        description="SPEACE Rollback CLI — riuso primitive SafeProactive (M2).",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="Elenca snapshot disponibili")
    g.add_argument("--dry-run", metavar="SNAP_ID", help="Mostra cosa ripristinerebbe (no-op)")
    g.add_argument("--restore", metavar="SNAP_ID", help="Ripristina snapshot (richiede --yes o conferma interattiva)")
    p.add_argument("--approver", default="Roberto De Biase", help="Nome approver (default: Roberto De Biase)")
    p.add_argument("--yes", action="store_true", help="Salta prompt di conferma (usare con cautela)")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        return cmd_list()
    if args.dry_run:
        return cmd_dry_run(args.dry_run)
    if args.restore:
        return cmd_restore(args.restore, approver=args.approver, auto_yes=args.yes)
    return EXIT_ERROR  # unreachable


if __name__ == "__main__":
    sys.exit(main())
