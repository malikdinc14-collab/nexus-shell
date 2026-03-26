# Idea: LSP Integration (Code Intelligence)

## Problem Statement
Nexus-shell hosts editor panes but has no code intelligence. Users get no diagnostics, no go-to-definition, no completions — they must rely entirely on their editor's built-in LSP support, which doesn't benefit from nexus-shell's workspace context.

## Proposed Solution
Two-tier LSP support owned entirely by nexus-shell:

1. **Classical LSP hosting**: Auto-detect and spawn standard language servers (pyright, rust-analyzer, clangd) based on pack configuration. Render diagnostics, completions, and hover info in TextualSurface panes.

2. **AI LSP bridge**: A nexus-shell module that acts as an LSP server, routing completion requests to model-server (`localhost:8080`) for AI-powered suggestions with full workspace context.

## Key Features
- **LSP client framework**: Core client managing language server lifecycle per workspace.
- **Pack-driven config**: Each pack declares its preferred LSP server and settings.
- **Diagnostics rendering**: Inline error/warning indicators in TextualSurface.
- **Go-to-definition**: `Alt+d` jumps to symbol definition across workspace files.
- **Hover information**: Type info and docstrings on keybind.
- **Completion popups**: Autocomplete suggestions in TextualSurface editor panes.
- **AI bridge**: LSP server routing to model-server, with workspace context injection.

## Ownership Model
- **Nexus-shell** owns the LSP client, rendering, and AI bridge.
- **Model-server** is just an inference pipe — serves completions via existing API.
- **The bridge** lives as a nexus-shell module, translating LSP protocol to REST calls.

## Target User
Developers who want IDE-level code intelligence within their nexus-shell workspace.
