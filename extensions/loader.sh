#!/usr/bin/env bash
# extensions/loader.sh
# Nexus Shell Extension System
# Discovers, loads, and manages extensions

EXTENSION_DIR="${NEXUS_HOME}/extensions"
REGISTRY_FILE="${EXTENSION_DIR}/.registry.json"

# List all available extensions
list_extensions() {
    local found=0
    for manifest in "$EXTENSION_DIR"/*/manifest.yaml; do
        [[ -f "$manifest" ]] || continue
        local name=$(basename "$(dirname "$manifest")")
        local desc=$(grep "^description:" "$manifest" 2>/dev/null | cut -d: -f2- | xargs || echo "No description")
        local binary=$(grep "^binary:" "$manifest" 2>/dev/null | awk '{print $2}' || echo "$name")
        local installed=$(command -v "$binary" &>/dev/null && echo "✓" || echo "○")
        echo "$installed $name - $desc"
        found=1
    done
    [[ $found -eq 0 ]] && echo "No extensions found"
}

# Check if extension binary is installed
is_installed() {
    local ext_name="$1"
    local manifest="$EXTENSION_DIR/$ext_name/manifest.yaml"
    [[ -f "$manifest" ]] || return 1
    local binary=$(grep "^binary:" "$manifest" 2>/dev/null | awk '{print $2}')
    [[ -n "$binary" ]] && command -v "$binary" &>/dev/null
}

# Get extension info
get_info() {
    local ext_name="$1"
    local manifest="$EXTENSION_DIR/$ext_name/manifest.yaml"
    [[ -f "$manifest" ]] || { echo "Extension not found: $ext_name"; return 1; }
    
    echo "Extension: $ext_name"
    echo "---"
    grep -E "^(name|version|description|author|type|binary):" "$manifest" 2>/dev/null | while read line; do
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
    local ext_dir="$EXTENSION_DIR/$ext_name"
    
    if [[ ! -f "$ext_dir/manifest.yaml" ]]; then
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
        echo "[!] No install script for $ext_name"
        return 1
    fi
}

# Uninstall an extension (removes binary, not extension directory)
uninstall_extension() {
    local ext_name="$1"
    local manifest="$EXTENSION_DIR/$ext_name/manifest.yaml"
    
    if [[ ! -f "$manifest" ]]; then
        echo "[!] Extension not found: $ext_name"
        return 1
    fi
    
    local binary=$(grep "^binary:" "$manifest" 2>/dev/null | awk '{print $2}')
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
    local ext_dir="$EXTENSION_DIR/$ext_name"
    local manifest="$ext_dir/manifest.yaml"
    
    [[ -f "$manifest" ]] || return 1
    
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
    for manifest in "$EXTENSION_DIR"/*/manifest.yaml; do
        [[ -f "$manifest" ]] || continue
        local name=$(basename "$(dirname "$manifest")")
        load_extension "$name" 2>/dev/null
    done
}

# Get hook path for an extension
get_hook() {
    local ext_name="$1"
    local hook_name="$2"
    local hook_path="$EXTENSION_DIR/$ext_name/hooks/${hook_name}.sh"
    [[ -f "$hook_path" ]] && echo "$hook_path"
}

# Execute a hook across all extensions that have it
exec_hook() {
    local hook_name="$1"
    shift
    for manifest in "$EXTENSION_DIR"/*/manifest.yaml; do
        [[ -f "$manifest" ]] || continue
        local name=$(basename "$(dirname "$manifest")")
        local hook_path="$EXTENSION_DIR/$name/hooks/${hook_name}.sh"
        if [[ -f "$hook_path" ]]; then
            bash "$hook_path" "$@" 2>/dev/null
        fi
    done
}

# Build registry (for caching)
build_registry() {
    local tmp_file=$(mktemp)
    echo "{" > "$tmp_file"
    local first=1
    for manifest in "$EXTENSION_DIR"/*/manifest.yaml; do
        [[ -f "$manifest" ]] || continue
        local name=$(basename "$(dirname "$manifest")")
        [[ $first -eq 0 ]] && echo "," >> "$tmp_file"
        first=0
        echo -n "  \"$name\": " >> "$tmp_file"
        # Convert YAML to JSON inline
        python3 -c "import yaml,json,sys; print(json.dumps(yaml.safe_load(open('$manifest'))))" >> "$tmp_file" 2>/dev/null || echo "{}" >> "$tmp_file"
    done
    echo "" >> "$tmp_file"
    echo "}" >> "$tmp_file"
    mv "$tmp_file" "$REGISTRY_FILE"
    echo "[*] Registry built: $REGISTRY_FILE"
}

# CLI dispatcher
case "${1:-}" in
    list) list_extensions ;;
    info) shift; get_info "$@" ;;
    install) shift; install_extension "$@" ;;
    uninstall) shift; uninstall_extension "$@" ;;
    load) shift; load_extension "$@" ;;
    load-all) load_all_extensions ;;
    hook) shift; get_hook "$@" ;;
    exec-hook) shift; exec_hook "$@" ;;
    registry) build_registry ;;
    *)
        echo "Nexus Extension Manager"
        echo ""
        echo "Usage: loader.sh <command> [args]"
        echo ""
        echo "Commands:"
        echo "  list              List all extensions"
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
