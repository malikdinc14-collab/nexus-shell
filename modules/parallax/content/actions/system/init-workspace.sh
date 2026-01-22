#!/bin/bash
# Initialize Workspace
# Creates a Parallax workspace for the current project.
# @param NAME: Workspace name (my-project)
# @param MODE: Registration mode [stealth, local]

echo "🏗️  Starting Workspace Factory..."

NAME="${NAME:-$1}"
MODE="${MODE:-$2}"

[[ -z "$NAME" ]] && NAME=$(basename "$(pwd)")
[[ -z "$MODE" ]] && MODE="stealth"

CWD=$(pwd)

if [[ "$MODE" == "local" ]]; then
    DASHBOARD_DIR="$CWD/.parallax"
    DASHBOARD_FILE="$DASHBOARD_DIR/dashboard.json"
    echo "📦 Mode: LOCAL (.parallax/ in CWD)"
else
    DASHBOARD_DIR="$HOME/.parallax/workspaces/$NAME"
    DASHBOARD_FILE="$DASHBOARD_DIR/dashboard.json"
    mkdir -p "$DASHBOARD_DIR"
    echo "🥷 Mode: STEALTH (Stored in ~/.parallax/workspaces/)"
    
    # Register in Stealth Registry
    REGISTRY="$HOME/.parallax/registry.json"
    [[ ! -f "$REGISTRY" ]] && echo "{}" > "$REGISTRY"
    
    # Use jq if available, otherwise Python
    if command -v jq &> /dev/null; then
        jq --arg cwd "$CWD" --arg dashboard "$DASHBOARD_FILE" --arg library "$DASHBOARD_DIR/library" \
           '.[$cwd] = {"dashboard": $dashboard, "library": $library}' "$REGISTRY" > "${REGISTRY}.tmp" && mv "${REGISTRY}.tmp" "$REGISTRY"
    else
        python3 << PYEOF
import json, os
registry_path = os.path.expanduser("$REGISTRY")
with open(registry_path, "r") as f: reg = json.load(f)
reg["$CWD"] = {"dashboard": "$DASHBOARD_FILE", "library": "$DASHBOARD_DIR/library"}
with open(registry_path, "w") as f: json.dump(reg, f, indent=2)
PYEOF
    fi
fi

# Bootstrap
mkdir -p "$DASHBOARD_DIR/library"/{actions,agents,docs,surfaces}
cat <<EOF > "$DASHBOARD_FILE"
{
  "title": "$NAME",
  "settings": {},
  "sections": [
    {
      "name": "Project Specific",
      "items": [
        { "label": "Project TODO", "type": "DOC", "path": "$DASHBOARD_DIR/TODO.md" }
      ]
    }
  ]
}
EOF

touch "$DASHBOARD_DIR/TODO.md"

echo "✅ Workspace '$NAME' initialized."
echo "💡 Running 'parallax' in this directory will auto-discover it."
