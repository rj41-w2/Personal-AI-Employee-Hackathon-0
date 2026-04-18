# Odoo 19 Gold Tier Setup Guide

This guide walks you through setting up Odoo 19 Community Edition locally and integrating it with your Personal AI Employee system.

## Prerequisites

- Docker Desktop installed and running
- At least 4GB RAM available for containers
- Python dependencies: `odoorpc` and `requests` (already in requirements.txt)

## Step 1: Start Odoo with Docker

```bash
# Navigate to project directory
cd Personal-AI-Employee-Hackathon-0

# Start Odoo and PostgreSQL containers
docker-compose up -d

# Wait for initialization (first run takes 2-3 minutes)
docker logs -f odoo
```

## Step 2: Initial Odoo Configuration

1. **Access Odoo**: Open http://localhost:8069 in your browser

2. **Create Master Password**: On first run, set a strong master password for the database manager

3. **Create Database**:
   - Database Name: `ai_employee_db`
   - Email: admin@example.com (or your preferred admin email)
   - Password: Create a secure admin password
   - Select "Create Database"

4. **Install Accounting Module**:
   - After login, go to Apps
   - Search for "Accounting" and install it
   - This enables invoicing, chart of accounts, and financial reports

5. **Configure Demo Data (Optional)**:
   - Install "Contacts" app to manage customers/vendors
   - Install "Sales" app for sales order workflow

## Step 3: Configure Environment Variables

Edit your `.env` file to add Odoo credentials:

```bash
# --- Odoo ERP ---
ODOO_URL=http://localhost:8069
ODOO_DB=ai_employee_db
ODOO_USERNAME=admin@example.com  # Use the email you set during database creation
ODOO_PASSWORD=your_secure_admin_password
```

## Step 4: Test the Integration

### Test Odoo MCP Server Directly

```bash
# Activate virtual environment
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Run the Odoo MCP server
python src/mcp/odoo_mcp_server.py
```

If successful, you'll see: "Successfully connected to Odoo!"

### Create a Test Invoice

Create an approval file manually:

```bash
cat > AI_Employee_Vault/Approved/test_odoo_invoice.md << 'EOF'
## Action: create_invoice
Customer: Test Company LLC
Amount: 1250.00
Product: Consulting Services
Description: AI consulting for March 2026

---
EOF
```

Then run the orchestrator:
```bash
python src/orchestrator.py
```

The invoice will be created in Odoo automatically.

## Step 5: Run the Full System

Start all components in separate terminals:

```bash
# Terminal 1: Odoo (already running via Docker)
docker-compose ps  # Verify containers are running

# Terminal 2: Orchestrator
python src/orchestrator.py

# Terminal 3: Gmail Watcher (optional)
python src/watchers/gmail_watcher.py

# Terminal 4: Filesystem Watcher (optional)
python src/watchers/filesystem_watcher.py

# Terminal 5: Odoo Watcher (optional - monitors for new Odoo events)
python src/watchers/odoo_watcher.py
```

## Supported Accounting Actions

### 1. Create Invoice

Trigger files should contain:
```markdown
## Action: create_invoice
Customer: <customer_name>
Amount: <amount>
Product: <product_name> (optional)
Description: <description> (optional)
```

### 2. Get Accounting Summary

Trigger files should contain:
```markdown
## Action: get_accounting_summary
Report: <sales|outstanding|profit>
```

### 3. List Partners

Trigger files should contain:
```markdown
## Action: list_partners
Search: <search_term>
```

## Creating Accounting Tasks

You can create accounting tasks by dropping files into `AI_Employee_Vault/Needs_Action/`:

```bash
# Example: Create a task for invoice generation
cat > AI_Employee_Vault/Needs_Action/ACCOUNTING_invoice_001.md << 'EOF'
---
type: accounting
task: create_invoice
---

Please create an invoice for:
Customer: Acme Corporation
Amount: $5,000
For: Monthly AI Employee retainer - April 2026
EOF
```

The AI will draft the structured invoice action and place it in `Pending_Approval/`. After you approve it (move to `Approved/`), the orchestrator will execute it via the Odoo MCP server.

## Troubleshooting

### Odoo Container Won't Start

```bash
# Check logs
docker-compose logs odoo

# Ensure database is healthy first
docker-compose logs db

# Rebuild if needed
docker-compose down -v
docker-compose up -d
```

### Authentication Failures

- Verify credentials in `.env` match your Odoo admin account
- Check that the database `ai_employee_db` exists at http://localhost:8069/web/database/manager
- Ensure Odoo is fully started (check `docker-compose logs odoo`)

### MCP Server Connection Issues

```bash
# Test Odoo connectivity manually
python -c "
import odoorpc
odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login('ai_employee_db', 'admin', 'your_password')
print('Connected! UID:', odoo.env.uid)
"
```

## Persistent Data

Odoo data is persisted in Docker volumes:
- `odoo-web-data`: Odoo filestore (attachments, documents)
- `odoo-db-data`: PostgreSQL database files

To backup:
```bash
# Backup database
docker exec -it odoo_db pg_dump -U odoo -d ai_employee_db > odoo_backup.sql

# Backup filestore
docker cp odoo:/var/lib/odoo/filestore ./odoo_filestore_backup
```

To restore:
```bash
# Restore database
cat odoo_backup.sql | docker exec -i odoo_db psql -U odoo -d ai_employee_db

# Restore filestore
docker cp ./odoo_filestore_backup odoo:/var/lib/odoo/filestore
```
