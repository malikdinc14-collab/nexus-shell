#!/bin/bash
# core/exec/task_runner.sh — Run project tasks defined in .nexus.yaml
# Tasks are defined in the project's .nexus.yaml file under the tasks: key.
# Usage: task_runner.sh <task_name>

NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
NEXUS_STATE="${NEXUS_STATE:-/tmp/nexus_$(whoami)}"
SESSION_NAME=$(tmux display-message -p '#S' 2>/dev/null)
PROJECT_NAME=${SESSION_NAME#nexus_}
NVIM_PIPE="$NEXUS_STATE/pipes/nvim_${PROJECT_NAME}.pipe"
PROJECT_ROOT=$(tmux display-message -p '#{pane_current_path}' 2>/dev/null || pwd)

TASK_NAME="$1"
NEXUS_YAML="$PROJECT_ROOT/.nexus.yaml"

if [[ -z "$TASK_NAME" ]]; then
    echo "Usage: task_runner.sh <task_name>"
    echo "Available tasks:"
    python3 -c "
import yaml, sys
try:
    data = yaml.safe_load(open('$NEXUS_YAML'))
    tasks = data.get('tasks', {})
    for name, cfg in tasks.items():
        cmd = cfg.get('command', cfg) if isinstance(cfg, dict) else cfg
        print(f'  {name}: {cmd}')
except Exception as e:
    print(f'  Error reading .nexus.yaml: {e}', file=sys.stderr)
" 2>/dev/null
    exit 1
fi

# Parse the task from .nexus.yaml
TASK_CMD=$(python3 -c "
import yaml, json, sys
try:
    data = yaml.safe_load(open('$NEXUS_YAML'))
    tasks = data.get('tasks', {})
    task = tasks.get('$TASK_NAME')
    if task is None:
        print('__NOT_FOUND__')
    elif isinstance(task, str):
        print(task)
    elif isinstance(task, dict):
        print(task.get('command', ''))
    else:
        print('__NOT_FOUND__')
except Exception:
    print('__NOT_FOUND__')
" 2>/dev/null)

if [[ "$TASK_CMD" == "__NOT_FOUND__" || -z "$TASK_CMD" ]]; then
    tmux display-message "Task '$TASK_NAME' not found in .nexus.yaml"
    exit 1
fi

# Parse output mode (terminal or popup)
OUTPUT_MODE=$(python3 -c "
import yaml
try:
    data = yaml.safe_load(open('$NEXUS_YAML'))
    task = data.get('tasks', {}).get('$TASK_NAME', {})
    print(task.get('output', 'terminal') if isinstance(task, dict) else 'terminal')
except: print('terminal')
" 2>/dev/null)

ERROR_LOG="/tmp/nexus_task_${TASK_NAME}_err.log"

case "$OUTPUT_MODE" in
    popup)
        tmux display-popup -E -w 80% -h 80% "cd '$PROJECT_ROOT' && $TASK_CMD 2>'$ERROR_LOG'; echo ''; echo 'Press Enter to close'; read"
        ;;
    *)
        # Run in the terminal pane
        tmux send-keys -t terminal "cd '$PROJECT_ROOT' && $TASK_CMD 2>'$ERROR_LOG'" Enter
        ;;
esac

# Check for quickfix integration
ON_ERROR=$(python3 -c "
import yaml
try:
    data = yaml.safe_load(open('$NEXUS_YAML'))
    task = data.get('tasks', {}).get('$TASK_NAME', {})
    print(task.get('on_error', 'ignore') if isinstance(task, dict) else 'ignore')
except: print('ignore')
" 2>/dev/null)

if [[ "$ON_ERROR" == "quickfix" && -S "$NVIM_PIPE" && -f "$ERROR_LOG" ]]; then
    # Wait a moment for the task to finish, then load errors into quickfix
    sleep 2
    if [[ -s "$ERROR_LOG" ]]; then
        nvim --server "$NVIM_PIPE" --remote-send ":cfile $ERROR_LOG<CR>" 2>/dev/null
    fi
fi
