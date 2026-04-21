#!/bin/bash
# Build Windows EXE using Docker/Podman on any Linux
# Wymaga: docker lub podman na maszynie x86_64

set -e

CONTAINER_CMD=""
if command -v docker &>/dev/null; then
    CONTAINER_CMD="docker"
elif command -v podman &>/dev/null; then
    CONTAINER_CMD="podman"
else
    echo "[BLAD] Nie znaleziono docker ani podman!"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"
mkdir -p "$OUTPUT_DIR"

# Ensure we have antygona.txt (create dummy if missing)
if [ ! -f "$SCRIPT_DIR/antygona.txt" ] && [ -f "$SCRIPT_DIR/../antygona.txt" ]; then
    cp "$SCRIPT_DIR/../antygona.txt" "$SCRIPT_DIR/antygona.txt"
fi

echo "[*] Budowanie obrazu Docker..."
$CONTAINER_CMD build --platform linux/amd64 -t stego-builder "$SCRIPT_DIR"

echo "[*] Uruchamianie buildu..."
$CONTAINER_CMD run --platform linux/amd64 --rm \
    -v "$OUTPUT_DIR:/output" \
    stego-builder

echo ""
echo "[+] === GOTOWE ==="
if ls "$OUTPUT_DIR"/*.exe 1>/dev/null 2>&1; then
    ls -lh "$OUTPUT_DIR"/*.exe
    echo "[+] EXE w: $OUTPUT_DIR/"
else
    echo "[-] Nie znaleziono EXE. Sprawdz logi powyzej."
fi
