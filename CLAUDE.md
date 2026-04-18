# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Personal AI Employee** system - an autonomous agent that monitors communications (Gmail, LinkedIn, filesystem, Odoo ERP), drafts responses using a local LLM (Ollama), and executes actions via MCP (Model Context Protocol) after human approval. The system is local-first with an Obsidian vault serving as the dashboard and state management.

**Gold Tier Features**: Includes Odoo 19 ERP integration for accounting tasks (create invoices, get financial reports, manage partners) and **Ralph Wiggum Loop** for autonomous multi-step task completion.

## Architecture: Perception → Reasoning → Action

The system operates in a continuous loop with three stages:

1. **Perception (Watchers)** - `src/watchers/`: Monitor external sources (Gmail, filesystem, Odoo) and create Markdown task files in `AI_Employee_Vault/Needs_Action/`
2. **Reasoning (Orchestrator & Skills)** - `src/orchestrator.py` + `src/skills/`: Process tasks using Ollama LLM to draft responses, moving drafts to `Pending_Approval/`
3. **Action (MCP Servers)** - `src/mcp/`: Execute approved tasks (send emails, post to LinkedIn, Odoo accounting) when files are moved to `Approved/`
4. **Autonomous Loop (Ralph Wiggum)** - `src/skills/ralph_wiggum_loop.py`: Every 60 seconds, analyzes completed tasks and autonomously creates follow-up actions

## Key Commands

### Running the System

```bash
# Activate virtual environment first
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Run the orchestrator (main controller)
python src/orchestrator.py

# Run watchers (in separate terminals)
python src/watchers/gmail_watcher.py
python src/watchers/filesystem_watcher.py
python src/watchers/odoo_watcher.py

# Run MCP servers directly (for testing)
python src/mcp/email_mcp_server.py
python src/mcp/linkedin_mcp_server.py
python src/mcp/odoo_mcp_server.py

# Start Odoo (Gold Tier)
docker-compose up -d
```

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your LinkedIn and Ollama credentials
```

## Vault Directory Structure

The `AI_Employee_Vault/` directory is the central state store:

- `Needs_Action/` - Tasks waiting for AI processing
- `Pending_Approval/` - AI-drafted responses waiting for human review
- `Approved/` - Human-approved tasks ready for execution
- `Done/` - Successfully completed tasks
- `Rejected/` - Failed task executions
- `Archive/` - Original trigger files archived after processing
- `Plans/` - Generated plan files from drafters
- `Dashboard.md` - Live status dashboard

**Workflow**: Watchers create files in `Needs_Action/` → Orchestrator drafts responses → Files appear in `Pending_Approval/` → Human moves files to `Approved/` → MCP executes → Files moved to `Done/` or `Rejected/`

**Human-in-the-Loop Policy**: ALL tasks (including Ralph Wiggum auto-triggered) require CEO manual approval before execution. Auto-triggered tasks are drafted to `Pending_Approval/` and must be manually moved to `Approved/`.

## Key Implementation Details

### Ollama Integration
- Skills (`email_drafter.py`, `linkedin_drafter.py`) call Ollama API at `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- Model is configured via `OLLAMA_MODEL` env var (default: `llama3.2`)
- Prompts are loaded from `src/prompts/email_rules.md` and `linkedin_rules.md`

### MCP Execution Flow
- `mcp_executor.py` spawns MCP servers as subprocesses via stdio transport
- Uses absolute paths to server scripts to avoid working directory issues
- Error detection scans output for keywords like "Error", "FAILED", "401", etc.
- LinkedIn MCP returns "SUCCESS:" prefix on successful posts

### Gmail Authentication
- Requires `credentials.json` (OAuth2 client secrets) in project root
- Authenticates interactively on first run, saves `token.json` for subsequent runs
- Both watcher and MCP server share the same token

### Filename Conventions
- GMAIL emails create files: `GMAIL_{message_id}.md`
- LinkedIn tasks: `LINKEDIN_{descriptor}.md`
- Accounting/Odoo tasks: `ACCOUNTING_{descriptor}.md` or `ODOO_{descriptor}.md`
- Pending approvals: `PENDING_{timestamp}_{original_name}.md`
- Category detection uses substring matching (`"GMAIL_" in filename`, `"ACCOUNTING_" in filename`, etc.)

## Environment Variables

Required in `.env`:
- `LINKEDIN_ACCESS_TOKEN` - LinkedIn OAuth2 token
- `LINKEDIN_PERSON_URN` - LinkedIn person URN (format: `urn:li:person:XXX`)
- `OLLAMA_BASE_URL` - Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - Model name (default: `llama3.2`)
- `ODOO_URL` - Odoo instance URL (default: `http://localhost:8069`)
- `ODOO_DB` - Database name (default: `ai_employee_db`)
- `ODOO_USERNAME` - Odoo admin username
- `ODOO_PASSWORD` - Odoo admin password

## Testing MCP Tools

Test email sending:
```bash
# Create an approval file manually
cat > AI_Employee_Vault/Approved/test_email.md << 'EOF'
## Action: send_email
To: test@example.com
Subject: Test Subject
Body:
This is a test email.

---
EOF
```

Test LinkedIn posting:
```bash
cat > AI_Employee_Vault/Approved/test_linkedin.md << 'EOF'
## Action: post_to_linkedin
Content:
This is a test LinkedIn post.

---
EOF
```

Test Odoo invoice creation:
```bash
cat > AI_Employee_Vault/Approved/test_odoo_invoice.md << 'EOF'
## Action: create_invoice
Customer: Test Company LLC
Amount: 1250.00
Product: Consulting Services
Description: Test invoice from AI Employee

---
EOF
```

## Odoo Integration (Gold Tier)

Odoo 19 Community runs locally via Docker with persistent volumes for accounting data.

**Setup**: See `ODOO_SETUP.md` for detailed installation steps.

**Quick Start**:
```bash
# Start Odoo and PostgreSQL
docker-compose up -d

# Create database at http://localhost:8069
# Database name: ai_employee_db
# Install Accounting module

# Run Odoo MCP server for testing
python src/mcp/odoo_mcp_server.py
```

**Supported Odoo Tools**:
- `create_invoice` - Create draft customer invoices
- `get_accounting_summary` - Fetch sales, outstanding, or profit reports
- `list_partners` - Search customers and vendors
- `get_invoice_status` - Check invoice payment status

## Ralph Wiggum Loop (Autonomous Multi-Step Task Completion)

The Ralph Wiggum Loop enables autonomous task completion by observing completed tasks and generating logical follow-ups.

**How it works**:
1. Every 60 seconds, the loop scans `Done/` directories for files modified in the last 10 minutes
2. It passes task summaries to the LLM with strict reasoning rules
3. LLM decides if a follow-up action is needed (e.g., invoice created → send confirmation email)
4. If yes, creates a new file in `Needs_Action/` with `[AUTO_TRIGGERED]` tag
5. **Human-in-the-Loop**: Task is drafted to `Pending_Approval/` - CEO must manually move to `Approved/` for execution

**Memory**: Uses `loop_memory.json` to track processed files and avoid duplicate follow-ups

**Decision Rules**:
- Invoice Created → Suggest email confirmation to client
- LinkedIn Post → Log the post
- Report Generated → Email report to stakeholders
- If already a follow-up → Do NOT create another (avoids infinite loops)

**Manual Trigger**:
```bash
uv run python src/skills/ralph_wiggum_loop.py
```
