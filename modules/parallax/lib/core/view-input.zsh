#!/usr/bin/env zsh
# zsh/core/view-input.zsh
# The Modern Orchestrator for Parallax (Resident-FZF Era).

view-input() {
  local source_id=""
  local prompt_text=""
  local base_header=""
  
  # Parse Args
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --source) source_id="$2"; shift 2 ;;
      --prompt) prompt_text="$2"; shift 2 ;;
      --header) base_header="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  [[ -z "$source_id" ]] && source_id="menu"
  [[ -z "$prompt_text" ]] && prompt_text="$(echo "$source_id" | awk '{print toupper(substr($0,1,1))substr($0,2)}') > "

  export PX_HUD_CONTEXT="$source_id"
  
  # 🛡️ THE VISUAL CAGE: Use Alternate Screen Buffer
  tput smcup
  tput civis
  
  # Ensure cleanup on any exit
  cleanup() {
    tput cnorm
    tput rmcup
  }
  trap cleanup EXIT INT TERM

  while true; do
    # 1. Selection Items
    local items=$("$HOME/bin/px-source" "$source_id")

    # 2. UI Selection Loop (Standard Engine)
    # The engine should handle its own persistence, but we catch exits here.
    local extra_args=""
    if [[ "$source_id" == "chat" || "$source_id" == "actions" ]]; then
       extra_args="--resident"
    fi
    
    local selection=$(echo "$items" | px-ui-select "$prompt_text" "$base_header" $extra_args)
    
    # 🩹 CAGE REPAIR: FZF exit drops us to Main Buffer (rmcup).
    # We must INSTANTLY re-assert Alternate Screen to hide the shell prompt.
    tput smcup
    tput civis
    
    # 3. Handle EXIT signals
    # ONLY exit if we get an explicit EXIT signal.
    if [[ "$selection" == "SIGNAL|EXIT" ]]; then
       break
    fi

    # Persistent Guard: If selection is empty (fzf aborted but no signal), just continue the loop.
    if [[ -z "$selection" ]]; then
       continue
    fi

    # 4. Handle Navigation vs Execution
    if [[ "$selection" == "Selection|"* ]]; then
       selection="${selection#Selection|}"
    fi

    # Plane change detection (for syncing HUD_CONTEXT)
    if [[ "$selection" == "PLANE:"* ]]; then
       source_id="${selection#PLANE:}"
       export PX_HUD_CONTEXT="$source_id"
       prompt_text="$(echo "$source_id" | awk '{print toupper(substr($0,1,1))substr($0,2)}') > "
       continue # Refresh loop with new source
    fi

    # 5. Route to Brain
    px-router "$selection"
    local status=$?
    
    # If router returns 0, it means "Terminal process should exit"
    [[ $status -eq 0 ]] && break
  done

  # Restore state
  tput cnorm
  tput rmcup
}
