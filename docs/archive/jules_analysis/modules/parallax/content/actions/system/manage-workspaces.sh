#!/bin/bash
# Manage Workspaces
# List and manage (delete/unregister) existing workspaces.
# @param PROJECT: Select Project $(python3 ~/.parallax/lib/exec/px-list-workspaces.py)
# @param ACTION: Action [Unregister, Delete Config, Nuke Project]

echo "🏗️  Workspace Manager"

REGISTRY="$HOME/.parallax/registry.json"

if [[ -z "$PROJECT" ]]; then
    echo "❌ No project selected."
    exit 1
fi

echo "  Target: $PROJECT"
echo "  Action: $ACTION"

# Extract Path from "Name (Path)" format if needed, or assume PROJECT is the path or name
# The listing script will return paths as values usually.

TARGET_PATH="$PROJECT"

if [[ "$ACTION" == "Unregister" ]]; then
    echo "  > Unregistering from registry..."
    # Use python to remove from json
    python3 << PYEOF
import json, os
registry_path = os.path.expanduser("$REGISTRY")
if os.path.exists(registry_path):
    with open(registry_path, "r") as f: reg = json.load(f)
    if "$TARGET_PATH" in reg:
        del reg["$TARGET_PATH"]
        with open(registry_path, "w") as f: json.dump(reg, f, indent=2)
        print("  ✅ Removed from registry.")
    else:
        print("  ⚠️ Not found in registry.")
PYEOF

elif [[ "$ACTION" == "Delete Config" ]]; then
    echo "  > Removing .parallax configuration..."
    if [[ -d "$TARGET_PATH/.parallax" ]]; then
        rm -rf "$TARGET_PATH/.parallax"
        echo "  ✅ Deleted .parallax folder."
    elif [[ -d "$HOME/.parallax/workspaces/$(basename "$TARGET_PATH")" ]]; then
        # Check if it's a stealth workspace
        rm -rf "$HOME/.parallax/workspaces/$(basename "$TARGET_PATH")"
        echo "  ✅ Deleted Stealth workspace."
    else
        echo "  ⚠️ No configuration found at target."
    fi
    
    # Also unregister
    python3 << PYEOF
import json, os
registry_path = os.path.expanduser("$REGISTRY")
if os.path.exists(registry_path):
    with open(registry_path, "r") as f: reg = json.load(f)
    if "$TARGET_PATH" in reg:
        del reg["$TARGET_PATH"]
        with open(registry_path, "w") as f: json.dump(reg, f, indent=2)
PYEOF

elif [[ "$ACTION" == "Nuke Project" ]]; then
    echo "  ☢️  NUKING PROJECT FOLDER..."
    if [[ -d "$TARGET_PATH" ]]; then
        # Safety check: Don't delete root or home
        if [[ "$TARGET_PATH" == "$HOME" || "$TARGET_PATH" == "/" ]]; then
            echo "  ❌ SAFETY ABORT: Cannot nuke HOME or ROOT."
            exit 1
        fi
        rm -rf "$TARGET_PATH"
        echo "  ✅ Deleted $TARGET_PATH"
    else
        echo "  ⚠️ Path not found."
    fi
    # Also unregister
    python3 << PYEOF
import json, os
registry_path = os.path.expanduser("$REGISTRY")
if os.path.exists(registry_path):
    with open(registry_path, "r") as f: reg = json.load(f)
    if "$TARGET_PATH" in reg:
        del reg["$TARGET_PATH"]
        with open(registry_path, "w") as f: json.dump(reg, f, indent=2)
PYEOF

fi

echo "Done."
