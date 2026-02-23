# --- Nexus-Shell Local Installer (Modular) ---
# Syncs code from this project folder to your live environment (~/.config/nexus-shell)

NEXUS_HOME_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_TARGET="$HOME/.config/nexus-shell"

echo "[*] Syncing Nexus-Shell to $INSTALL_TARGET..."

# Ensure target structure exists
mkdir -p "$INSTALL_TARGET"

# List of core directories to sync
CORE_DIRS=("core" "lib" "config" "themes" "compositions")

for dir in "${CORE_DIRS[@]}"; do
    if [[ -d "$NEXUS_HOME_SRC/$dir" ]]; then
        echo "    -> Syncing $dir..."
        # Use -r for recursive and -u for update (if supported, otherwise plain cp)
        cp -rv "$NEXUS_HOME_SRC/$dir" "$INSTALL_TARGET/"
    fi
done

# Sync actions to Parallax if present
if [[ -d "$HOME/.parallax/content/actions" ]]; then
    echo "[*] Syncing actions to Parallax..."
    mkdir -p "$HOME/.parallax/content/actions/nexus"
    cp -rv "$NEXUS_HOME_SRC/actions/"* "$HOME/.parallax/content/actions/nexus/" 2>/dev/null || true
fi

echo "[✅] Success. Your live station has been updated."
