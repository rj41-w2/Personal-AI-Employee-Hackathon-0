import os
import sys
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Odoo_MCP")

# Load environment variables from project root
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(root_dir, ".env")
load_dotenv(env_path)

# Odoo configuration from environment
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "ai_employee_db")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "admin")

# Try to import odoorpc, fallback to requests
ODOORPC_AVAILABLE = False
REQUESTS_AVAILABLE = False

try:
    import odoorpc
    ODOORPC_AVAILABLE = True
    logger.info("Using odoorpc library for Odoo communication")
except ImportError:
    logger.warning("odoorpc not available, will fallback to requests")
    try:
        import requests
        REQUESTS_AVAILABLE = True
        logger.info("Using requests library for Odoo JSON-RPC")
    except ImportError:
        logger.error("Neither odoorpc nor requests available. Please install one.")
        raise ImportError("Odoo MCP requires either 'odoorpc' or 'requests' library")


class OdooClient:
    """Wrapper for Odoo JSON-RPC communication."""

    def __init__(self):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USERNAME
        self.password = ODOO_PASSWORD
        self._odoo = None
        self._uid = None
        self._session = None

    def _get_common_endpoint(self) -> str:
        """Get the JSON-RPC common endpoint URL."""
        return f"{self.url}/jsonrpc"

    def _get_object_endpoint(self) -> str:
        """Get the JSON-RPC object endpoint URL."""
        return f"{self.url}/jsonrpc"

    def _jsonrpc(self, endpoint: str, service: str, method: str, args: list = None) -> Any:
        """Make a JSON-RPC call using requests."""
        import requests
        import json

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args or []
            },
            "id": 1
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise Exception(f"Odoo RPC Error: {result['error']}")

        return result.get("result")

    def authenticate(self) -> int:
        """Authenticate with Odoo and return user ID."""
        if ODOORPC_AVAILABLE:
            self._odoo = odoorpc.ODOO(self.url.replace("http://", "").replace("https://", "").split(":")[0], port=8069)
            self._odoo.login(self.db, self.username, self.password)
            self._uid = self._odoo.env.uid
            return self._uid
        else:
            # Using requests for JSON-RPC
            self._uid = self._jsonrpc(
                self._get_common_endpoint(),
                "common",
                "login",
                [self.db, self.username, self.password]
            )
            if not self._uid:
                raise Exception("Authentication failed")
            logger.info(f"Authenticated with Odoo, UID: {self._uid}")
            return self._uid

    def _convert_to_tuples(self, domain):
        """Convert domain lists to tuples for Odoo JSON-RPC compatibility."""
        if not isinstance(domain, list):
            return domain
        result = []
        for item in domain:
            if isinstance(item, list) and len(item) == 3:
                # Convert ['field', 'operator', value] to ('field', 'operator', value)
                result.append((item[0], item[1], item[2]))
            else:
                result.append(item)
        return result

    def execute_kw(self, model: str, method: str, args: list = None, kwargs: dict = None) -> Any:
        """Execute a method on an Odoo model."""
        if not self._uid:
            self.authenticate()

        if ODOORPC_AVAILABLE and self._odoo:
            model_obj = self._odoo.env[model]
            if method == "search":
                return model_obj.search(args or [])
            elif method == "search_read":
                return model_obj.search_read(args or [], kwargs.get("fields", []))
            elif method == "create":
                return model_obj.create(args[0])
            elif method == "read":
                return model_obj.read(args[0] if args else [], kwargs.get("fields", []))
            elif method == "read_group":
                return model_obj.read_group(args[0] if args else [], kwargs.get("fields", []), kwargs.get("groupby", []), kwargs.get("lazy", True))
            else:
                return getattr(model_obj, method)(*(args or []), **(kwargs or {}))
        else:
            # Using requests for JSON-RPC - convert domain lists to tuples
            converted_args = []
            if args:
                for arg in args:
                    # Convert domain lists to tuples
                    if isinstance(arg, list) and arg and isinstance(arg[0], list):
                        converted_args.append(self._convert_to_tuples(arg))
                    else:
                        converted_args.append(arg)

            rpc_args = [self.db, self._uid, self.password, model, method]
            if converted_args:
                rpc_args.append(converted_args)
            if kwargs:
                rpc_args.append(kwargs)

            return self._jsonrpc(
                self._get_object_endpoint(),
                "object",
                "execute_kw",
                rpc_args
            )


