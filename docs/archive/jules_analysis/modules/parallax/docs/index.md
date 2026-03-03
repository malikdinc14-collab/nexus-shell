# Parallax V3: The Invariant Shell 🛡️🐚

> "Design is the act of stating how reality is allowed to behave."

Parallax V3 is a terminal-native workspace capability system. It adheres to **Invariant-Driven Design**, prioritizing stability, persistence, and deterministic execution over complexity.

## 🌟 Core Philosophy

### 1. The Kernel & The Planes
Parallax is not just a bunch of scripts. It is a **Kernel** (`px-engine`) that projects **Planes** of capability onto your terminal.
- **Planes**: Actions, Agents, Surfaces, Places, Intel, docs.
- **Kernel**: Context-aware, state-preserving, and fast.

### 2. Negative Space Persistence
We do not "save" your state by copying it. We save it by **not destroying it**.
- When you exit the Dashboard, the pane closes, but your shell (Stage) remains.
- The Dashboard allows the Stage to exist in the negative space of its own execution.

### 3. Spatial Interfaces
Tmux is not just a multiplexer; it is a **Surface Manager**.
- Parallax defines "Surfaces" (YAML layouts) that materialize instantly.
- Complex toolchains (e.g., AI Agent + Terminal + Dashboard) become single keystrokes.

## 🚀 Quick Start

```bash
# Launch the Dashboard
parallax

# Navigation
Enter  : Execute Action / Enter Directory
Esc    : Back / Clear Query
Ctrl+D : Directory Navigator (cdr)
Ctrl+N : Notes / Scratchpad
Ctrl+I : Intelligence Registry
Ctrl+W : Save Surface
Ctrl+Y : Toggle Verbosity
?      : Toggle Legend
Settings : Configure Layout (Classic/Reverse)
```

## 📚 Documentation Index

1. [User Guide](user-guide.md) - Mastering the Dashboard.
2. [Architecture](architecture.md) - Under the hood of V3.
3. [Extensions](extensions.md) - create your own Actions & Contexts.
