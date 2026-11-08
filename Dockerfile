# syntax=docker/dockerfile:1

# ---------- Stage 1: builder ----------
# Resolve and build every Python dependency into wheels. Compilers, pip
# caches and build metadata stay in this stage and never reach production.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="task-tracker" \
      org.opencontainers.image.description="Task Tracker web app - Alfido Tech DevOps internship" \
      org.opencontainers.image.authors="Raghavapuram Sai Harshith"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:////app/data/task_tracker.db

# Run as an unprivileged user; only /app/data is writable.
RUN groupadd --gid 10001 appuser \
 && useradd --uid 10001 --gid 10001 --create-home appuser \
 && mkdir -p /app/data \
 && chown 10001:10001 /app/data

WORKDIR /app

# Install only the pre-built wheels: no network access and no compilers needed.
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Application code is copied last so code changes do not invalidate the
# (slow) dependency layers above.
COPY app/ ./app/
COPY wsgi.py .

USER 10001:10001
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "30", "wsgi:app"]
