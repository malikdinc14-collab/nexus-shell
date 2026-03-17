#!/bin/bash
# lib/yazi_open.sh
# Bridge between Yazi and Nexus Shell to open files in the Editor pane.

FILE_PATH="$1"

# 1. Resolve Canonical Path (The "Sovereign Bridge")
# IDE Sidebar uses symlinks in /tmp, but editors need real paths for LSPs/Git.
if [[ -L "$FILE_PATH" || "$FILE_PATH" == /tmp/nexus/* ]]; then
    # Use python3 for a portable 'realpath' on macOS/Linux
    FILE_PATH=$(python3 -c "import os, sys; print(os.path.realpath(sys.argv[1]))" "$FILE_PATH")
elif [[ "$FILE_PATH" != /* ]]; then
    FILE_PATH="$(pwd)/$FILE_PATH"
fi

if [[ -n "$NEXUS_HOME" && -x "$NEXUS_HOME/core/kernel/exec/router.sh" ]]; then
    echo "NOTE|$FILE_PATH" | "$NEXUS_HOME/core/kernel/exec/router.sh"
else
    # Fallback if outside nexus
    ${EDITOR:-nvim} "$FILE_PATH"
fi
