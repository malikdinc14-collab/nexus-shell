import os

def render(context, config, paths):
    """
    Renders the 'Ghosts' pillar and its sub-contexts.
    """
    # Lazy imports handled in specific blocks to avoid dependency issues
    output = []
    BIN_DIR = paths['BIN_DIR']
    
    # 1. Main Ghosts View
    if context in ["agents", "ghosts"]:
        output.append({"label": "📁 Identity Templates", "type": "FOLDER", "payload": "ghosts:templates"})
        output.append({"label": "📁 Agent Factory", "type": "FOLDER", "payload": "ghosts:factory"})
        return output

    # 3. Identity Templates (File Scan)
    elif context == "ghosts:templates":
        # Scan both local and global agents folders
        agent_roots = ["./library/agents", os.path.expanduser("~/.parallax/library/agents")]
        for root in agent_roots:
            if os.path.exists(root):
                source_lbl = 'Local' if './' in root else 'Global'
                output.append({"label": f"📁 Personas ({source_lbl})", "type": "FOLDER", "payload": f"agents:personas:{root}"})
                output.append({"label": f"📁 Operators ({source_lbl})", "type": "FOLDER", "payload": f"agents:humans:{root}"})
                output.append({"label": f"📁 Systems ({source_lbl})", "type": "FOLDER", "payload": f"agents:systems:{root}"})
        return output
        
    # 4. Agent Factory (Direct Actions)
    elif context == "ghosts:factory":
        output.append({"label": "🏗️  Initialize Workspace", "type": "ACTION", "path": f"{BIN_DIR}/../content/actions/system/init-workspace.sh"})
        output.append({"label": "🎭 Create New Persona", "type": "ACTION", "path": f"{BIN_DIR}/../content/actions/factory/create-persona.sh"})
        return output

    return None
