#!/usr/bin/env bash
# ============================================================
#  Build AutoMacro into a pinnable macOS .app bundle
#  Usage:  bash build/build_macos.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

echo
echo "=== Building AutoMacro for macOS ==="
echo

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "[ERROR] python3 not found. Install Python 3.9+ from https://python.org"
    exit 1
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
echo " Done!  Your app bundle is here:"
echo "     dist/AutoMacro.app"
echo
echo " Drag it into /Applications, then keep it in the Dock."
echo " On first run, grant Accessibility permission in"
echo " System Settings > Privacy & Security > Accessibility."
echo "============================================================"
