# zsh/core/projection-shell.zsh
# The orchestrator for Parallax (Input Shell).

export PX_ZSH_ROOT="$HOME/.parallax/lib"
export PX_STATE_DIR="${PX_STATE_DIR:-$HOME/.config/parallax}"
export PX_CORE_DIR="$PX_ZSH_ROOT/core"
export PX_MODES_DIR="$PX_ZSH_ROOT/modes"

# Load Core Protocols
source "$PX_CORE_DIR/ui-adapter.zsh"

# Ensure state dir exists
mkdir -p "$PX_STATE_DIR"

# Initialize Sticky Intent State
export PX_INTENT_MODE="${PX_INTENT_MODE:-EXECUTE}"

# Resolve Session ID (Pane ID or PID)
if [[ -n "$TMUX" ]]; then
  export PX_SESSION_ID=$(tmux display-message -p '#{pane_id}' | tr -d '%')
else
  # Use the parent PID if we are in a subshell, or our own
  export PX_SESSION_ID="${PX_SESSION_ID:-$$}"
fi

export PX_TARGET_FILE="$PX_STATE_DIR/.px_target_$PX_SESSION_ID"
export PX_SYNC_BUS="$PX_STATE_DIR/.px_sync_bus"

px-broadcast() {
  local event="$1"
  echo "$(date +%s)|$PX_SESSION_ID|$event" >> "$PX_SYNC_BUS"
}

px-sync-check() {
  # Read the last event from the bus
  local last_event=$(tail -n 1 "$PX_SYNC_BUS" 2>/dev/null)
  [[ -z "$last_event" ]] && return
  
  local timestamp="${last_event%%|*}"
  local origin_id=$(echo "$last_event" | cut -d'|' -f2)
  local payload="${last_event##*|}"
  
  # Only react to events from OTHER terminals
  if [[ "$origin_id" != "$PX_SESSION_ID" ]]; then
     # Handle specific sync events
     case "$payload" in
       TARGET_CHANGED:*)
         # Optional: Update local HUD or state
         ;;
     esac
  fi
}

