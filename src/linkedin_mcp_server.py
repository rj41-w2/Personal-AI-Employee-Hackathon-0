import os
import requests
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Linkedin_MCP")

# Load environment variables (from project root)
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
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
        raise ValueError("Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_URN in .env file.")
        
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
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        post_id = response.headers.get("x-restli-id", "Unknown_ID")
        logger.info(f"Successfully posted to LinkedIn! Post ID: {post_id}")
        return f"Successfully posted to LinkedIn. ID: {post_id}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to post to LinkedIn: {e}\nResponse: {e.response.text if hasattr(e, 'response') and e.response else ''}")
        return f"Error executing LinkedIn Post: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting up standalone LinkedIn MCP server on stdio...")
    mcp.run(transport='stdio')
