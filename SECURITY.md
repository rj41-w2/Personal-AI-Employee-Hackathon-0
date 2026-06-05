# Security Policy

## Before Publishing

- Do not commit `.env`, `credentials.json`, `token.json`, Obsidian vault data, or OAuth export files.
- If any secret was ever committed, rotate it before making the repository public. Removing it from the latest commit is not enough.
- Keep the API bound to `127.0.0.1` unless you are intentionally deploying behind authentication and TLS.
- Set `API_CORS_ORIGINS` to exact dashboard origins. Do not use `*` for a machine that can reach private services.
- Replace demo Odoo passwords before connecting to real company data.

## Reporting Issues

Open a private advisory or contact the maintainer directly for vulnerabilities involving credentials, account access, or data exposure.
