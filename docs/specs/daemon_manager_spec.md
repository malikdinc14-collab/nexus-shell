# Specification: Daemon Manager (`core/services/daemon_manager.sh`)

## 1. Component Overview
The Daemon Manager is responsible for orchestrating invisible background processes (Services) within the Nexus Shell environment. It must execute long-running services (like Language Servers, Debug Adapters, and AI Agents) without consuming visible geometric space in the active Tmux layout.

## 2. Architectural Mechanism
*   **Invisible Isolation:** The Daemon Manager must operate within a dedicated, hidden Tmux window named precisely `[services]`.
*   **Lifecycle:** This `[services]` window must be attached to the current `$NEXUS_SESSION`. It should be created silently if it does not exist.
*   **Encapsulation:** Every individual service must run inside its own uniquely named Tmux pane within the `[services]` window.

## 3. CLI Contract
The script must accept the following command-line interface:

### 3.1. Start a Service
`./daemon_manager.sh start <service_id> <command...>`
*   **Behavior:** 
    1. Checks if the `[services]` window exists; creates it detached if not (`tmux new-window -d -n "[services]"`).
    2. Checks if a pane with the title `<service_id>` already exists in the `[services]` window. If it does, outputs an error and exits.
    3. Splits a new detached pane in the `[services]` window (`tmux split-window -d -t $SESSION:[services]`).
    4. Sets the title of the new pane to `<service_id>` (`tmux select-pane -T <service_id>`).
    5. Dispatches the raw `<command...>` to that specific pane using `tmux send-keys`.

### 3.2. Stop a Service
`./daemon_manager.sh stop <service_id>`
*   **Behavior:** Locates the pane named `<service_id>` in the `[services]` window and gracefully terminates its execution using `tmux send-keys -t ... C-c` and then kills the pane (`tmux kill-pane`).

### 3.3. List Services
`./daemon_manager.sh list`
*   **Behavior:** Queries Tmux for all active panes inside the `[services]` window and outputs the list of running `<service_id>` strings to `stdout`.

## 4. Constraints & Guardrails
*   Must be written in pure POSIX-compliant Bash.
*   Must utilize `tmux` natively. It should not rely on OS-level `nohup` or `&` backgrounds, as we want Tmux to maintain process ownership for session cleanup.
*   Must include robust error handling (e.g., verifying `$NEXUS_SESSION` is set).
*   All output should be cleanly formatted, suitable for consumption by other Nexus dispatch scripts.
