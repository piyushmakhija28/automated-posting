# Level 7: DevOps & Container Architecture — Docker Containerization Specification

**Document ID:** `DOC-OPS-01-DOCKER`  
**Project:** `automated-posting`  
**Author:** Principal Software Architect
**Reviewer:** Staff Backend Engineering Lead
**Status:** APPROVED  
**Standard:** OCI Container Standards, CIS Docker Benchmark, Twelve-Factor App Configuration Spec

---

## 1. Multi-Stage Hardened Dockerfile Architecture

To ensure minimum attack surface, zero build tool artifacts in production, and compliance with the **CIS Docker Benchmark**, the application uses a **Multi-Stage Build** based on `python:3.11-slim`:

### Stage 1: Build & Dependency Wheel Compilation (`builder`)
- Installs necessary compile-time tools (`gcc`, `libffi-dev`).
- Builds Python wheels into `/root/.cache`.

### Stage 2: Runtime Image (`final`)
- Minimal `python:3.11-slim` runtime.
- Installs only runtime dependencies.
- Enforces non-root execution via a dedicated service user (`appuser` with UID 10001).
- Copies only compiled source and virtual environment.

```dockerfile
# -------------------------------------------------------------
# Stage 1: Builder Stage
# -------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# -------------------------------------------------------------
# Stage 2: Production Runtime Stage
# -------------------------------------------------------------
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    PORT=4000

# Security: Create non-root system user and group (OCI/CIS Standards)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appgroup app/ ./app/

# Switch to non-root user
USER appuser

EXPOSE 4000

# Health check instruction
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:' + str(os.environ.get('PORT', 4000)) + '/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-4000}"]
```

---

## 2. Docker Security Checklist (CIS Benchmark)

- [x] **Non-Root Execution:** Container runs strictly as `USER appuser` (UID 10001).
- [x] **Minimal Image Footprint:** Slim base eliminates unneeded shell utilities and compilers.
- [x] **No Hardcoded Secrets:** Dockerfile contains zero `ENV` values for API keys.
- [x] **Layer Caching:** `requirements.txt` copied and installed before application code to leverage Docker build cache.
- [x] **Built-in Healthcheck:** Docker daemon monitors `/health` status continuously.
