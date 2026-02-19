# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Environment settings for uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy only config files
COPY pyproject.toml uv.lock ./
COPY apps/agent_app/pyproject.toml ./apps/agent_app/
COPY shared_core/pyproject.toml ./shared_core/
COPY mcp_servers/quote_mcp/pyproject.toml ./mcp_servers/quote_mcp/

# 1. PEHLA BADLAV: Install dependencies globally (system-wide in builder)
# --system flag se uv libraries ko standard python path mein install karega
RUN uv sync --frozen --no-dev --no-install-project --system

COPY . .

# 2. DUSRA BADLAV: Poore project ko system-wide install karein
RUN uv sync --frozen --no-dev --system

# ==========================================
# STAGE 2: RUNTIME
# ==========================================
FROM python:3.12-slim-bookworm

RUN useradd -m -u 1000 agentuser
WORKDIR /app

# 3. TEESRA BADLAV: .venv copy karne ke bajaye hum system site-packages copy karenge
# Ye zyada reliable hai monorepos ke liye
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder --chown=agentuser:agentuser /app /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

USER agentuser
EXPOSE 8000

# Ab 'uvicorn' direct command ki tarah chalega dakhty hain phr
CMD ["uvicorn", "apps.agent_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]