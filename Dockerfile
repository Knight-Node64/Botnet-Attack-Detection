# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS builder
WORKDIR /build
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime
WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --create-home app
COPY --from=builder /install /usr/local
COPY app.py preprocessing.py predict.py .
COPY models/ models/
RUN chown -R app:app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]