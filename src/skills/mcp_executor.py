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

def parse_mcp_arguments(content):
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
            
    return {
        "to_email": to_email,
        "subject": subject,
        "body": "\n".join(body).strip(' \t\n\r'),
        "content": "\n".join(body).strip(' \t\n\r')
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

def process_approved_file(file_path, base_vault_path):
    """
    Executes an approved task and handles its movement.
    Returns a status message on success to push to the dashboard log, or raises an exception.
    """
    content = file_path.read_text(encoding='utf-8')
    # Detect category by checking if GMAIL_ appears anywhere in the filename,
    # because drafter prefixes like PENDING_ shift the original prefix position.
    category = "email" if "GMAIL_" in file_path.name else "linkedin"
    
    category_done_dir = base_vault_path / "Done" / category
    category_done_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if "Action: send_email" in content:
            args = parse_mcp_arguments(content)
            if not args.get("to_email"):
                raise ValueError(f"Could not parse 'To:' parameter in {file_path.name}.")
                
            result = asyncio.run(execute_mcp_tool("send_email", EMAIL_MCP_SERVER, 
                {"to_email": args["to_email"], "subject": args["subject"], "body": args["body"]}
            ))
            
            logger.info(f"MCP Result: {result}")
            shutil.move(str(file_path), str(category_done_dir / file_path.name))
            return f"MCP Protocol Server executed 'send_email' for {file_path.name}."

        elif "Action: post_to_linkedin" in content:
            args = parse_mcp_arguments(content)
            if not args.get("content"):
                raise ValueError("Could not parse 'Content:' parameter.")
                
            result = asyncio.run(execute_mcp_tool("post_to_linkedin", LINKEDIN_MCP_SERVER, 
                {"content": args["content"]}
            ))
            
            logger.info(f"MCP Result: {result}")
            shutil.move(str(file_path), str(category_done_dir / file_path.name))
            return f"Published LinkedIn Post via API for {file_path.name}."
            
        else:
            return None
            
    except Exception as e:
        logger.error(f"Execution failed for {file_path.name}: {type(e).__name__}: {e}")
        shutil.move(str(file_path), str(category_done_dir / f"FAILED_{file_path.name}"))
        raise e
