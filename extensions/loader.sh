#!/usr/bin/env bash
# extensions/loader.sh
# Nexus Shell Extension System
# Discovers, loads, and manages extensions

EXTENSION_DIR="${NEXUS_HOME}/extensions"
REGISTRY_FILE="${EXTENSION_DIR}/.registry.json"

# Get all manifest files (supports nested category structure)
get_all_manifests() {
    find "$EXTENSION_DIR" -name "manifest.yaml" -type f 2>/dev/null | grep -v ".registry"
}

# Parse manifest key
parse_manifest_key() {
    local manifest="$1"
    local key="$2"
    grep "^${key}:" "$manifest" 2>/dev/null | head -1 | awk -F': ' '{print $2}' | xargs
}

# Get extension name from manifest path
get_ext_name_from_manifest() {
    local manifest="$1"
    basename "$(dirname "$manifest")"
}

# Get extension category from manifest path
get_ext_category_from_manifest() {
    local manifest="$1"
    basename "$(dirname "$(dirname "$manifest")")"
}

# List all available extensions
list_extensions() {
    local found=0
    for manifest in $(get_all_manifests); do
        [[ -f "$manifest" ]] || continue
        local name=$(parse_manifest_key "$manifest" "name")
        local desc=$(parse_manifest_key "$manifest" "description")
        local binary=$(parse_manifest_key "$manifest" "binary")
        local category=$(parse_manifest_key "$manifest" "category")
        
        [[ -z "$name" ]] && name=$(get_ext_name_from_manifest "$manifest")
        [[ -z "$category" ]] && category=$(get_ext_category_from_manifest "$manifest")
        
        local installed="○"
        [[ -n "$binary" ]] && command -v "$binary" &>/dev/null && installed="✓"
        
        printf "%s %-15s [%-10s] %s\n" "$installed" "$name" "$category" "$desc"
        found=1
    done
    [[ $found -eq 0 ]] && echo "No extensions found"
}

# List all extensions (detailed, for fzf)
list_all_extensions() {
    for manifest in $(get_all_manifests); do
        [[ -f "$manifest" ]] || continue
        local name=$(parse_manifest_key "$manifest" "name")
        local desc=$(parse_manifest_key "$manifest" "description")
        local binary=$(parse_manifest_key "$manifest" "binary")
        local category=$(parse_manifest_key "$manifest" "category")
        
        [[ -z "$name" ]] && name=$(get_ext_name_from_manifest "$manifest")
        [[ -z "$category" ]] && category=$(get_ext_category_from_manifest "$manifest")
        
        local installed="○"
        [[ -n "$binary" ]] && command -v "$binary" &>/dev/null && installed="✓"
        
        echo "$installed $name [$category] - $desc"
    done | sort
}

# List extensions by category
list_by_category() {
    local category="$1"
    for manifest in $(get_all_manifests); do
        local cat=$(parse_manifest_key "$manifest" "category")
        [[ -z "$cat" ]] && cat=$(get_ext_category_from_manifest "$manifest")
        [[ "$cat" == "$category" ]] || continue
        
        local name=$(parse_manifest_key "$manifest" "name")
        local desc=$(parse_manifest_key "$manifest" "description")
        local binary=$(parse_manifest_key "$manifest" "binary")
        
        [[ -z "$name" ]] && name=$(get_ext_name_from_manifest "$manifest")
        
        local installed="○"
        [[ -n "$binary" ]] && command -v "$binary" &>/dev/null && installed="✓"
        
        echo "$installed $name - $desc"
    done
}

# Find manifest by extension name
find_manifest() {
    local ext_name="$1"
    # Try flat structure first
    if [[ -f "$EXTENSION_DIR/$ext_name/manifest.yaml" ]]; then
        echo "$EXTENSION_DIR/$ext_name/manifest.yaml"
        return
    fi
    # Try nested structure
    for manifest in $(get_all_manifests); do
        local name=$(parse_manifest_key "$manifest" "name")
        local dir_name=$(get_ext_name_from_manifest "$manifest")
        if [[ "$name" == "$ext_name" ]] || [[ "$dir_name" == "$ext_name" ]]; then
            echo "$manifest"
            return
        fi
    done
}

# Find extension directory by name
find_ext_dir() {
    local ext_name="$1"
    local manifest=$(find_manifest "$ext_name")
    [[ -n "$manifest" ]] && dirname "$manifest"
}

# Check if extension binary is installed
is_installed() {
    local ext_name="$1"
    local manifest=$(find_manifest "$ext_name")
    [[ -z "$manifest" ]] && return 1
    local binary=$(parse_manifest_key "$manifest" "binary")
    [[ -n "$binary" ]] && command -v "$binary" &>/dev/null
}

# Get extension info
get_info() {
    local ext_name="$1"
    local manifest=$(find_manifest "$ext_name")
    
    if [[ -z "$manifest" ]]; then
        echo "Extension not found: $ext_name"
        return 1
    fi
    
    echo "Extension: $ext_name"
    echo "---"
    grep -E "^(name|version|description|author|type|category|binary|role):" "$manifest" 2>/dev/null | while read line; do
        echo "$line"
    done
    
    if is_installed "$ext_name"; then
        echo "status: installed ✓"
    else
        echo "status: not installed ○"
    fi
}

