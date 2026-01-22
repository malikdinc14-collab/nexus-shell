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
    echo "    Downloading tools (this may take a moment)..."
    
    # Detect architecture
    ARCH=$(uname -m)
    case "$ARCH" in
        arm64|aarch64) ARCH_SUFFIX="arm64" ;;
        x86_64) ARCH_SUFFIX="x86_64" ;;
        *) echo "    Unsupported architecture: $ARCH"; exit 1 ;;
    esac
    
    OS=$(uname -s)
    case "$OS" in
        Darwin) OS_NAME="macos" ;;
        Linux) OS_NAME="linux" ;;
        *) echo "    Unsupported OS: $OS"; exit 1 ;;
    esac
    
    cd /tmp
    
    # Neovim
    if [[ ! -x "$NEXUS_BIN/nvim" ]]; then
        echo "    Downloading Neovim..."
        if [[ "$OS_NAME" == "macos" ]]; then
            curl -sL "https://github.com/neovim/neovim/releases/latest/download/nvim-macos-${ARCH_SUFFIX}.tar.gz" -o nvim.tar.gz
            tar -xzf nvim.tar.gz
            # Copy entire structure (bin, share, lib) to ~/.nexus-shell/
            cp -r nvim-macos-${ARCH_SUFFIX}/* "$USER_HOME/.nexus-shell/"
            rm -rf nvim.tar.gz nvim-macos-${ARCH_SUFFIX}
        else
            curl -sL "https://github.com/neovim/neovim/releases/latest/download/nvim-linux64.tar.gz" -o nvim.tar.gz
            tar -xzf nvim.tar.gz
            cp -r nvim-linux64/* "$USER_HOME/.nexus-shell/"
            rm -rf nvim.tar.gz nvim-linux64
        fi
    fi
    
    # Yazi
    if [[ ! -x "$NEXUS_BIN/yazi" ]]; then
        echo "    Downloading Yazi..."
        YAZI_TAG=$(curl -sI https://github.com/sxyazi/yazi/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
        if [[ "$OS_NAME" == "macos" ]]; then
            curl -sL "https://github.com/sxyazi/yazi/releases/download/${YAZI_TAG}/yazi-aarch64-apple-darwin.zip" -o yazi.zip
            unzip -q yazi.zip
            cp yazi-aarch64-apple-darwin/yazi "$NEXUS_BIN/"
            rm -rf yazi.zip yazi-aarch64-apple-darwin
        else
            curl -sL "https://github.com/sxyazi/yazi/releases/download/${YAZI_TAG}/yazi-x86_64-unknown-linux-gnu.zip" -o yazi.zip
            unzip -q yazi.zip
            cp yazi-x86_64-unknown-linux-gnu/yazi "$NEXUS_BIN/"
            rm -rf yazi.zip yazi-x86_64-unknown-linux-gnu
        fi
    fi
    
    # Glow
    if [[ ! -x "$NEXUS_BIN/glow" ]]; then
        echo "    Downloading Glow..."
        GLOW_TAG=$(curl -sI https://github.com/charmbracelet/glow/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
        GLOW_VER="${GLOW_TAG#v}"
        if [[ "$OS_NAME" == "macos" ]]; then
            curl -sL "https://github.com/charmbracelet/glow/releases/download/${GLOW_TAG}/glow_${GLOW_VER}_Darwin_${ARCH_SUFFIX}.tar.gz" -o glow.tar.gz
        else
            curl -sL "https://github.com/charmbracelet/glow/releases/download/${GLOW_TAG}/glow_${GLOW_VER}_Linux_${ARCH_SUFFIX}.tar.gz" -o glow.tar.gz
        fi
        mkdir -p glow_tmp
        tar -xzf glow.tar.gz -C glow_tmp
        find glow_tmp -type f -name "glow" -exec cp {} "$NEXUS_BIN/" \;
        rm -rf glow.tar.gz glow_tmp
    fi
    
    # Gum
    if [[ ! -x "$NEXUS_BIN/gum" ]]; then
        echo "    Downloading Gum..."
        GUM_TAG=$(curl -sI https://github.com/charmbracelet/gum/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
        GUM_VER="${GUM_TAG#v}"
        if [[ "$OS_NAME" == "macos" ]]; then
            curl -sL "https://github.com/charmbracelet/gum/releases/download/${GUM_TAG}/gum_${GUM_VER}_Darwin_${ARCH_SUFFIX}.tar.gz" -o gum.tar.gz
        else
            curl -sL "https://github.com/charmbracelet/gum/releases/download/${GUM_TAG}/gum_${GUM_VER}_Linux_${ARCH_SUFFIX}.tar.gz" -o gum.tar.gz
        fi
        mkdir -p gum_tmp
        tar -xzf gum.tar.gz -C gum_tmp
        find gum_tmp -type f -name "gum" -exec cp {} "$NEXUS_BIN/" \;
        rm -rf gum.tar.gz gum_tmp
    fi

    # OpenCode
    if [[ ! -x "$NEXUS_BIN/opencode" ]]; then
        echo "    Downloading OpenCode..."
        OC_TAG=$(curl -sI https://github.com/anomalyco/opencode/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
        
        if [[ "$OS_NAME" == "macos" ]]; then
            curl -sL "https://github.com/anomalyco/opencode/releases/download/${OC_TAG}/opencode-darwin-${ARCH_SUFFIX}.zip" -o opencode.zip
            unzip -oq opencode.zip 2>/dev/null || true
        else
            curl -sL "https://github.com/anomalyco/opencode/releases/download/${OC_TAG}/opencode-linux-${ARCH_SUFFIX}.tar.gz" -o opencode.tar.gz
            tar -xzf opencode.tar.gz 2>/dev/null || true
        fi
        
        if [[ -f "opencode" ]]; then
            cp opencode "$NEXUS_BIN/"
        elif [[ -d "opencode_tmp" ]]; then
            find opencode_tmp -type f -name "opencode" -exec cp {} "$NEXUS_BIN/" \;
        fi
        rm -rf opencode opencode.zip opencode.tar.gz opencode_tmp
    fi

    # Micro
    if [[ ! -x "$NEXUS_BIN/micro" ]]; then
        echo "    Downloading Micro..."
        MICRO_TAG=$(curl -sI https://github.com/zyedidia/micro/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
        MICRO_VER="${MICRO_TAG#v}"
        if [[ "$OS_NAME" == "macos" ]]; then
            # Micro uses a different naming convention: micro-2.0.14-macos-arm64.tar.gz
            # ARCH_SUFFIX is arm64 or x86_64
            curl -sL "https://github.com/zyedidia/micro/releases/download/${MICRO_TAG}/micro-${MICRO_VER}-macos-${ARCH_SUFFIX}.tar.gz" -o micro.tar.gz
        else
            curl -sL "https://github.com/zyedidia/micro/releases/download/${MICRO_TAG}/micro-${MICRO_VER}-linux64.tar.gz" -o micro.tar.gz
        fi
        if [[ -f micro.tar.gz ]]; then
            mkdir -p micro_tmp
            if tar -xzf micro.tar.gz -C micro_tmp 2>/dev/null; then
                find micro_tmp -type f -name "micro" -exec cp {} "$NEXUS_BIN/" \;
            else
                echo "    [!] Warning: Failed to extract Micro archive."
            fi
            rm -rf micro.tar.gz micro_tmp
        else
            echo "    [!] Warning: Failed to download Micro."
        fi
    fi

    # LazyGit
    if [[ ! -x "$NEXUS_BIN/lazygit" ]]; then
        echo "    Downloading LazyGit..."
        LG_TAG=$(curl -sI https://github.com/jesseduffield/lazygit/releases/latest | grep -i location | sed 's/.*tag\///' | tr -d '\r\n')
        LG_VER="${LG_TAG#v}"
        if [[ "$OS_NAME" == "macos" ]]; then
            # lazygit_0.58.1_darwin_arm64.tar.gz
            curl -sL "https://github.com/jesseduffield/lazygit/releases/download/${LG_TAG}/lazygit_${LG_VER}_darwin_${ARCH_SUFFIX}.tar.gz" -o lazygit.tar.gz
        else
            curl -sL "https://github.com/jesseduffield/lazygit/releases/download/${LG_TAG}/lazygit_${LG_VER}_linux_${ARCH_SUFFIX}.tar.gz" -o lazygit.tar.gz
        fi
        mkdir -p lazygit_tmp
        tar -xzf lazygit.tar.gz -C lazygit_tmp
        find lazygit_tmp -type f -name "lazygit" -exec cp {} "$NEXUS_BIN/" \;
        rm -rf lazygit.tar.gz lazygit_tmp
    fi
    
    chmod +x "$NEXUS_BIN"/*
    echo "    Tools installed to $NEXUS_BIN"
    
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

        # Determine values (Priority: Existing > Default)
        VAL_EDITOR=$(get_conf_val "NEXUS_EDITOR")
        [[ -z "$VAL_EDITOR" ]] && VAL_EDITOR="$NEXUS_BIN/nvim"
        
        VAL_FILES=$(get_conf_val "NEXUS_FILES")
        [[ -z "$VAL_FILES" ]] && VAL_FILES="$NEXUS_BIN/yazi"
        
        VAL_RENDER=$(get_conf_val "NEXUS_RENDER")
        [[ -z "$VAL_RENDER" ]] && VAL_RENDER="$NEXUS_BIN/glow"
        
        VAL_GUM=$(get_conf_val "NEXUS_GUM")
        [[ -z "$VAL_GUM" ]] && VAL_GUM="$NEXUS_BIN/gum"
        
        VAL_GIT=$(get_conf_val "NEXUS_GIT")
        [[ -z "$VAL_GIT" ]] && VAL_GIT="$NEXUS_BIN/lazygit"
        
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

# Copy nexus-shell config
cp -r "$NEXUS_HOME/config/tmux" "$CONFIG_DIR/"
cp -r "$NEXUS_HOME/themes" "$CONFIG_DIR/"
cp -r "$NEXUS_HOME/scripts" "$CONFIG_DIR/"

# Install Nexus actions to Parallax
if [[ -d "$HOME/.parallax/content/actions" ]]; then
    echo "    Installing Nexus actions to Parallax..."
    mkdir -p "$HOME/.parallax/content/actions/nexus"
    cp -rf "$NEXUS_HOME/actions/"* "$HOME/.parallax/content/actions/nexus/" 2>/dev/null || true
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
cp "$NEXUS_HOME/themes/nexus-cyber.json" "$NEXUS_STATE/theme.json" 2>/dev/null || true
echo "    State directory: $NEXUS_STATE"

# === Step 5: Add shell hooks ===
echo ""
echo "[5/6] Setting up shell integration..."

# Create standalone hook file
NEXUS_ZSH="$USER_HOME/.nexus-shell.zsh"
cat > "$NEXUS_ZSH" << EOF
# Nexus-Shell Integration
export NEXUS_HOME="$NEXUS_HOME"
export NEXUS_CONFIG="$CONFIG_DIR"
export NEXUS_BIN="$NEXUS_BIN"

# Source tools config
[[ -f "\$NEXUS_CONFIG/tools.conf" ]] && source "\$NEXUS_CONFIG/tools.conf"

# Add nexus-shell bin to PATH if using downloaded tools
[[ -d "\$NEXUS_BIN" ]] && export PATH="\$NEXUS_BIN:\$PATH"

# Shell hooks
source "\$NEXUS_CONFIG/scripts/shell_hooks.zsh"
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

ln -sf "$CONFIG_DIR/scripts/launcher.sh" "$BIN_DIR/nexus"
ln -sf "$CONFIG_DIR/scripts/launcher.sh" "$BIN_DIR/nxs"
echo "    $BIN_DIR/nexus -> launcher.sh"
echo "    $BIN_DIR/nxs -> launcher.sh"

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
