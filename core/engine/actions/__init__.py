#!/usr/bin/env python3
"""
Nexus Action Layer
==================
Surface-agnostic actions that compose adapter calls.

This is the ONLY layer that shell scripts and keybinds should call.
Actions express INTENT ("open file in editor", "focus editor pane").
Adapters express HOW (tmux select-pane, nvim --server, etc.).

Architecture:
  Layer 1: Shell entry points (keybinds, bin/ scripts) — thin, call Python
  Layer 2: Actions (this module) — intent, composes adapters
  Layer 3: Adapters (capabilities/adapters/) — surface-specific execution
  Layer 4: Surface (tmux, native app, tiling WM)

INVARIANT: No code outside Layer 3 may call tmux, nvim --server, or any
other surface-specific command directly.
"""
