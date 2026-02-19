# ==========================================
# STAGE 1: BUILDER
# ==========================================
FROM python:3.12-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy configuration files
COPY pyproject.toml uv.lock ./
COPY apps/agent_app/pyproject.toml ./apps/agent_app/
COPY shared_core/pyproject.toml ./shared_core/
COPY mcp_servers/quote_mcp/pyproject.toml ./mcp_servers/quote_mcp/

# 1. FIX: Use 'uv pip' to install dependencies system-wide
# This populates the standard site-packages that Stage 2 will copy
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy the rest of the source code
COPY . .

# 2. Install the local packages (monorepo members) as editable/system-wide
RUN uv pip install --system --no-cache -e ./shared_core -e ./apps/agent_app

# ==========================================
# STAGE 2: RUNTIME
# ==========================================
FROM python:3.12-slim-bookworm

# Security: Create non-root user
RUN useradd -m -u 1000 agentuser
WORKDIR /app

# 3. Copy only the necessary python artifacts from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder --chown=agentuser:agentuser /app /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

USER agentuser
EXPOSE 8000

# 4. Standard uvicorn execution
CMD ["uvicorn", "apps.agent_app.main:app", "--host", "0.0.0.0", "--port", "8000"]