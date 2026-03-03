#!/bin/bash
# install.sh
# Deploys Parallax to ~/.parallax

set -e

SOURCE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="$HOME/.parallax"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║              PARALLAX INSTALLER                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check for Dev Mode
DEV_MODE=false
if [[ "$1" == "--dev" ]]; then
    DEV_MODE=true
    echo "[*] DEV MODE: Symlinking sources instead of copying..."
fi

echo "[1/5] Checking dependencies..."
# Check for required tools
MISSING=""
command -v tmux >/dev/null || MISSING="$MISSING tmux"
command -v fzf >/dev/null || MISSING="$MISSING fzf"
command -v jq >/dev/null || MISSING="$MISSING jq"

if [[ -n "$MISSING" ]]; then
    echo "    Missing required tools:$MISSING"
    echo "    Install with: brew install$MISSING"
    exit 1
fi
echo "    All dependencies found."

echo "[2/5] Deploying Parallax to $TARGET_DIR..."
mkdir -p "$TARGET_DIR"

if [ "$DEV_MODE" = true ]; then
    # SYMLINK MODE (Dev)
    rm -rf "$TARGET_DIR/bin" "$TARGET_DIR/lib" "$TARGET_DIR/content"
    ln -sf "$SOURCE_DIR/bin" "$TARGET_DIR/bin"
    ln -sf "$SOURCE_DIR/lib" "$TARGET_DIR/lib"
    ln -sf "$SOURCE_DIR/content" "$TARGET_DIR/content"
    echo "    Symlinked: bin, lib, content"
else
    # COPY MODE (Standard)
    rm -rf "$TARGET_DIR/bin" "$TARGET_DIR/lib" "$TARGET_DIR/content"
    cp -rf "$SOURCE_DIR/bin" "$TARGET_DIR/bin"
    cp -rf "$SOURCE_DIR/lib" "$TARGET_DIR/lib"
    cp -rf "$SOURCE_DIR/content" "$TARGET_DIR/content"
    echo "    Copied: bin, lib, content"
fi

echo "[3/5] Creating symlinks..."
# Determine bin directory
if [[ -w "/usr/local/bin" ]]; then
    BIN_DIR="/usr/local/bin"
    NEED_SUDO=""
else
    BIN_DIR="$HOME/bin"
    mkdir -p "$BIN_DIR"
    NEED_SUDO=""
fi

# Link main binaries
for cmd in parallax px-link px-exec; do
    $NEED_SUDO ln -sf "$TARGET_DIR/bin/$cmd" "$BIN_DIR/$cmd" 2>/dev/null || \
    sudo ln -sf "$TARGET_DIR/bin/$cmd" "$BIN_DIR/$cmd"
done
echo "    Linked: parallax, px-link, px-exec -> $BIN_DIR"

echo "[4/5] Initializing state directories..."
mkdir -p "$HOME/.parallax/links"
mkdir -p "$HOME/.parallax/sessions"
mkdir -p "$HOME/.parallax/content"/{actions/{system,ui,factory},agents/{personas,systems},docs}
mkdir -p "$HOME/.config/parallax"

# Copy tmux snippet if exists
if [[ -f "$SOURCE_DIR/tmux/tmux.conf.snippet" ]]; then
    mkdir -p "$TARGET_DIR/tmux"
    cp -f "$SOURCE_DIR/tmux/tmux.conf.snippet" "$TARGET_DIR/tmux/"
fi

echo "[5/5] Setting up shell integration..."
# Create shell integration file
SHELL_HOOK="$TARGET_DIR/shell-hook.zsh"
cat > "$SHELL_HOOK" << 'HOOK'
# Parallax Shell Integration
# Source this in your ~/.zshrc

export PARALLAX_HOME="${PARALLAX_HOME:-$HOME/.parallax}"

# Source px-link for session sync (skip if already in Parallax)
if [[ -z "$PX_SESSION_ID" && -f "$PARALLAX_HOME/bin/px-link" ]]; then
    source "$PARALLAX_HOME/bin/px-link"
fi

# Ensure parallax is in PATH
[[ ":$PATH:" != *":$PARALLAX_HOME/bin:"* ]] && export PATH="$PARALLAX_HOME/bin:$PATH"
HOOK

# Add to .zshrc if not present
ZSHRC="$HOME/.zshrc"
if [[ -f "$ZSHRC" ]]; then
    if ! grep -q "parallax/shell-hook.zsh" "$ZSHRC" 2>/dev/null; then
        echo "" >> "$ZSHRC"
        echo "# Parallax" >> "$ZSHRC"
        echo '[[ -f "$HOME/.parallax/shell-hook.zsh" ]] && source "$HOME/.parallax/shell-hook.zsh"' >> "$ZSHRC"
        echo "    Added source line to ~/.zshrc"
    else
        echo "    ~/.zshrc already has Parallax integration"
    fi
else
    echo '[[ -f "$HOME/.parallax/shell-hook.zsh" ]] && source "$HOME/.parallax/shell-hook.zsh"' > "$ZSHRC"
    echo "    Created ~/.zshrc with Parallax integration"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            INSTALLATION COMPLETE!                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "To get started:"
echo "  1. Open a new terminal (or run: source ~/.zshrc)"
echo "  2. Run: parallax"
echo ""
echo "Shell sessions will auto-link via px-link."
echo "Documentation: https://github.com/samir-alsayad/parallax"
echo ""
