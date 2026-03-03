import os
import yaml
from pathlib import Path

def render(context, config, paths):
    """
    Scans for custom YAML lists in:
    1. Project: .nexus/lists/*.yaml
    2. Global: ~/.config/nexus-shell/lists/*.yaml
    """
    if context != "lists":
        return None
        
    items = []
    
    cwd = Path(os.getcwd())
    project_lists_dir = cwd / ".nexus" / "lists"
    global_lists_dir = Path(os.path.expanduser("~/.config/nexus-shell/lists"))
    
    # Render Global Lists
    if global_lists_dir.exists():
        for lst in global_lists_dir.glob("*.yaml"):
            try:
                with open(lst, 'r') as f:
                    data = yaml.safe_load(f)
                    if not data: continue
                    items.extend(_parse_list(data, scope="GLOBAL"))
            except Exception as e:
                items.append({
                    "label": f"⚠ Error loading {lst.name}",
                    "type": "NONE"
                })

    # Render Project Lists
    if project_lists_dir.exists():
        for lst in project_lists_dir.glob("*.yaml"):
            try:
                with open(lst, 'r') as f:
                    data = yaml.safe_load(f)
                    if not data: continue
                    items.extend(_parse_list(data, scope="PROJECT"))
            except Exception:
                pass

    return items

def _parse_list(data, scope="GLOBAL"):
    """Parses a YAML list definition into Parallax entities."""
    entities = []
    
    # Handle simple array of strings/dicts
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                entities.append({
                    "label": item,
                    "type": "NONE",
                    "meta": f"[{scope}]"
                })
            elif isinstance(item, dict):
                e_type = item.get("type", "ACTION")
                payload = item.get("payload", "")
                
                new_ent = {
                    "label": item.get("label", "Unknown"),
                    "type": e_type,
                    "payload": payload,
                    "meta": f"[{scope}]"
                }
                
                if e_type == "PLACE":
                    new_ent["place"] = payload
                else:
                    new_ent["path"] = payload
                    new_ent["action"] = payload
                    
                entities.append(new_ent)
                
    # Handle structured object: { "title": "My List", "items": [...] }
    elif isinstance(data, dict):
        title = data.get("title", "")
        if title:
            # Add a visual separator/header if a title is provided
            entities.append({
                "label": f"─── {title.upper()} ───",
                "type": "NONE"
            })
            
        items = data.get("items", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    e_type = item.get("type", "ACTION")
                    payload = item.get("payload", "")
                    
                    new_ent = {
                        "label": item.get("label", "Unknown"),
                        "type": e_type,
                        "payload": payload,
                        "meta": f"[{scope}] {item.get('meta', '')}".strip()
                    }
                    
                    if e_type == "PLACE":
                        new_ent["place"] = payload
                    else:
                        new_ent["path"] = payload
                        new_ent["action"] = payload
                        
                    entities.append(new_ent)

    return entities