# Initialize MCP server
mcp = FastMCP("Personal_AI_Employee_Odoo")

# Global client instance
_odoo_client = None

def get_odoo_client() -> OdooClient:
    """Get or create Odoo client instance."""
    global _odoo_client
    if _odoo_client is None:
        _odoo_client = OdooClient()
        _odoo_client.authenticate()
    return _odoo_client


@mcp.tool()
def create_invoice(customer_name: str, amount: float, product_name: str = "Service",
                     description: str = "", currency_id: int = 1) -> str:
    """
    Create a draft customer invoice in Odoo.

    Args:
        customer_name: Name of the customer (will search/create partner)
        amount: Invoice amount
        product_name: Name of the product/service (default: "Service")
        description: Optional invoice line description
        currency_id: Currency ID (default: 1 for USD)

    Returns:
        Success message with invoice number or error message
    """
    try:
        client = get_odoo_client()

        # Search for existing partner by name
        partner_ids = client.execute_kw(
            "res.partner", "search",
            [("name", "ilike", customer_name)]
        )

        if partner_ids:
            partner_id = partner_ids[0] if isinstance(partner_ids, list) else partner_ids
            logger.info(f"Found existing partner: {customer_name} (ID: {partner_id})")
        else:
            # Create new partner
            partner_vals = {
                "name": customer_name,
                "customer_rank": 1,
                "is_company": False
            }
            new_partner_id = client.execute_kw(
                "res.partner", "create", [[partner_vals]]
            )
            partner_id = new_partner_id[0] if isinstance(new_partner_id, list) else new_partner_id
            logger.info(f"Created new partner: {customer_name} (ID: {partner_id})")

        # Search for product
        product_ids = client.execute_kw(
            "product.product", "search",
            [("name", "ilike", product_name)]
        )

        if product_ids:
            product_id = product_ids[0] if isinstance(product_ids, list) else product_ids
            product_data = client.execute_kw(
                "product.product", "read",
                [[product_id]], {"fields": ["name", "lst_price"]}
            )
            unit_price = product_data[0].get("lst_price", amount) if isinstance(product_data[0], dict) else amount
        else:
            # Use generic service product
            product_id = False
            unit_price = amount

        # Prepare invoice lines
        invoice_line_vals = [{
            "name": description or product_name,
            "quantity": 1,
            "price_unit": amount,
            "product_id": product_id if product_id else False
        }]

        # Create invoice
        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": partner_id,
            "invoice_date": str(date.today()),
            "currency_id": currency_id,
            "invoice_line_ids": [(0, 0, line) for line in invoice_line_vals]
        }

        invoice_id = client.execute_kw(
            "account.move", "create", [[invoice_vals]]
        )
        invoice_id = invoice_id[0] if isinstance(invoice_id, list) else invoice_id

        # Get invoice name
        invoice_data = client.execute_kw(
            "account.move", "read",
            [[invoice_id]], {"fields": ["name", "state"]}
        )

        invoice_info = invoice_data[0] if isinstance(invoice_data, list) and invoice_data else {}
        invoice_name = invoice_info.get("name", f"INV-{invoice_id}") if isinstance(invoice_info, dict) else f"INV-{invoice_id}"

        logger.info(f"Created invoice: {invoice_name} for {customer_name}, amount: {amount}")
        return f"SUCCESS: Created draft invoice {invoice_name} for {customer_name} with amount ${amount:.2f}. Invoice ID: {invoice_id}"

    except Exception as e:
        error_msg = f"ERROR: Failed to create invoice: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
