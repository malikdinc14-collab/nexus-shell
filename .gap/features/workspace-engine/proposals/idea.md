# Idea: Multi-Folder Workspace Engine

## Problem Statement
Nexus Shell currently operates on a "Single Directory" paradigm. While we have multiple windows (Slots 1-10), they all default to the root of the session. This prevents true "Monolith-level" development where multiple microservices or repositories are indexed and searchable as a single logical project.

## Proposed Solution
Introduce the `.nxs-workspace` JSON specification. This file will allow a user to define a collection of "Project Roots". Nexus will then orchestrate background services (LSP, Search, Git) to treat these routes as a union.

## Key Features
- **Project Aggregation**: Load `A/`, `B/`, and `C/` into one session.
- **Unified Search**: `Alt-F` (ripgrep) and `Alt-f` (fd) will automatically iterate through all roots.
- **Context Persistence**: The workspace file saves which files were open and which tools were running *per root*.
- **Sync status**: Track branches across all repositories in the workspace at once.

## Target User
The "Nexus Architect" managing multi-repo ecosystems (like the Sovereign Machine).
