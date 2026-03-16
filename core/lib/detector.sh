#!/usr/bin/env bash
# core/lib/detector.sh
# System-wide tool detection for Nexus Shell

set -e

EXTENSION_DIR="${NEXUS_HOME}/extensions"
PROFILE_FILE="${HOME}/.nexus/profile.yaml"

# Detect if a binary exists on the system
detect_binary() {
    local binary="$1"
    command -v "$binary" &>/dev/null
}

# Get list of all extension manifests
get_all_manifests() {
    find "$EXTENSION_DIR" -name "manifest.yaml" -type f 2>/dev/null
}

# Parse a manifest file and return key value
parse_manifest_key() {
    local manifest="$1"
    local key="$2"
    grep "^${key}:" "$manifest" 2>/dev/null | head -1 | awk '{$1=""; print substr($0,2)}' | xargs
}

# Detect all installed tools from extensions
detect_installed_tools() {
    local detected=""
    local roles=""
    
    for manifest in $(get_all_manifests); do
        local name=$(parse_manifest_key "$manifest" "name")
        local binary=$(parse_manifest_key "$manifest" "binary")
        local role=$(parse_manifest_key "$manifest" "role")
        
        # Skip internal extensions (no binary to detect)
        [[ -z "$binary" ]] && continue
        
        if detect_binary "$binary"; then
            detected="$detected DETECTED_TOOLS[$name]=\"$binary\""
            [[ -n "$role" ]] && roles="$roles DETECTED_ROLES[$role]=\"$name\""
        fi
    done
    
    # Output as eval-able shell
    echo "# Detected tools"
    echo "$detected"
    echo ""
    echo "# Role mappings"
    echo "$roles"
}

# Detect tools and output as JSON (for Python consumption)
detect_as_json() {
    python3 << 'PYTHON'
import os
import yaml
import json
import subprocess
from pathlib import Path

extension_dir = os.environ.get("NEXUS_HOME", "") + "/extensions"
detected = {"tools": {}, "roles": {}}

def detect_binary(binary):
    try:
        subprocess.run(["command", "-v", binary], check=True, capture_output=True, shell=True)
        return True
    except:
        return False

def parse_manifest(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except:
        return {}

for manifest_path in Path(extension_dir).rglob("manifest.yaml"):
    manifest = parse_manifest(manifest_path)
    if not manifest:
        continue
    
    name = manifest.get("name", "")
    binary = manifest.get("binary", "")
    role = manifest.get("role", "")
    
    if binary and detect_binary(binary):
        detected["tools"][name] = binary
        if role:
            detected["roles"][role] = name

print(json.dumps(detected))
PYTHON
}

# Get the best extension for a role (highest priority that's installed)
get_best_for_role() {
    local role="$1"
    local best_name=""
    local best_priority=-1
    
    for manifest in $(get_all_manifests); do
        local manifest_role=$(parse_manifest "$manifest" "role")
        [[ "$manifest_role" == "$role" ]] || continue
        
        local name=$(parse_manifest "$manifest" "name")
        local binary=$(parse_manifest "$manifest" "binary")
        local priority=$(parse_manifest "$manifest" "role_priority")
        priority=${priority:-50}
        
        if detect_binary "$binary" && [[ $priority -gt $best_priority ]]; then
            best_name="$name"
            best_priority=$priority
        fi
    done
    
    echo "$best_name"
}

# Get suggestions for missing roles
suggest_missing_extensions() {
    local roles=("editor" "explorer" "chat" "terminal" "viewer" "search")
    local suggestions=""
    
    for role in "${roles[@]}"; do
        local current=$(get_best_for_role "$role")
        if [[ -z "$current" ]]; then
            # Find best extension to suggest (highest priority, even if not installed)
            local best_manifest=""
            local best_priority=-1
            
            for manifest in $(get_all_manifests); do
                local manifest_role=$(parse_manifest "$manifest" "role")
                [[ "$manifest_role" == "$role" ]] || continue
                
                local priority=$(parse_manifest "$manifest" "role_priority")
                priority=${priority:-50}
                
                if [[ $priority -gt $best_priority ]]; then
                    best_manifest="$manifest"
                    best_priority=$priority
                fi
            done
            
            if [[ -n "$best_manifest" ]]; then
                local name=$(parse_manifest "$best_manifest" "name")
                local desc=$(parse_manifest "$best_manifest" "description")
                suggestions+="$name|$role|$desc"$'\n'
            fi
        fi
    done
    
    echo "$suggestions"
}

# Get all available extensions grouped by category
list_extensions_by_category() {
    local current_category=""
    local output=""
    
    for manifest in $(get_all_manifests | sort); do
        local name=$(parse_manifest_key "$manifest" "name")
        local category=$(parse_manifest_key "$manifest" "category")
        local desc=$(parse_manifest_key "$manifest" "description")
        local binary=$(parse_manifest_key "$manifest" "binary")
        
        local installed="○"
        [[ -n "$binary" ]] && detect_binary "$binary" && installed="✓"
        
        # Print category header when category changes
        if [[ "$category" != "$current_category" ]]; then
            [[ -n "$current_category" ]] && output="$output"$'\n'
            output="$output[$category]"$'\n'
            current_category="$category"
        fi
        
        output="$output  $installed $name - $desc"$'\n'
    done
    
    echo -n "$output"
}

# CLI interface
case "${1:-detect}" in
    detect)
        detect_installed_tools
        ;;
    json)
        detect_as_json
        ;;
    roles)
        shift
        get_best_for_role "$@"
        ;;
    suggest)
        suggest_missing_extensions
        ;;
    list)
        list_extensions_by_category
        ;;
    binary)
        shift
        detect_binary "$1" && echo "installed" || echo "not found"
        ;;
    *)
        echo "Usage: detector.sh {detect|json|roles|suggest|list|binary}"
        echo "  detect   - Output detected tools as shell vars"
        echo "  json     - Output detected tools as JSON"
        echo "  roles    - Get best tool for a role"
        echo "  suggest  - Suggest extensions for missing roles"
        echo "  list     - List all extensions by category"
        echo "  binary X - Check if binary X is installed"
        ;;
esac
