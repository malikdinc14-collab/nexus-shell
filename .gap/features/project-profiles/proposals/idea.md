# Idea: Project Profiles (Role-Based Environments)

## Problem Statement
Nexus Shell is used for many roles: SRE, AI Swarm Orchestration, Learning (Ascent), and pure Software Engineering. Switching between these currently requires manual composition loading and configuration adjustment.

## Proposed Solution
Introduce `profiles`—high-level environment presets that bundle themes, keybinds, composition layouts, and active daemon sets.

## Key Features
- **Switching**: `:profile <name>` (e.g., `:profile focus` or `:profile swarm`).
- **Persistence**: Profiles can be defined globally or project-locally.
- **Service Gating**: The "Focus" profile might kill all AI daemons to save CPU/Focus, while "Swarm" spins them up.
- **Visual Distinction**: Each profile can have its own theme preset.
