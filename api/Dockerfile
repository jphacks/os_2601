FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/
WORKDIR /app
COPY api/pyproject.toml api/uv.lock /app/api/
RUN uv sync --frozen --no-dev --directory /app/api
COPY api/ /app/api/
CMD uv run --frozen --no-dev --directory /app/api uvicorn app.main:app --host 0.0.0.0 --port $PORT
