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
from skills.accounting_drafter import draft_accounting_task
from skills.dashboard_manager import update_dashboard
from skills.mcp_executor import process_approved_file
from skills.ralph_wiggum_loop import run_autonomous_reasoning, get_loop_status

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

            # Read file content to check for auto-trigger
            content = ""
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                pass

            is_auto_triggered = "[AUTO_TRIGGERED]" in content or "type: autonomous_followup" in content

            # Detect category
            if "GMAIL_" in file_path.name:
                category = "email"
            elif "ACCOUNTING_" in file_path.name:
                category = "accounting"
            elif "ODOO_" in file_path.name:
                category = "accounting"
            else:
                category = "linkedin"

            if category == "email":
                draft_email(file_path, self.vault_path)
                status_msg = f"Drafted email plan/reply for {file_path.name}"
            elif category == "accounting":
                draft_accounting_task(file_path, self.vault_path)
                status_msg = f"Drafted accounting task for {file_path.name}"
            else:
                draft_linkedin_post(file_path, self.vault_path)
                status_msg = f"Drafted LinkedIn post for {file_path.name}"

            # Log auto-trigger status but still require human approval
            if is_auto_triggered:
                logger.info(f"AUTO-TRIGGERED: {file_path.name} drafted - requires CEO approval before execution")

            # Move the original file to Archive
            category_archive_dir = self.archive / category
            category_archive_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(file_path), str(category_archive_dir / file_path.name))
            except FileNotFoundError:
                pass  # File might have been moved already

            # Post-task dashboard update
            try:
                update_dashboard(self.vault_path, status_msg)
            except Exception as e:
                logger.error(f"Dashboard update error: {e}")

    def process_approved(self):
        for file_path in self.approved.rglob("*.md"):
            logger.info(f"Routing approved execution: {file_path.name}.")

            # Determine category from filename
            if "GMAIL_" in file_path.name:
                category = "email"
            elif "ACCOUNTING_" in file_path.name or "ODOO_" in file_path.name:
                category = "accounting"
            else:
                category = "linkedin"

            try:
                success, status_msg = process_approved_file(file_path, self.vault_path)
            except Exception as e:
                success = False
                status_msg = f"EXCEPTION during execution of {file_path.name}: {e}"
                logger.error(status_msg)
            
            if success:
                # SUCCESS: Move to Done/{category}/
                dest_dir = self.vault_path / "Done" / category
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest_dir / file_path.name))
                logger.info(f"SUCCESS: Moved {file_path.name} -> Done/{category}/")
            else:
                # FAILURE: Move to Rejected/{category}/
                dest_dir = self.vault_path / "Rejected" / category
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest_dir / file_path.name))
                logger.warning(f"REJECTED: Moved {file_path.name} -> Rejected/{category}/")
            
            # Always log to dashboard regardless of outcome
            try:
                update_dashboard(self.vault_path, status_msg)
            except Exception:
                pass

if __name__ == "__main__":
    # Dynamically resolve vault path relative to project root
    vault_path = str(PROJECT_ROOT / "AI_Employee_Vault")
    orchestrator = Orchestrator(vault_path)

    logger.info("Starting Ultra-Lightweight Decoupled Orchestrator with Ralph Wiggum Loop...")
    logger.info("Human-in-the-Loop ENFORCED: All tasks require CEO approval before execution.")

    loop_counter = 0
    Ralph_Wiggum = 60  # Run Ralph Wiggum Loop every 60 seconds

    try:
        while True:
            # Poll both queues indefinitely
            orchestrator.process_needs_action()
            orchestrator.process_approved()

            # Ralph Wiggum Loop - Autonomous Reasoning
            loop_counter += 10
            if loop_counter >= Ralph_Wiggum:
                logger.info("Running Ralph Wiggum Loop - Autonomous Task Analysis...")
                try:
                    actions_created = run_autonomous_reasoning()
                    if actions_created > 0:
                        logger.info(f"Ralph Wiggum Loop created {actions_created} new autonomous action(s).")
                        # Update dashboard with loop status
                        status = get_loop_status()
                        update_dashboard(vault_path, f"Ralph Wiggum: Created {actions_created} follow-up task(s)")
                except Exception as e:
                    logger.error(f"Ralph Wiggum Loop error: {e}")
                loop_counter = 0

            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down Orchestrator.")

