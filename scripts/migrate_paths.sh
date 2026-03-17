#!/bin/bash
# scripts/migrate_paths.sh
# Atomic Migration: Sanitizes legacy hardcoded paths in Nexus session states and scripts.

NEXUS_HOME="${NEXUS_HOME:-$HOME/.config/nexus-shell}"
OLD_PATH="$Python_BIN"
OLD_VAR_PATH="\$Python_BIN"
NEW_VAR="\$Python_BIN"

echo "[*] Starting Atomic Path Migration..."

# 1. Target Directories
TARGETS=(
    ".nexus"
    "core"
    "modules"
    "scripts"
    "$NEXUS_HOME/core/engine/state"
)

for dir in "${TARGETS[@]}"; do
    if [[ -d "$dir" ]]; then
        echo "[>] Sanitizing: $dir"
        find "$dir" -type f \( -name "*.json" -o -name "*.sh" -o -name "*.py" -o -not -name "*.*" \) -not -path "*/node_modules/*" -not -path "*/external/*" 2>/dev/null | while read -r file; do
            # Check if file is readable and writable
            if [[ ! -r "$file" || ! -w "$file" ]]; then
                echo "    [WARN] Skipping (no permission): $file"
                continue
            fi

            # Handle Shebangs specifically for Python files or binaries without extensions
            if head -n 1 "$file" | grep -q "$OLD_PATH"; then
                echo "    [SHEBANG] $file"
                sed -i '' "1s|$OLD_PATH|/usr/bin/env python3|g" "$file"
            fi

            # Handle hardcoded paths in content
            if grep -qE "nexus_env|Users/Shared/Projects/nexus-shell/nexus_env" "$file"; then
                echo "    [FIX] $file"
                sed -i '' "s|$OLD_PATH|$NEW_VAR|g" "$file"
                sed -i '' "s|$OLD_VAR_PATH|$NEW_VAR|g" "$file"
                # Catch-all for other nexus_env references
                sed -i '' "s|$Python_BIN|\$Python_BIN|g" "$file"
            fi
        done
    fi
done

echo "[*] Migration complete."
