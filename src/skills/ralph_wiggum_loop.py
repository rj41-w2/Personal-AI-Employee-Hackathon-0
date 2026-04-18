import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger("RalphWiggumLoop")

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

MEMORY_FILE = PROJECT_ROOT / "AI_Employee_Vault" / "loop_memory.json"
VAULT_PATH = PROJECT_ROOT / "AI_Employee_Vault"


def load_memory():
    """Load the loop memory JSON file."""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"processed_files": [], "created_actions": []}
    return {"processed_files": [], "created_actions": []}


def save_memory(memory):
    """Save the loop memory JSON file."""
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)


def get_recent_done_files(minutes=10):
    """
    Scan Done/ directories for files modified in the last N minutes.
    Returns list of dicts with file_path, category, and content.
    """
    done_dir = VAULT_PATH / "Done"
    if not done_dir.exists():
        return []

    cutoff_time = time.time() - (minutes * 60)
    recent_files = []

    for category_dir in done_dir.iterdir():
        if category_dir.is_dir():
            category = category_dir.name
            for file_path in category_dir.rglob("*.md"):
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime >= cutoff_time:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        recent_files.append({
                            "path": str(file_path),
                            "name": file_path.name,
                            "category": category,
                            "modified": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                            "content": content[:1500]  # Limit content to avoid token overflow
                        })
                except Exception as e:
                    logger.warning(f"Error reading {file_path}: {e}")

    return recent_files


def generate_followup_prompt(recent_tasks):
    """
    Generate the LLM prompt for autonomous reasoning.
    """
    if not recent_tasks:
        return None

    tasks_summary = []
    for task in recent_tasks:
        tasks_summary.append(f"""
=== {task['category'].upper()} TASK ===
File: {task['name']}
Modified: {task['modified']}
Content Preview: {task['content'][:500]}...
""")

    system_prompt = """You are an expert Autonomous Task Analyzer. Your job is to observe completed tasks and determine if logical follow-up actions are needed.

TASK COMPLETION ANALYSIS RULES:
1. Invoice Created → Consider: Send email confirmation to client, or create follow-up invoice
2. LinkedIn Post Published → Consider: Log the post in records, create engagement summary
3. Email Sent → Consider: Log in sent folder, create follow-up reminder
4. Report Generated → Consider: Email report to stakeholders, archive report

CRITICAL DECISION LOGIC:
- IF a task creates something (invoice, post, report) → ALWAYS suggest a notification/follow-up
- IF a task receives something (email, data) → Consider acknowledgment or response
- IF task is already a follow-up → Do NOT create another follow-up (avoid loops)

OUTPUT FORMAT - Answer ONLY with this exact format:

REASONING: <your brief analysis of what was completed and what makes sense next>

DECISION: YES or NO

IF YES:
ACTION_TYPE: email OR linkedin_post OR accounting OR log
TARGET: <who/what this action is for>
CONTENT: <exact content for the Needs_Action file - be specific>

Example YES response:
REASONING: An invoice was just created for Tech Corp. The client should be notified.
DECISION: YES
ACTION_TYPE: email
TARGET: Tech Corp
CONTENT: Please send a professional email to Tech Corp at tech@corp.com informing them that invoice INV-001 for $500 has been generated and is due in 30 days.

Example NO response:
REASONING: This was already a follow-up email. No further action needed.
DECISION: NO"""

    user_prompt = f"""Analyze these recently completed tasks and determine if follow-up actions are needed:

{''.join(tasks_summary)}

Based on this analysis, should I create a follow-up task? Respond with the exact format specified."""

    return {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False
    }


def parse_llm_response(response_text):
    """
    Parse the LLM response to extract decision and action details.
    """
    lines = response_text.strip().split('\n')

    reasoning = ""
    decision = "NO"
    action_type = ""
    target = ""
    content = ""

    current_field = None
    content_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith("REASONING:"):
            reasoning = line.replace("REASONING:", "").strip()
            current_field = None
        elif line.startswith("DECISION:"):
            decision = line.replace("DECISION:", "").strip().upper()
            current_field = None
        elif line.startswith("ACTION_TYPE:") and decision == "YES":
            action_type = line.replace("ACTION_TYPE:", "").strip()
            current_field = None
        elif line.startswith("TARGET:") and decision == "YES":
            target = line.replace("TARGET:", "").strip()
            current_field = None
        elif line.startswith("CONTENT:") and decision == "YES":
            content = line.replace("CONTENT:", "").strip()
            current_field = "content"
        elif current_field == "content" and line:
            content += " " + line

    return {
        "reasoning": reasoning,
        "decision": decision,
        "action_type": action_type,
        "target": target,
        "content": content
    }


