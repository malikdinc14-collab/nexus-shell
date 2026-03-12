#!/usr/bin/env bats

setup() {
    export NEXUS_HOME="$BATS_TEST_DIRNAME/../../"
    export BATS_TMPDIR=$(mktemp -d)

    # Mock tmux
    function tmux() {
        echo "mock_tmux $@" >> "$BATS_TMPDIR/tmux_calls.log"
    }
    export -f tmux
}

teardown() {
    rm -rf "$BATS_TMPDIR"
    unset -f tmux
}

@test "load_workspace returns 1 for missing file" {
    run bash "$NEXUS_HOME/core/workspace/workspace_manager.sh" load "$BATS_TMPDIR/nonexistent.json"
    [ "$status" -eq 1 ]
    [[ "$output" == *"[!] Error: Workspace file not found:"* ]]
}

@test "load_workspace correctly extracts and exports roots and name" {
    # Don't mock jq, just create a real json file
    local ws_file="$BATS_TMPDIR/workspace.json"
    echo '{"name": "test-workspace", "roots": ["/root1", "/root2"]}' > "$ws_file"

    run source "$NEXUS_HOME/core/workspace/workspace_manager.sh" load "$ws_file"

    [ "$status" -eq 0 ]
    [[ "$output" == *"[*] Loading Workspace: test-workspace"* ]]
    [[ "$output" == *"[*] Workspace Loaded. Aggregate search enabled for: /root1:/root2"* ]]

    grep "mock_tmux set-environment -g NEXUS_ROOTS /root1:/root2" "$BATS_TMPDIR/tmux_calls.log"
    grep "mock_tmux set-environment -g NEXUS_WORKSPACE_NAME test-workspace" "$BATS_TMPDIR/tmux_calls.log"
}

@test "auto_load_workspace loads .nxs-workspace if present" {
    cd "$BATS_TMPDIR"
    echo '{"name": "auto-workspace", "roots": ["/auto1"]}' > .nxs-workspace

    run source "$NEXUS_HOME/core/workspace/workspace_manager.sh" auto

    [ "$status" -eq 0 ]
    [[ "$output" == *"[*] Loading Workspace: auto-workspace"* ]]

    grep "mock_tmux set-environment -g NEXUS_ROOTS /auto1" "$BATS_TMPDIR/tmux_calls.log"
}
