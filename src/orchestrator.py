import os
import time
import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(PROJECT_ROOT / ".env")

from skills.email_drafter import draft_email
from skills.linkedin_drafter import draft_linkedin_post
from skills.dashboard_manager import update_dashboard
from skills.mcp_executor import process_approved_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrafficOrchestrator")

class Orchestrator:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.approved = self.vault_path / "Approved"
        self.archive = self.vault_path / "Archive"

        for root_dir in [self.needs_action, self.approved, self.archive]:
            root_dir.mkdir(parents=True, exist_ok=True)

    def process_needs_action(self):
        for file_path in self.needs_action.rglob("*.md"):
            logger.info(f"Routing new task: {file_path.name}")
            # Detect category: use 'in' to handle any prefix chains (e.g., PENDING_timestamp_GMAIL_...)
            category = "email" if "GMAIL_" in file_path.name else "linkedin"
            
            if category == "email":
                draft_email(file_path, self.vault_path)
                status_msg = f"Drafted email plan/reply for {file_path.name}"
            else:
                draft_linkedin_post(file_path, self.vault_path)
                status_msg = f"Drafted LinkedIn post for {file_path.name}"
                
            # Move the original file to Archive
            category_archive_dir = self.archive / category
            category_archive_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(category_archive_dir / file_path.name))
            
            # Post-task dashboard update
            try:
                update_dashboard(self.vault_path, status_msg)
            except Exception as e:
                logger.error(f"Dashboard update error: {e}")

    def process_approved(self):
        for file_path in self.approved.rglob("*.md"):
            logger.info(f"Routing approved execution: {file_path.name}.")
            try:
                status_msg = process_approved_file(file_path, self.vault_path)
                if status_msg:
                    update_dashboard(self.vault_path, status_msg)
            except Exception as e:
                logger.error(f"Execution routing error on {file_path.name}: {e}")

if __name__ == "__main__":
    # Dynamically resolve vault path relative to project root
    vault_path = str(PROJECT_ROOT / "AI_Employee_Vault")
    orchestrator = Orchestrator(vault_path)
    
    logger.info("Starting Ultra-Lightweight Decoupled Orchestrator...")
    try:
        while True:
            # Poll both queues indefinitely
            orchestrator.process_needs_action()
            orchestrator.process_approved()
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down Orchestrator.")

