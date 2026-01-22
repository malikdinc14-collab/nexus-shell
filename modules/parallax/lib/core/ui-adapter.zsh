#!/usr/bin/env zsh
# zsh/core/ui-adapter.zsh
# The Protocol Interpreter for Parallax Interfaces.
# Translates UI Engine outputs into standard Signal|Payload tuples.

px-ui-select() {
    local prompt="$1"
    local base_header="$2"
    # Capture remaining args (e.g. --resident)
    shift 2
    local extra_args=("$@")
    
    # 1. Read Input into array
    local -a items
    while IFS= read -r line; do
        items+=("$line")
    done
    [[ ${#items} -eq 0 ]] && return 0
    local input_str=$(printf "%s\n" "${items[@]}")

    # 2. Resolve UI Engine
    local GET_CONTEXT="$HOME/bin/px-context"
    local engine=$($GET_CONTEXT get primary_ui_selector 2>/dev/null || echo "fzf")
    engine="${PX_FORCE_UI:-$engine}"

    # Fetch dynamic keybinds
    local k_stage=$($GET_CONTEXT get key_stage || echo "tab")
    local k_view=$($GET_CONTEXT get key_view || echo "right")
    local k_edit=$($GET_CONTEXT get key_edit || echo "ctrl-e")
    local k_toggle_dashboard=$($GET_CONTEXT get key_toggle_dashboard || echo "ctrl-d")

    # 3. Run Engine
    local output
    case "$engine" in
      term)
        output=$(echo "$input_str" | ui-term "$prompt" "$base_header" "${extra_args[@]}")
        ;;
      composer)
        local clean_prompt="${prompt%% > }"
        clean_prompt="${clean_prompt%%: }"
        output=$(echo "$input_str" | px-ui-composer \
            --prompt "${clean_prompt} > " \
            --footer "$base_header" \
            --sticky-headers \
            --bind "$k_stage:STAGE" \
            --bind "$k_view:VIEW" \
            --bind "$k_edit:EDIT" \
            --bind "$k_toggle_dashboard:TOGGLE_DASHBOARD" \
            ${PX_MODE_LOG:+--live-log "$PX_MODE_LOG"})
        ;;
      *)
        # Default/Standard FZF Engine
        output=$(echo "$input_str" | ui-term "$prompt" "$base_header" "${extra_args[@]}")
        ;;
    esac

    [[ -z "$output" ]] && return 0

    # 4. UNIVERSAL PROTOCOL INTERPRETER
    # Engines now return "SIGNAL|PAYLOAD" or "TYPE|CONTENT"
    
    # Check for direct pass-through signals (starts with ..|)
    if [[ "$output" == "..|"* ]]; then
        echo "${output#..|}"
        return 0
    fi

    # Handle multi-column protocol output
    local label="${output%%|*}"
    local payload="${output#*|}"

    case "$label" in
      Selection|SIGNAL|STAGE|VIEW|EDIT|BACK|TOGGLE_DASHBOARD)
        # Protocol signals from Composer or standardized FZF
        echo "$output"
        ;;
      QUERY)
        # User hit Enter on raw text
        echo "QUERY|$payload"
        ;;
      ID)
        # User selected a history item by ID
        echo "ID|$payload"
        ;;
      ALT_ENTER_QUERY)
        # Specialized Alt-Enter return: "ALT_ENTER_QUERY:query|ALT_ENTER_SELECTION:selection"
        # We process this as a forced EXECUTE signal
        local q="${payload%%|*}"; q="${q#ALT_ENTER_QUERY:}"
        local s="${payload#*|}"; s="${s#ALT_ENTER_SELECTION:}"
        if [[ -n "$s" ]]; then
           echo "EXECUTE_ID|$s"
        else
           echo "EXECUTE_CMD|$q"
        fi
        ;;
      SIGNAL|STAGE|VIEW|EDIT|BACK|TOGGLE_DASHBOARD)
        # Protocol signals from Composer or standardized FZF
        echo "$output"
        ;;
      *)
        # Fallback: Just return the selection
        echo "$output"
        ;;
    esac
}
