import os

def render(context, config, paths):
    """
    Renders the 'Library' pillar and its sub-contexts.
    """
    output = []
    BIN_DIR = paths['BIN_DIR']
    LIBRARY_ROOT = paths['LIBRARY_ROOT']
    
    # Helpers
    def _get_icon(path):
        """Reads .icon file or returns default."""
        icon_path = os.path.join(path, ".icon")
        if os.path.exists(icon_path):
            try:
                with open(icon_path, 'r') as f:
                    return f.read().strip()
            except: pass
        return "📁" # Default folder icon

    # 1. Main Library View
    if context == "library":
        # A. Special System Items (Genesis)
        genesis_path = os.path.join(str(LIBRARY_ROOT), "actions/factory/project-genesis.sh")
        if os.path.exists(genesis_path):
            output.append({"label": "✨ START NEW PROJECT (GENESIS)", "type": "ACTION", "path": genesis_path})
        
        # B. Dynamic Folders (Scanned from global and local actions)
        action_roots = [os.path.join(str(LIBRARY_ROOT), "actions")]
        if paths.get('LOCAL_ACTIONS'):
            action_roots.append(paths['LOCAL_ACTIONS'])
            
        categories = set()
        for root in action_roots:
            if os.path.exists(root):
                for d in os.listdir(root):
                    if os.path.isdir(os.path.join(root, d)) and d != "factory":
                        categories.add(d)

        for d in sorted(list(categories)):
            # Icon check (Local takes precedence)
            icon = "📁"
            local_icon_path = os.path.join(paths['LOCAL_ACTIONS'], d) if paths.get('LOCAL_ACTIONS') else None
            global_icon_path = os.path.join(str(LIBRARY_ROOT), "actions", d)
            
            if local_icon_path and os.path.exists(local_icon_path):
                icon = _get_icon(local_icon_path)
            elif os.path.exists(global_icon_path):
                icon = _get_icon(global_icon_path)

            label_name = d.replace("-", " ").title()
            output.append({
                "label": f"{icon} {label_name}", 
                "type": "FOLDER", 
                "payload": f"library:actions:{d}"
            })

        # C. Blueprints
        output.append({"label": "📄 Blueprints", "type": "FOLDER", "payload": "library:blueprints"})
        return output

    # 2. Dynamic Action Scanning (Generic Handler)
    elif context.startswith("library:actions:"):
        folder_name = context.replace("library:actions:", "")
        
        # Scan both global and local directories for this category
        dirs_to_scan = []
        if paths.get('LOCAL_ACTIONS'):
            dirs_to_scan.append(os.path.join(paths['LOCAL_ACTIONS'], folder_name))
        dirs_to_scan.append(os.path.join(str(LIBRARY_ROOT), "actions", folder_name))
        
        seen_files = set()
        for action_dir in dirs_to_scan:
            if os.path.exists(action_dir):
                for f in sorted(os.listdir(action_dir)):
                    if f in seen_files: continue
                    full_path = os.path.join(action_dir, f)
                    
                    # Filter for executables (scripts) and ignore hidden files/folders
                    if os.path.isfile(full_path) and os.access(full_path, os.X_OK) and not f.startswith("."):
                        name = f.replace(".sh", "").replace("-", " ").title()
                        
                        # Icons (Try script specific icon, or default based on folder metadata?)
                        icon = "⚡"
                        if "stop" in f or "down" in f: icon = "🛑"
                        elif "start" in f or "up" in f: icon = "🚀"
                        
                        output.append({
                            "label": f"{icon} {name}", 
                            "type": "ACTION", 
                            "path": full_path
                        })
                        seen_files.add(f)
        return output

    # 3. Blueprints
    elif context == "library:blueprints":
        blueprints_dir = os.path.join(str(LIBRARY_ROOT), "blueprints")
        if os.path.exists(blueprints_dir):
            for f in sorted(os.listdir(blueprints_dir)):
                 output.append({"label": f"📄 {f}", "type": "DOC", "path": os.path.join(blueprints_dir, f)})
        return output

    return None
