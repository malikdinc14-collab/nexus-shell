#!/usr/bin/env bash
# core/engine/env/keychain_loader.sh
# Detects and loads project-specific secrets from macOS Keychain into the environment.

SERVICE_NAME="nexus-shell"
PROJECT_ACCOUNT="${NEXUS_PROJECT:-global}-secrets"
GLOBAL_ACCOUNT="global-secrets"

# Helper to load keys from a specific account
load_keys() {
    local account="$1"
    local keys=$(security find-generic-password -a "$account" -s "$SERVICE_NAME" -g 2>&1 | grep "0x00000007 <blob>=" | sed 's/.*"\(.*\)".*/\1/')
    
    for key in $keys; do
        if [[ -n "$key" ]]; then
            # Load the value into the environment
            local value=$(security find-generic-password -a "$account" -s "$SERVICE_NAME" -l "$key" -w 2>/dev/null)
            if [[ -n "$value" ]]; then
                export "$key"="$value"
                echo "    [*] Loaded secret: $key"
            fi
        fi
    done
}

echo "[*] Initializing Nexus Keychain..."
# 1. Load Global Keys
load_keys "$GLOBAL_ACCOUNT"
# 2. Load Project-Specific Keys
if [[ "$PROJECT_ACCOUNT" != "$GLOBAL_ACCOUNT" ]]; then
    load_keys "$PROJECT_ACCOUNT"
fi
