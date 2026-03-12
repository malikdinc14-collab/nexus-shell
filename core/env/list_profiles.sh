#!/bin/bash
# core/env/list_profiles.sh
# Lists available Nexus profiles.

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"

PROFILES_DIR="${NEXUS_HOME}/config/profiles"

echo "Available Profiles:"
echo "-------------------"
if [[ -d "$PROFILES_DIR" ]]; then
    ls -1 "$PROFILES_DIR" | grep ".yaml$" | sed 's/.yaml$//'
else
    echo "No profiles found in $PROFILES_DIR"
fi