px-target() {
  local name="main"
  local target_mind=""
  local links_dir="$PX_STATE_DIR/links"
  mkdir -p "$links_dir"

  # Parse args
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --to) target_mind="$2"; shift 2 ;;
      *) name="$1"; shift ;;
    esac
  done
  
  # Register PID and Metadata
  echo "$$" > "$links_dir/$name.pid"
  printf "TTY: %s\nUSER: %s\nSTART: %s\n" "$(tty)" "$USER" "$(date)" > "$links_dir/$name.meta"
  
  # Install Signal Trap (Command Reception)
  source "$PX_CORE_DIR/execution-link.zsh"
  
  echo ">>> Terminal registered as Output Shell: $name"
  
  if [[ -n "$target_mind" ]]; then
     echo ">>> Requesting remote link for: $target_mind"
     # Attempt to switch Nexus UI via Bridge
     local response=$(curl -s -X POST http://localhost:8000/px/open -d "{\"workspace\": \"$target_mind\"}")
     local status=$(echo "$response" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
     
     if [[ "$status" == "genesis" ]]; then
        echo ">>> Workspace '$target_mind' not found. Remote UI triggered Genesis Protocol."
     elif [[ "$status" == "ok" ]]; then
        echo ">>> Remote UI synchronized."
     fi
  fi

  # 1. AUTO-TARGET MIND (Handshake)
  local mind_file=""
  local sessions_dir="$PX_STATE_DIR/sessions"
  
  if [[ -n "$target_mind" ]]; then
     # Look for specific name or ID
     if [[ -f "$sessions_dir/$target_mind.mind" ]]; then
        mind_file="$sessions_dir/$target_mind.mind"
     else
        # Search by NAME: field
        for f in "$sessions_dir"/*.mind(N); do
           if grep -q "NAME: $target_mind" "$f"; then
              mind_file="$f"
              break
           fi
        done
     fi
  else
     # Auto-pick the only active mind (if only one)
     local minds=("$sessions_dir"/*.mind(N))
     if [[ ${#minds} -eq 1 ]]; then
        mind_file="${minds[1]}"
     fi
  fi

  if [[ -n "$mind_file" ]]; then
     local mind_id=$(basename "$mind_file" .mind)
     echo ">>> Linked to Mind Session: $(grep 'NAME:' "$mind_file" | cut -d' ' -f2)"
     px-broadcast "LINK_ESTABLISHED:$mind_id:$name"
     # Also update the Mind's target file directly for immediate effect
     local mind_pid=$(grep 'PID:' "$mind_file" | awk '{print $2}')
     echo "LINKED:$name" > "$PX_STATE_DIR/.px_target_$mind_id"
  fi

  echo ">>> Ready for linked commands from Input Shell."
}

px-exit() {
  # Close any panes running our Planes
  local panes
  panes=$(tmux list-panes -a -F "#{pane_id} #{pane_current_command} #{pane_start_command}" | grep -E "mode-actions|mode-places|mode-console|ui-fzf" | awk '{print $1}')
  
  for p in ${(f)panes}; do
    tmux kill-pane -t "$p"
  done
  
  # Cleanup stale link for THIS terminal if it was a target
  local links_dir="$PX_STATE_DIR/links"
  local my_pid="$$"
  for f in "$links_dir"/*.pid(N); do
    if [[ "$(cat "$f")" == "$my_pid" ]]; then
       rm -f "$f" "${f%.pid}.meta"
    fi
  done
}

px-router() {
  local signal="$1"
  local payload="$2"

  # Ensure TARGET_PANE is resolved
  if [[ -z "$TARGET_PANE" ]]; then
     TARGET_PANE=$(cat "$PX_TARGET_FILE" 2>/dev/null)
  fi

  case "$signal" in
    PLANE:*)
      local plane="${signal#PLANE:}"
      source "$PX_ZSH_ROOT/core/view-input.zsh"
      case "$plane" in
        actions) view-input --source actions --prompt "Action > " ;;
        places)  view-input --source places --prompt "Place > " ;;
        trace)   view-input --source trace --prompt "Trace > " ;;
        recent)  view-input --source recent --prompt "Recent > " ;;
        settings) view-input --source settings --prompt "Settings > " ;;
        chat)    export PX_STREAM="chat"; view-input --source history --prompt "Chat > " ;;
        shell)   export PX_STREAM="cmd";  view-input --source history --prompt "Shell > " ;;
        chat-native) source "$PX_CORE_DIR/view-chat.zsh"; view-chat ;;
        portal|main) view-input --source menu --prompt "Parallax > " ;;
        custom-dashboard) source "$PX_MODES_DIR/mode-custom-dashboard"; mode-custom-dashboard ;;
        *)
          # Fallback for dynamic/legacy modes
          if [[ -f "$PX_MODES_DIR/mode-$plane" ]]; then
             source "$PX_MODES_DIR/mode-$plane"
             "mode-$plane"
          fi
          ;;
      esac
      return 2
      ;;
    ACTION:sys/alchemy)
      "$HOME/bin/px-alchemy"
      return 2
      ;;
    MODE:*|PLANE_SWITCH:*)
      # Standardize on PLANE signal for all TUI context switches
      local p="${signal#*:}"
      px-router "PLANE:$p"
      return 2
      ;;
    LIST:*)
      local list_id="${signal#LIST:}"
      view-input --source list-items --arg "$list_id" --prompt "$list_id > "
      return 2
      ;;
    UI:*)
      local method="${signal#UI:}"
      export PX_FORCE_UI="$method"
      return 2
      ;;
    PROJECT:*)
      local sub_signal="${signal#PROJECT:}"
      local p_type="${sub_signal%%|*}"
      local p_payload="${sub_signal#*|}"
      [[ "$p_payload" == "$sub_signal" ]] && p_payload="last"
      
      local project_payload="$p_payload"
      if [[ "$p_type" == "reader" || "$p_type" == "editor" ]]; then
        if [[ "$p_payload" =~ '^[0-9]{15,}$' || "$p_payload" == "last" ]]; then
          project_payload=$("$HOME/bin/px-logger" get-content "$p_payload")
        fi
      fi
      "$HOME/bin/px-project" "$p_type" "$project_payload"
      return 2
      ;;
    DISPATCH:*)
      local cmd="${signal#DISPATCH:}"
      if [[ "$cmd" == "clear" ]]; then
         "$HOME/bin/dispatch" "$TARGET_PANE" "clear"
      else
         "$HOME/bin/dispatch" "$TARGET_PANE" "$cmd"
      fi
      return 2
      ;;
    LOCAL:*)
      local cmd="${signal#LOCAL:}"
      eval "$cmd"
      return 2
      ;;
    LINK:*)
      local item="${signal#LINK:}"
      local current=$($HOME/bin/px-context get staged_context)
      $HOME/bin/px-context set staged_context "$current\n$item"
      return 2
      ;;
    CHAT:*)
      local msg="${signal#CHAT:}"
      # Universal Intent Routing via px-prompt
      "$HOME/bin/dispatch" "$TARGET_PANE" "$HOME/bin/px-prompt" "chat" "$msg"
      return 2
      ;;
    TRANSFORM_MENU:*)
      local ids_str="${signal#TRANSFORM_MENU:}"
      local ids=(${(s: :)ids_str})
      local first_id="${ids[1]}"
      
      # Determine type based on the first selected item
      local type=$("$HOME/bin/px-logger" list-stream all | grep "|$first_id|" | awk -F'|' '{print $3}')
      
      local menu=()
      case "$type" in
        cmd) menu+=("Promote to Action (Bundle)|TRANSFORM_EXEC:${ids_str// /:}:action") ;;
        chat) menu+=("Promote to Prompt|TRANSFORM_EXEC:${ids_str// /:}:prompt") ;;
      esac
      menu+=("Export Output to File|TRANSFORM_EXEC:${ids_str// /:}:file")
      
      local transform=$(printf "%s\n" "${menu[@]}" | px-ui-select "Alchemy > ")
      [[ -n "$transform" ]] && px-router "$transform"
      return 2
      ;;
    TRANSFORM_EXEC:*)
      local sub="${signal#TRANSFORM_EXEC:}"
      # Remove the type suffix (:action, :prompt, or :file)
      local ids_colon="${sub%:*}"
      local type="${sub##*:}"
      
      local ids=(${(s:::)ids_colon})
      local result=$("$HOME/bin/px-transform" "${ids[*]}" "$type")
      
      # UI Feedback
      echo ">>> $result"
      sleep 1
      return 2
      ;;
    SIGN:*)
      local sign="${signal#SIGN:}"
      local sign_type="${sign%%:*}"
      local ids="${sign#*:}"

      case "$sign_type" in
        COPY_IN) "$HOME/bin/px-logger" bundle "$ids" input ;;
        COPY_OUT) "$HOME/bin/px-logger" bundle "$ids" output ;;
        COPY_EVIDENCE) "$HOME/bin/px-logger" bundle "$ids" evidence ;;
      esac
      
      # UI Feedback
      echo ">>> Selection Copied to Clipboard."
      sleep 0.5
      return 2
      ;;
    RELOOP)
      return 2
      ;;
    BACK)
      return 0
      ;;
    ID:*)
      local id="${signal#ID:}"
      local payload=$("$HOME/bin/px-logger" get-payload "$id")
      local type=$("$HOME/bin/px-logger" get-type "$id")
      "$HOME/bin/px-intent" "EXECUTE" "${type:u}" "$payload"
      return 2
      ;;
    QUERY\|*|QUERY:*)
      local payload="${signal#QUERY|}"
      # Handle legacy colon separator if present
      [[ "$payload" == "$signal" ]] && payload="${signal#QUERY:}"
      
      "$HOME/bin/px-intent" "QUERY" "QUERY" "$payload"
      return 2
      ;;
    EXECUTE_ID:*)
      local id="${signal#EXECUTE_ID:}"
      local payload=$("$HOME/bin/px-logger" get-payload "$id")
      "$HOME/bin/px-intent" "EXECUTE" "CUSTOM" "$payload"
      return 2
      ;;
    EXECUTE_CMD:*)
      local cmd="${signal#EXECUTE_CMD:}"
      "$HOME/bin/px-intent" "EXECUTE" "CUSTOM" "$cmd"
      return 2
      ;;
    STAGE|*)
      local p="${signal#STAGE|}"
      "$HOME/bin/px-intent" "STAGE" "CUSTOM" "$p"
      return 2
      ;;
    VIEW|*)
      local p="${signal#VIEW|}"
      "$HOME/bin/px-intent" "INSPECT" "CUSTOM" "$p"
      return 2
      ;;
    EDIT|*)
      local p="${signal#EDIT|}"
      "$HOME/bin/px-intent" "MODIFY" "CUSTOM" "$p"
      return 2
      ;;
ACTION:*|PLACE:*|FILE:*|PROMPT:*|AGENT:*|CUSTOM:*|HISTORY:*)
      local type="${signal%%:*}"
      local p="${signal#*:}"
      [[ "$type" == "HISTORY" ]] && type="QUERY"
      "$HOME/bin/px-intent" "$PX_INTENT_MODE" "$type" "$p"
      return 2
      ;;
    EXIT)
      px-exit
      exit 0
      ;;
    SIGNAL|TOGGLE_DASHBOARD)
      # Toggle between normal dashboard and custom dashboard
      # Check if we're currently in custom dashboard mode
      if [[ -f "$PX_STATE_DIR/.dashboard_mode" ]]; then
        local current_mode=$(cat "$PX_STATE_DIR/.dashboard_mode")
        if [[ "$current_mode" == "custom" ]]; then
          # Switch to normal dashboard
          echo "normal" > "$PX_STATE_DIR/.dashboard_mode"
          px-router "PLANE:dashboard"
        else
          # Switch to custom dashboard
          echo "custom" > "$PX_STATE_DIR/.dashboard_mode"
          px-router "PLANE:custom-dashboard"
        fi
      else
        # Default to custom dashboard
        echo "custom" > "$PX_STATE_DIR/.dashboard_mode"
        px-router "PLANE:custom-dashboard"
      fi
      return 2
      ;;
    *)
      # Payload fallthrough (Selection|...)
      # If signal is a Parallax ID (15+ chars), treat as Console selection
      if [[ "$signal" =~ '^[0-9]{15,}$' ]]; then
         # Rerun/Project from history
         local cmd=$("$HOME/bin/px-logger" get-payload "$signal")
         if [[ -n "$cmd" ]]; then
           "$HOME/bin/dispatch" "$TARGET_PANE" "$cmd"
         fi
         return 2
      else
         return 1
      fi
      ;;
    [['$current_mode" == "normal']]
      # If signal is a Parallax ID (15+ chars), treat as Console selection
      if [[ "$signal" =~ '^[0-9]{15,}$' ]]; then
         # Rerun/Project from history
         local cmd=$("$HOME/bin/px-logger" get-payload "$signal")
         if [[ -n "$cmd" ]]; then
           "$HOME/bin/dispatch" "$TARGET_PANE" "$cmd"
         fi
         return 2
      else
         return 1
      fi
      ;;
  esac

}

px-load-keys() {
  # Load Keybinds from Context into Env
  # We do this once per session start to avoid lag on every fzf render
  # Default fallback logic is in ui-fzf, but we can override here if needed
  
  # Optimization: Only call px-context if we suspect custom keys (checking a flag?)
  # For now, let's just attempt to load or default.
  
  # We access the context KV directly for speed if possible, but px-context is the API.
  # Let's rely on defaults in ui-fzf for now, but if the user SETS one, we need to export it.
  
  # Ideally, we read all keys:
  # export PX_KEY_EXEC=$(px-context get key_exec)
  # export PX_KEY_STAGE=$(px-context get key_stage)
  # ...
  
  # For the purpose of this task (User Request), we assume they WILL set them.
  # We implement a bulk read if px-context supports it, otherwise individual.
}

function parallax {
  # 1. IDENTITY & BOOTSTRAP
  local name_arg=""
  local force_native=0
  
  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name) name_arg="$2"; shift 2 ;;
      --target) target_arg="$2"; shift 2 ;;
      --native) force_native=1; shift ;;
      *) session_number="$1"; shift ;;
    esac
  done

  # Resolve Identity (Name)
  if [[ -z "$name_arg" ]]; then
     name_arg=$(basename "$PWD" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
  fi
  export PX_SESSION_NAME="$name_arg"

  # Register in Session Hub
  local sessions_hub="$PX_STATE_DIR/sessions"
  mkdir -p "$sessions_hub"
  export PX_SESSION_ID=$(date +%s%N | cut -b1-15)
  local session_file="$sessions_hub/$PX_SESSION_ID.mind"
  
  cat > "$session_file" <<EOF
NAME: $PX_SESSION_NAME
PID: $$
CWD: $PWD
STARTED: $(date)
EOF

  # Clean up session on exit
  trap "rm -f '$session_file'; px-exit" EXIT

  # 2. ACTIVE HANDSHAKE (Resolve Target)
  local target_id=""
  if [[ $force_native -eq 0 ]]; then
    # Check for linked terminals
    local links_dir="$PX_STATE_DIR/links"
    local active_links=()
    for f in "$links_dir"/*.pid(N); do
      local link_name=$(basename "$f" .pid)
      local link_pid=$(cat "$f")
      if kill -0 "$link_pid" 2>/dev/null; then
         active_links+=("$link_name")
      else
         # Purge stale link
         rm -f "$f" "${f%.pid}.meta"
      fi
    done

    if [[ -n "$target_arg" ]]; then
       target_id="LINKED:$target_arg"
    elif [[ ${#active_links} -eq 1 ]]; then
       target_id="LINKED:${active_links[1]}"
    fi
  fi

  if [[ -n "$target_id" ]]; then
     echo "$target_id" > "$PX_TARGET_FILE"
  fi

  # 2. RESOLVE ACTIONS ROOT (Explicit)
  # Priority: 1. Environment Variable, 2. Preset, 3. Default (~/.actions)
  local actions_root="${PX_ACTIONS_ROOT:-$HOME/.actions}"
  
  if [[ -n "$PRESET_FILE" ]]; then
    local preset_root=$(px-preset get "$PX_SESSION_NUMBER" "actions_root" "")
    if [[ -n "$preset_root" && "$preset_root" != "null" ]]; then
       actions_root="$preset_root"
    fi
  fi
  
  export PX_ACTIONS_ROOT="$actions_root"
  echo "$actions_root" > "$PX_STATE_DIR/.px_actions_root"

  # 9. PERSPECTIVE SELECTION
  if [[ -n "$target_id" ]]; then
     echo ">>> Parallax Mind engaged (Linked to: ${target_id#LINKED:})"
     px-portal
  else
     echo ">>> Parallax Mind engaged (Stand-alone mode)"
     source "$PX_CORE_DIR/view-chat.zsh"
     view-chat
  fi
}

px-link() {
  # Alias for px-target to ensure it runs in current shell
  px-target "$@"
}

px-diagnostic() {
  # Activate the Diagnostic/Genesis Plane
  while true; do
     local items=$("$PX_MODES_DIR/mode-diagnostic")
     local selection=$(echo "$items" | px-ui-select "Genesis > ")
     [[ -z "$selection" ]] && break
     px-router "$selection"
  done
}

px-portal() {
  # The Universal Landing Page.
  # Simply launches the Input View with the 'menu' source.
  source "$PX_ZSH_ROOT/core/view-input.zsh"
  view-input --source menu --prompt "Parallax > "
}

px-hud() {
  local context="${PX_HUD_CONTEXT:-$1}"
  local live_status=$(cat "$PX_STATE_DIR/.hud_msg" 2>/dev/null)
  local indicator="[OFF]"
  [[ -f "$PX_STATE_DIR/.preview_state" ]] && [[ $(cat "$PX_STATE_DIR/.preview_state") == "1" ]] && indicator="[ON]"
  
  local index_msg=""
  if [[ -n "$PX_TERMINAL_INDEX" ]]; then
     index_msg=" (Orbiter: $PX_TERMINAL_INDEX)"
  fi

  local selector=$($HOME/bin/px-context get primary_ui_selector 2>/dev/null || echo "fzf")
  local hud_msg="Optic | $context | Selector: $selector | Intent: $PX_INTENT_MODE | Keys: A:Actions P:Places T:Trace 1-4:Strategy"
  [[ -n "$live_status" ]] && hud_msg="$hud_msg | $live_status"
  
  local term_width=$(tput cols)
  if [[ ${#hud_msg} -gt $term_width ]]; then
      # Truncate to fit terminal width with an ellipsis
      echo "${hud_msg:0:$term_width-3}..."
  else
      echo "$hud_msg"
  fi
}

# Trap Common Typos
Parallax() {
  echo "❌ Error: Case-sensitive universe detected."
  echo "   Please run 'parallax' (lowercase) to engage the function."
  return 127
}
