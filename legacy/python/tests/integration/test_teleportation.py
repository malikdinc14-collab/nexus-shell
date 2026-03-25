#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import json
import uuid
from pathlib import Path

# Setup paths
NEXUS_HOME = Path("/Users/Shared/Projects/nexus-shell")
TEST_ROOT = Path("/tmp/nexus_test_run")
TEST_SOCKET = "nexus_test_socket"
DAEMON_PY = NEXUS_HOME / "core/services/internal/daemon.py"
STACK_BIN = NEXUS_HOME / "core/kernel/stack/stack"

def run_tmux(args):
    cmd = ["tmux", "-L", TEST_SOCKET]
    return subprocess.check_output(cmd + args).decode().strip()

def setup_env():
    if TEST_ROOT.exists():
        import shutil
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir(parents=True)
    os.environ["PROJECT_ROOT"] = str(TEST_ROOT)
    os.environ["SOCKET_LABEL"] = TEST_SOCKET
    os.environ["NEXUS_HOME"] = str(NEXUS_HOME)

def start_daemon():
    print("[*] Starting Test Daemon...")
    subprocess.Popen([sys.executable, str(DAEMON_PY)], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL,
                     preexec_fn=os.setpgrp)
    time.sleep(1) # Wait for socket

def run_test():
    print("[*] Initializing Test Session...")
    run_tmux(["new-session", "-d", "-s", "test_session", "-n", "main", "-x", "80", "-y", "24", "/bin/zsh"])
    
    # Create two panes
    run_tmux(["split-window", "-h", "-t", "test_session:main"])
    p1 = "%0" # Left
    p2 = "%1" # Right
    
    print(f"[*] Simulating Contamination: Pane {p1} set as 'editor'...")
    # Manually simulate what the old Orchestrator did
    run_tmux(["set-option", "-p", "-t", p1, "@nexus_role", "editor"])
    run_tmux(["set-option", "-p", "-t", p1, "@nexus_stack_id", "editor"])
    
    # Initialize the first stack in the Daemon
    subprocess.run([str(STACK_BIN), "init", "editor"], env={**os.environ, "TMUX_PANE": p1})
    
    print(f"[*] Moving to Pane {p2} (Focused Container)...")
    run_tmux(["select-pane", "-t", p2])
    
    print(f"[*] Operation: 'stack push editor' from {p2}...")
    # This is the moment of failure. 
    # If the bug exists, this will resolve to the stack 'editor' in pane p1 
    # and might shift focus or background p1.
    res = subprocess.run([str(STACK_BIN), "push", "editor", "zsh"], 
                         env={**os.environ, "TMUX_PANE": p2},
                         capture_output=True, text=True)
    
    print(f"[*] Push Result: {res.stdout.strip()}")
    
    # Assertion: Who has focus now?
    current_pane = run_tmux(["display-message", "-p", "#{pane_id}"])
    current_stack = run_tmux(["display-message", "-p", "-t", p2, "#{@nexus_stack_id}"])
    
    print(f"[*] Final Focus: {current_pane}")
    print(f"[*] Pane {p2} Stack ID: {current_stack}")

    if current_pane == p2:
        print("\033[1;32m[PASS] Local Focus Maintained.\033[0m")
    else:
        print("\033[1;31m[FAIL] Teleportation Detected! Focus jumped to " + current_pane + "\033[0m")

    # Cleanup
    run_tmux(["kill-session", "-t", "test_session"])

if __name__ == "__main__":
    setup_env()
    try:
        start_daemon()
        run_test()
    finally:
        # Kill daemon
        subprocess.run(["pkill", "-f", str(DAEMON_PY)])
