#!/usr/bin/env bash
# bin/nxs-keys.sh
# Secure API Key Manager via macOS Keychain.
#
# Usage:
#   nxs-keys set <provider> <key>    - Store a key (e.g., nxs-keys set anthropic sk-...)
#   nxs-keys get <provider>          - Print key to stdout
#   nxs-keys export <provider>       - Set ENV_VAR for the provider in current session
#   nxs-keys list                    - List stored providers

SERVICE_NAME="NexusShell"

_usage() {
    echo "Usage: nxs-keys <command> [args]"
    echo "Commands:"
    echo "  set <provider> <key>    Store an API key"
    echo "  get <provider>          Print API key"
    echo "  export <provider>       Export provider-specific env var (e.g. ANTHROPIC_API_KEY)"
    echo "  list                    List all stored providers"
    echo "  delete <provider>       Remove a key"
}

case "$1" in
    set)
        if [[ -z "$2" || -z "$3" ]]; then _usage; exit 1; fi
        security add-generic-password -a "$USER" -s "$SERVICE_NAME" -l "Nexus: $2" -w "$3" -U
        echo "[Nexus] Key stored for $2"
        ;;
    get)
        if [[ -z "$2" ]]; then _usage; exit 1; fi
        security find-generic-password -a "$USER" -s "$SERVICE_NAME" -l "Nexus: $2" -w 2>/dev/null
        ;;
    delete)
        if [[ -z "$2" ]]; then _usage; exit 1; fi
        security delete-generic-password -a "$USER" -s "$SERVICE_NAME" -l "Nexus: $2"
        echo "[Nexus] Key deleted for $2"
        ;;
    list)
        security find-generic-password -a "$USER" -s "$SERVICE_NAME" -g 2>&1 | grep "0x00000007 <" | awk -F'="' '{print $2}' | sed 's/"//g' | sed 's/Nexus: //g'
        ;;
    export)
        if [[ -z "$2" ]]; then _usage; exit 1; fi
        case "${2,,}" in
            anthropic) VAR="ANTHROPIC_API_KEY" ;;
            openai)    VAR="OPENAI_API_KEY" ;;
            google)    VAR="GOOGLE_API_KEY" ;;
            deepseek)  VAR="DEEPSEEK_API_KEY" ;;
            openrouter) VAR="OPENROUTER_API_KEY" ;;
            *)         VAR="${2^^}_API_KEY" ;;
        esac
        VAL=$(security find-generic-password -a "$USER" -s "$SERVICE_NAME" -l "Nexus: $2" -w 2>/dev/null)
        if [[ -n "$VAL" ]]; then
            export "$VAR"="$VAL"
            echo "export $VAR='$VAL'"
        else
            echo "[Nexus] Error: No key found for $2" >&2
            exit 1
        fi
        ;;
    *)
        _usage
        exit 1
        ;;
esac
