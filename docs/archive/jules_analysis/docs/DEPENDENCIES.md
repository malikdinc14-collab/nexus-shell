# Project Dependencies: Nexus Intelligence Stack

This document tracks all external binaries and libraries required for the Parallax/Nexus local intelligence system.

## 1. Intelligence Runtimes
- **MLX LM**: Python library for native Apple Silicon inference.
- **Ollama**: (Optional) For GGUF model management.
- **Letta**: Python-based memory OS service.

## 2. Binaries (Stored in `~/.nexus-shell/bin/`)
- **mactop**: Apple Silicon hardware monitor (v0.2.7 installed).
- **mmdc (mermaid-cli)**: For rendering Mermaid diagrams (Planned).
- **imgcat**: iTerm2 inline image display protocol (Planned).

## 3. Python Virtual Environments
- **Location**: `~/.parallax/venvs/intel`
- **Packages**:
    - `letta`
    - `mlx_lm`
    - `jq` (for JSON processing)
    - `langchain` (for RLM orchestration)
    - `requests` (for model API communication)
    - `openai` (for standard LLM API)

## 4. Terminal Environment
- **iTerm2**: Required for rich-media rendering features.
- **Tmux**: Required for Nexus-Shell multi-pane layout.

## 5. Development Tools
- **Neovim**: Primary IDE with Nexus integration.
- **Yazi**: File navigator.
- **Glow**: Markdown renderer (to be wrapped by `nexus-view`).
