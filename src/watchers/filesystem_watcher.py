from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import shutil
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DropFolderHandler")

class DropFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.inbox = self.vault_path / 'Inbox'
        
        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(parents=True, exist_ok=True)
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        source = Path(event.src_path)
        # Skip if the file is an intermediate download or not fully written.
        # Simple wait check, though typically better handled with specific locks.
        time.sleep(1)
        
        try:
            # We copy instead of move if we want to retain original or let it be deleted later
            dest = self.needs_action / f'FILE_{source.name}'
            if not dest.exists():
                shutil.copy2(source, dest)
                self.create_metadata(source, dest)
                logger.info(f"Copied {source.name} to Needs_Action and generated metadata.")
        except Exception as e:
            logger.error(f"Error copying {source.name}: {e}")

    def create_metadata(self, source: Path, dest: Path):
        meta_path = dest.with_suffix('.md')
        if not meta_path.exists():
            meta_path.write_text(f'''---
type: file_drop
original_name: {source.name}
size: {source.stat().st_size}
---

New file dropped for processing. Check the contents and write an appropriate response.
''')

if __name__ == "__main__":
    # Dynamically resolve vault path: src/watchers/ -> src/ -> project root
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    vault_path = Path(os.path.join(project_root, "AI_Employee_Vault"))
    
    event_handler = DropFolderHandler(str(vault_path))
    observer = Observer()
    
    inbox_dir = vault_path / "Inbox"
    if not inbox_dir.exists():
        inbox_dir.mkdir(parents=True, exist_ok=True)
        
    logger.info(f"Starting filesystem watcher on {inbox_dir}")
    observer.schedule(event_handler, str(inbox_dir), recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

