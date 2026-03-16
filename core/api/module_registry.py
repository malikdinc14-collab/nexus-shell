#!/usr/bin/env python3
# core/api/module_registry.py
# --- Nexus Role Registry ---
# Resolves abstract roles (EDITOR, EXPLORER) to specific tool commands.

import os
import sys
import yaml
from pathlib import Path

def resolve_role(role_name: str) -> str:
    """
    Find the provider for a role across cascading layers.
    Priority: 
      1. Project: $PROJECT_ROOT/.nexus/modules.yaml
      2. User:    ~/.nexus/modules.yaml
      3. Global:  $NEXUS_HOME/config/modules.yaml
    """
    role_name = role_name.lower()
    nexus_home = Path(os.environ.get("NEXUS_HOME", Path(__file__).resolve().parents[2]))
    project_root = Path(os.environ.get("PROJECT_ROOT", os.getcwd()))
    user_home = Path.home()

    locations = [
        project_root / ".nexus" / "modules.yaml",
        user_home / ".nexus" / "modules.yaml",
        nexus_home / "config" / "modules.yaml"
    ]

    for loc in locations:
        if loc.exists():
            try:
                with open(loc, 'r') as f:
                    config = yaml.safe_load(f)
                    if config and "roles" in config:
                        provider = config["roles"].get(role_name)
                        if provider:
                            return provider
            except Exception as e:
                # Silently fail and check next layer
                continue
    
    # Absolute fallbacks if everything is missing
    fallbacks = {
        "editor": "vi",
        "explorer": "ls -la",
        "chat": "zsh",
        "viewer": "cat",
        "terminal": "zsh"
    }
    return fallbacks.get(role_name, "echo 'No provider for role: " + role_name + "'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: module_registry.py <role_name>")
        sys.exit(1)
    
    print(resolve_role(sys.argv[1]))
