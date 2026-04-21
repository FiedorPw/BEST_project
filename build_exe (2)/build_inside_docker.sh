#!/bin/bash
set -e

echo "[*] === Build pipeline: Obfuscated EXE ==="

WINE_PYTHON="wine C:\\Python311\\python.exe"
WINE_PYARMOR="wine C:\\Python311\\Scripts\\pyarmor.exe"
WINE_PYINSTALLER="wine C:\\Python311\\Scripts\\pyinstaller.exe"

echo "[1/3] PyArmor obfuskacja..."
$WINE_PYARMOR gen --output /build/armored /build/v2_final.py 2>/dev/null || {
    echo "[!] PyArmor nie dostepny, pomijam ten krok"
    mkdir -p /build/armored
    cp /build/v2_final.py /build/armored/v2_final.py
}

echo "[2/3] PyInstaller budowanie EXE..."
cd /build/armored

# Create PyInstaller spec for maximum obfuscation
cat > /build/v2_final.spec << 'SPECEOF'
# -*- mode: python ; coding: utf-8 -*-
import os

a = Analysis(
    ['v2_final.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pydivert', 'struct', 'sys'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'email', 'html', 'http', 'xml',
              'pydoc', 'doctest', 'argparse', 'pdb', 'profile'],
    noarchive=False,
    optimize=2,
)

# Strip debug info
a.binaries = [x for x in a.binaries if not x[0].endswith('.pdb')]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='svchost',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
SPECEOF

$WINE_PYINSTALLER /build/v2_final.spec \
    --clean \
    --log-level WARN \
    2>/dev/null || $WINE_PYINSTALLER --onefile --noconsole \
    --name svchost \
    --strip \
    --upx-dir /usr/bin \
    --exclude-module tkinter \
    --exclude-module unittest \
    --optimize 2 \
    /build/armored/v2_final.py 2>/dev/null

echo "[3/3] Kompresja UPX..."
if command -v upx &>/dev/null; then
    upx --best --lzma /build/dist/svchost.exe 2>/dev/null || true
fi

echo ""
echo "[+] === BUILD COMPLETE ==="
ls -lh /build/dist/svchost.exe 2>/dev/null && echo "[+] EXE gotowy: /build/dist/svchost.exe" || echo "[-] EXE w /build/dist/"

# Copy output
cp /build/dist/*.exe /output/ 2>/dev/null || true
echo "[+] Skopiowano do /output/"
