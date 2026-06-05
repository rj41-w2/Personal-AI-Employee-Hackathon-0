# Digital FTE: Personal AI Employee

Your life and business on autopilot: local-first, agent-driven, and human-in-the-loop.

This project is an autonomous "Digital FTE" built for the Personal AI Employee Hackathon. It combines an Obsidian vault, Python watchers, local LLM drafting, MCP action servers, and a Next.js dashboard.

## Architecture

The system runs as a perception -> reasoning -> action loop:

1. Watchers monitor Gmail, Odoo, LinkedIn, and local files.
2. Watchers create Markdown tasks in `AI_Employee_Vault/Needs_Action`.
3. The orchestrator drafts plans and actions into `Pending_Approval`.
4. A human reviews the draft and moves it into `Approved`.
5. The MCP executor validates approval metadata and environment safety flags before any live action runs.

## Project Structure

```text
.
|-- AI_Employee_Vault/          # Obsidian vault and workflow folders
|   |-- Dashboard.md            # Real-time status updates
|   |-- Needs_Action/           # New tasks waiting for AI drafting
|   |-- Pending_Approval/       # Drafts waiting for human review
|   |-- Approved/               # Human-approved tasks
|   `-- Done/                   # Successfully completed tasks
|-- ai-dashboard/               # Next.js dashboard
|-- src/
|   |-- orchestrator.py         # Main workflow controller
|   |-- api_server.py           # FastAPI backend for the dashboard
|   |-- mcp/                    # Email, LinkedIn, and Odoo MCP servers
|   |-- skills/                 # Drafters and MCP executor
|   |-- watchers/               # Gmail, Odoo, filesystem, and LinkedIn watchers
|   `-- prompts/                # Prompt rules and guardrails
|-- GEMINI.md                   # Agent instruction context
`-- main.py
```

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Node.js 20.9 or newer
- Obsidian pointed at `AI_Employee_Vault`
- Ollama running locally if you use the built-in local LLM drafting flow

### Installation

```bash
git clone <your-repo-url>
cd Personal-AI-Employee-Hackathon-0

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd ai-dashboard
npm install
cd ..

copy .env.example .env
```

Fill in `.env` with your local credentials. Never commit real secrets.

## Usage

Start the orchestrator:

```bash
python src/orchestrator.py
```

Start watchers in separate terminals:

```bash
python src/watchers/gmail_watcher.py
python src/watchers/filesystem_watcher.py
python src/watchers/odoo_watcher.py
```

Start the dashboard:

```bash
python src/api_server.py

cd ai-dashboard
npm run dev
```

## Live Action Safety

Moving a file to `AI_Employee_Vault/Approved` is not enough to send an email, post to LinkedIn, or write to Odoo. Live execution is blocked unless all required safety checks pass.

To enable live actions, set:

```env
ENABLE_LIVE_ACTIONS=true
```

Then add approval metadata to the approved Markdown file:

```text
Approval: approved
Approved_By: your-name
```

Additional per-action guards:

- Email sending requires `EMAIL_ALLOWED_RECIPIENTS` or `EMAIL_ALLOWED_DOMAINS`.
- LinkedIn posting requires `LINKEDIN_POSTING_ENABLED=true`.
- Odoo write actions require `ODOO_WRITE_ACTIONS_ENABLED=true`.
- Odoo read actions require `ODOO_READ_ACTIONS_ENABLED=true`.

With live actions disabled, approved files are treated as dry runs and no external MCP tool is called.

## Security & Privacy

- Local-first by default.
- Real secrets belong in `.env`, not in Git.
- Gmail OAuth files (`credentials.json`, `token.json`) are ignored by `.gitignore`.
- Review `SECURITY.md` before publishing or deploying.

## License

MIT. See `LICENSE`.
