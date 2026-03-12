#!/usr/bin/env zsh
# core/exec/nxs-keychain.sh
# Secure secret management for Nexus Shell using MacOS Keychain.

SERVICE_NAME="nexus-shell"
# Default account, but can be overridden by project
ACCOUNT_NAME="${NEXUS_PROJECT:-global}-secrets"

case "$1" in
  set)
    # args: [--global] <key> [value]
    local account="$ACCOUNT_NAME"
    if [[ "$2" == "--global" ]]; then
        account="global-secrets"
        shift
    fi
    local key="$2"
    local val="$3"
    
    if [[ -z "$key" ]]; then
      echo "Usage: nxs-keychain set [--global] <key> [value]"
      exit 1
    fi
    
    if [[ "$val" == "-" || -z "$val" ]]; then
      security add-generic-password -U -a "$account" -s "$SERVICE_NAME" -l "$key" -w -
    else
      security add-generic-password -U -a "$account" -s "$SERVICE_NAME" -l "$key" -w "$val"
    fi
    echo "Saved secret '$key' to Keychain ($account)."
    ;;

  get)
    # args: [--global] <key>
    local account="$ACCOUNT_NAME"
    if [[ "$2" == "--global" ]]; then
        account="global-secrets"
        shift
    fi
    local key="$2"
    if [[ -z "$key" ]]; then
      echo "Usage: nxs-keychain get [--global] <key>"
      exit 1
    fi
    security find-generic-password -a "$account" -s "$SERVICE_NAME" -l "$key" -w 2>/dev/null
    ;;

  list)
    echo -e "\033[1;36m--- Project Secrets ($ACCOUNT_NAME) ---\033[0m"
    security find-generic-password -a "$ACCOUNT_NAME" -s "$SERVICE_NAME" -g 2>&1 | grep "0x00000007 <blob>=" | sed 's/.*"\(.*\)".*/\1/' || echo "None"
    echo ""
    echo -e "\033[1;36m--- Global Secrets (global-secrets) ---\033[0m"
    security find-generic-password -a "global-secrets" -s "$SERVICE_NAME" -g 2>&1 | grep "0x00000007 <blob>=" | sed 's/.*"\(.*\)".*/\1/' || echo "None"
    ;;

  delete)
    # args: [--global] <key>
    local account="$ACCOUNT_NAME"
    if [[ "$2" == "--global" ]]; then
        account="global-secrets"
        shift
    fi
    local key="$2"
    security delete-generic-password -a "$account" -s "$SERVICE_NAME" -l "$key"
    echo "Deleted secret '$key' from Keychain ($account)."
    ;;

  *)
    echo "Usage: nxs-keychain {set|get|list|delete} [--global] [args...]"
    exit 1
    ;;
esac
