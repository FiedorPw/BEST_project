FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wine64 wine32 wget unzip upx-ucl xvfb ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download Python for Windows (embeddable)
RUN mkdir -p /opt/winpython && \
    wget -q "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" \
    -O /tmp/python-win.zip && \
    unzip /tmp/python-win.zip -d /opt/winpython && \
    rm /tmp/python-win.zip

# Download full Python installer for Windows (needed for pip/pyinstaller)
RUN wget -q "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" \
    -O /tmp/python-installer.exe

# Install Python for Windows via Wine
ENV WINEARCH=win64
ENV WINEPREFIX=/root/.wine
RUN xvfb-run wine /tmp/python-installer.exe /quiet InstallAllUsers=0 \
    PrependPath=1 Include_test=0 TargetDir=C:\\Python311 2>/dev/null; \
    rm /tmp/python-installer.exe; \
    exit 0

# Install pyarmor and pyinstaller in Wine Python
RUN wine C:\\Python311\\python.exe -m pip install --upgrade pip 2>/dev/null; exit 0
RUN wine C:\\Python311\\python.exe -m pip install pyarmor pyinstaller pydivert 2>/dev/null; exit 0

WORKDIR /build

# Copy source files
COPY v2_final.py /build/v2_final.py
COPY v2.py /build/v2_original.py
COPY antygona.txt /build/antygona.txt 2>/dev/null || true

# Build script inside container
COPY build_inside_docker.sh /build/build_inside_docker.sh
RUN chmod +x /build/build_inside_docker.sh

CMD ["/build/build_inside_docker.sh"]
