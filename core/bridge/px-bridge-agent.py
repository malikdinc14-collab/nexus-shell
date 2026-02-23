import os
import sys

# Add project root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "modules", "parallax"))

import subprocess
import json
import re


def get_env_bool(name, default=False):
    val = os.getenv(name, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# Configuration
AUTO_EXEC = get_env_bool("PX_AGENT_AUTO_EXEC", True)
LIVE_EDIT = os.getenv("PX_AGENT_LIVE_EDIT", "overwrite")  # options: overwrite, diff
TRACE_MODE = os.getenv("PX_AGENT_TRACE_MODE", "clean")  # options: raw, clean

NVIM_PIPE = os.getenv("NEXUS_PIPE")
TERM_PANE = os.getenv("PX_NEXUS_TERMINAL_PANE", "3")


def log_trace(msg, mode="clean"):
    if TRACE_MODE == "raw" or mode == "clean":
        print(f"[{mode.upper()}] {msg}")


def tmux_send(pane, cmd, enter=True):
    log_trace(f"Terminal Command: {cmd}", mode="clean")
    if enter and AUTO_EXEC:
        subprocess.run(["tmux", "send-keys", "-t", pane, cmd, "Enter"])
    else:
        subprocess.run(["tmux", "send-keys", "-t", pane, cmd])


def nvim_edit(file_path, content):
    log_trace(f"Editing: {file_path}", mode="clean")
    if not NVIM_PIPE:
        return

    if LIVE_EDIT == "overwrite":
        # Direct buffer modification via RPC
        # 1. Open file
        subprocess.run(["nvim", "--server", NVIM_PIPE, "--remote", file_path])
        # 2. Replace content (Simplified: writing to disk then reloading for now)
        with open(file_path, "w") as f:
            f.write(content)
        subprocess.run(["nvim", "--server", NVIM_PIPE, "--remote-send", "<Esc>:e!<CR>"])
    else:
        # Diff mode
        tmp_diff = f"/tmp/nexus_diff_{os.path.basename(file_path)}"
        with open(tmp_diff, "w") as f:
            f.write(content)
        subprocess.run(
            [
                "nvim",
                "--server",
                NVIM_PIPE,
                "--remote-send",
                f"<Esc>:vsplit {tmp_diff}<CR>:windo diffthis<CR>",
            ]
        )


def log_task(msg):
    with open("/tmp/px-agent-task.log", "w") as f:
        f.write(msg)


import difflib
from lib.core.workspace import WorkspaceGuard


def generate_diff(path, new_content):
    abs_path = os.path.join(os.getcwd(), path)
    if os.path.exists(abs_path):
        with open(abs_path, "r") as f:
            old_content = f.read()
    else:
        old_content = ""

    diff = difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=path,
        tofile=path,
    )
    return "".join(diff)


def main():
    if len(sys.argv) < 2:
        return
    query = sys.argv[1]
    log_trace(f"Query: {query}", mode="clean")
    log_task(f"🎯 TASK: {query}")

    guard = WorkspaceGuard(os.getcwd())

    # Call local expert (Qwen-30B on Port 8080)
    try:
        EXPERT_URL = "http://localhost:8080/v1"
        import requests

        log_trace("Thinking...", mode="clean")
        log_task(f"🎯 TASK: {query}\n🧠 STATUS: Thinking...")
        response = requests.post(
            f"{EXPERT_URL}/chat/completions",
            json={
                "messages": [{"role": "user", "content": query}],
                "model": "default",
                "temperature": 0.2,
            },
            timeout=300,
        )

        result = response.json()["choices"][0]["message"]["content"]
        log_trace("Response received.", mode="clean")

        # 1. Parse Shell Blocks
        sh_blocks = re.findall(r"```(?:sh|bash)\n(.*?)\n```", result, re.DOTALL)
        for block in sh_blocks:
            # We still allow immediate shell execution if configured,
            # but maybe we should stage these too?
            # For now, keeping as is but respecting PX_AGENT_AUTO_EXEC
            tmux_send(TERM_PANE, block.strip())

        # 2. Parse Code/Write Blocks and STAGE them
        code_blocks = re.findall(r"```(\w+):([^\n]+)\n(.*?)\n```", result, re.DOTALL)
        staged_changes = []
        for lang, path, content in code_blocks:
            diff = generate_diff(path.strip(), content)
            if diff:
                staged_changes.append({"path": path.strip(), "diff": diff})

        if staged_changes:
            log_trace(f"Staging {len(staged_changes)} changes...", mode="clean")
            tid = guard.stage_patch(query, staged_changes)
            log_trace(f"Transaction staged: {tid}", mode="clean")

        # 3. Simple text output to Trace
        clean_text = re.sub(r"```.*?```", "", result, flags=re.DOTALL).strip()
        if clean_text:
            log_trace(f"Agent Voice: {clean_text}")

        log_task(f"🎯 TASK: {query}\n✅ STATUS: Done.")

    except Exception as e:
        log_trace(f"Error in bridge: {e}", mode="clean")
        log_task(f"🎯 TASK: {query}\n❌ STATUS: Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)
    main()
