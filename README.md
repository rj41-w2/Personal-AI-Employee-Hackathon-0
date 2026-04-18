# 🤖 Digital FTE: Personal AI Employee

**Tagline:** *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

This project is an autonomous "Digital FTE" (Full-Time Equivalent) built for the **Personal AI Employee Hackathon**. It uses a local-first architecture combining **Claude Code** for reasoning, **Obsidian** for management, and **MCP (Model Context Protocol)** for action execution.

---

## 🏗️ Architecture: Perception → Reasoning → Action

The system operates in a continuous loop:
1.  **Perception (Watchers):** Lightweight Python scripts monitor Gmail, LinkedIn, and the filesystem. When a trigger is detected, they create a Markdown file in the `/Needs_Action` folder.
2.  **Reasoning (Claude Code & Orchestrator):** The `orchestrator.py` picks up these files and uses AI Skills to draft plans, emails, or posts.
3.  **Action (MCP Servers):** Once a human approves the draft (by moving it to the `/Approved` folder), the system executes the action via MCP (e.g., sending an email or posting to LinkedIn).

---

## 📁 Project Structure

```text
.
├── AI_Employee_Vault/          # Obsidian Vault (The Dashboard & Memory)
│   ├── Dashboard.md            # Real-time status updates (Markdown)
│   ├── Needs_Action/           # Tasks waiting for AI processing
│   ├── Pending_Approval/       # AI drafts waiting for Human review
│   ├── Approved/               # Human-approved tasks
│   └── Done/                   # Successfully completed tasks
├── ai-dashboard/               # Next.js Web Dashboard
├── src/
│   ├── orchestrator.py         # Main traffic controller
│   ├── api_server.py           # FastAPI backend for the web dashboard
│   ├── mcp/                    # MCP Servers (Email, LinkedIn, Odoo)
│   ├── skills/                 # AI Logic (Drafters, MCP Executor)
│   ├── watchers/               # Sensors (Gmail, Filesystem, LinkedIn)
│   └── prompts/                # Rules and Guardrails
├── GEMINI.md                   # AI Agent Instruction Context
└── main.py                     # Entry point
```

---

## 🚀 Getting Started

### Prerequisites
- **Python:** 3.14 or higher
- **Node.js:** v24+ (for MCP servers and Web Dashboard)
- **Obsidian:** Installed and pointed to `AI_Employee_Vault`
- **Claude Code:** Installed and configured

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd Personal-AI-Employee-Hackathon-0
    ```

2.  **Set up Python Virtual Environment:**
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # Linux/Mac:
    source .venv/bin/activate
    
    pip install -r requirements.txt
    ```

3.  **Set up Dashboard:**
    ```bash
    cd ai-dashboard
    npm install
    cd ..
    ```

4.  **Configuration:**
    Copy `.env.example` to `.env` and fill in your API keys:
    ```bash
    cp .env.example .env
    ```

---

## 🛠️ Usage

### 1. Start the Orchestrator
The orchestrator manages the flow between folders and executes approved tasks:
```bash
python src/orchestrator.py
```

### 2. Start the Watchers
Run the watchers to begin monitoring your communications (use separate terminals):
```bash
python src/watchers/gmail_watcher.py
python src/watchers/filesystem_watcher.py
```

### 3. Start the Dashboard (Optional)
To monitor your Digital FTE via a web interface:
```bash
# Terminal 1: API Backend
python src/api_server.py

# Terminal 2: Frontend
cd ai-dashboard
npm run dev
```

### 4. Human-in-the-Loop Workflow
1.  Open **Obsidian** and monitor the `Dashboard.md`.
2.  Check `Pending_Approval/` for any drafts created by the AI.
3.  If satisfied, move the file to the `Approved/` folder.
4.  The Orchestrator will detect the move and execute the task via MCP.

---

## 🛡️ Security & Privacy
- **Local-First:** All reasoning and logs stay on your local machine within the Obsidian vault.
- **Human Approval:** No sensitive actions (emails, payments, social posts) are taken without manual movement of files to the `Approved` folder.
- **Secret Management:** Credentials are never stored in the vault; they are managed via `.env`.

---

## 📖 AI Instructions
This project includes a `GEMINI.md` file which serves as a foundational context for AI agents working on this codebase. It defines architecture, conventions, and workflows.

---
*Built for the Personal AI Employee Hackathon 2026.*