def get_accounting_summary(report_type: str = "sales", month: Optional[int] = None,
                              year: Optional[int] = None) -> str:
    """
    Get accounting summary from Odoo.

    Args:
        report_type: Type of report - "sales", "invoices", "outstanding", "profit"
        month: Month number (1-12), defaults to current month
        year: Year (e.g., 2026), defaults to current year

    Returns:
        Summary report as formatted string
    """
    try:
        client = get_odoo_client()

        now = datetime.now()
        target_month = month or now.month
        target_year = year or now.year

        # Calculate date range
        start_date = date(target_year, target_month, 1)
        if target_month == 12:
            end_date = date(target_year + 1, 1, 1)
        else:
            end_date = date(target_year, target_month + 1, 1)

        logger.info(f"Generating {report_type} report for {target_month}/{target_year}")

        if report_type == "sales":
            # Get confirmed invoices (posted)
            domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_date", ">=", str(start_date)),
                ("invoice_date", "<", str(end_date))
            ]

            invoices = client.execute_kw(
                "account.move", "search_read",
                [domain],
                {"fields": ["name", "amount_total", "invoice_date", "partner_id"]}
            )

            total_sales = sum(inv.get("amount_total", 0) if isinstance(inv, dict) else 0
                            for inv in invoices)
            invoice_count = len(invoices)

            result = f"Sales Report for {target_month}/{target_year}\n"
            result += f"Total Sales: ${total_sales:,.2f}\n"
            result += f"Invoice Count: {invoice_count}\n"
            if invoice_count > 0:
                result += "\nTop 5 Invoices:\n"
                for inv in invoices[:5]:
                    if isinstance(inv, dict):
                        result += f"  - {inv.get('name', 'N/A')}: ${inv.get('amount_total', 0):,.2f}\n"

            return f"SUCCESS: {result}"

        elif report_type == "outstanding":
            # Get unpaid invoices
            domain = [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ["not_paid", "partial"])
            ]

            invoices = client.execute_kw(
                "account.move", "search_read",
                [domain],
                {"fields": ["name", "amount_residual", "partner_id", "invoice_date"]}
            )

            total_outstanding = sum(inv.get("amount_residual", 0) if isinstance(inv, dict) else 0
                                  for inv in invoices)
            invoice_count = len(invoices)

            result = f"Outstanding Invoices Report\n"
            result += f"Total Outstanding: ${total_outstanding:,.2f}\n"
            result += f"Unpaid Invoices: {invoice_count}\n"
            if invoice_count > 0:
                result += "\nTop 10 Outstanding:\n"
                for inv in invoices[:10]:
                    if isinstance(inv, dict):
                        result += f"  - {inv.get('name', 'N/A')}: ${inv.get('amount_residual', 0):,.2f}\n"

            return f"SUCCESS: {result}"

        elif report_type == "profit":
            # Get income and expense accounts
            accounts = client.execute_kw(
                "account.account", "search_read",
                [[("account_type", "in", ["income", "expense"])]],
                {"fields": ["name", "account_type", "balance"]}
            )

            total_income = sum(acc.get("balance", 0) if isinstance(acc, dict) and acc.get("account_type") == "income" else 0
                           for acc in accounts)
            total_expense = sum(acc.get("balance", 0) if isinstance(acc, dict) and acc.get("account_type") == "expense" else 0
                           for acc in accounts)

            profit = total_income - total_expense

            result = f"Profit/Loss Summary\n"
            result += f"Total Income: ${total_income:,.2f}\n"
            result += f"Total Expense: ${total_expense:,.2f}\n"
            result += f"Net Profit: ${profit:,.2f}\n"

            return f"SUCCESS: {result}"

        else:
            return f"ERROR: Unknown report type: {report_type}. Use: sales, outstanding, profit"

    except Exception as e:
        error_msg = f"ERROR: Failed to get accounting summary: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
