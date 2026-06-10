import os
import time
import logging
from gemini_client import call_gemini

logger = logging.getLogger("EmailDrafter")

def draft_email(file_path, base_vault_path, model=None):
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "email_rules.md")
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        system_rules = f.read()
        
    try:
        text_content = call_gemini(system_rules, f"Task Header and Content:\n{content}", model)
        
        timestamp = int(time.time())
        parts = text_content.split('## Action:')
        plan_text = parts[0].strip()
        
        plan_dir = base_vault_path / "Plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_filename = f"PLAN_{timestamp}_{file_path.name}"
        (plan_dir / plan_filename).write_text(f"{plan_text}\n\n---\n**Trigger**: {file_path.name}", encoding='utf-8')
        
        if len(parts) > 1:
            action_text = f"## Action: {parts[1].strip()}"
            new_filename = f"PENDING_{timestamp}_{file_path.name}"
            pending_dir = base_vault_path / "Pending_Approval" / "email"
            pending_dir.mkdir(parents=True, exist_ok=True)
            pending_file = pending_dir / new_filename
            
            full_content = f"{action_text}\n\n---\n**Original Trigger Task**: {file_path.name}\n"
            pending_file.write_text(full_content, encoding='utf-8')
            
        logger.info(f"Successfully drafted email for {file_path.name}")
    except Exception as e:
        logger.error(f"Error drafting email for {file_path.name}: {e}")
