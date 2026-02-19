# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/agent_app/pyproject.toml ./apps/agent_app/
COPY shared_core/pyproject.toml ./shared_core/
COPY mcp_servers/quote_mcp/pyproject.toml ./mcp_servers/quote_mcp/

RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

RUN uv pip install --system --no-cache -e ./shared_core -e ./apps/agent_app

# ==========================================
# STAGE 2: RUNTIME
# ==========================================
FROM python:3.12-slim-bookworm

# Security: Create non-root user
RUN useradd -m -u 1000 agentuser

WORKDIR /app

# 1. FIX: Create logs folder and set permissions BEFORE switching to agentuser
RUN mkdir -p /app/logs && chown -u 1000:1000 /app/logs

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder --chown=agentuser:agentuser /app /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

# 2. FIX: Ensure runtime user has access to logs
USER agentuser
EXPOSE 8000

CMD ["uvicorn", "apps.agent_app.main:app", "--host", "0.0.0.0", "--port", "8000"]