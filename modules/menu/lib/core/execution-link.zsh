#!/usr/bin/env zsh
# zsh/core/execution-link.zsh
# Source this file in the target terminal to set up command reception.

# 1. Define the signal handler
# 1. Define the signal handler
px-handle-command() {
    local cmd_file="$HOME/.config/parallax/.transmitted_cmd"
    [[ ! -f "$cmd_file" ]] && return

    # Parse JSON envelope
    local payload=$(cat "$cmd_file")
    local action=$(echo "$payload" | jq -r '.action')
    
    case "$action" in
        "RUN_SHELL")
            local cmd=$(echo "$payload" | jq -r '.args.command')
            local cwd=$(echo "$payload" | jq -r '.args.cwd')
            local resp_file=$(echo "$payload" | jq -r '.args.response_file // empty')
            
            # --- SAFETY GATE: Path Guard ---
            # Configurable via PX_ALLOWED_PATHS (colon-separated)
            local real_cwd="${cwd:A}"
            local allowed_paths="${PX_ALLOWED_PATHS:-$HOME:$TMPDIR:/tmp}"
            local is_allowed=false
            
            for allowed in ${(s/:/)allowed_paths}; do
                [[ "$real_cwd" =~ ^"${allowed:A}"/ || "$real_cwd" == "${allowed:A}" ]] && is_allowed=true && break
            done
            
            if [[ "$is_allowed" == "false" ]]; then
                printf "\e[1;31m🛡️ SAFETY BLOCK: Target path '%s' is outside allowed workspace.\e[0m\n" "$real_cwd"
                [[ -n "$resp_file" ]] && echo "ERROR: Safety Block - Path outside workspace" > "$resp_file"
                return 1
            fi

            # Execute
            if [[ -n "$resp_file" ]]; then
                (cd "$real_cwd" && eval "$cmd") > "$resp_file" 2>&1
                echo "---CORTEX_EXIT_CODE:$?---" >> "$resp_file"
            else
                (cd "$real_cwd" && eval "$cmd")
            fi
            ;;
            
        "PROTOCOL:MODE_SWITCH")
            # Legacy support refactored to structured mode
            local mode=$(echo "$payload" | jq -r '.args.mode')
            local mode_file="$PX_ZSH_ROOT/modes/mode-$mode"
            [[ -f "$mode_file" ]] && source "$mode_file" && clear && "mode-$mode"
            ;;
            
        *)
            printf "\e[1;33m⚠️ WARNING: Unknown action '%s' received.\e[0m\n" "$action"
            ;;
    esac
}

# 2. Mirroring handler (SIGUSR2)
# Static context mirroring (faint thoughts)
px-handle-mirror() {
    local mirror_file="$HOME/.config/parallax/.px_mirror_$$"
    if [[ -f "$mirror_file" ]]; then
        local msg=$(cat "$mirror_file")
        printf "\e[2;3m>>> Mirror: %s\e[0m\n" "$msg"
    fi
}

# Set the traps
trap px-handle-command USR1
trap px-handle-mirror USR2

echo "Signal handlers (USR1, USR2) installed. Body terminal ready."
