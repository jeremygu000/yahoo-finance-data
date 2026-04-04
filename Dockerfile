FROM python:3.12-slim AS base

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev

RUN mkdir -p /data/parquet /data/logs

ENV MARKET_DATA_DIR=/data/parquet \
    MARKET_DATA_LOG_DIR=/data/logs

EXPOSE 8100

CMD ["uv", "run", "uvicorn", "market_data.server:app", "--host", "0.0.0.0", "--port", "8100"]
