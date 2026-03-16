#!/usr/bin/env python3
import os
import sys
import yaml
from pathlib import Path

def merge_dicts(dict1, dict2):
    """Recursively merges dict2 into dict1."""
    if not isinstance(dict2, dict):
        return dict1
    for k, v in dict2.items():
        if k in dict1 and isinstance(dict1[k], dict) and isinstance(v, dict):
            merge_dicts(dict1[k], v)
        else:
            dict1[k] = v
    return dict1

def main():
    # 1. System Defaults (The Engine)
    # Resolve relative to this script's location (core/api/config_helper.py)
    core_dir = Path(__file__).parent.parent
    system_cfg_path = core_dir / "config" / "default_settings.yaml"
    
    # 2. User Global (User Preferences)
    global_cfg_path = Path(os.path.expanduser("~/.config/nexus-shell/settings.yaml"))
    
    # 3. Project Local (Workspace Overrides)
    project_cfg_path = Path(os.getcwd()) / ".nexus.yaml"
    
    config = {}

    # Load Hierarchy (Bottom-Up)
    paths_to_load = [system_cfg_path, global_cfg_path, project_cfg_path]
    
    for path in paths_to_load:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    file_cfg = yaml.safe_load(f)
                    if file_cfg: 
                        merge_dicts(config, file_cfg)
            except Exception as e:
                print(f"# Error loading config {path}: {e}", file=sys.stderr)


    # Output for Shell Evaluation
    # Output for Shell Evaluation
    def safe_export(key, val):
        safe_val = str(val).strip().replace("\n", " ")
        print(f"export {key}='{safe_val}'")

    safe_export("NEXUS_COMPOSITION", config.get('composition', 'vscodelike'))
    tools = config.get('tools', {})
    safe_export("NEXUS_EDITOR", tools.get('editor', 'nvim'))
    safe_export("NEXUS_FILES", tools.get('files', 'yazi'))
    safe_export("NEXUS_CHAT", tools.get('chat', 'opencode'))
    safe_export("NEXUS_MENU", tools.get('menu', '$NEXUS_HOME/modules/menu/bin/nexus-menu'))
    safe_export("NEXUS_TERMINAL", tools.get('terminal', '/bin/zsh -i'))
    
    # Stack Settings
    stack = config.get('stack', {})
    safe_export("NEXUS_ROLE_ROUTING", str(stack.get('role_routing', True)).lower())
    
    # Parallax Specifics
    parallax = config.get('parallax', {})
    safe_export("PX_ENABLED", str(parallax.get('enabled', True)).lower())
    pillars = set(parallax.get('pillars', []))
    safe_export("PX_PILLARS", ','.join(pillars))

if __name__ == "__main__":
    main()
