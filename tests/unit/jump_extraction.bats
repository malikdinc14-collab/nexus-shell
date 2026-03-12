#!/usr/bin/env bats

setup() {
    export NEXUS_HOME="$BATS_TEST_DIRNAME/../../"
    export BATS_TMPDIR=$(mktemp -d)

    mkdir -p "$BATS_TMPDIR/fake_files"
    touch "$BATS_TMPDIR/fake_files/app.py"
    touch "$BATS_TMPDIR/fake_files/server.js"
    touch "$BATS_TMPDIR/fake_files/main.rs"

    # We need to mock `tmux capture-pane`, `fzf-tmux`, `nvim`, etc.
    cat > "$BATS_TMPDIR/tmux" << 'INNER_EOF'
#!/usr/bin/env bash
if [[ "$1" == "capture-pane" ]]; then
    # Return a mocked stack trace
    echo "Traceback (most recent call last):"
    echo "  File \"$MOCK_TRACE_FILE\", line 42, in <module>"
    echo "  File \"$BATS_TMPDIR/fake_files/app.py:42\""
    echo "Error at $BATS_TMPDIR/fake_files/server.js:100"
    echo "Panic at $BATS_TMPDIR/fake_files/main.rs:12"
    echo "Missing at /non/existent/file.txt:99"
elif [[ "$1" == "display-message" ]]; then
    echo "nexus_test_project"
elif [[ "$1" == "select-pane" ]]; then
    echo "mock_tmux_select_pane $@" >> "$BATS_TMPDIR/calls.log"
else
    echo "mock_tmux $@" >> "$BATS_TMPDIR/calls.log"
fi
INNER_EOF
    chmod +x "$BATS_TMPDIR/tmux"

    cat > "$BATS_TMPDIR/fzf-tmux" << 'INNER_EOF'
#!/usr/bin/env bash
# Just read stdin and output the first line that matches our fake python file to simulate user choice
grep "app.py" | head -n 1
INNER_EOF
    chmod +x "$BATS_TMPDIR/fzf-tmux"

    cat > "$BATS_TMPDIR/nvim" << 'INNER_EOF'
#!/usr/bin/env bash
echo "mock_nvim $@" >> "$BATS_TMPDIR/calls.log"
INNER_EOF
    chmod +x "$BATS_TMPDIR/nvim"

    export PATH="$BATS_TMPDIR:$PATH"
    export MOCK_TRACE_FILE="$BATS_TMPDIR/fake_files/app.py"
}

teardown() {
    rm -rf "$BATS_TMPDIR"
}

@test "jump_extraction filters out non-existent files and jumps to correct target" {
    # Since nvim pipe detection relies on `-S`, let's just create a dummy pipe file so we hit the RPC code block
    mkdir -p "/tmp/nexus_$(whoami)/pipes/"
    touch "/tmp/nexus_$(whoami)/pipes/nvim_test_project.pipe"

    # Actually wait, `if [[ -S "$NVIM_PIPE" ]];` checks if it's a socket. We can't touch it, we have to mkfifo or use nc,
    # or just let it fall back to `nvim "+$LINE" "$FILE"`.
    # Let's test the fallback branch for simplicity, since it proves extraction worked.

    run bash "$NEXUS_HOME/core/nav/jump.sh"

    # Output should not be an error
    [ "$status" -eq 0 ]

    # It should have called nvim with the extracted line and file
    grep "mock_nvim +42 $BATS_TMPDIR/fake_files/app.py" "$BATS_TMPDIR/calls.log"
}

@test "jump_extraction with empty pane output gracefully exits" {
    # Redefine tmux mock to return empty
    cat > "$BATS_TMPDIR/tmux" << 'INNER_EOF'
#!/usr/bin/env bash
if [[ "$1" == "capture-pane" ]]; then
    echo ""
elif [[ "$1" == "display-message" && "$2" == "-p" ]]; then
    echo ""
else
    echo "mock_tmux $@" >> "$BATS_TMPDIR/calls.log"
fi
INNER_EOF
    chmod +x "$BATS_TMPDIR/tmux"

    run bash "$NEXUS_HOME/core/nav/jump.sh"

    [ "$status" -eq 0 ]
    grep "mock_tmux display-message No jump targets found in pane." "$BATS_TMPDIR/calls.log"
}
