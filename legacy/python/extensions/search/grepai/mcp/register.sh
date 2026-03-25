#!/usr/bin/env bash
# extensions/grepai/mcp/register.sh
# Registers grepai as an MCP server for AI agents

set -e

ACTION="${1:-register}"

# MCP config locations for different AI tools
MCP_CONFIGS=(
    "$HOME/.config/claude-code/mcp.json"
    "$HOME/.config/cursor/mcp.json"
    "$HOME/.config/windsurf/mcp.json"
)

register_server() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        # Create minimal config if doesn't exist
        mkdir -p "$(dirname "$config_file")"
        echo '{"mcpServers":{}}' > "$config_file"
    fi
    
    # Check if already registered
    if grep -q '"grepai"' "$config_file" 2>/dev/null; then
        echo "[grepai] MCP already registered in $(basename "$(dirname "$config_file")")"
        return 0
    fi
    
    # Add grepai server to config
    python3 -c "
import json
import sys

config_file = '$config_file'
try:
    with open(config_file, 'r') as f:
        config = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    config = {'mcpServers': {}}

config.setdefault('mcpServers', {})
config['mcpServers']['grepai'] = {
    'command': 'grepai',
    'args': ['mcp'],
    'env': {}
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print('[grepai] Registered in $(basename \"$(dirname \"$config_file\")\")')
" 2>/dev/null
}

unregister_server() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        return 0
    fi
    
    python3 -c "
import json

config_file = '$config_file'
try:
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    if 'mcpServers' in config and 'grepai' in config['mcpServers']:
        del config['mcpServers']['grepai']
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print('[grepai] Unregistered from $(basename \"$(dirname \"$config_file\")\")')
except:
    pass
" 2>/dev/null
}

case "$ACTION" in
    register)
        if ! command -v grepai &>/dev/null; then
            echo "[grepai] Not installed. Install first: nxs extension install grepai"
            exit 1
        fi
        
        echo "[grepai] Registering MCP server..."
        for config in "${MCP_CONFIGS[@]}"; do
            register_server "$config"
        done
        echo "[grepai] ✓ MCP registration complete"
        echo ""
        echo "Available MCP tools:"
        echo "  - semantic_search: Search code by meaning"
        echo "  - trace_callers: Find who calls a function"
        echo "  - trace_callees: Find what a function calls"
        echo "  - list_functions: List all functions in codebase"
        ;;
    
    unregister)
        echo "[grepai] Unregistering MCP server..."
        for config in "${MCP_CONFIGS[@]}"; do
            unregister_server "$config"
        done
        echo "[grepai] ✓ MCP unregistration complete"
        ;;
    
    status)
        echo "[grepai] MCP Registration Status:"
        for config in "${MCP_CONFIGS[@]}"; do
            if [[ -f "$config" ]] && grep -q '"grepai"' "$config" 2>/dev/null; then
                echo "  ✓ $(dirname "$config" | xargs basename)"
            fi
        done
        ;;
    
    *)
        echo "Usage: register.sh {register|unregister|status}"
        exit 1
        ;;
esac
