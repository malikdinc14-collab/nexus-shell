#!/usr/bin/env bash
# core/engine/git/hook_manager.sh
# Manages Nexus-specific Git hooks to trigger automation (like the Conflict Matrix).

MODE="${1:-install}"
PROJECT_ROOT="${2:-$(pwd)}"

install_hooks() {
    local hook_dir="$PROJECT_ROOT/.git/hooks"
    if [[ ! -d "$hook_dir" ]]; then
        echo "[!] Not a git repository or no hook directory found."
        return 1
    fi

    # post-merge hook to detect conflicts early
    cat <<EOF > "$hook_dir/post-merge"
#!/bin/bash
# Nexus Post-Merge Hook
"${NEXUS_HOME}/core/kernel/boot/conflict_detector.sh" trigger
EOF
    chmod +x "$hook_dir/post-merge"
    echo "[*] Nexus post-merge hook installed in $PROJECT_ROOT"
}

case "$MODE" in
    install) install_hooks ;;
esac
