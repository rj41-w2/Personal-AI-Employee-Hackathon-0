import os
import time
import logging
import re
from pathlib import Path
from datetime import datetime

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False

from base_watcher import BaseWatcher

logger = logging.getLogger("GmailWatcher")

class GmailWatcher(BaseWatcher):
    def __init__(self, vault_path: str, credentials_path: str = "credentials.json"):
        super().__init__(vault_path, check_interval=60)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.credentials_path = os.path.join(root_dir, credentials_path)
        self.token_path = os.path.join(root_dir, "token.json")
        self.service = None
        self.processed_ids = set()
        
        if GMAIL_AVAILABLE:
            self._authenticate()
        else:
            logger.warning("Gmail API libraries missing. GmailWatcher will be disabled.")
            
    def _authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, ['https://www.googleapis.com/auth/gmail.modify'])
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}. Removing stale token.json to force re-authentication.")
                    if os.path.exists(self.token_path):
                        os.remove(self.token_path)
                    creds = None
                    
            if not creds:
                if os.path.exists(self.credentials_path):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_path, ['https://www.googleapis.com/auth/gmail.modify'])
                        creds = flow.run_local_server(port=0)
                    except Exception as e:
                        logger.warning(f"Could not initialize OAuth flow. Ensure {self.credentials_path} is valid.")
            
            if creds:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                    
        if creds:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Successfully authenticated with Gmail.")
        else:
            logger.warning(f"Could not authenticate. Missing {self.credentials_path}?")
            
    def check_for_updates(self) -> list:
        if not self.service:
            return []
            
        try:
            results = self.service.users().messages().list(
                userId='me', q='is:unread in:inbox', maxResults=10
            ).execute()
            messages = results.get('messages', [])
            return [m for m in messages if m['id'] not in self.processed_ids]
        except Exception as e:
            logger.error(f"Error checking Gmail: {e}")
            return []

    def extract_email_address(self, full_from):
        match = re.search(r'<(.+?)>', full_from)
        if match:
            return match.group(1)
        return full_from.strip()
            
    def create_action_file(self, message) -> Path:
        try:
            msg = self.service.users().messages().get(
                userId='me', id=message['id'], format='full'
            ).execute()
            
            headers = msg['payload'].get('headers', [])
            header_dict = {h['name']: h['value'] for h in headers}
            
            raw_from = header_dict.get('From', 'Unknown')
            sender_email = self.extract_email_address(raw_from)
            
            content = f"### Email ID: {message['id']}\n"
            content += f"Sender_Email: {sender_email}\n"
            content += f"Subject: {header_dict.get('Subject', 'No Subject')}\n"
            content += f"Snippet: {msg.get('snippet', '')}\n"
            
            email_dir = self.needs_action / "email"
            os.makedirs(email_dir, exist_ok=True)
            filepath = email_dir / f'GMAIL_{message["id"]}.md'
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"---\ntype: email\npriority: high\nstatus: pending\n---\n\n{content}\n")
            
            self.processed_ids.add(message['id'])
            logger.info(f"Downloaded email {message['id']} from {sender_email} to Needs_Action.")
            return filepath
        except Exception as e:
            logger.error(f"Failed to fetch message details: {e}")
            return None

if __name__ == "__main__":
    # Dynamically resolve vault path: src/watchers/ -> src/ -> project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    vault_path = os.path.join(project_root, "AI_Employee_Vault")
    watcher = GmailWatcher(vault_path)
    try:
        watcher.run()
    except KeyboardInterrupt:
        logger.info("Gracefully shut down GmailWatcher.")