def list_partners(search_term: str = "", limit: int = 20, partner_type: str = "all") -> str:
    """
    Search for customers/vendors in Odoo.

    Args:
        search_term: Name or email to search for
        limit: Maximum number of results (default: 20)
        partner_type: Filter by type - "customer", "vendor", "all"

    Returns:
        Formatted list of matching partners
    """
    try:
        client = get_odoo_client()

        # Build domain
        domain = []
        if search_term:
            domain.append("|" if len(domain) == 0 else "&")
            domain.append(("name", "ilike", search_term))
            domain.append(("email", "ilike", search_term))

        if partner_type == "customer":
            domain.append(("customer_rank", ">", 0))
        elif partner_type == "vendor":
            domain.append(("supplier_rank", ">", 0))

        partners = client.execute_kw(
            "res.partner", "search_read",
            [domain] if domain else [[]],
            {"fields": ["name", "email", "phone", "city", "country_id", "customer_rank", "supplier_rank"],
             "limit": limit}
        )

        if not partners:
            return f"No partners found for search: '{search_term}'"

        result = f"Found {len(partners)} partners:\n\n"
        for partner in partners:
            if isinstance(partner, dict):
                partner_type_str = []
                if partner.get("customer_rank", 0) > 0:
                    partner_type_str.append("Customer")
                if partner.get("supplier_rank", 0) > 0:
                    partner_type_str.append("Vendor")

                result += f"ID: {partner.get('id', 'N/A')}\n"
                result += f"  Name: {partner.get('name', 'N/A')}\n"
                result += f"  Email: {partner.get('email', 'N/A')}\n"
                result += f"  Phone: {partner.get('phone', 'N/A')}\n"
                result += f"  Location: {partner.get('city', '')}, {partner.get('country_id', ['', ''])[1] if partner.get('country_id') else ''}\n"
                result += f"  Type: {', '.join(partner_type_str) or 'Contact'}\n"
                result += "\n"

        return f"SUCCESS: {result}"

    except Exception as e:
        error_msg = f"ERROR: Failed to list partners: {str(e)}"
        logger.error(error_msg)
        return error_msg


@mcp.tool()
def get_invoice_status(invoice_name: str = "", partner_name: str = "") -> str:
    """
    Check the status of an invoice.

    Args:
        invoice_name: Invoice number (e.g., "INV/2026/0001")
        partner_name: Filter by customer name

    Returns:
        Invoice status information
    """
    try:
        client = get_odoo_client()

        domain = []
        if invoice_name:
            domain.append(("name", "ilike", invoice_name))
        if partner_name:
            partner_ids = client.execute_kw(
                "res.partner", "search",
                [("name", "ilike", partner_name)]
            )
            if partner_ids:
                domain.append(["partner_id", "in", partner_ids])

        if not domain:
            return "ERROR: Please provide invoice_name or partner_name"

        invoices = client.execute_kw(
            "account.move", "search_read",
            [domain],
            {"fields": ["name", "state", "amount_total", "amount_residual", "payment_state",
                       "partner_id", "invoice_date", "due_date"], "limit": 20}
        )

        if not invoices:
            return f"No invoices found matching criteria"

        result = f"Found {len(invoices)} invoices:\n\n"
        for inv in invoices:
            if isinstance(inv, dict):
                result += f"Invoice: {inv.get('name', 'N/A')}\n"
                result += f"  State: {inv.get('state', 'N/A')}\n"
                result += f"  Payment: {inv.get('payment_state', 'N/A')}\n"
                result += f"  Total: ${inv.get('amount_total', 0):,.2f}\n"
                result += f"  Residual: ${inv.get('amount_residual', 0):,.2f}\n"
                result += f"  Partner: {inv.get('partner_id', ['', ''])[1] if inv.get('partner_id') else 'N/A'}\n"
                result += "\n"

        return f"SUCCESS: {result}"

    except Exception as e:
        error_msg = f"ERROR: Failed to get invoice status: {str(e)}"
        logger.error(error_msg)
        return error_msg


if __name__ == "__main__":
    logger.info("Starting Odoo MCP server...")
    logger.info(f"Connecting to Odoo at: {ODOO_URL}")
    logger.info(f"Database: {ODOO_DB}")

    # Test connection on startup
    try:
        client = get_odoo_client()
        logger.info("Successfully connected to Odoo!")
    except Exception as e:
        logger.error(f"Failed to connect to Odoo: {e}")
        logger.error("Server will start but tools may fail until connection is available")

    logger.info("Running Odoo MCP server on stdio...")
    mcp.run(transport='stdio')
