#!/usr/bin/env bats

setup() {
    export ORIGINAL_NEXUS_HOME="$(cd "$BATS_TEST_DIRNAME/../../" && pwd)"
    export BATS_TMPDIR=$(mktemp -d)

    # Create a mock home specifically for testing
    export NEXUS_HOME="$BATS_TMPDIR/mock_nexus_home"

    mkdir -p "$NEXUS_HOME/core/env"
    mkdir -p "$NEXUS_HOME/core/boot"
    mkdir -p "$NEXUS_HOME/config/profiles"

    # Copy the script to test it locally
    cp "$ORIGINAL_NEXUS_HOME/core/env/profile_loader.sh" "$NEXUS_HOME/core/env/profile_loader.sh"
    chmod +x "$NEXUS_HOME/core/env/profile_loader.sh"

    # Mock theme.sh at the mocked NEXUS_HOME
    cat > "$NEXUS_HOME/core/boot/theme.sh" << 'INNER_EOF'
#!/usr/bin/env bash
echo "mock_theme_sh $@" >> "$BATS_TMPDIR/calls.log"
INNER_EOF
    chmod +x "$NEXUS_HOME/core/boot/theme.sh"

    # Mock nexus-switch-layout via PATH
    cat > "$BATS_TMPDIR/nexus-switch-layout" << 'INNER_EOF'
#!/usr/bin/env bash
echo "mock_nexus_switch_layout $@" >> "$BATS_TMPDIR/calls.log"
INNER_EOF
    chmod +x "$BATS_TMPDIR/nexus-switch-layout"

    cat > "$BATS_TMPDIR/yq" << 'INNER_EOF'
#!/usr/bin/env bash
if [[ "$1" == "-r" ]]; then
    filter="$2"
else
    filter="$1"
fi

if [[ "$filter" == *".theme // empty"* ]]; then
    echo "cyberpunk"
elif [[ "$filter" == *".composition // empty"* ]]; then
    echo "dev-layout"
elif [[ "$filter" == *".env // empty"* ]]; then
    echo 'export TEST_VAR="test_value"'
    echo 'export SECOND_VAR="second_value"'
fi
INNER_EOF
    chmod +x "$BATS_TMPDIR/yq"

    export PATH="$BATS_TMPDIR:$PATH"
}

teardown() {
    rm -rf "$BATS_TMPDIR"
}

@test "load_profile returns 1 for missing file" {
    run bash "$NEXUS_HOME/core/env/profile_loader.sh" load "nonexistent_profile"
    [ "$status" -eq 1 ]
    [[ "$output" == *"[!] Error: Profile not found: nonexistent_profile"* ]]
}

@test "load_profile correctly applies theme, composition, and env vars" {
    local profile_file="$NEXUS_HOME/config/profiles/test_profile.yaml"

    cat > "$profile_file" << 'INNER_EOF'
theme: cyberpunk
composition: dev-layout
env:
  TEST_VAR: test_value
  SECOND_VAR: second_value
INNER_EOF

    run bash -c "export PATH=\"$PATH\" && source \"$NEXUS_HOME/core/env/profile_loader.sh\" load test_profile && echo \"TEST_VAR=\$TEST_VAR\" && echo \"NEXUS_PROFILE=\$NEXUS_PROFILE\""

    [ "$status" -eq 0 ]
    [[ "$output" == *"[*] Activating Profile: test_profile"* ]]
    [[ "$output" == *"TEST_VAR=test_value"* ]]
    [[ "$output" == *"NEXUS_PROFILE=test_profile"* ]]

    grep "mock_theme_sh apply cyberpunk" "$BATS_TMPDIR/calls.log"
    grep "mock_nexus_switch_layout dev-layout" "$BATS_TMPDIR/calls.log"
}