def create_needs_action_file(action_type, target, content, auto_triggered=True):
    """
    Create a new .md file in Needs_Action/ directory.
    """
    timestamp = int(time.time())

    # Determine prefix based on action type
    if action_type == "email":
        prefix = "GMAIL_"
    elif action_type == "linkedin_post":
        prefix = "LINKEDIN_"
    elif action_type == "accounting":
        prefix = "ACCOUNTING_"
    else:
        prefix = "AUTO_"

    filename = f"{prefix}AUTO_{timestamp}.md"
    needs_action_dir = VAULT_PATH / "Needs_Action"

    # Create category subdirectory if needed
    if action_type == "email":
        needs_action_dir = needs_action_dir / "email"
    elif action_type == "linkedin_post":
        needs_action_dir = needs_action_dir / "linkedin"
    elif action_type == "accounting":
        needs_action_dir = needs_action_dir / "accounting"

    needs_action_dir.mkdir(parents=True, exist_ok=True)

    file_path = needs_action_dir / filename

    auto_tag = "[AUTO_TRIGGERED] " if auto_triggered else ""

    file_content = f"""---
type: autonomous_followup
triggered_by: ralph_wiggum_loop
timestamp: {datetime.now().isoformat()}
target: {target}
---

{auto_tag}{content}

---
**Auto-generated by Ralph Wiggum Loop**
This task was autonomously created based on completed task analysis.
"""

    file_path.write_text(file_content, encoding='utf-8')
    logger.info(f"Created autonomous follow-up: {file_path.name}")

    return str(file_path)


def run_autonomous_reasoning():
    """
    Main entry point - run one cycle of observe, orient, decide, act.
    """
    logger.info("Ralph Wiggum Loop: Starting autonomous reasoning cycle...")

    # Load memory
    memory = load_memory()
    processed = set(memory.get("processed_files", []))
    created = memory.get("created_actions", [])

    # OBSERVE: Get recent completed tasks
    recent_files = get_recent_done_files(minutes=10)

    if not recent_files:
        logger.info("Ralph Wiggum Loop: No recently completed tasks found.")
        return 0

    # Filter out already processed files
    new_tasks = [f for f in recent_files if f["path"] not in processed]

    if not new_tasks:
        logger.info("Ralph Wiggum Loop: All recent tasks already processed.")
        return 0

    logger.info(f"Ralph Wiggum Loop: Found {len(new_tasks)} new completed tasks to analyze.")

    # ORIENT & DECIDE: Generate LLM prompt and get decision
    prompt_data = generate_followup_prompt(new_tasks)

    try:
        import requests
        response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=prompt_data, timeout=60)
        response.raise_for_status()
        llm_response = response.json().get("message", {}).get("content", "")
        logger.info(f"Ralph Wiggum Loop: LLM Response:\n{llm_response}")
    except Exception as e:
        logger.error(f"Ralph Wiggum Loop: LLM call failed: {e}")
        return 0

    # Parse LLM decision
    decision = parse_llm_response(llm_response)

    if decision["decision"] != "YES":
        logger.info("Ralph Wiggum Loop: LLM decided no follow-up action needed.")
        # Mark these tasks as processed
        for task in new_tasks:
            processed.add(task["path"])
        memory["processed_files"] = list(processed)
        save_memory(memory)
        return 0

    # ACT: Create the follow-up task
    if decision["action_type"] and decision["content"]:
        created_path = create_needs_action_file(
            action_type=decision["action_type"],
            target=decision["target"],
            content=decision["content"],
            auto_triggered=True
        )

        # Update memory
        for task in new_tasks:
            processed.add(task["path"])

        created.append({
            "timestamp": datetime.now().isoformat(),
            "source_files": [t["path"] for t in new_tasks],
            "created_file": created_path,
            "reasoning": decision["reasoning"]
        })

        memory["processed_files"] = list(processed)
        memory["created_actions"] = created[-50:]  # Keep last 50
        save_memory(memory)

        logger.info(f"Ralph Wiggum Loop: Created follow-up action based on reasoning: {decision['reasoning']}")
        return 1
    else:
        logger.warning("Ralph Wiggum Loop: LLM said YES but missing action details.")
        return 0


def get_loop_status():
    """Return current loop memory status for dashboard."""
    memory = load_memory()
    return {
        "total_processed": len(memory.get("processed_files", [])),
        "total_created": len(memory.get("created_actions", [])),
        "recent_actions": memory.get("created_actions", [])[-5:]
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    result = run_autonomous_reasoning()
    print(f"\nRalph Wiggum Loop completed. Actions created: {result}")
