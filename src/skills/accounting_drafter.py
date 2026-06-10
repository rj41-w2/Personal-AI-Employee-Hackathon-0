import os
import time
import logging
from gemini_client import call_gemini

logger = logging.getLogger("AccountingDrafter")

def draft_accounting_task(file_path, base_vault_path, model=None):
    """
    Draft an Odoo accounting task (invoice creation, report generation, etc.)
    """
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "accounting_rules.md")

    # Default rules if file doesn't exist
    system_rules = """
You are an expert Odoo Accounting Assistant. Create structured accounting commands.

INSTRUCTIONS:
1. Analyze the accounting request (create invoice, check reports, list customers).
2. Generate a structured action that can be executed by the Odoo MCP server.
3. Output MUST follow this exact format:

## Plan
(Your analysis and reasoning here)

## Action: <tool_name>
<parameter>: <value>
<parameter>: <value>

Supported Actions:
- create_invoice: Parameters: Customer, Amount, Product (optional), Description (optional)
- get_accounting_summary: Parameters: Report (sales, outstanding, profit)
- list_partners: Parameters: Search (optional name/email filter)

IMPORTANT: Replace angle brackets with actual values. Do NOT deviate from this structure.
"""

    if os.path.exists(rules_path):
        with open(rules_path, 'r', encoding='utf-8') as f:
            system_rules = f.read()

    try:
        text_content = call_gemini(system_rules, f"Task Content:\n{content}", model)

        timestamp = int(time.time())
        parts = text_content.split('## Action:')
        plan_text = parts[0].strip()

        # Save plan
        plan_dir = base_vault_path / "Plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_filename = f"PLAN_{timestamp}_{file_path.name}"
        (plan_dir / plan_filename).write_text(f"{plan_text}\n\n---\n**Trigger**: {file_path.name}", encoding='utf-8')

        if len(parts) > 1:
            action_text = f"## Action: {parts[1].strip()}"
            new_filename = f"PENDING_{timestamp}_{file_path.name}"
            pending_dir = base_vault_path / "Pending_Approval" / "accounting"
            pending_dir.mkdir(parents=True, exist_ok=True)
            pending_file = pending_dir / new_filename

            full_content = f"{action_text}\n\n---\n**Original Trigger Task**: {file_path.name}\n"
            pending_file.write_text(full_content, encoding='utf-8')

        logger.info(f"Successfully drafted accounting task for {file_path.name}")
    except Exception as e:
        logger.error(f"Error drafting accounting task for {file_path.name}: {e}")
