import os
import time
import logging
from pathlib import Path
from datetime import datetime

import requests

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
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")


class OdooWatcher(BaseWatcher):
    """
    Watcher for Odoo ERP events - monitors for new invoices, payments, etc.
    Creates actionable tasks when specific accounting events occur.
    """

    def __init__(self, vault_path: str, check_interval: int = 300):
        super().__init__(vault_path, check_interval)
        self.url = ODOO_URL.rstrip("/")
        self.db = ODOO_DB
        self.username = ODOO_USERNAME
        self.password = ODOO_PASSWORD
        self._uid = None
        self._last_invoice_id = 0
        self._last_payment_id = 0

    def _rpc_call(self, service, method, *args, **kwargs):
        """Call Odoo JSON-RPC endpoint."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": list(args)
            },
            "id": int(time.time())
        }
        if kwargs:
            payload["params"]["kwargs"] = kwargs
        resp = requests.post(f"{self.url}/jsonrpc", json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get("error"):
            raise Exception(f"Odoo RPC error: {result['error']}")
        return result.get("result")

    def _connect(self):
        """Authenticate with Odoo via JSON-RPC."""
        if not self.username or not self.password:
            logger.warning("ODOO_USERNAME and ODOO_PASSWORD must be set in .env. OdooWatcher disabled.")
            return False

        try:
            self._uid = self._rpc_call("common", "login", self.db, self.username, self.password)
            if not self._uid:
                logger.error("Odoo authentication failed")
                return False
            logger.info(f"Connected to Odoo (uid: {self._uid})")
            return True
        except Exception as e:
            logger.error(f"Odoo connection failed: {e}")
            return False

    def check_for_updates(self) -> list:
        """Check for new invoices or significant events in Odoo."""
        try:
            if not self._uid:
                if not self._connect():
                    return []

            new_items = []

            # Search for new invoices
            invoice_ids = self._rpc_call(
                "object", "execute",
                self.db, self._uid, self.password,
                "account.move", "search",
                [("move_type", "=", "out_invoice"), ("id", ">", self._last_invoice_id)],
                limit=10, order="id desc"
            )

            if invoice_ids:
                self._last_invoice_id = max(invoice_ids)
                invoices = self._rpc_call(
                    "object", "execute",
                    self.db, self._uid, self.password,
                    "account.move", "read",
                    invoice_ids, ["name", "partner_id", "amount_total", "state"]
                )
                for inv in invoices:
                    partner_name = ""
                    if inv.get("partner_id"):
                        if isinstance(inv["partner_id"], list):
                            partner_name = inv["partner_id"][1] if len(inv["partner_id"]) > 1 else str(inv["partner_id"][0])
                        else:
                            partner_name = str(inv["partner_id"])
                    new_items.append({
                        "type": "new_invoice",
                        "id": inv["id"],
                        "name": inv.get("name", ""),
                        "partner": partner_name,
                        "amount": inv.get("amount_total", 0),
                        "state": inv.get("state", "")
                    })

            return new_items

        except Exception as e:
            logger.error(f"Error checking Odoo: {e}")
            self._uid = None
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
