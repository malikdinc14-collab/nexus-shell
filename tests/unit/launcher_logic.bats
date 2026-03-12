#!/usr/bin/env bats

setup() {
    export ORIGINAL_NEXUS_HOME="$(cd "$BATS_TEST_DIRNAME/../../" && pwd)"
    export BATS_TMPDIR=$(mktemp -d)

    # Create a mock home specifically for testing
    export NEXUS_HOME="$BATS_TMPDIR/mock_nexus_home"

    # We will copy the actual launcher.sh script to test it, and mock its dependencies there
    mkdir -p "$NEXUS_HOME/core/api"
    mkdir -p "$NEXUS_HOME/core/exec"
    mkdir -p "$NEXUS_HOME/core/layout"
    mkdir -p "$NEXUS_HOME/core/boot"
    mkdir -p "$NEXUS_HOME/core/hud"
    mkdir -p "$NEXUS_HOME/core/services"

    cp "$ORIGINAL_NEXUS_HOME/core/boot/launcher.sh" "$NEXUS_HOME/core/boot/launcher.sh"
    chmod +x "$NEXUS_HOME/core/boot/launcher.sh"

    # The script uses `REAL_PATH="$0"` to resolve `$NEXUS_HOME`. Since it's located at `$NEXUS_HOME/core/boot/launcher.sh`,
    # resolving `../../` from `$NEXUS_HOME/core/boot/` gets it to `$NEXUS_HOME`. Perfect.

    cat > "$NEXUS_HOME/core/api/config_helper.py" << 'INNER_EOF'
print("export NEXUS_COMPOSITION='__saved_session__'")
INNER_EOF
    chmod +x "$NEXUS_HOME/core/api/config_helper.py"

    cat > "$NEXUS_HOME/core/api/station_manager.sh" << 'INNER_EOF'
#!/usr/bin/env bash
echo "mock_station_manager $@" >> "$BATS_TMPDIR/calls.log"
INNER_EOF
    chmod +x "$NEXUS_HOME/core/api/station_manager.sh"

    cat > "$NEXUS_HOME/core/layout/layout_engine.sh" << 'INNER_EOF'
#!/usr/bin/env bash
echo "mock_layout_engine $@" >> "$BATS_TMPDIR/calls.log"
INNER_EOF
    chmod +x "$NEXUS_HOME/core/layout/layout_engine.sh"

    cat > "$NEXUS_HOME/core/services/hud_service.sh" << 'INNER_EOF'
#!/usr/bin/env bash
echo "mock_hud_service $@" >> "$BATS_TMPDIR/calls.log"
INNER_EOF
    chmod +x "$NEXUS_HOME/core/services/hud_service.sh"

    cat > "$NEXUS_HOME/core/boot/theme.sh" << 'INNER_EOF'
#!/usr/bin/env bash
echo "cyberpunk"
INNER_EOF
    chmod +x "$NEXUS_HOME/core/boot/theme.sh"

    cat > "$BATS_TMPDIR/tmux" << 'INNER_EOF'
#!/usr/bin/env bash
if [[ -f "$BATS_TMPDIR/tmux_mode" ]]; then
    MODE=$(cat "$BATS_TMPDIR/tmux_mode")
else
    MODE="default"
fi

if [[ "$1" == "display-message" ]]; then
    if [[ "$MODE" == "recursive" ]]; then
        echo "nexus_recursive_project"
    else
        echo "unknown"
    fi
elif [[ "$1" == "has-session" ]]; then
    if [[ "$MODE" == "station_exists" ]]; then
        bash -c "e\xit 0"
    else
        bash -c "e\xit 1"
    fi
elif [[ "$1" == "list-windows" ]]; then
    if [[ "$MODE" == "station_exists" ]]; then
        echo "0"
        echo "1"
        echo "2"
    else
        bash -c "e\xit 1"
    fi
elif [[ "$1" == "attach-session" ]]; then
    echo "mock_tmux $@" >> "$BATS_TMPDIR/calls.log"
    bash -c "e\xit 0"
else
    echo "mock_tmux $@" >> "$BATS_TMPDIR/calls.log"
fi
INNER_EOF
    sed -i 's/e\\xit/exit/g' "$BATS_TMPDIR/tmux"
    chmod +x "$BATS_TMPDIR/tmux"

    export PATH="$BATS_TMPDIR:$PATH"

    export NEXUS_STATION_ACTIVE=""
    export NEXUS_BOOT_IN_PROGRESS=""
    export TMUX=""

    export PROJECT_NAME="test_project"
    export PROJECT_ROOT="$BATS_TMPDIR/test_project"
    mkdir -p "$PROJECT_ROOT"
}

teardown() {
    rm -rf "$BATS_TMPDIR"
}

@test "launcher fails instantly if NEXUS_STATION_ACTIVE is already set (Identity Guard 1)" {
    export NEXUS_STATION_ACTIVE="1"
    run bash "$NEXUS_HOME/core/boot/launcher.sh" "$PROJECT_ROOT"

    [ "$status" -eq 109 ]
    [[ "$output" == *"[!] ERROR: Station already active in this shell."* ]]
}

@test "launcher fails if recursive nexus session detected (Identity Guard 2)" {
    export TMUX="/tmp/tmux-1000/default,1234,0"
    echo "recursive" > "$BATS_TMPDIR/tmux_mode"
    run bash "$NEXUS_HOME/core/boot/launcher.sh" "$PROJECT_ROOT"

    [ "$status" -eq 110 ]
    [[ "$output" == *"[!] ERROR: Recursive Nexus detected."* ]]
}

@test "launcher boots clean layout 0 when station does not exist" {
    echo "default" > "$BATS_TMPDIR/tmux_mode"
    run timeout 2s bash "$NEXUS_HOME/core/boot/launcher.sh" "$PROJECT_ROOT"

    [ "$status" -eq 0 ]
    grep "mock_tmux .* new-session -d -s nexus_test_project -n workspace_0" "$BATS_TMPDIR/calls.log"
    grep "mock_layout_engine nexus_test_project:0 __saved_session__ nexus_test_project $PROJECT_ROOT" "$BATS_TMPDIR/calls.log"
    grep "mock_tmux attach-session" "$BATS_TMPDIR/calls.log"
}

@test "launcher utilizes Multi-window slotting to find next available slot when station exists" {
    echo "station_exists" > "$BATS_TMPDIR/tmux_mode"
    run timeout 2s bash "$NEXUS_HOME/core/boot/launcher.sh" "$PROJECT_ROOT"

    [ "$status" -eq 0 ]
    [[ "$output" == *"[*] Opening new window slot: 3"* ]]
    grep "mock_tmux new-window -d -t nexus_test_project:3 -n workspace_3" "$BATS_TMPDIR/calls.log"
    grep "mock_layout_engine nexus_test_project:3 __saved_session__ nexus_test_project $PROJECT_ROOT" "$BATS_TMPDIR/calls.log"
}
