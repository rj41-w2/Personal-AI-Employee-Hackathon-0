import os
import time
import shutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Orchestrator")

class Orchestrator:
    def __init__(self, vault_path: str, model_name="llama3.2"):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.pending_approval = self.vault_path / "Pending_Approval"
        self.pending_approval_linkedin = self.vault_path / "Pending_Approval" / "Linkedin_Post"
        self.approved = self.vault_path / "Approved"
        self.done = self.vault_path / "Done"
        self.done_linkedin = self.vault_path / "Done" / "Linkedin_Post"
        self.plans = self.vault_path / "Plans"
        self.original_mail = self.vault_path / "Original_Mail"
        self.dashboard = self.vault_path / "Dashboard.md"
        self.model = model_name

        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.pending_approval.mkdir(parents=True, exist_ok=True)
        self.pending_approval_linkedin.mkdir(parents=True, exist_ok=True)
        self.approved.mkdir(parents=True, exist_ok=True)
        self.done.mkdir(parents=True, exist_ok=True)
        self.done_linkedin.mkdir(parents=True, exist_ok=True)
        self.plans.mkdir(parents=True, exist_ok=True)
        self.original_mail.mkdir(parents=True, exist_ok=True)

    def process_needs_action(self):
        for file_path in self.needs_action.glob("*.md"):
            logger.info(f"Ollama reasoning started for: {file_path.name}")
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            if file_path.name.startswith("LINKEDIN_"):
                prompt = (
                    f"Task Content:\n{content}\n\n"
                    "INSTRUCTIONS:\n"
                    "1. Formulate a professional LinkedIn post based on the given topic.\n"
                    "2. Generate a strict Markdown output matching this exact template:\n"
                    "## Plan\n"
                    "(Your reasoning and outline here)\n\n"
                    "## Action: post_to_linkedin\n"
                    "Content:\n<your highly engaging linkedin post text here>\n"
                )
                pending_target_dir = self.pending_approval_linkedin
            else:
                prompt = (
                    f"Task Header and Content:\n{content}\n\n"
                    "INSTRUCTIONS:\n"
                    "1. Read the task. Generate a plan detailing how you will respond.\n"
                    "2. Generate a strict Markdown output matching this exact template:\n"
                    "## Plan\n"
                    "(Your step-by-step reasoning plan here)\n\n"
                    "## Action: send_email\n"
                    "To: <extracted sender email>\n"
                    "Subject: <your generated subject>\n"
                    "Body:\n<your exact email body here>\n"
                    "\n"
                    "IMPORTANT: Replace the angle brackets with your generated content. Do NOT deviate from this structure."
                )
                pending_target_dir = self.pending_approval

            try:
                response = ollama.chat(
                    model=self.model,
                    messages=[
                        {'role': 'system', 'content': 'You are the Reasoning Agent. Generate strictly formatted markdown plans and action templates.'},
                        {'role': 'user', 'content': prompt}
                    ]
                )
                
                text_content = response['message']['content']
                timestamp = int(time.time())
                
                parts = text_content.split('## Action:')
                plan_text = parts[0].strip()
                
                plan_filename = f"PLAN_{timestamp}_{file_path.name}"
                plan_file = self.plans / plan_filename
                plan_file.write_text(f"{plan_text}\n\n---\n**Trigger Task**: {file_path.name}", encoding='utf-8')
                
                if len(parts) > 1:
                    action_text = f"## Action:{parts[1]}"
                    new_filename = f"PENDING_{timestamp}_{file_path.name}"
                    pending_file = pending_target_dir / new_filename
                    full_content = f"{action_text}\n\n---\n**Original Trigger Task**: {file_path.name}\n"
                    pending_file.write_text(full_content, encoding='utf-8')
                
                shutil.move(str(file_path), str(self.original_mail / file_path.name))
                logger.info(f"Successfully drafted plan/reply to {pending_file.name}")
                self.update_dashboard(file_path.name, "Reasoning complete. Requesting HITL Approval.")
                
            except Exception as e:
                logger.error(f"Error logic processing {file_path.name}: {e}")

    async def execute_mcp_tool(self, tool_name, server_script, kwargs):
        server_params = StdioServerParameters(
            command="uv",
            args=["run", server_script],
            env=None
        )
        logger.info(f"Initializing MCP Stdio ClientSession to invoke server tool: {tool_name}...")
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=kwargs)
                return result

    def parse_mcp_arguments(self, content):
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

    def process_approved(self):
        for file_path in self.approved.glob("*.md"):
            logger.info(f"Detected HITL Approved task: {file_path.name}.")
            content = file_path.read_text(encoding='utf-8')
            
            if "Action: send_email" in content:
                args = self.parse_mcp_arguments(content)
                if not args["to_email"]:
                    logger.error(f"Could not parse 'To:' parameter in {file_path.name}. Failing execution.")
                    shutil.move(str(file_path), str(self.done / f"FAILED_{file_path.name}"))
                    continue
                
                try:
                    # Execute async MCP client bridge block securely
                    logger.info("Parsed Action parameters successfully. Attempting MCP Execution...")
                    result = asyncio.run(self.execute_mcp_tool("send_email", "src/mcp_server.py", {"to_email": args["to_email"], "subject": args["subject"], "body": args["body"]}))
                    
                    logger.info(f"MCP Action Output: {result}")
                    self.update_dashboard(file_path.name, f"MCP Protocol Server executed 'send_email'.")
                    
                    dest_path = self.done / file_path.name
                    shutil.move(str(file_path), str(dest_path))
                except Exception as e:
                    logger.error(f"MCP Protocol error trying to execute tool: {e}")
                    # If it fails, move to a failed state to avoid infinite loop
                    dest_path = self.done / f"FAILED_{file_path.name}"
                    shutil.move(str(file_path), str(dest_path))

            elif "Action: post_to_linkedin" in content:
                args = self.parse_mcp_arguments(content)
                if not args.get("content"):
                    logger.error("Could not parse 'Content:' parameter. Failing execution.")
                    shutil.move(str(file_path), str(self.done_linkedin / f"FAILED_{file_path.name}"))
                    continue
                
                try:
                    logger.info("Parsed LinkedIn payload safely. Attempting execution...")
                    result = asyncio.run(self.execute_mcp_tool("post_to_linkedin", "src/linkedin_mcp_server.py", {"content": args["content"]}))
                    
                    logger.info(f"MCP Action Output: {result}")
                    self.update_dashboard(file_path.name, "Published LinkedIn Post via API.")
                    
                    dest_path = self.done_linkedin / file_path.name
                    shutil.move(str(file_path), str(dest_path))
                except Exception as e:
                    logger.error(f"LinkedIn MCP error: {e}")
                    dest_path = self.done_linkedin / f"FAILED_{file_path.name}"
                    shutil.move(str(file_path), str(dest_path))

    def update_dashboard(self, task_name, action_desc):
        if not self.dashboard.exists():
            return
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"- [{current_time}] {action_desc} -> {task_name}\n"
        
        content = self.dashboard.read_text(encoding='utf-8')
        if "## Recent Activity\n" in content:
            content = content.replace("## Recent Activity\n", f"## Recent Activity\n{entry}")
            self.dashboard.write_text(content, encoding='utf-8')

if __name__ == "__main__":
    vault_path = r"c:\Users\rehan\Projects\Personal-AI-Employee-Hackathon-0\AI_Employee_Vault"
    orchestrator = Orchestrator(vault_path)
    
    logger.info("Starting Decoupled Architecture Orchestrator (Ollama Reasoning & MCP Client)...")
    try:
        while True:
            # Poll both queues in sequence indefinitely
            orchestrator.process_needs_action()
            orchestrator.process_approved()
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down Orchestrator.")
