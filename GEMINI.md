# GEMINI.md - Personal AI Employee (Digital FTE)

## Project Overview
This project is an autonomous **Digital FTE (Full-Time Equivalent)** designed for the Personal AI Employee Hackathon 2026. It operates on a **Perception → Reasoning → Action** loop with a strict **Human-in-the-Loop** (CEO Approval) requirement.

The system uses an **Obsidian Vault** as its primary "memory" and communication interface, allowing for local-first, transparent, and auditable AI operations.

### Core Architecture
1.  **Perception (Watchers):** Python scripts in `src/watchers/` monitor Gmail, LinkedIn, and the local filesystem. They create Markdown files in the vault's `Needs_Action` folder when triggers are detected.
2.  **Reasoning (Orchestrator & Skills):** `src/orchestrator.py` monitors the vault. It uses specialized "skills" in `src/skills/` (e.g., `email_drafter.py`) to process incoming tasks and create drafts in `Pending_Approval`.
3.  **Action (MCP Servers):** Once a human moves a draft to the `Approved` folder, the orchestrator triggers execution via **Model Context Protocol (MCP)** servers located in `src/mcp/`.
4.  **Dashboard:** A real-time monitoring system consisting of a FastAPI backend (`src/api_server.py`) and a Next.js frontend (`ai-dashboard/`).

## Building and Running

### Prerequisites
- Python 3.14+
- Node.js v24+ (for MCP servers/client and Dashboard)
- Obsidian (pointing to `AI_Employee_Vault/`)
- Odoo (for accounting integration)

### Setup
1.  **Python Environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
2.  **Configuration:**
    Copy `.env.example` to `.env` and configure your API keys (Gmail, LinkedIn, Odoo, Gemini/Claude).
3.  **Dashboard Setup:**
    ```bash
    cd ai-dashboard
    npm install
    ```

### Execution
1.  **Start the Orchestrator:**
    ```bash
    python src/orchestrator.py
    ```
2.  **Start the Watchers (in separate terminals):**
    ```bash
    python src/watchers/gmail_watcher.py
    python src/watchers/filesystem_watcher.py
    ```
3.  **Start the API Server:**
    ```bash
    python src/api_server.py
    ```
4.  **Start the Web Dashboard:**
    ```bash
    cd ai-dashboard
    npm run dev
    ```

## Development Conventions

### Human-in-the-Loop Workflow
All sensitive actions follow this lifecycle:
1.  **Watcher** detects event -> Creates file in `Needs_Action/`.
2.  **Orchestrator** drafts response -> Moves file to `Pending_Approval/`.
3.  **Human (CEO)** reviews draft in Obsidian -> Moves file to `Approved/`.
4.  **Orchestrator** detects approval -> Executes via **MCP** -> Moves to `Done/` (or `Rejected/`).

### Project Structure
- `src/watchers/`: Perception layer (sensors).
- `src/skills/`: Reasoning layer (logic/drafting).
- `src/mcp/`: Action layer (execution servers).
- `src/orchestrator.py`: The central loop and folder router.
- `AI_Employee_Vault/`: The "Source of Truth" (Obsidian Vault).
- `ai-dashboard/`: Next.js frontend for monitoring.

### Technical Standards
- **Local-First:** Keep all reasoning logs and task states within the Markdown files in the vault.
- **MCP-Driven:** Use the Model Context Protocol for all external tool executions.
- **Ralph Wiggum Loop:** An autonomous reasoning loop that runs every 60 seconds to identify proactive tasks.
- **Surgical Edits:** When modifying skills or watchers, ensure the folder-based state machine logic is preserved.
