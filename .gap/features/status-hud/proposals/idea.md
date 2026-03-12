# Idea: The Status HUD (The Cockpit)

## Problem Statement
AI agents and background sync processes are invisible. Users must "context switch" or look at logs to see if a build passed or if an agent is thinking.

## Proposed Solution
A persistent, 1-line "Status HUD" at the bottom of the terminal that provides subliminal awareness of the entire environment state.

## Key Features
- **Agent Pulse**: Reasoning/Acting/Error states represented by color-coded breathing animations.
- **Environment Telemetry**: Active workspace, branch, and locality (M1 vs M4).
- **Physical Isolation**: Rendered via a dedicated, pinned Tmux window to ensure it never gets buried by editor splits.
- **Lightweight**: Updates via a simple JSON telemetry file to minimize overhead.
