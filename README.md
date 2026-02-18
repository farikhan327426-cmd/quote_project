# 🤖 Quote & Order Agent (Enterprise Edition)

**A Production-Ready AI Agent System built with LangGraph, FastAPI, and PostgreSQL.**

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Persistent-orange?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker)

---

## 📖 Overview

The **Quote & Order Agent** is an autonomous AI system designed to handle complex logistics and order processing workflows. Unlike simple chatbots, this agent maintains **long-term state**, supports **human-in-the-loop approval**, and integrates with external systems via **MCP (Model Context Protocol)**.

### ✨ Key Features
*   **🧠 Cognitive Architecture:** Uses `LangGraph` for stateful, cyclic reasoning (Scout → Agent → Inspector → Interviewer).
*   **💾 Persistent Memory:** Interactions are stored in PostgreSQL, allowing sessions to pause and resume (e.g., waiting for human approval).
*   **🛠️ Monorepo Structure:** managed by `uv`, enforcing strict separation between `apps/agent_app`, `shared_core`, and `mcp_servers`.
*   **🛡️ Enterprise Security:** Fail-fast configuration checks, masked error handling, and API Key authentication.
*   **🐳 Deployment Ready:** Fully containerized with Docker Compose; optimized for IIS reverse proxy deployment.

---

## 🏗️ Architecture

The project follows a modern monorepo structure:

```plaintext
Quote_And_Order_Angent/
├── apps/
│   └── agent_app/       # Main FastAPI Application & LangGraph Workflow
├── shared_core/         # Shared utilities (Logging, Exceptions) installed as a package
├── mcp_servers/         # Independent MCP Servers (Quote Service)
├── logs/                # Centralized structured logging
├── docker-compose.prod.yaml  # Production orchestration
└── pyproject.toml       # Workspace dependency definition (uv)
```

---

## 🚀 Getting Started

### Prerequisites
*   **Python 3.12+** (Managed via `uv`)
*   **PostgreSQL** (Local or Docker)
*   **uv** (Ultra-fast Python package installer)

### 1. Installation
Clone the repository and sync dependencies:
```bash
# Instaall uv if you haven't
pip install uv

# Install all dependencies (including shared_core)
uv sync
```

### 2. Configuration
Create a `.env` file in the project root:
```ini
# Database (PostgreSQL)
POSTGRES_URL=postgresql://user:pass@localhost:5432/agent_db

# Security (CRITICAL: App will not start without this)
AGENT_API_KEY=your_secure_secret_key

# AI Provider
OPENAI_API_KEY=sk-...
```

### 3. Running the Application
**Option A: The API Server (Production)**
Start the FastAPI server from the **root directory**:
```bash
uv run uvicorn apps.agent_app.main:app --reload
```
*   **Docs:** `http://localhost:8000/docs`
*   **Health:** `http://localhost:8000/health`

**Option B: The Interactive CLI (Testing)**
Run the terminal-based chat interface:
```bash
uv run python -m apps.agent_app.test_cli
```

---

## 📡 API Usage

### Authentication
All requests must include the `X-API-Key` header.

### Endpoints

#### `POST /chat`
Send a message to the agent.
```json
{
  "message": "I need a quote for shipping 50kg to London",
  "thread_id": "session_123"
}
```

#### `POST /approve`
Approve a quote when the agent hits the `Review_Gate`.
```json
{
  "thread_id": "session_123"
}
```

---

## 🐳 Deployment (Docker)

1.  **Build & Run:**
    ```bash
    docker-compose -f docker-compose.prod.yaml up -d --build
    ```
2.  **Verify:**
    The container exposes port `8000` (mapped to `APP_PORT` env var).

---

## 🧪 Development Standards
*   **Imports:** Always use absolute package imports (`from agenticAI_full_workflow...`).
*   **Execution:** Always run commands from the **Project Root**.
*   **Logging:** Use `shared_core.logger.logging.logger`.

---

**© 2026 Metropolitan Software Development**
