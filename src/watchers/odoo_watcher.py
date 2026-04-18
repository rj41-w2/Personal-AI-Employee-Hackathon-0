import os
import time
import logging
from pathlib import Path
from datetime import datetime

try:
    import odoorpc
    ODOORPC_AVAILABLE = True
except ImportError:
    ODOORPC_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from base_watcher import BaseWatcher

logger = logging.getLogger("OdooWatcher")

# Odoo config from environment
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(root_dir, ".env")

# Load env vars
if os.path.exists(env_path):
    from dotenv import load_dotenv
    load_dotenv(env_path)

ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "ai_employee_db")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")


class OdooWatcher(BaseWatcher):
    """
    Watcher for Odoo ERP events - monitors for new invoices, payments, etc.
    Creates actionable tasks when specific accounting events occur.
    """

    def __init__(self, vault_path: str, check_interval: int = 300):
        super().__init__(vault_path, check_interval)
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USERNAME
        self.password = ODOO_PASSWORD
        self._odoo = None
        self._last_invoice_id = 0
        self._last_payment_id = 0

        if not ODOORPC_AVAILABLE and not REQUESTS_AVAILABLE:
            logger.warning("No Odoo client library available. OdooWatcher disabled.")

    def _connect(self):
        """Connect to Odoo using odoorpc or requests."""
        if ODOORPC_AVAILABLE:
            host = self.url.replace("http://", "").replace("https://", "").split(":")[0]
            port = 8069
            if ":" in self.url.replace("http://", "").replace("https://", ""):
                try:
                    port = int(self.url.split(":")[-1])
                except ValueError:
                    pass
            self._odoo = odoorpc.ODOO(host, port=port)
            self._odoo.login(self.db, self.username, self.password)
            logger.info("Connected to Odoo via odoorpc")
            return True
        return False

    def check_for_updates(self) -> list:
        """Check for new invoices or significant events in Odoo."""
        if not ODOORPC_AVAILABLE:
            return []

        try:
            if not self._odoo:
                if not self._connect():
                    return []

            new_items = []

            # Check for invoices created since last check
            Invoice = self._odoo.env['account.move']
            new_invoices = Invoice.search([
                ('move_type', '=', 'out_invoice'),
                ('id', '>', self._last_invoice_id)
            ], limit=10, order='id desc')

            if new_invoices:
                self._last_invoice_id = max(new_invoices)
                for inv_id in new_invoices:
                    inv = Invoice.browse(inv_id)
                    new_items.append({
                        'type': 'new_invoice',
                        'id': inv_id,
                        'name': inv.name,
                        'partner': inv.partner_id.name,
                        'amount': inv.amount_total,
                        'state': inv.state
                    })

            return new_items

        except Exception as e:
            logger.error(f"Error checking Odoo: {e}")
            self._odoo = None  # Reset connection
            return []

    def create_action_file(self, item) -> Path:
        """Create a markdown file for the Odoo event."""
        try:
            timestamp = int(time.time())

            if item['type'] == 'new_invoice':
                content = f"### New Invoice Created\n"
                content += f"Invoice: {item['name']}\n"
                content += f"Customer: {item['partner']}\n"
                content += f"Amount: ${item['amount']:.2f}\n"
                content += f"State: {item['state']}\n\n"
                content += f"This invoice was just created in Odoo and may need follow-up.\n"

                filename = f"ODOO_invoice_{timestamp}_{item['id']}.md"

            accounting_dir = self.needs_action / "accounting"
            accounting_dir.mkdir(parents=True, exist_ok=True)
            filepath = accounting_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"---\ntype: odoo_event\nsubtype: {item['type']}\npriority: medium\nstatus: pending\n---\n\n{content}\n")

            logger.info(f"Created Odoo event file: {filepath.name}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to create action file: {e}")
            return None


if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    vault_path = os.path.join(project_root, "AI_Employee_Vault")

    watcher = OdooWatcher(vault_path)
    logger.info("Starting Odoo Watcher...")
    try:
        watcher.run()
    except KeyboardInterrupt:
        logger.info("Gracefully shut down OdooWatcher.")
