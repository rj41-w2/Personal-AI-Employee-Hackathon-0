import os
import base64
import logging
from email.message import EmailMessage
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MCP_Server")

mcp = FastMCP("Personal_AI_Employee_Skills")

# Config path to vault directory to access the tokens easily
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CREDENTIALS_PATH = os.path.join(root_dir, "credentials.json")
TOKEN_PATH = os.path.join(root_dir, "token.json")

def get_gmail_service():
    creds = None
    
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, ['https://www.googleapis.com/auth/gmail.modify'])
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Token refresh failed: {e}. Removing stale token.json.")
                if os.path.exists(TOKEN_PATH):
                    os.remove(TOKEN_PATH)
                raise ValueError("Stale token removed. Please run src/gmail_watcher.py to re-authenticate first.")
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"Missing {CREDENTIALS_PATH}. Cannot authenticate Gmail.")
            # Note: Server cannot initiate an interactive flow inside an MCP pipe.
            # Local token.json must exist beforehand for absolute purity.
            raise ValueError("Token is invalid and requires manual browser re-authentication first.")
            
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

@mcp.tool()
def send_email(to_email: str, subject: str, body: str) -> str:
    """
    Physically sends an email to the specified address using the authenticated Gmail API.
    Used by the Orchestrator internally. Only fires successfully if token.json is authenticated.
    """
    logger.info(f"Received MCP command to send email to {to_email}")
    try:
        service = get_gmail_service()
        
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['From'] = 'me'
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        msg_id = send_message.get('id')
        logger.info(f"Message Id: {msg_id} sent successfully.")
        return f"Successfully sent email to {to_email}. Message ID: {msg_id}"
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Error sending email: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting up decoupled FastMCP server on stdio...")
    mcp.run(transport='stdio')
