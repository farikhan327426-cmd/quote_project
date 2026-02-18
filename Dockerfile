# ==========================================
# STAGE 1: BUILDER (The Factory)
# ==========================================
FROM python:3.12-slim-bookworm AS builder

# 1. Install uv (The fastest Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 2. Environment Settings for Build
ENV UV_COMPILE_BYTECODE=1 
ENV UV_LINK_MODE=copy

# 3. CACHE OPTIMIZATION STEP:
# We copy ONLY the configuration files first. 
# This allows Docker to cache the "dependency download" layer.
# If you change your code but not your dependencies, this step is skipped (Instant Build).

# Copy Root Configs
COPY pyproject.toml uv.lock ./

# Copy Child Configs (CRITICAL FOR MONOREPO)
# We must replicate the folder structure for uv to find the workspace members
COPY apps/agent_app/pyproject.toml ./apps/agent_app/
COPY shared_core/pyproject.toml ./shared_core/
COPY mcp_servers/quote_mcp/pyproject.toml ./mcp_servers/quote_mcp/

# 4. Install Dependencies (No Project Code yet)
# --no-install-project: Installs pandas, langchain, etc., but NOT your own code.
RUN uv sync --frozen --no-install-project --no-dev

# 5. Copy the Actual Source Code
COPY . .

# 6. Install The Project (Now we install 'agent_app' and 'shared_core')
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
# PATH: critical to ensure we use the venv python, not system python
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PATH="/app/.venv/bin:$PATH"

# 4. Copy the Virtual Environment from Builder
# This is the only heavy thing we copy. It includes all installed libraries.
COPY --from=builder --chown=agentuser:agentuser /app/.venv /app/.venv

# 5. Copy Application Code
COPY --from=builder --chown=agentuser:agentuser /app .

# 6. Switch to Secure User
USER agentuser

# 7. Expose Port
EXPOSE 8000

# 8. Healthcheck (Enterprise Standard)
# Fails if the server doesn't respond within 30s
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 9. Start Command
# We use the absolute path to the module because we are in the root /app
CMD ["uvicorn", "apps.agent_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]