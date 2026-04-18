import os
import time
import requests
import logging

logger = logging.getLogger("LinkedinDrafter")

# Ollama config from environment (set in .env, loaded by orchestrator)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

def draft_linkedin_post(file_path, base_vault_path, model=None):
    model = model or OLLAMA_MODEL
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    rules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "linkedin_rules.md")
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        system_rules = f.read()
        
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": f"Task Content:\n{content}"}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        response.raise_for_status()
        text_content = response.json().get("message", {}).get("content", "")
        
        timestamp = int(time.time())
        parts = text_content.split('## Action:')
        plan_text = parts[0].strip()
        
        plan_dir = base_vault_path / "Plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_filename = f"PLAN_{timestamp}_{file_path.name}"
        (plan_dir / plan_filename).write_text(f"{plan_text}\n\n---\n**Trigger**: {file_path.name}", encoding='utf-8')
        
        if len(parts) > 1:
            raw_action = parts[1].strip()
            # If the LLM didn't include a "Content:" label, inject one
            if not raw_action.startswith("Content:") and "\nContent:" not in raw_action:
                # Find where "post_to_linkedin" header ends and content begins
                action_lines = raw_action.split('\n', 1)
                header = action_lines[0].strip()  # e.g., " post_to_linkedin"
                body_text = action_lines[1].strip() if len(action_lines) > 1 else ""
                action_text = f"## Action: {header}\nContent:\n{body_text}"
            else:
                action_text = f"## Action: {raw_action}"
            
            new_filename = f"PENDING_{timestamp}_{file_path.name}"
            pending_dir = base_vault_path / "Pending_Approval" / "linkedin"
            pending_dir.mkdir(parents=True, exist_ok=True)
            pending_file = pending_dir / new_filename
            
            full_content = f"{action_text}\n\n---\n**Original Trigger Task**: {file_path.name}\n"
            pending_file.write_text(full_content, encoding='utf-8')
            
        logger.info(f"Successfully drafted LinkedIn post for {file_path.name}")
    except Exception as e:
        logger.error(f"Error drafting LinkedIn post for {file_path.name}: {e}")

