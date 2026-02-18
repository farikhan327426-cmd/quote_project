import os
from pathlib import Path
import logging

# logging setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s]: %(message)s:')

project_name = "agenticAI_full_workflow"

list_of_files = [
    # --- ROOT CONFIGURATIONS ---
    ".env",
    ".gitignore",
    "docker-compose.yaml",
    "README.md",

    # --- AGENT ORCHESTRATOR APP (The Main Brain) ---
    f"apps/agent_app/src/{project_name}/agent/agent_workflow.py",
    f"apps/agent_app/src/{project_name}/project_nodes/scout_node.py",
    f"apps/agent_app/src/{project_name}/project_nodes/inspector_node.py",
    f"apps/agent_app/src/{project_name}/project_nodes/interviewer_nodes.py",
    f"apps/agent_app/src/{project_name}/project_nodes/review_nodes.py",
    f"apps/agent_app/src/{project_name}/agent_state/state.py",
    f"apps/agent_app/src/{project_name}/prompt_library/prompts.py",
    f"apps/agent_app/src/{project_name}/schemas/form_schema.py",
    f"apps/agent_app/src/{project_name}/utils/common.py",
    f"apps/agent_app/src/{project_name}/utils/api_loader.py",
    f"apps/agent_app/src/{project_name}/utils/model_loader.py",
    f"apps/agent_app/config/config.yaml",
    "apps/agent_app/main.py",
    "apps/agent_app/Dockerfile",
    "apps/agent_app/pyproject.toml",

    # --- MCP VERIFICATION SERVER (The Human-in-the-loop Bridge) ---
    "mcp_servers/verification_mcp/src/server.py",
    "mcp_servers/verification_mcp/src/tools/verify_data.py",
    "mcp_servers/verification_mcp/src/tools/db_handler.py",
    "mcp_servers/verification_mcp/config/mcp_config.json",
    "mcp_servers/verification_mcp/Dockerfile",
    "mcp_servers/verification_mcp/pyproject.toml",

    # --- SHARED CORE (Cross-cutting Concerns) ---
    "shared_core/logger/logging.py",
    "shared_core/exception/exceptionhandling.py",
    "shared_core/__init__.py",

    # --- DEPLOYMENT & CI/CD ---
    ".github/workflows/.gitkeep",
    "notebook/experiments.ipynb",
]

for filepath in list_of_files:
    filepath = Path(filepath)
    filedir, filename = os.path.split(filepath)

    if filedir != "":
        os.makedirs(filedir, exist_ok=True)
        logging.info(f"Creating directory; {filedir} for the file: {filename}")

    if (not os.path.exists(filepath)) or (os.path.getsize(filepath) == 0):
        with open(filepath, "w") as f:
            pass
        logging.info(f"Creating empty file: {filepath}")
    else:
        logging.info(f"{filename} already exists")