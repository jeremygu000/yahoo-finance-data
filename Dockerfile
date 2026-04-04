# ---- Build stage: install dependencies ----
FROM python:3.12-slim AS builder

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev

# ---- Runtime stage: minimal image ----
FROM python:3.12-slim AS runtime

RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --create-home app

WORKDIR /app

# Copy uv + installed venv from builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=builder /app /app

RUN mkdir -p /data/parquet /data/logs && \
    chown -R app:app /data /app

ENV MARKET_DATA_DIR=/data/parquet \
    MARKET_DATA_LOG_DIR=/data/logs \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8100

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/api/tickers')" || exit 1

CMD ["uv", "run", "uvicorn", "market_data.server:app", "--host", "0.0.0.0", "--port", "8100"]
