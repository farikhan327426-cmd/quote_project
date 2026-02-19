# ==========================================
# STAGE 1: BUILDER (The Factory)
# ==========================================
FROM python:3.12-slim-bookworm AS builder

# 1. Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 2. Environment Settings for Build
ENV UV_COMPILE_BYTECODE=1 
ENV UV_LINK_MODE=copy

# 3. Copy Configs (Caching optimization)
COPY pyproject.toml uv.lock ./
COPY apps/agent_app/pyproject.toml ./apps/agent_app/
COPY shared_core/pyproject.toml ./shared_core/
COPY mcp_servers/quote_mcp/pyproject.toml ./mcp_servers/quote_mcp/

# 4. Install Dependencies
# Professional Change: Humen poora project install karna hoga taake paths set ho jayein
RUN uv sync --frozen --no-dev --no-install-project

# 5. Copy Source Code
COPY . .

# 6. Final Sync
RUN uv sync --frozen --no-dev

# ==========================================
# STAGE 2: RUNTIME (The Production Server)
# ==========================================
FROM python:3.12-slim-bookworm

# 1. Security: Create a non-root user
RUN useradd -m -u 1000 agentuser

# 2. Set Working Directory
WORKDIR /app

# 3. Environment Variables
# PATH: Isme virtual environment ka bin folder sabse pehle rakha hai
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# 4. Copy Virtual Environment and Code
COPY --from=builder --chown=agentuser:agentuser /app/.venv /app/.venv
COPY --from=builder --chown=agentuser:agentuser /app /app

# 5. Switch to Secure User
USER agentuser

# 6. Expose Port
EXPOSE 8000

# 7. Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -m curl -f http://localhost:8000/health || exit 1

# 8. Professional Start Command
# Change: "python -m uvicorn" use kiya hai jo 100% path dhoond leta hai
CMD ["python", "-m", "uvicorn", "apps.agent_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]