# core/ui/hud/modules/burn.sh
# HUD Provider for Model-Server burn rate.

TARGET=$1

# Poll the Gateway
status=$(curl -s --max-time 0.5 http://localhost:8080/status)

if [[ -n "$status" && "$status" != "null" ]]; then
    # Filter by Group or Slot if requested
    query='[.slots[]'
    if [[ -n "$TARGET" ]]; then
        if [[ "$TARGET" == slot-* ]]; then
            query+=" | select(.slot_id == \"$TARGET\")"
        else
            query+=" | select(.group_id == \"$TARGET\")"
        fi
    fi
    query+=']'

    # Total Cost & Tokens via jq
    metrics=$(echo "$status" | jq -r "
        $query as \$subset |
        ([\$subset[].cost_usd] | add // 0) as \$cost |
        ([\$subset[] | .input_tokens + .output_tokens] | add // 0) as \$tokens |
        {cost: \$cost, tokens: \$tokens}
    ")

    cost=$(echo "$metrics" | jq -r '.cost')
    tokens=$(echo "$metrics" | jq -r '.tokens')

    # Format Tokens
    if (( tokens >= 1000000 )); then
        token_fmt=$(printf "%.1fM" $(echo "$tokens / 1000000" | bc -l 2>/dev/null || echo "0"))
    elif (( tokens >= 1000 )); then
        token_fmt=$(printf "%.1fK" $(echo "$tokens / 1000" | bc -l 2>/dev/null || echo "0"))
    else
        token_fmt="$tokens"
    fi

    # Determine Color & Icon
    color="CYAN"
    icon="🪙"
    # Basic bash float comparison
    if (( $(echo "$cost > 1.0" | awk '{print ($1 > $2)}' 2>/dev/null || echo 0) )); then 
        color="ORANGE"
        icon="🔥"
    fi
    if (( $(echo "$cost > 5.0" | awk '{print ($1 > $2)}' 2>/dev/null || echo 0) )); then 
        color="RED"
        icon="🚨"
    fi
    
    label=$(printf "%s $%0.2f (%s)" "$icon" $cost $token_fmt)
    echo "{\"label\": \"$label\", \"color\": \"$color\"}"
else
    # Server offline or no slots
    exit 0
fi
