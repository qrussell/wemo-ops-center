# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libxml2-dev \
    libxslt1-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir flask requests pywemo waitress

# Stage 2: Runtime
FROM python:3.11-slim

LABEL org.opencontainers.image.title="Wemo Ops Server" \
      org.opencontainers.image.version="5.2.3" \
      org.opencontainers.image.description="Wemo device automation server" \
      org.opencontainers.image.source="https://github.com/qrussell/wemo-ops-center"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    gosu \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY wemo_server.py .
COPY templates templates
COPY static static
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /data

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",5050)}/api/status')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
