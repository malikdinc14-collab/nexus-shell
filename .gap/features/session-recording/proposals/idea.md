# Idea: Session Recording & Replay

## Problem Statement
Terminal sessions are ephemeral. There's no way to capture what happened in a workspace for later review, demos, onboarding, or debugging. Screen recordings are large and lose interactivity.

## Proposed Solution
A recording system that captures terminal I/O with timestamps, enabling lightweight replay at original or accelerated speed. Think `asciinema` but integrated with nexus-shell's multi-pane awareness.

## Key Features
- **Multi-pane recording**: Capture all panes simultaneously, not just one.
- **Lightweight**: Store terminal sequences + timestamps, not pixels.
- **Replay**: `nexus replay <session>` plays back in TextualSurface at original or accelerated speed.
- **Export**: Convert to GIF, SVG, or asciinema format for sharing.
- **Annotations**: Mark key moments during recording for navigation.
- **Auto-record**: Optional always-on recording per workspace (circular buffer).

## Target User
Developers who do demos, onboarding, debugging, or want audit trails of workspace activity.
