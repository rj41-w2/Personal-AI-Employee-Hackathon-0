import os
import sys
import asyncio
import shutil
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("MCPExecutor")

# Resolve absolute paths to the MCP server scripts from project root
# src/skills/mcp_executor.py -> src/skills/ -> src/ -> project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMAIL_MCP_SERVER = os.path.join(PROJECT_ROOT, "src", "mcp", "email_mcp_server.py")
LINKEDIN_MCP_SERVER = os.path.join(PROJECT_ROOT, "src", "mcp", "linkedin_mcp_server.py")
ODOO_MCP_SERVER = os.path.join(PROJECT_ROOT, "src", "mcp", "odoo_mcp_server.py")

def parse_mcp_arguments(content):
    """
    Parses To/Subject/Body for emails and Content for LinkedIn posts.
    Includes a fallback: if no explicit Content: label is found for LinkedIn,
    it extracts everything between the Action header and the --- delimiter.
    """
    to_email = None
    subject = None
    body = []
    in_body = False
    
    for line in content.split('\n'):
        if line.startswith('To:'):
            to_email = line.replace('To:', '').strip(' \t\n\r<>`\'"')
        elif line.startswith('Subject:'):
            subject = line.replace('Subject:', '').strip(' \t\n\r')
        elif line.startswith('Body:') or line.startswith('Content:'):
            in_body = True
        elif in_body and not line.startswith('---'):
            body.append(line)
    
    parsed_content = "\n".join(body).strip(' \t\n\r')
    
    # Fallback for LinkedIn: if no Content:/Body: label was found,
    # grab everything between "Action: post_to_linkedin" and "---"
    if not parsed_content and "post_to_linkedin" in content:
        fallback_lines = []
        in_action = False
        for line in content.split('\n'):
            if "Action:" in line and "post_to_linkedin" in line:
                in_action = True
                continue
            elif in_action and line.strip().startswith('---'):
                break
            elif in_action:
                fallback_lines.append(line)
        parsed_content = "\n".join(fallback_lines).strip(' \t\n\r')
        if parsed_content:
            logger.info("Used fallback parser: extracted content between Action header and --- delimiter.")
            
    return {
        "to_email": to_email,
        "subject": subject,
        "body": "\n".join(body).strip(' \t\n\r'),
        "content": parsed_content
    }

async def execute_mcp_tool(tool_name, server_script_abs_path, kwargs):
    """
    Spawns the target MCP server as a subprocess via stdio and calls the specified tool.
    Uses absolute paths to avoid working-directory-dependent failures.
    """
    server_params = StdioServerParameters(
        command=sys.executable,  # Use the current Python interpreter
        args=[server_script_abs_path],
        env=None
    )
    logger.info(f"Spawning MCP server: {server_script_abs_path} for tool: {tool_name}")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=kwargs)
                return result
    except BaseException as e:
        # Unwrap ExceptionGroup / TaskGroup errors to expose the real root cause
        real_error = e
        if hasattr(e, 'exceptions'):
            for sub_exc in e.exceptions:
                logger.error(f"  Sub-exception: {type(sub_exc).__name__}: {sub_exc}")
            real_error = e.exceptions[0] if e.exceptions else e
        raise RuntimeError(f"MCP tool '{tool_name}' failed: {type(real_error).__name__}: {real_error}") from real_error

ERROR_KEYWORDS = ["Error", "FAILED", "Failed", "ERROR", "401", "400", "403", "404", "500 Internal"]

def _check_mcp_result_for_errors(result):
    """
    Extracts the text output from the MCP result and scans it for error indicators.
    Returns (is_success: bool, output_text: str).
    """
    # Extract all text from result content blocks
    output_text = ""
    if hasattr(result, 'content') and result.content:
        output_text = " | ".join(
            getattr(c, 'text', str(c)) for c in result.content
        )
    
    # Also check structuredContent if present
    if hasattr(result, 'structuredContent') and result.structuredContent:
        sc = str(result.structuredContent)
        output_text = f"{output_text} | {sc}" if output_text else sc

    logger.info(f"MCP raw output: {output_text}")
    
    # Check isError flag first
    if hasattr(result, 'isError') and result.isError:
        logger.error(f"MCP returned isError=True: {output_text}")
        return False, output_text
    
    # Scan text for error keywords
    for keyword in ERROR_KEYWORDS:
        if keyword in output_text:
            logger.error(f"MCP output contains error keyword '{keyword}': {output_text}")
            return False, output_text
    
    # Check for SUCCESS prefix (our LinkedIn server explicitly returns this)
    if output_text.startswith("SUCCESS:"):
        return True, output_text
    
    # No errors found
    return True, output_text


