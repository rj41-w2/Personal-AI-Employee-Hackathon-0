import os
import sys
import requests
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Linkedin_MCP")

# Load environment variables (from project root)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(root_dir, ".env")
load_dotenv(env_path)

mcp = FastMCP("Personal_AI_Employee_Linkedin")

@mcp.tool()
def post_to_linkedin(content: str) -> str:
    """
    Physically publishes a text post to LinkedIn using the local .env credentials.
    Only call explicitly approved payloads.
    """
    logger.info(f"Received request to post to LinkedIn. Length: {len(content)} chars.")
    
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")
    
    if not access_token or not person_urn:
        msg = "ERROR: Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN in .env file."
        print(msg, file=sys.stderr)
        return msg
        
    # Log what we're sending for debugging
    print(f"LINKEDIN DEBUG: Using URN={person_urn}, Token={access_token[:10]}...", file=sys.stderr)
        
    url = "https://api.linkedin.com/v2/ugcPosts"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }
    
    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    # LOUD stderr logging so you always see the raw API response in terminal
    print(f"LINKEDIN API RESPONSE: {response.status_code} - {response.text}", file=sys.stderr)
    
    # Strict validation: LinkedIn returns 201 on successful post creation
    if response.status_code == 201:
        post_id = response.headers.get("x-restli-id", "Unknown_ID")
        logger.info(f"Successfully posted to LinkedIn! Post ID: {post_id}")
        return f"SUCCESS: Posted to LinkedIn. ID: {post_id}"
    else:
        error_msg = f"ERROR: LinkedIn API Failed (HTTP {response.status_code}): {response.text}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    logger.info("Starting up standalone LinkedIn MCP server on stdio...")
    mcp.run(transport='stdio')

