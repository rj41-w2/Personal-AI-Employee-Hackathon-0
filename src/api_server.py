"""
AI Employee Headless Dashboard API Server
FastAPI backend for monitoring vault activities.
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json

# Load environment
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("APIServer")

VAULT_PATH = PROJECT_ROOT / "AI_Employee_Vault"


def count_files_in_dir(directory: Path, recursive: bool = True) -> dict:
    """Count markdown files in a directory, broken down by subfolders."""
    counts = {"total": 0, "categories": {}}

    if not directory.exists():
        return counts

    pattern = "**/*.md" if recursive else "*.md"

    for item in directory.iterdir():
        if item.is_dir():
            sub_counts = count_files_in_dir(item, recursive=False)
            counts["categories"][item.name] = sub_counts["total"]
            counts["total"] += sub_counts["total"]
        elif item.suffix == ".md":
            counts["total"] += 1

    return counts


def get_vault_stats() -> dict:
    """Get statistics for all vault directories."""
    stats = {
        "timestamp": datetime.now().isoformat(),
        "vault_path": str(VAULT_PATH),
        "directories": {}
    }

    dir_names = ["Needs_Action", "Pending_Approval", "Approved", "Done", "Rejected", "Archive", "Plans"]

    for dir_name in dir_names:
        dir_path = VAULT_PATH / dir_name
        dir_stats = {
            "total": 0,
            "categories": {}
        }

        if dir_path.exists():
            for category_dir in dir_path.iterdir():
                if category_dir.is_dir():
                    file_count = len(list(category_dir.rglob("*.md")))
                    dir_stats["categories"][category_dir.name] = file_count
                    dir_stats["total"] += file_count

        stats["directories"][dir_name] = dir_stats

    return stats


def get_recent_activity(hours: int = 24, limit: int = 20) -> list:
    """Get recent activity from dashboard file."""
    dashboard_path = VAULT_PATH / "Dashboard.md"

    if not dashboard_path.exists():
        return []

    try:
        content = dashboard_path.read_text(encoding='utf-8')
        activities = []

        in_activity = False
        for line in content.split('\n'):
            if line.startswith("## Recent Activity"):
                in_activity = True
            elif in_activity and line.startswith("- ["):
                # Extract timestamp and message
                line = line.strip()
                if line.startswith("- ["):
                    line = line[2:]  # Remove leading "-"
                    if "]:" in line:
                        timestamp_str, message = line.split("]:", 1)
                        activities.append({
                            "timestamp": timestamp_str.strip(),
                            "message": message.strip()
                        })

        # Filter by hours if specified
        if hours > 0:
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered = []
            for act in activities:
                try:
                    act_time = datetime.strptime(act["timestamp"], "%Y-%m-%d %H:%M:%S")
                    if act_time >= cutoff:
                        filtered.append(act)
                except ValueError:
                    filtered.append(act)
            activities = filtered

        return activities[:limit]

    except Exception as e:
        logger.error(f"Error reading dashboard: {e}")
        return []


def get_loop_status() -> dict:
    """Get Ralph Wiggum Loop status."""
    memory_file = VAULT_PATH / "loop_memory.json"

    if not memory_file.exists():
        return {
            "enabled": True,
            "total_processed": 0,
            "total_created": 0,
            "recent_actions": []
        }

    try:
        import json
        with open(memory_file, 'r') as f:
            memory = json.load(f)

        return {
            "enabled": True,
            "total_processed": len(memory.get("processed_files", [])),
            "total_created": len(memory.get("created_actions", [])),
            "recent_actions": memory.get("created_actions", [])[-5:]
        }
    except Exception as e:
        logger.error(f"Error reading loop memory: {e}")
        return {"enabled": True, "error": str(e)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    logger.info("AI Employee Dashboard API starting up...")
    logger.info(f"Monitoring vault at: {VAULT_PATH}")
    yield
    logger.info("AI Employee Dashboard API shutting down...")


app = FastAPI(
    title="AI Employee Dashboard API",
    description="Headless API for monitoring AI Employee vault activities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "AI Employee Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "vault_path": str(VAULT_PATH),
        "endpoints": {
            "/api/stats": "Vault directory statistics",
            "/api/recent": "Recent activity (last 24h)",
            "/api/loop": "Ralph Wiggum Loop status",
            "/api/dashboard": "Full dashboard data"
        }
    }


@app.get("/api/stats")
async def get_stats():
    """Get vault statistics - file counts by directory and category."""
    stats = get_vault_stats()
    return {
        "success": True,
        "data": stats
    }


@app.get("/api/recent")
async def get_recent(hours: int = 24, limit: int = 20):
    """Get recent activity from dashboard."""
    activities = get_recent_activity(hours=hours, limit=limit)
    return {
        "success": True,
        "count": len(activities),
        "data": activities
    }


@app.get("/api/loop")
async def get_loop():
    """Get Ralph Wiggum Loop status."""
    status = get_loop_status()
    return {
        "success": True,
        "data": status
    }


@app.get("/api/dashboard")
async def get_dashboard():
    """Get full dashboard data (combined stats + recent + loop status)."""
    stats = get_vault_stats()
    recent = get_recent_activity(hours=24, limit=10)
    loop = get_loop_status()

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "stats": stats,
        "recent_activity": recent,
        "loop_status": loop
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    odoo_running = False
    try:
        import requests
        odoo_url = os.getenv("ODOO_URL", "http://localhost:8069")
        resp = requests.get(f"{odoo_url}/web/database/manager", timeout=5)
        odoo_running = resp.status_code == 200
    except Exception:
        pass

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "vault_exists": VAULT_PATH.exists(),
        "odoo_running": odoo_running
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")

    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )