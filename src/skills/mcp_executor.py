import asyncio
import shutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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

async def execute_mcp_tool(tool_name, server_script, kwargs):
    server_params = StdioServerParameters(
        command="uv",
        args=["run", server_script],
        env=None
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments=kwargs)

def process_approved_file(file_path, base_vault_path):
    """
    Executes an approved task and handles its movement.
    Returns a status message on success to push to the dashboard log, or raises an exception.
    """
    content = file_path.read_text(encoding='utf-8')
    category = "email" if file_path.name.startswith("GMAIL_") else "linkedin"
    
    category_done_dir = base_vault_path / "Done" / category
    category_done_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if "Action: send_email" in content:
            args = parse_mcp_arguments(content)
            if not args.get("to_email"):
                raise ValueError(f"Could not parse 'To:' parameter in {file_path.name}.")
                
            result = asyncio.run(execute_mcp_tool("send_email", "src/mcp/email_mcp_server.py", 
                {"to_email": args["to_email"], "subject": args["subject"], "body": args["body"]}
            ))
            
            shutil.move(str(file_path), str(category_done_dir / file_path.name))
            return f"MCP Protocol Server executed 'send_email' for {file_path.name}."

        elif "Action: post_to_linkedin" in content:
            args = parse_mcp_arguments(content)
            if not args.get("content"):
                raise ValueError("Could not parse 'Content:' parameter.")
                
            result = asyncio.run(execute_mcp_tool("post_to_linkedin", "src/mcp/linkedin_mcp_server.py", 
                {"content": args["content"]}
            ))
            
            shutil.move(str(file_path), str(category_done_dir / file_path.name))
            return f"Published LinkedIn Post via API for {file_path.name}."
            
        else:
            return None
            
    except Exception as e:
        shutil.move(str(file_path), str(category_done_dir / f"FAILED_{file_path.name}"))
        raise e
