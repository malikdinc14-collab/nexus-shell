# Nexus Event Bus Design

**Purpose**: Real-time inter-pane communication for reactive workflows  
**Status**: Design Phase

---

## Architecture

### Unix Socket Server
- **Location**: `/tmp/nexus_$USER/$PROJECT/bus.sock`
- **Protocol**: JSON messages over Unix domain socket
- **Concurrency**: Async I/O (Python asyncio)
- **Lifecycle**: Started by station manager, stopped on cleanup

### Message Format

```json
{
  "type": "EVENT_TYPE",
  "source": "pane_id",
  "timestamp": 1706543210.123,
  "data": {
    "key": "value"
  }
}
```

---

## Event Types

### File System Events
```json
{
  "type": "FS_EVENT",
  "source": "editor",
  "data": {
    "action": "file_opened|file_saved|file_closed",
    "path": "/workspace/src/main.py",
    "line": 42
  }
}
```

### Test Events
```json
{
  "type": "TEST_EVENT",
  "source": "terminal",
  "data": {
    "status": "passed|failed|running",
    "test_name": "test_authentication",
    "duration_ms": 1234,
    "output": "..."
  }
}
```

### Editor Events
```json
{
  "type": "EDITOR_EVENT",
  "source": "editor",
  "data": {
    "action": "cursor_moved|selection_changed|buffer_changed",
    "file": "/workspace/src/main.py",
    "line": 42,
    "column": 10
  }
}
```

### AI Events
```json
{
  "type": "AI_EVENT",
  "source": "chat",
  "data": {
    "action": "response_started|response_completed|error",
    "message": "...",
    "tokens": 1234
  }
}
```

### GAP Events
```json
{
  "type": "GAP_EVENT",
  "source": "spec_manager",
  "data": {
    "action": "gate_advanced|gate_blocked|acl_loaded|write_denied|exec_denied",
    "gate": "gate_path",
    "reason": "..."
  }
}
```

### UI Events
```json
{
  "type": "UI_EVENT",
  "source": "pane_wrapper",
  "data": {
    "action": "pane_focused|pane_resized|tool_crashed|tool_restarted",
    "pane_id": "%3",
    "tool": "nvim"
  }
}
```

---

## Subscription Model

### Subscribe to Event Type
```bash
nxs-event subscribe FS_EVENT /path/to/handler.sh
```

Handler receives JSON on stdin:
```bash
#!/bin/bash
# handler.sh
while read -r event; do
    echo "Received: $event"
    # Process event
done
```

### Publish Event
```bash
nxs-event publish FS_EVENT '{"action":"file_saved","path":"main.py"}'
```

### List Subscriptions
```bash
nxs-event list
# Output:
# FS_EVENT: 2 subscribers
#   - /path/to/handler1.sh (pid: 1234)
#   - /path/to/handler2.sh (pid: 5678)
# TEST_EVENT: 1 subscriber
#   - /path/to/test_handler.sh (pid: 9012)
```

---

## Implementation Details

### Server (Python asyncio)

```python
# core/bus/event_server.py
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Set, Callable

class EventBus:
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.subscribers: Dict[str, Set[asyncio.StreamWriter]] = {}
        self.server = None
        
    async def start(self):
        """Start the event bus server"""
        # Remove old socket if exists
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
            
        # Create Unix socket server
        self.server = await asyncio.start_unix_server(
            self.handle_client,
            path=self.socket_path
        )
        
    async def handle_client(self, reader, writer):
        """Handle client connection"""
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                    
                message = json.loads(data.decode())
                
                if message.get("action") == "subscribe":
                    await self.subscribe(message["type"], writer)
                elif message.get("action") == "publish":
                    await self.publish(message)
                    
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            
    async def subscribe(self, event_type: str, writer):
        """Subscribe to event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = set()
        self.subscribers[event_type].add(writer)
        
    async def publish(self, message: dict):
        """Publish event to subscribers"""
        event_type = message.get("type")
        if event_type not in self.subscribers:
            return
            
        # Broadcast to all subscribers
        dead_writers = set()
        for writer in self.subscribers[event_type]:
            try:
                writer.write(json.dumps(message).encode() + b'\n')
                await writer.drain()
            except Exception:
                dead_writers.add(writer)
                
        # Remove dead connections
        self.subscribers[event_type] -= dead_writers
```

