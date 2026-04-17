import os
import re
from datetime import datetime

def update_dashboard(base_vault_path, new_activity_message):
    dashboard_path = base_vault_path / "Dashboard.md"
    
    def count_md_files(subdir):
        d = base_vault_path / subdir
        if not d.exists(): return 0
        return len(list(d.rglob("*.md")))
        
    counts = {
        "Needs_Action": count_md_files("Needs_Action"),
        "Pending_Approval": count_md_files("Pending_Approval"),
        "Approved": count_md_files("Approved"),
        "Done": count_md_files("Done"),
        "Plans": count_md_files("Plans"),
        "Archive": count_md_files("Archive")
    }

    activities = []
    if dashboard_path.exists():
        content = dashboard_path.read_text(encoding='utf-8')
        in_activity = False
        for line in content.split('\n'):
            if line.startswith("## Recent Activity"):
                in_activity = True
            elif in_activity and line.startswith("- ["):
                activities.append(line.strip())
            elif in_activity and line.strip() == "" and len(activities) > 0:
                pass
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"- [{current_time}] {new_activity_message}"
    
    activities.insert(0, entry)
    activities = activities[:5] # keep only the latest 5
    
    new_dashboard = f"""# Personal AI Employee Dashboard

## Active Stats
- Needs_Action: {counts['Needs_Action']}
- Pending_Approval: {counts['Pending_Approval']}
- Approved: {counts['Approved']}
- Done: {counts['Done']}
- Plans: {counts['Plans']}
- Archive: {counts['Archive']}

## Recent Activity
"""
    new_dashboard += "\n".join(activities) + "\n"
    dashboard_path.write_text(new_dashboard, encoding='utf-8')