# Install an extension
install_extension() {
    local ext_name="$1"
    local manifest=$(find_manifest "$ext_name")
    local ext_dir=$(dirname "$manifest")
    
    if [[ -z "$manifest" ]]; then
        echo "[!] Extension not found: $ext_name"
        return 1
    fi
    
    if is_installed "$ext_name"; then
        echo "[*] $ext_name already installed"
        return 0
    fi
    
    if [[ -f "$ext_dir/install.sh" ]]; then
        echo "[*] Installing $ext_name..."
        bash "$ext_dir/install.sh"
    else
        echo "[*] $ext_name has no install script. Install manually."
        echo "    Binary: $(parse_manifest_key "$manifest" "binary")"
        return 1
    fi
}

# Uninstall an extension
uninstall_extension() {
    local ext_name="$1"
    local manifest=$(find_manifest "$ext_name")
    
    if [[ -z "$manifest" ]]; then
        echo "[!] Extension not found: $ext_name"
        return 1
    fi
    
    local binary=$(parse_manifest_key "$manifest" "binary")
    if [[ -z "$binary" ]]; then
        echo "[!] No binary defined for $ext_name"
        return 1
    fi
    
    local bin_path=$(command -v "$binary" 2>/dev/null)
    if [[ -z "$bin_path" ]]; then
        echo "[*] $ext_name not installed"
        return 0
    fi
    
    echo "[*] Uninstalling $ext_name ($bin_path)..."
    rm -f "$bin_path"
    echo "[*] $ext_name uninstalled"
}

# Load extension hooks into environment
load_extension() {
    local ext_name="$1"
    local ext_dir=$(find_ext_dir "$ext_name")
    local manifest=$(find_manifest "$ext_name")
    
    [[ -z "$manifest" ]] && return 1
    
    # Add bin/ to PATH
    if [[ -d "$ext_dir/bin" ]]; then
        export PATH="$ext_dir/bin:$PATH"
    fi
    
    # Register MCP servers if extension is installed
    if is_installed "$ext_name" && [[ -f "$ext_dir/mcp/register.sh" ]]; then
        bash "$ext_dir/mcp/register.sh" register 2>/dev/null
    fi
}

# Load all extensions at boot
load_all_extensions() {
    for manifest in $(get_all_manifests); do
        local name=$(parse_manifest_key "$manifest" "name")
        [[ -z "$name" ]] && name=$(get_ext_name_from_manifest "$manifest")
        load_extension "$name" 2>/dev/null
    done
}

# Get hook path for an extension
get_hook() {
    local ext_name="$1"
    local hook_name="$2"
    local ext_dir=$(find_ext_dir "$ext_name")
    local hook_path="$ext_dir/hooks/${hook_name}.sh"
    [[ -f "$hook_path" ]] && echo "$hook_path"
}

# Execute a hook across all extensions that have it
exec_hook() {
    local hook_name="$1"
    shift
    for manifest in $(get_all_manifests); do
        local ext_dir=$(dirname "$manifest")
        local hook_path="$ext_dir/hooks/${hook_name}.sh"
        if [[ -f "$hook_path" ]]; then
            bash "$hook_path" "$@" 2>/dev/null
        fi
    done
}

# Build registry (for caching)
build_registry() {
    python3 << 'PYTHON'
import os
import yaml
import json
from pathlib import Path

ext_dir = os.environ.get("EXTENSION_DIR", "")
registry = {}

for manifest_path in Path(ext_dir).rglob("manifest.yaml"):
    try:
        with open(manifest_path) as f:
            data = yaml.safe_load(f) or {}
        name = data.get("name", manifest_path.parent.name)
        registry[name] = data
    except:
        pass

output_path = Path(ext_dir) / ".registry.json"
with open(output_path, "w") as f:
    json.dump(registry, f, indent=2)

print(f"[*] Registry built: {output_path}")
print(f"[*] {len(registry)} extensions indexed")
PYTHON
}

# CLI dispatcher
case "${1:-}" in
    list) list_extensions ;;
    list-all) list_all_extensions ;;
    list-category) shift; list_by_category "$@" ;;
    info) shift; get_info "$@" ;;
    install) shift; install_extension "$@" ;;
    uninstall) shift; uninstall_extension "$@" ;;
    load) shift; load_extension "$@" ;;
    load-all) load_all_extensions ;;
    hook) shift; get_hook "$@" ;;
    exec-hook) shift; exec_hook "$@" ;;
    registry) build_registry ;;
    find) shift; find_manifest "$@" ;;
    categories)
        echo "Available categories:"
        for dir in "$EXTENSION_DIR"/*/; do
            [[ -d "$dir" ]] && echo "  - $(basename "$dir")"
        done
        ;;
    *)
        echo "Nexus Extension Manager"
        echo ""
        echo "Usage: loader.sh <command> [args]"
        echo ""
        echo "Commands:"
        echo "  list              List all extensions"
        echo "  list-all          List all extensions (detailed)"
        echo "  list-category CAT List extensions in a category"
        echo "  categories        List all categories"
        echo "  info NAME         Show extension details"
        echo "  install NAME      Install an extension"
        echo "  uninstall NAME    Uninstall an extension"
        echo "  load NAME         Load an extension"
        echo "  load-all          Load all extensions"
        echo "  hook NAME HOOK    Get hook path"
        echo "  exec-hook HOOK    Execute hook across all extensions"
        echo "  registry          Build extension registry"
        ;;
esac
