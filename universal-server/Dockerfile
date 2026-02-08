# Stage 1: Build dependencies
FROM python:3.11-alpine AS builder

RUN apk add --no-cache gcc musl-dev libxml2-dev libxslt-dev libffi-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir flask requests pywemo

# Stage 2: Runtime
FROM python:3.11-alpine

RUN apk add --no-cache libxml2 libxslt su-exec

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY wemo_server.py .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /data

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/status')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