### Client (Bash wrapper)

```bash
# core/bus/nxs-event
#!/bin/bash

SOCKET="/tmp/nexus_$(whoami)/$NEXUS_PROJECT/bus.sock"

nxs_event_publish() {
    local type="$1"
    local data="$2"
    
    local message=$(cat <<EOF
{
  "action": "publish",
  "type": "$type",
  "source": "$TMUX_PANE",
  "timestamp": $(date +%s.%N),
  "data": $data
}
EOF
)
    
    echo "$message" | nc -U "$SOCKET"
}

nxs_event_subscribe() {
    local type="$1"
    local handler="$2"
    
    local message=$(cat <<EOF
{
  "action": "subscribe",
  "type": "$type"
}
EOF
)
    
    echo "$message" | nc -U "$SOCKET"
    
    # Read events and pipe to handler
    while read -r event; do
        echo "$event" | "$handler"
    done
}

case "$1" in
    publish) nxs_event_publish "$2" "$3" ;;
    subscribe) nxs_event_subscribe "$2" "$3" ;;
    list) nxs_event_list ;;
    *) echo "Usage: nxs-event {publish|subscribe|list}" ;;
esac
```

---

## Integration Points

### Station Manager
```bash
# core/api/station_manager.sh
nexus_station_init() {
    # ...
    
    # Start event bus
    python3 "$NEXUS_CORE/bus/event_server.py" &
    echo $! > "$STATE_DIR/bus.pid"
}

nexus_station_cleanup() {
    # Stop event bus
    if [[ -f "$STATE_DIR/bus.pid" ]]; then
        kill $(cat "$STATE_DIR/bus.pid")
        rm "$STATE_DIR/bus.pid"
    fi
}
```

### File Watcher Example
```bash
# Example: Watch for file changes
nxs-event subscribe FS_EVENT - <<'EOF'
#!/bin/bash
while read -r event; do
    action=$(echo "$event" | jq -r '.data.action')
    file=$(echo "$event" | jq -r '.data.path')
    
    if [[ "$action" == "file_saved" ]]; then
        echo "File saved: $file"
        # Run tests, linters, etc.
    fi
done
EOF
```

### Editor Integration
```bash
# In nvim config
autocmd BufWritePost * call system('nxs-event publish FS_EVENT ''{"action":"file_saved","path":"' . expand('%:p') . '"}''')
```

---

## Performance Considerations

### Latency Target
- Event delivery: <100ms (p99)
- Typical: <10ms

### Throughput
- Support 100+ events/second
- Support 50+ concurrent subscribers

### Memory
- Keep event history in memory (last 1000 events)
- Circular buffer to prevent unbounded growth

### Error Handling
- Dead subscriber detection
- Automatic cleanup
- Graceful degradation

---

## Testing Strategy

### Unit Tests
- Message serialization/deserialization
- Subscription management
- Event routing

### Integration Tests
- Multi-client communication
- Concurrent publishing
- Subscriber cleanup

### Property Tests
- Event delivery guarantee (at-most-once)
- No message loss under normal conditions
- Subscriber isolation (one crash doesn't affect others)

---

## Future Enhancements

### Event Filtering
```bash
nxs-event subscribe FS_EVENT --filter '.data.path | endswith(".py")'
```

### Event History
```bash
nxs-event history FS_EVENT --last 10
```

### Event Replay
```bash
nxs-event replay --from "2026-01-29 10:00" --to "2026-01-29 11:00"
```

### Remote Events
```bash
nxs-event publish FS_EVENT --remote "user@host"
```

---

**Status**: Design Complete, Ready for Implementation
