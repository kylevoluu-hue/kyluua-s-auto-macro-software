#!/usr/bin/env bash
# ============================================================
#  Build AutoMacro into a single executable on Linux
#  Usage:  bash build/build_linux.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo
echo "=== Building AutoMacro for Linux ==="
echo

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "[ERROR] python3 not found. Install Python 3.9+ with your package manager."
    exit 1
fi

# Tkinter is a system package on Linux; warn early if it is missing.
if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
    echo "[WARN] Python 'tkinter' is not available."
    echo "       Install it first, e.g.:  sudo apt install python3-tk"
    echo
fi

echo "Creating build environment..."
"$PY" -m venv .buildenv
# shellcheck disable=SC1091
source .buildenv/bin/activate

echo "Installing dependencies..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt pyinstaller

echo "Packaging (this can take a couple of minutes)..."
pyinstaller --noconfirm automacro.spec

echo
echo "============================================================"
echo " Done!  Your executable is here:"
echo "     dist/AutoMacro"
echo
echo " Optional: create a .desktop launcher so it appears in your"
echo " applications menu and can be pinned/favourited. See README."
echo
echo " For window targeting, install:  sudo apt install wmctrl xdotool"
echo "============================================================"
