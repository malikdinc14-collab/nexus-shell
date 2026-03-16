#!/bin/bash

# --- Nexus-Shell Installer ---
# A VSCode-style terminal IDE built on TMUX
# Requires: Parallax (https://github.com/samir-alsayad/parallax)

set -e

NEXUS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_HOME="$HOME"
USER_NAME="$(whoami)"
CONFIG_DIR="$USER_HOME/.config/nexus-shell"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║            NEXUS-SHELL INSTALLER                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# === Step 0: Check dependencies ===
echo "[0/6] Checking dependencies..."

# Initialize submodules if present
if [[ -d "$NEXUS_HOME/.git" ]]; then
    echo "    Initializing submodules..."
    git -C "$NEXUS_HOME" submodule update --init --recursive
fi

# Install/Update Parallax from submodule
if [[ -d "$NEXUS_HOME/modules/parallax" ]]; then
    echo "    Updating Parallax components..."
    (cd "$NEXUS_HOME/modules/parallax" && ./install.sh --dev)
else
    if ! command -v parallax &>/dev/null && [[ ! -f "$HOME/.parallax/bin/parallax" ]]; then
        echo ""
        echo "    ERROR: Parallax is required but not installed."
        echo ""
        echo "    Install Parallax first:"
        echo "      git clone https://github.com/samir-alsayad/parallax.git"
        echo "      cd parallax && ./install.sh"
        echo ""
        exit 1
    fi
fi
echo "    Parallax: OK"

# Check for tmux
if ! command -v tmux &>/dev/null; then
    echo "    ERROR: tmux is required. Install with: brew install tmux"
    exit 1
fi
echo "    tmux: OK"

# Check for fzf
if ! command -v fzf &>/dev/null; then
    echo "    ERROR: fzf is required. Install with: brew install fzf"
    exit 1
fi
echo "    fzf: OK"

# === Step 1: Ask about tool installation ===
echo ""
echo "[1/6] Tool configuration..."
echo ""
echo "    Nexus-Shell can work with:"
echo "      - Tools downloaded to ~/.nexus-shell/bin/ (isolated)"
echo "      - System tools from your PATH (nvim, yazi, glow, gum)"
echo ""

DOWNLOAD_TOOLS="n"
if [[ "$1" != "--system" ]]; then
    read -p "    Download tools? (nvim, yazi, glow, gum, opencode, micro, lazygit) [y/N]: " DOWNLOAD_TOOLS
fi

# Create config directory
mkdir -p "$CONFIG_DIR"

# === Step 2: Download or check tools ===
echo ""
echo "[2/6] Setting up tools..."

NEXUS_BIN="$USER_HOME/.nexus-shell/bin"
mkdir -p "$NEXUS_BIN"

