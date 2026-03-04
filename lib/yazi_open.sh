#!/bin/bash
# lib/yazi_open.sh
# Bridge between Yazi and Nexus Shell to open files in the Editor pane.

FILE_PATH="$1"

# Resolve absolute path if needed
if [[ "$FILE_PATH" != /* ]]; then
    FILE_PATH="$(pwd)/$FILE_PATH"
fi

if [[ -n "$NEXUS_HOME" && -x "$NEXUS_HOME/core/exec/router.sh" ]]; then
    echo "NOTE|$FILE_PATH" | "$NEXUS_HOME/core/exec/router.sh"
else
    # Fallback if outside nexus
    ${EDITOR:-nvim} "$FILE_PATH"
fi
