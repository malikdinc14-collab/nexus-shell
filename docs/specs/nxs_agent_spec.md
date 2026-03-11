# Specification: Agent Configuration & Control Plane (`bin/nxs-agent`)

## 1. Component Overview
`nxs-agent` is the primary master CLI for interacting with the invisible Agent Zero backend. It routes lifecycle commands to the Daemon Manager, provides access to the 50+ configuration settings, and triggers the Ghost Driving observability mode.

## 2. CLI Contract
The Bash script must parse the first argument as a sub-command.

### 2.1. Lifecycle Commands (`start`, `stop`, `restart`, `status`)
*   **start:** Invokes `$NEXUS_HOME/core/services/daemon_manager.sh start agent-zero "cd $NEXUS_HOME/modules/agent-zero && python main.py"`.
*   **stop:** Invokes `$NEXUS_HOME/core/services/daemon_manager.sh stop agent-zero`.
*   **restart:** Executes `stop`, waits 1 second, then `start`.
*   **status:** Parses the output of `$NEXUS_HOME/core/services/daemon_manager.sh list` to check if the string `agent-zero` is present. Outputs a stylized status indicator (Running / Stopped).

### 2.2. Configuration Menu (`config` or `c`)
*   **Behavior:** 
    1. Sets the path to `$NEXUS_HOME/modules/agent-zero/usr/settings.json`.
    2. If the file does not exist, prints an error and exits.
    3. Opens the file using the `$EDITOR` environment variable (add a fallback to `nvim` if `$EDITOR` is unset).
    4. Prints "Agent configuration updated." upon exit.

### 2.3. Ghost Driving / Follow Mode (`follow` or `f`)
*   **Behavior:** 
    1. Checks if `agent-zero` is currently running (via status).
    2. If running, it utilizes a powerful Tmux trick: it temporarily pulls the invisible background pane into the current visual window.
    3. Runs the Tmux command: `tmux join-pane -s "${NEXUS_SESSION}:[services].agent-zero"`
    4. Prints instructions to `stdout` before joining: "Ghost Driving active. To detach and send the agent back to the shadows, type prefix + ! (break-pane)."

## 3. Strict Guardrails
*   Must be a highly crafted, robust POSIX-compliant Bash script.
*   Must dynamically resolve `$NEXUS_HOME` based on the script's physical location (e.g., `DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"` and export `NEXUS_HOME=$DIR`).
*   Must verify `$NEXUS_SESSION` is set.
*   Must source `$NEXUS_HOME/core/boot/theme.sh` if it exists for standardized color variables.
*   Must display a beautiful, stylized help/usage menu if invoked with no arguments, invalid arguments, or `--help`.