def process_approved_file(file_path, base_vault_path):
    """
    Executes an approved task via MCP.
    Returns (success: bool, status_message: str).
    Does NOT move files — the orchestrator handles that.
    """
    import traceback
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        if "Action: send_email" in content or "Action:send_email" in content:
            args = parse_mcp_arguments(content)
            if not args.get("to_email"):
                return False, f"Could not parse 'To:' parameter in {file_path.name}."
                
            result = asyncio.run(execute_mcp_tool("send_email", EMAIL_MCP_SERVER, 
                {"to_email": args["to_email"], "subject": args["subject"], "body": args["body"]}
            ))
            
            success, output = _check_mcp_result_for_errors(result)
            if success:
                return True, f"MCP executed 'send_email' for {file_path.name}."
            else:
                return False, f"send_email FAILED for {file_path.name}: {output}"

        elif "Action: post_to_linkedin" in content or "Action:post_to_linkedin" in content:
            args = parse_mcp_arguments(content)
            if not args.get("content"):
                return False, "Could not parse 'Content:' parameter."

            result = asyncio.run(execute_mcp_tool("post_to_linkedin", LINKEDIN_MCP_SERVER,
                {"content": args["content"]}
            ))

            success, output = _check_mcp_result_for_errors(result)
            if success:
                return True, f"Published LinkedIn Post for {file_path.name}."
            else:
                return False, f"post_to_linkedin FAILED for {file_path.name}: {output}"

        elif "Action: create_invoice" in content or "Action:create_invoice" in content:
            # Parse invoice parameters directly from content
            customer_name = None
            amount = None
            product_name = "Service"
            description = ""

            for line in content.split('\n'):
                if line.startswith('Customer:'):
                    customer_name = line.replace('Customer:', '').strip()
                elif line.startswith('Amount:'):
                    amount_str = line.replace('Amount:', '').strip().replace('$', '').replace(',', '')
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        pass
                elif line.startswith('Product:'):
                    product_name = line.replace('Product:', '').strip()
                elif line.startswith('Description:'):
                    description = line.replace('Description:', '').strip()

            if not customer_name or amount is None:
                return False, f"Missing Customer or Amount in invoice request: {file_path.name}"

            result = asyncio.run(execute_mcp_tool("create_invoice", ODOO_MCP_SERVER,
                {"customer_name": customer_name, "amount": amount, "product_name": product_name, "description": description}
            ))

            success, output = _check_mcp_result_for_errors(result)
            if success:
                return True, f"Odoo MCP created invoice for {file_path.name}: {output}"
            else:
                return False, f"create_invoice FAILED for {file_path.name}: {output}"

        elif "Action: get_accounting_summary" in content or "Action:get_accounting_summary" in content:
            report_type = "sales"
            for line in content.split('\n'):
                if line.startswith('Report:'):
                    report_type = line.replace('Report:', '').strip()

            result = asyncio.run(execute_mcp_tool("get_accounting_summary", ODOO_MCP_SERVER,
                {"report_type": report_type}
            ))

            success, output = _check_mcp_result_for_errors(result)
            if success:
                return True, f"Odoo accounting summary for {file_path.name}: {output}"
            else:
                return False, f"get_accounting_summary FAILED for {file_path.name}: {output}"

        elif "Action: list_partners" in content or "Action:list_partners" in content:
            search_term = ""
            for line in content.split('\n'):
                if line.startswith('Search:'):
                    search_term = line.replace('Search:', '').strip()

            result = asyncio.run(execute_mcp_tool("list_partners", ODOO_MCP_SERVER,
                {"search_term": search_term}
            ))

            success, output = _check_mcp_result_for_errors(result)
            if success:
                return True, f"Odoo partners list for {file_path.name}: {output}"
            else:
                return False, f"list_partners FAILED for {file_path.name}: {output}"

        else:
            return False, f"No recognized Action found in {file_path.name}."
            
    except Exception as e:
        # Print the FULL traceback to terminal so the exact crash point is visible
        full_traceback = traceback.format_exc()
        logger.error(f"MCP EXECUTOR CRASH for {file_path.name}:\n{full_traceback}")
        return False, f"EXECUTOR CRASHED: {type(e).__name__}: {e}"

