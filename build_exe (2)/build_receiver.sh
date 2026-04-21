#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

WORK_DIR=$(mktemp -d)
trap "rm -rf $WORK_DIR" EXIT

echo "[1/5] Generowanie zobfuskowanego payloadu..."
python3 generate_obfuscated_receiver.py

echo "[2/5] Kompilacja launchera (mingw64 cross-compile)..."
x86_64-w64-mingw32-gcc -O2 -s -mwindows -o "$WORK_DIR/launcher.exe" launcher.c -static

echo "[3/5] Pobieranie Python 3.11 embeddable for Windows..."
PYTHON_ZIP="$WORK_DIR/python-embed.zip"
if [ -f "$SCRIPT_DIR/.cache/python-3.11.9-embed-amd64.zip" ]; then
    cp "$SCRIPT_DIR/.cache/python-3.11.9-embed-amd64.zip" "$PYTHON_ZIP"
    echo "    (z cache)"
else
    wget -q "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -O "$PYTHON_ZIP"
    mkdir -p "$SCRIPT_DIR/.cache"
    cp "$PYTHON_ZIP" "$SCRIPT_DIR/.cache/python-3.11.9-embed-amd64.zip"
fi

echo "[4/5] Pakowanie payloadu..."
PAYLOAD_DIR="$WORK_DIR/python_runtime"
mkdir -p "$PAYLOAD_DIR"
unzip -q "$PYTHON_ZIP" -d "$PAYLOAD_DIR"

# Enable site packages
sed -i 's/#import site/import site/' "$PAYLOAD_DIR/python311._pth"

cp receiver_final.py "$PAYLOAD_DIR/__main__.py"

cd "$WORK_DIR"
zip -q -r payload.zip python_runtime/

echo "[5/5] Sklejanie EXE..."
cat launcher.exe > "$SCRIPT_DIR/receiver.exe"
printf '~~PAYLOAD_START~~' >> "$SCRIPT_DIR/receiver.exe"
cat payload.zip >> "$SCRIPT_DIR/receiver.exe"

echo ""
echo "============================================"
echo " BUILD COMPLETE!"
echo "============================================"
file "$SCRIPT_DIR/receiver.exe"
ls -lh "$SCRIPT_DIR/receiver.exe"
echo ""
echo "Plik: $SCRIPT_DIR/receiver.exe"
