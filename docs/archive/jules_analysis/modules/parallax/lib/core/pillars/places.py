import os
import subprocess
import json

def render(context, config, paths):
    """
    Renders the 'Places' pillar and its sub-contexts.
    """
    output = []
    
    # 1. Main Places View
    if context == "places":
        output.append({"label": "📁 Registered Projects", "type": "FOLDER", "payload": "places:projects"})
        output.append({"label": "📁 Knowledge Base", "type": "FOLDER", "payload": "places:knowledge"})
        return output

    # 2. Registered Projects (Git-Aware)
    elif context == "places:projects":
        registry_path = os.path.expanduser("~/.parallax/registry.json")
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r") as f:
                    reg = json.load(f)
                for path, meta in reg.items():
                    name = os.path.basename(path)
                    
                    # Git Status Check
                    git_info = ""
                    if os.path.exists(os.path.join(path, ".git")):
                        try:
                            # Get branch
                            branch = subprocess.check_output(["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
                            # Check dirty
                            is_dirty = subprocess.call(["git", "-C", path, "diff", "--quiet"], stderr=subprocess.DEVNULL) != 0
                            dirty_mark = "*" if is_dirty else ""
                            git_info = f" [{branch}{dirty_mark}]"
                        except:
                            git_info = " [git error]"

                    output.append({
                        "label": f"🏙️  {name.upper()}{git_info}",
                        "type": "PLACE",
                        "place": path,
                        "description": f"Managed Project: {path}"
                    })
                    # Add sub-actions for the place
                    output.append({
                        "label": f"   ✨ Focus & Sync {name}",
                        "type": "ACTION",
                        "path": f"cd {path} && ACTION=sync {paths['LIBRARY_ROOT']}/actions/factory/project-genesis.sh"
                    })
                    if git_info:
                        output.append({
                            "label": f"   🐙 Version Control {name}",
                            "type": "FOLDER",
                            "payload": f"places:git:{path}"
                        })

            except Exception as e:
                output.append({"label": f"Error: {e}", "type": "SEPARATOR"})
        return output

    # 3. Git Operations Sub-Menu
    elif context.startswith("places:git:"):
        path = context.replace("places:git:", "")
        output.append({"label": f"--- REPO: {os.path.basename(path)} ---", "type": "SEPARATOR"})
        output.append({"label": "📊 Status", "type": "ACTION", "path": f"cd {path} && git status", "is_prompt_terminal": True})
        output.append({"label": "⬇️  Pull", "type": "ACTION", "path": f"cd {path} && git pull", "is_prompt_terminal": True})
        output.append({"label": "⬆️  Push", "type": "ACTION", "path": f"cd {path} && git push", "is_prompt_terminal": True})
        output.append({"label": "📝 Commit All", "type": "ACTION", "path": f"cd {path} && git add . && git commit -v", "is_prompt_terminal": True})
        return output

    # 4. Knowledge Base
    elif context == "places:knowledge":
        output.append({"label": "📁 Project Documents", "type": "CONTEXT", "payload": "docs"})
        return output

    return None
