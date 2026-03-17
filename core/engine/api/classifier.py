#!/usr/bin/env python3
import sys
import os

# Extension -> Role Mapping
# Logic: Code/Config -> Editor
# Narrative: Docs/Graphics -> Renderer
ROUTING_MAP = {
    # Editor Roles (Code/Logic/Narrative Default)
    ".py": "editor", ".js": "editor", ".ts": "editor", ".jsx": "editor", ".tsx": "editor",
    ".rs": "editor", ".c": "editor", ".cpp": "editor", ".h": "editor", ".hpp": "editor",
    ".go": "editor", ".sh": "editor", ".bash": "editor", ".zsh": "editor",
    ".yaml": "editor", ".json": "editor", ".toml": "editor", ".conf": "editor",
    ".css": "editor", ".html": "editor", ".lua": "editor",
    ".md": "editor", ".markdown": "editor", ".txt": "editor", ".org": "editor",
    
    # Renderer Roles (Graphics/Special Docs)
    ".png": "renderer", ".jpg": "renderer", ".jpeg": "renderer", ".gif": "renderer",
    ".svg": "renderer", ".pdf": "renderer", ".mermaid": "renderer", ".mmd": "renderer",
}

def classify(filename):
    _, ext = os.path.splitext(filename.lower())
    return ROUTING_MAP.get(ext, "editor") # Default to editor for unknown

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("editor")
        sys.exit(0)
    
    print(classify(sys.argv[1]))
