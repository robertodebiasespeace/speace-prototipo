#!/usr/bin/env bash
# ============================================================
# SPEACE – Avvio rapido (Linux / macOS)
# chmod +x run_speace.sh && ./run_speace.sh
# ============================================================
set -e
cd "$(dirname "$0")"

echo ""
echo "  ███████╗██████╗ ███████╗ █████╗  ██████╗███████╗"
echo "  ██╔════╝██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝"
echo "  ███████╗██████╔╝█████╗  ███████║██║     █████╗  "
echo "  ╚════██║██╔═══╝ ██╔══╝  ██╔══██║██║     ██╔══╝  "
echo "  ███████║██║     ███████╗██║  ██║╚██████╗███████╗"
echo "  ╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝"
echo ""
echo "  SuPer Entità Autonoma Cibernetica Evolutiva v0.1.0"
echo "  Rigene Project — Roberto De Biase"
echo "  ============================================================"
echo ""

# Check Python version
PYTHON=$(which python3 || which python)
PYVER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python: $PYVER"
if [[ "$PYVER" < "3.10" ]]; then
    echo "[ERRORE] Python 3.10+ richiesto. Trovato: $PYVER"
    exit 1
fi

# Install deps if missing
if ! $PYTHON -c "import yaml, requests, psutil" &>/dev/null; then
    echo "[SETUP] Installazione dipendenze..."
    $PYTHON -m pip install -r requirements.txt
fi

# Parse mode from args, default to --brain
MODE="${1:---brain}"

echo "[AVVIO] Modalità: $MODE"
echo ""
exec $PYTHON SPEACE-main.py $MODE "$@"
