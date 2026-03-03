import os
from pathlib import Path

def render(context, config, paths):
    """
    Renders the 'Projects' pillar - lists registered workspaces.
    """
    output = []
    BIN_DIR = paths['BIN_DIR']
    
    # 1. Main Projects View
    if context == "projects":
        # A. Create New Workspace
        output.append({"label": "✨ Create New Workspace", "type": "ACTION", "path": f"{BIN_DIR}/../content/actions/system/init-workspace.sh"})
        output.append({"label": "🛠️  Manage Workspaces", "type": "ACTION", "path": f"{BIN_DIR}/../content/actions/system/manage-workspaces.sh"})
        
        # A.5 Auto-Discover Current Directory (Nested Workspaces)
        cwd = os.getcwd()
        try:
             # Scan immediate subdirectories
             for d in os.listdir(cwd):
                 full_path = os.path.join(cwd, d)
                 if os.path.isdir(full_path):
                     # Check for .parallax inside
                     if os.path.isdir(os.path.join(full_path, ".parallax")):
                         output.append({
                            "label": f"📂 {d} (Local)",
                            "type": "PLACE",
                            "payload": full_path,
                            "description": f"Found in {cwd}"
                         })
        except: pass

        # B. Scan for registered projects
        registry_path = os.path.expanduser("~/.parallax/registry.json")
        if os.path.exists(registry_path):
            try:
                import json
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
                
                for project_path, info in registry.items():
                    name = os.path.basename(project_path)
                    output.append({
                        "label": f"📁 {name}",
                        "type": "PLACE",
                        "payload": project_path,
                        "description": f"Workspace at {project_path}"
                    })
            except Exception as e:
                output.append({"label": f"⚠️ Registry Error: {e}", "type": "DISABLED"})
        
        # C. Scan for local .parallax folders in common locations
        common_roots = [os.path.expanduser("~/Projects"), os.path.expanduser("~/Developer")]
        for root in common_roots:
            if os.path.exists(root):
                try:
                    for d in os.listdir(root):
                        project_dir = os.path.join(root, d, ".parallax")
                        if os.path.isdir(project_dir):
                            # Check if already in registry
                            full_path = os.path.join(root, d)
                            if full_path not in registry if 'registry' in dir() else True:
                                output.append({
                                    "label": f"📂 {d} (Local)",
                                    "type": "PLACE",
                                    "payload": full_path
                                })
                except: pass
        
        if len(output) == 2:  # Only separator and create button
            output.append({"label": "💡 No projects found. Create one above!", "type": "DISABLED"})
        
        return output

    return None
