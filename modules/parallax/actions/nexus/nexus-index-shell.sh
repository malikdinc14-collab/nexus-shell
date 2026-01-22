#!/bin/bash
# IDENTITY: [SOVEREIGN.USER]
# PROJECT:  NEXUS CORE
# ACTION:   INDEX SHELL & PARALLAX

echo "[*] Absorbing Nexus-Shell and Parallax codebases..."

/Users/Shared/letta-backend/.venv/bin/python3 /Users/compute/workspace/scripts/nexus_fast_index.py ShellArchitect /Users/compute/Projects/personal/nexus-shell
/Users/Shared/letta-backend/.venv/bin/python3 /Users/compute/workspace/scripts/nexus_fast_index.py ShellArchitect /Users/Shared/opensource/parallax

echo "[✅] Shell Knowledge Absorbed."
