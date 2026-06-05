# Contributing

Thanks for helping improve Digital FTE: Personal AI Employee. This project handles personal/business automation, so contributions should keep privacy, safety, and human approval at the center.

## Before You Start

- Read `README.md` to understand the perception -> reasoning -> action workflow.
- Read `SECURITY.md` before touching credentials, OAuth, MCP tools, or live actions.
- Copy `.env.example` to `.env` for local development, and never commit real secrets.
- Use Python 3.11+ and Node.js 20.9+.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd ai-dashboard
npm install
cd ..
```

## Development Workflow

1. Create a branch for your change.
2. Keep changes focused and easy to review.
3. Run the relevant local checks before opening a pull request.
4. Update docs or examples when behavior changes.
5. Open a pull request with a clear summary, testing notes, and any safety/privacy impact.

## Running the Project

Start the orchestrator:

```bash
python src/orchestrator.py
```

Start watchers in separate terminals as needed:

```bash
python src/watchers/gmail_watcher.py
python src/watchers/filesystem_watcher.py
python src/watchers/odoo_watcher.py
```

Start the API and dashboard:

```bash
python src/api_server.py

cd ai-dashboard
npm run dev
```

## Safety Rules

- Do not commit `.env`, real OAuth files, tokens, personal data, customer data, or vault content that should stay private.
- Keep live actions disabled by default unless a maintainer explicitly asks otherwise.
- Any feature that sends email, posts to LinkedIn, writes to Odoo, or changes external systems must require human approval and clear environment guards.
- Prefer dry-run behavior when adding new integrations.
- Document any new environment variables in `.env.example`.

## Code Style

- Follow the existing project structure and naming patterns.
- Keep automation logic explicit and auditable.
- Add short comments only where the behavior is not obvious.
- Avoid broad refactors in the same pull request as a feature or bug fix.

## Pull Request Checklist

Before submitting, make sure:

- The change is scoped to one clear purpose.
- Secrets and local-only files are not included.
- Relevant docs or config examples are updated.
- You tested the affected Python code, dashboard code, or workflow manually.
- Any live-action risk is called out in the pull request description.

## Questions

If you are unsure about a workflow, integration, or safety decision, open an issue or draft pull request first so maintainers can discuss the approach before implementation.
