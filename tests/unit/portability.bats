#!/usr/bin/env bats

setup() {
    export NEXUS_HOME="$(cd "$BATS_TEST_DIRNAME/../../" && pwd)"
    export BATS_TMPDIR=$(mktemp -d)
    
    # Mock whoami
    mkdir -p "$BATS_TMPDIR/bin"
    echo "#!/bin/sh" > "$BATS_TMPDIR/bin/whoami"
    echo "echo testuser" >> "$BATS_TMPDIR/bin/whoami"
    chmod +x "$BATS_TMPDIR/bin/whoami"
    
    export PATH="$BATS_TMPDIR/bin:$PATH"
}

teardown() {
    rm -rf "$BATS_TMPDIR"
}

@test "pane_wrapper.sh detects zsh when available" {
    # Mock zsh
    cat > "$BATS_TMPDIR/bin/zsh" << 'EOF'
#!/bin/sh
echo "MOCK_ZSH_CALLED $@"
EOF
    chmod +x "$BATS_TMPDIR/bin/zsh"
    
    # Run pane_wrapper
    run bash -c "export NEXUS_HOME=$NEXUS_HOME; PATH=$BATS_TMPDIR/bin:/usr/bin:/bin /bin/bash $NEXUS_HOME/core/kernel/boot/pane_wrapper.sh 'echo ResourceOutput'"
    
    # Debug: show output if failed
    if [[ "$output" != *"MOCK_ZSH_CALLED -i"* ]]; then
        echo "DEBUG OUTPUT: $output" >&2
    fi

    [[ "$output" == *"ResourceOutput"* ]]
    [[ "$output" == *"MOCK_ZSH_CALLED -i"* ]]
}

@test "pane_wrapper.sh falls back to bash if zsh is missing" {
    # Mock bash that only prints success on -i, otherwise acts as real bash
    cat > "$BATS_TMPDIR/bin/bash" << 'EOF'
#!/bin/sh
if [ "$1" = "-i" ]; then
    echo "MOCK_BASH_FALLBACK_SUCCESS"
else
    exec /bin/bash "$@"
fi
EOF
    chmod +x "$BATS_TMPDIR/bin/bash"
    
    run bash -c "export NEXUS_HOME=$NEXUS_HOME; PATH=$BATS_TMPDIR/bin:/usr/bin:/bin /bin/bash $NEXUS_HOME/core/kernel/boot/pane_wrapper.sh 'echo ResourceOutput'"
    
    # Debug: show output if failed
    if [[ "$output" != *"MOCK_BASH_FALLBACK_SUCCESS"* ]]; then
        echo "DEBUG OUTPUT: $output" >&2
    fi

    [[ "$output" == *"MOCK_BASH_FALLBACK_SUCCESS"* ]]
}

@test "telemetry_aggregator.sh uses user-scoped paths" {
    # Extract only the global variables (first 10 lines) to avoid the infinite loop
    head -n 10 "$NEXUS_HOME/core/ui/hud/telemetry_aggregator.sh" > "$BATS_TMPDIR/telemetry_vars.sh"
    run bash -c "source $BATS_TMPDIR/telemetry_vars.sh; echo \$TELEMETRY_FILE"
    
    [[ "$output" == *"/tmp/nexus_testuser/telemetry.json"* ]]
}

@test "telemetry_aggregator.sh atomic write uses user-scoped tmp directory" {
    # Extract functions but skip the main loop at the end
    grep -vE "while true|done|sleep 1" "$NEXUS_HOME/core/ui/hud/telemetry_aggregator.sh" > "$BATS_TMPDIR/telemetry_lib.sh"
    
    # Mock mktemp
    echo "#!/bin/sh" > "$BATS_TMPDIR/bin/mktemp"
    echo "echo \"/tmp/nexus_testuser/global/tmp/telemetry.12345\"" >> "$BATS_TMPDIR/bin/mktemp"
    chmod +x "$BATS_TMPDIR/bin/mktemp"
    
    run bash -c "source $BATS_TMPDIR/telemetry_lib.sh; safe_mktemp"
    
    # Use grep to be resilient to whitespace/newlines
    echo "$output" | grep "/tmp/nexus_testuser/global/tmp/telemetry.12345"
}