if [[ "$DOWNLOAD_TOOLS" =~ ^[Yy]$ ]]; then
    echo "    Installing modules..."

    # Detect architecture (Exported for modules to use)
    export ARCH=$(uname -m)
    export OS=$(uname -s)
    
    # Generic Module Installer Logic
    MODULES_DIR="$NEXUS_HOME/modules"
    
    # Loop through local modules (excluding parallax which is special)
    for mod_dir in "$MODULES_DIR"/*; do
        mod_name=$(basename "$mod_dir")
        
        # Skip parallax submodule as it's handled separately
        [[ "$mod_name" == "parallax" ]] && continue
        [[ "$mod_name" =~ template_* ]] && continue
        
        if [[ -f "$mod_dir/install.sh" ]]; then
            echo "    [$mod_name] Installing..."
            # Execute module installer
            (cd "$mod_dir" && ./install.sh "$NEXUS_BIN" "$OS" "$ARCH")
        fi
    done
    
    chmod +x "$NEXUS_BIN"/* 2>/dev/null || true
    echo "    Modules installed to $NEXUS_BIN"

    
    # Copy tool configs for isolated mode
    TOOL_CONFIGS="$CONFIG_DIR/tool-configs"
    mkdir -p "$TOOL_CONFIGS"
    cp -r "$NEXUS_HOME/config/nvim" "$TOOL_CONFIGS/"
    cp -r "$NEXUS_HOME/config/yazi" "$TOOL_CONFIGS/"
    echo "    Tool configs installed to $TOOL_CONFIGS"
    
    # Detect default chat tool
    DETECTED_CHAT=""
    command -v opencode &>/dev/null && DETECTED_CHAT="opencode"
    [[ -z "$DETECTED_CHAT" ]] && command -v aider &>/dev/null && DETECTED_CHAT="aider"

    # Merge with existing tools.conf if it exists
    EXISTING_CONF="$CONFIG_DIR/tools.conf"
    if [[ -f "$EXISTING_CONF" ]]; then
        echo "    Updating existing tools.conf..."
        # Use a temporary file to build the new config
        TMP_CONF="$EXISTING_CONF.tmp"
        
        # Helper to get value from config
        get_conf_val() {
            grep "^$1=" "$EXISTING_CONF" | cut -d'=' -f2- | tr -d '"' | tr -d "'"
        }

        # Determine values (Priority: Isolated > Existing > Default)
        
        # Helper: Check isolated binary
        get_isolated_or_conf() {
            local tool_name="$1"
            local conf_key="$2"
            local conf_val=$(get_conf_val "$conf_key")
            
            if [[ -x "$NEXUS_BIN/$tool_name" ]]; then
                echo "$NEXUS_BIN/$tool_name"
            else
                echo "$conf_val"
            fi
        }

        VAL_EDITOR=$(get_isolated_or_conf "nvim" "NEXUS_EDITOR")
        [[ -z "$VAL_EDITOR" ]] && VAL_EDITOR="nvim"
        
        VAL_FILES=$(get_isolated_or_conf "yazi" "NEXUS_FILES")
        [[ -z "$VAL_FILES" ]] && VAL_FILES="yazi"
        
        VAL_RENDER=$(get_isolated_or_conf "glow" "NEXUS_RENDER")
        [[ -z "$VAL_RENDER" ]] && VAL_RENDER="glow"
        
        VAL_GUM=$(get_isolated_or_conf "gum" "NEXUS_GUM")
        [[ -z "$VAL_GUM" ]] && VAL_GUM="gum"
        
        VAL_GIT=$(get_isolated_or_conf "lazygit" "NEXUS_GIT")
        [[ -z "$VAL_GIT" ]] && VAL_GIT="lazygit"
        
        VAL_CHAT=$(get_conf_val "NEXUS_CHAT")
        [[ -z "$VAL_CHAT" ]] && VAL_CHAT="$DETECTED_CHAT"
        
        VAL_PX_UI=$(get_conf_val "NEXUS_PX_UI")
        [[ -z "$VAL_PX_UI" ]] && VAL_PX_UI="tmux"

        # Write new config
        cat > "$EXISTING_CONF" << EOF
# Nexus-Shell Tool Configuration (updated)
NEXUS_EDITOR="$VAL_EDITOR"
NEXUS_FILES="$VAL_FILES"
NEXUS_RENDER="$VAL_RENDER"
NEXUS_GUM="$VAL_GUM"
NEXUS_GIT="$VAL_GIT"
NEXUS_CHAT="$VAL_CHAT"
NEXUS_PX_UI="$VAL_PX_UI"
NEXUS_ISOLATED="true"
EOF
    else
        # Write tools config to use downloaded binaries with isolated configs
        cat > "$CONFIG_DIR/tools.conf" << EOF
# Nexus-Shell Tool Configuration (downloaded binaries, isolated configs)
NEXUS_EDITOR="$NEXUS_BIN/nvim"
NEXUS_FILES="$NEXUS_BIN/yazi"
NEXUS_RENDER="$NEXUS_BIN/glow"
NEXUS_GUM="$NEXUS_BIN/gum"
NEXUS_GIT="$NEXUS_BIN/lazygit"
NEXUS_CHAT="$DETECTED_CHAT"
NEXUS_PX_UI="tmux"
NEXUS_ISOLATED="true"
EOF
    fi

else
    echo "    Using system tools from PATH..."
    
    # Check required tools exist
    MISSING=""
    command -v nvim &>/dev/null || MISSING="$MISSING nvim"
    command -v yazi &>/dev/null || MISSING="$MISSING yazi"
    command -v gum &>/dev/null || MISSING="$MISSING gum"
    
    if [[ -n "$MISSING" ]]; then
        echo ""
        echo "    WARNING: Missing tools:$MISSING"
        echo "    Install with: brew install$MISSING"
        echo ""
    fi
    
    # Check optional tools
    command -v glow &>/dev/null || echo "    Note: glow not found (optional, for markdown preview)"
    
    # Detect default chat tool
    DETECTED_CHAT=""
    command -v opencode &>/dev/null && DETECTED_CHAT="opencode"
    [[ -z "$DETECTED_CHAT" ]] && command -v aider &>/dev/null && DETECTED_CHAT="aider"

    # Merge with existing tools.conf if it exists
    EXISTING_CONF="$CONFIG_DIR/tools.conf"
    if [[ -f "$EXISTING_CONF" ]]; then
        echo "    Updating existing tools.conf..."
        # Helper to get value from config
        get_conf_val() {
            grep "^$1=" "$EXISTING_CONF" | cut -d'=' -f2- | tr -d '"' | tr -d "'"
        }

        # Determine values (Priority: Existing > Default)
        VAL_EDITOR=$(get_conf_val "NEXUS_EDITOR")
        [[ -z "$VAL_EDITOR" ]] && VAL_EDITOR="nvim"
        
        VAL_FILES=$(get_conf_val "NEXUS_FILES")
        [[ -z "$VAL_FILES" ]] && VAL_FILES="yazi"
        
        VAL_RENDER=$(get_conf_val "NEXUS_RENDER")
        [[ -z "$VAL_RENDER" ]] && VAL_RENDER="glow"
        
        VAL_GUM=$(get_conf_val "NEXUS_GUM")
        [[ -z "$VAL_GUM" ]] && VAL_GUM="gum"
        
        VAL_GIT=$(get_conf_val "NEXUS_GIT")
        [[ -z "$VAL_GIT" ]] && VAL_GIT="lazygit"
        
        VAL_CHAT=$(get_conf_val "NEXUS_CHAT")
        [[ -z "$VAL_CHAT" ]] && VAL_CHAT="$DETECTED_CHAT"
        
        VAL_PX_UI=$(get_conf_val "NEXUS_PX_UI")
        [[ -z "$VAL_PX_UI" ]] && VAL_PX_UI="tmux"

        cat > "$EXISTING_CONF" << EOF
# Nexus-Shell Tool Configuration (updated)
NEXUS_EDITOR="$VAL_EDITOR"
NEXUS_FILES="$VAL_FILES"
NEXUS_RENDER="$VAL_RENDER"
NEXUS_GUM="$VAL_GUM"
NEXUS_GIT="$VAL_GIT"
NEXUS_CHAT="$VAL_CHAT"
NEXUS_PX_UI="$VAL_PX_UI"
EOF
    else
        # Write tools config to use system binaries
        cat > "$CONFIG_DIR/tools.conf" << EOF
# Nexus-Shell Tool Configuration (system binaries)
NEXUS_EDITOR="nvim"
NEXUS_FILES="yazi"
NEXUS_RENDER="glow"
NEXUS_GUM="gum"
NEXUS_GIT="lazygit"
NEXUS_CHAT="$DETECTED_CHAT"
NEXUS_PX_UI="tmux"
EOF
    fi
fi

# === Step 3: Copy configs ===
echo ""
echo "[3/6] Setting up configuration..."

mkdir -p "$CONFIG_DIR"

# Copy Nexus 2.0 structure
cp -r "$NEXUS_HOME/core" "$CONFIG_DIR/"
cp -r "$NEXUS_HOME/config" "$CONFIG_DIR/"
cp -r "$NEXUS_HOME/docs" "$CONFIG_DIR/"
cp -r "$NEXUS_HOME/modules" "$CONFIG_DIR/"
cp -r "$NEXUS_HOME/examples" "$CONFIG_DIR/"

# Install Nexus actions to Parallax
if [[ -d "$HOME/.parallax/content/actions" ]]; then
    echo "    Installing Nexus actions to Parallax..."
    mkdir -p "$HOME/.parallax/content/actions/nexus"
    cp -rf "$NEXUS_HOME/core/actions/"* "$HOME/.parallax/content/actions/nexus/" 2>/dev/null || true
fi

# Copy example configs and integration files
mkdir -p "$CONFIG_DIR/nvim-integration"
cp "$NEXUS_HOME/config/nvim/lua/nexus_integration.lua" "$CONFIG_DIR/nvim-integration/"

echo "    Nexus uses your existing tool configs (nvim, yazi, etc.)"
echo ""
echo "    OPTIONAL: Add Nexus integration to your nvim config:"
echo "      Add to your init.lua:"
echo "        vim.opt.runtimepath:append('$CONFIG_DIR/nvim-integration')"
echo "        pcall(require, 'nexus_integration')"

echo "    Config directory: $CONFIG_DIR"

# === Step 4: Create state directory ===
echo ""
echo "[4/6] Creating state directory..."
NEXUS_STATE="/tmp/nexus_$USER_NAME"
mkdir -p "$NEXUS_STATE/pipes"
cp "$NEXUS_HOME/core/themes/nexus-cyber.json" "$NEXUS_STATE/theme.json" 2>/dev/null || true
echo "    State directory: $NEXUS_STATE"

# === Step 5: Add shell hooks ===
echo ""
echo "[5/6] Setting up shell integration..."

# Create standalone hook file
NEXUS_ZSH="$USER_HOME/.nexus-shell.zsh"
cat > "$NEXUS_ZSH" << EOF
# Nexus-Shell Integration
# Point NEXUS_HOME to the config directory for runtime usage
export NEXUS_HOME="$CONFIG_DIR"
export NEXUS_CONFIG="$CONFIG_DIR"
export NEXUS_BIN="$NEXUS_BIN"

# Source tools config
[[ -f "\$NEXUS_CONFIG/tools.conf" ]] && source "\$NEXUS_CONFIG/tools.conf"

# Add nexus-shell bin to PATH if using downloaded tools
[[ -d "\$NEXUS_BIN" ]] && export PATH="\$NEXUS_BIN:\$PATH"

# Shell hooks (Kernel Location)
source "\$NEXUS_CONFIG/core/boot/shell_hooks.zsh"

# Source module inits
if [[ -d "\$NEXUS_CONFIG/modules" ]]; then
    for init_file in "\$NEXUS_CONFIG"/modules/*/init.zsh; do
        [[ -f "\$init_file" ]] && source "\$init_file"
    done
