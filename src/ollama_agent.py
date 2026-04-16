import time
import os
import shutil
import ollama
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OllamaAgent")

class OllamaAgent:
    def __init__(self, vault_path: str, model_name="llama3.2"):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.done = self.vault_path / "Done"
        self.dashboard = self.vault_path / "Dashboard.md"
        self.model = model_name
        
        self.done.mkdir(parents=True, exist_ok=True)
        self.needs_action.mkdir(parents=True, exist_ok=True)

    def process_pending_files(self):
        # find .md files in Needs_Action
        for file_path in self.needs_action.glob("*.md"):
            logger.info(f"Processing: {file_path.name}")
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            prompt = f"You are an autonomous AI employee. Process this task described in this text:\n\n{content}\n\nConcisely state your completed actions."
            
            try:
                # generate response
                response = ollama.chat(model=self.model, messages=[
                    {
                        'role': 'system',
                        'content': 'You are a helpful Personal AI Employee running locally. You complete tasks and write plans. Follow the company handbook rules: be concise.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ])
                result_text = response['message']['content']
                
                # Append result to the file
                with open(file_path, "a", encoding='utf-8') as f:
                    f.write("\n\n## Agent Execution Result\n")
                    f.write(result_text)
                
                # Move to done
                dest_path = self.done / file_path.name
                # Avoid collision
                if dest_path.exists():
                    dest_path = dest_path.with_name(f"{dest_path.stem}_{int(time.time())}{dest_path.suffix}")
                    
                shutil.move(str(file_path), str(dest_path))
                logger.info(f"Successfully processed and moved {file_path.name} to Done.")
                
                # Update dashboard
                self.update_dashboard(file_path.name)
                
            except Exception as e:
                logger.error(f"Error processing {file_path.name} with model {self.model}: {e}")
                logger.error("Please ensure the Ollama server is running and the model is pulled ('ollama run llama3.2').")

    def update_dashboard(self, task_name):
        if not self.dashboard.exists():
            return
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"- [{current_time}] Completed processing for {task_name}\n"
        
        content = self.dashboard.read_text(encoding='utf-8')
        # Insert entry under Recent Activity
        if "## Recent Activity\n" in content:
            content = content.replace("## Recent Activity\n", f"## Recent Activity\n{entry}")
            self.dashboard.write_text(content, encoding='utf-8')

if __name__ == "__main__":
    vault = Path(r"c:\Users\rehan\Projects\Personal-AI-Employee-Hackathon-0\AI_Employee_Vault")
    agent = OllamaAgent(vault_path=str(vault), model_name="llama3.2")
    
    logger.info("Starting Ollama Agent loop...")
    try:
        while True:
            agent.process_pending_files()
            time.sleep(10) # Checks every 10 seconds
    except KeyboardInterrupt:
        logger.info("Shutting down Ollama Agent.")
