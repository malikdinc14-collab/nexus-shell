view-chat() {
  local prompt_text="Chat > "
  local input_buffer=""
  
  # Load Parallax history into local shell history for this session
  # This allows Up/Down arrows and Ctrl-R to work in vared
  local hist_items=$("$HOME/bin/px-logger" list-stream "chat" | cut -d'|' -f5)
  local hist_cmd_items=$("$HOME/bin/px-logger" list-stream "cmd" | cut -d'|' -f5)
  
  # Inject into current shell history (reverse order to keep most recent at bottom)
  # But list-stream is already chronological, so we just print them.
  while read -r line; do
    [[ -n "$line" ]] && print -s "$line"
  done <<< "$hist_items"$'\n'"$hist_cmd_items"

  # Check link status at start
  local initial_target=$(cat "$PX_TARGET_FILE" 2>/dev/null)
  export TARGET_PANE="LOCAL"

  while true; do
    # 1. Active Link Handshake (Hot-Swap Check)
    # Only auto-swap if we started WITHOUT a link and one appeared.
    local current_target=$(cat "$PX_TARGET_FILE" 2>/dev/null)
    if [[ -z "$initial_target" && -n "$current_target" ]]; then
       # A Body has linked to us! 
       echo ">>> Link established with ${current_target#LINKED:}. Switching to Mission Control..."
       sleep 1
       px-portal
       return 0
    fi

    # 2. Native Prompt (using vared)
    vared -p "$prompt_text" -c input_buffer
    
    [[ -z "$input_buffer" ]] && continue
    [[ "$input_buffer" == "exit" ]] && break
    
    # Manual return to portal
    if [[ "$input_buffer" == "!portal" || "$input_buffer" == "!p" ]]; then
       px-portal
       return 0
    fi

    # 3. Resolve Intent & Stream
    local signal=""
    local stream="chat"
    if [[ "$input_buffer" == "/"* ]]; then
       signal="ACTION:${input_buffer#\/}"
       stream="cmd"
    elif [[ "$input_buffer" == "!"* ]]; then
       signal="CUSTOM:${input_buffer#!}"
       stream="cmd"
    else
       signal="QUERY:$input_buffer"
       stream="chat"
    fi

    # 4. Persistence (Log before execution)
    export PX_STREAM="$stream"
    "$HOME/bin/px-logger" log "$stream" "USER" "$input_buffer"

    # 5. Route to Brain (Local Execution)
    px-router "$signal" | "$HOME/bin/px-lens"
    
    # Reset buffer
    input_buffer=""
    echo ""
  done
}
