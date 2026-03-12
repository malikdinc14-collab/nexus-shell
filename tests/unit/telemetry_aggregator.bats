#!/usr/bin/env bats

setup() {
    export NEXUS_HOME="$BATS_TEST_DIRNAME/../../"
    export BATS_TMPDIR=$(mktemp -d)

    cat > "$BATS_TMPDIR/jq" << 'INNER_EOF'
#!/usr/bin/env bash
# Record arguments properly
echo "mock_jq $@" >> "$BATS_TMPDIR/calls.log"

if [[ "$1" == *"-r"* && "$2" == *".level"* ]]; then
    echo "5"
else
    echo "{}"
fi
INNER_EOF
    chmod +x "$BATS_TMPDIR/jq"

    cat > "$BATS_TMPDIR/git" << 'INNER_EOF'
#!/usr/bin/env bash
if [[ "$1" == "rev-parse" && "$2" == "--is-inside-work-tree" ]]; then
    cat /dev/null
elif [[ "$1" == "rev-parse" && "$2" == "--abbrev-ref" && "$3" == "HEAD" ]]; then
    echo "feature/test-branch"
else
    echo "mock_git $@" >> "$BATS_TMPDIR/calls.log"
fi
INNER_EOF
    chmod +x "$BATS_TMPDIR/git"

    # Redefining sleep to just exit the while true loop gracefully by killing the specific subshell
    cat > "$BATS_TMPDIR/sleep" << 'INNER_EOF'
#!/usr/bin/env bash
# Just exit the entire bash script with status 0
kill -9 $PPID
INNER_EOF
    chmod +x "$BATS_TMPDIR/sleep"

    cat > "$BATS_TMPDIR/mv" << 'INNER_EOF'
#!/usr/bin/env bash
echo "mock_mv $@" >> "$BATS_TMPDIR/calls.log"
# atomic write stub: no actual move to prevent errors when jq outputs "{}" on our mock
touch "$2"
INNER_EOF
    chmod +x "$BATS_TMPDIR/mv"

    export PATH="$BATS_TMPDIR:$PATH"

    export NEXUS_WORKSPACE_NAME="mock_workspace"
    export NEXUS_PROFILE="mock_profile"

    rm -f /tmp/nexus_telemetry.json
}

teardown() {
    rm -rf "$BATS_TMPDIR"
    rm -f /tmp/nexus_telemetry.json
}

@test "telemetry_aggregator initializes file and performs atomic writes" {
    timeout 2s bash "$NEXUS_HOME/core/hud/telemetry_aggregator.sh" || true

    [ -f /tmp/nexus_telemetry.json ]

    grep "mock_jq .env.workspace = \"mock_workspace\" /tmp/nexus_telemetry.json" "$BATS_TMPDIR/calls.log"
    grep "mock_mv " "$BATS_TMPDIR/calls.log" | grep "/tmp/nexus_telemetry.json"
}

@test "telemetry_aggregator correctly detects Learner Level and Git Branch" {
    mkdir -p "/tmp/nexus_$(whoami)/ascent"
    echo '{"level": "5"}' > "/tmp/nexus_$(whoami)/ascent/progress.json"

    timeout 2s bash "$NEXUS_HOME/core/hud/telemetry_aggregator.sh" || true

    grep "mock_jq .env.level = \"5\" /tmp/nexus_telemetry.json" "$BATS_TMPDIR/calls.log"
    grep "mock_jq .env.git_branch = \"feature/test-branch\" /tmp/nexus_telemetry.json" "$BATS_TMPDIR/calls.log"
}
