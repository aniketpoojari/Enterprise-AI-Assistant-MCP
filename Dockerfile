# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x start.sh

# Create non-root user with access to persistent storage
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/logs /app/database /data && \
    chown -R appuser:appuser /app/logs /app/database /data

USER appuser

EXPOSE 7860 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; r = urllib.request.urlopen('http://localhost:8000/health'); exit(0 if r.status == 200 else 1)" 2>/dev/null || exit 1

CMD ["bash", "start.sh"]
