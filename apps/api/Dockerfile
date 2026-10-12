FROM ghcr.io/astral-sh/uv:0.6.14 AS uv-bin

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /app
COPY --from=uv-bin /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api ./apps/api
ENV PYTHONPATH=/app/apps/api
RUN groupadd --gid 10001 nex && useradd --uid 10001 --gid nex --no-create-home nex \
    && chown -R nex:nex /app /tmp/uv-cache
USER 10001:10001
ENV PORT=8000
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn nex_api.main:app --host 0.0.0.0 --port \"$PORT\" --no-access-log"]