fi
EOF

# Add to .zshrc if not already there
ZSHRC="$USER_HOME/.zshrc"
if [[ -f "$ZSHRC" ]]; then
    if ! grep -q "nexus-shell.zsh" "$ZSHRC" 2>/dev/null; then
        echo "" >> "$ZSHRC"
        echo "# Nexus-Shell" >> "$ZSHRC"
        echo '[[ -f "$HOME/.nexus-shell.zsh" ]] && source "$HOME/.nexus-shell.zsh"' >> "$ZSHRC"
        echo "    Added to ~/.zshrc"
    else
        echo "    ~/.zshrc already has nexus-shell integration"
    fi
fi

# === Step 6: Create launcher symlinks ===
echo ""
echo "[6/6] Creating launcher commands..."

# Determine bin directory
if [[ -w "/usr/local/bin" ]]; then
    BIN_DIR="/usr/local/bin"
else
    BIN_DIR="$USER_HOME/bin"
    mkdir -p "$BIN_DIR"
fi

ln -sf "$CONFIG_DIR/core/boot/launcher.sh" "$BIN_DIR/nexus"
ln -sf "$CONFIG_DIR/core/boot/launcher.sh" "$BIN_DIR/nxs"
echo "    $BIN_DIR/nexus -> core/boot/launcher.sh"
echo "    $BIN_DIR/nxs -> core/boot/launcher.sh"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║            INSTALLATION COMPLETE!                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "To get started:"
echo "  1. Open a new terminal (or run: source ~/.zshrc)"
echo "  2. Navigate to any project directory"
echo "  3. Run: nexus (or nxs)"
echo ""
echo "Commands inside Nexus:"
echo "  Ctrl+\\     - Open command prompt"
echo "  :help      - Show all commands"
echo "  :q         - Quit"
echo ""
echo "Documentation: https://github.com/samir-alsayad/nexus-shell"
echo ""
