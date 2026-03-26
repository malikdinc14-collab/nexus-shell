# Idea: Notification System

## Problem Statement
Nexus-shell has no way to notify users of important events outside the terminal — build failures, model errors, budget exhaustion, or long-running task completion are invisible unless the user is watching.

## Proposed Solution
A notification module that routes nexus events to platform-native notifications (macOS Notification Center, Linux libnotify), with urgency levels, sound options, and configurable filters.

## Key Features
- **Platform-native**: macOS (`osascript`/`terminal-notifier`), Linux (`notify-send`).
- **Urgency levels**: Info, warning, critical. Critical = sticky notification + sound.
- **Configurable filters**: Subscribe to specific event patterns (e.g., only `ai.budget.*` and `test.fail`).
- **HUD integration**: Notifications also appear in the Status HUD briefly.
- **Do-not-disturb**: Respects system DND settings. Focus profile suppresses non-critical.

## Target User
Any user who multitasks between nexus-shell and other applications.
