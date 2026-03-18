#!/bin/bash
# Nexus Shell Health Check (Doctor)
# Extension-aware system diagnostics

echo -e "\033[1;36m[+] Nexus Shell Doctor: Running Diagnostics...\033[0m"
echo "----------------------------------------------------"

# Resolve NEXUS_HOME
NEXUS_HOME="${NEXUS_HOME:-$(cd "$(dirname "$0")/../.." && pwd)}"
export NEXUS_HOME

# Source detector if available
if [[ -f "$NEXUS_HOME/core/engine/lib/detector.sh" ]]; then
    source "$NEXUS_HOME/core/engine/lib/detector.sh"
fi

# Portable tool lookup
get_tools_for_role() {
    case "$1" in
        editor) echo "nvim vim vi" ;;
        explorer) echo "yazi ranger nnn lf" ;;
        chat) echo "opencode gptme" ;;
        terminal) echo "zellij" ;;
        viewer) echo "glow bat" ;;
        search) echo "grepai rg" ;;
    esac
}

# 1. Environment Check
echo -n "[*] Checking NEXUS_HOME... "
if [[ -d "$NEXUS_HOME" ]]; then
    echo -e "\033[0;32mOK ($NEXUS_HOME)\033[0m"
else
    echo -e "\033[0;31mFAILED\033[0m"
fi

# 2. Core Dependencies (never extensions)
echo ""
echo -e "\033[1;37m[CORE DEPENDENCIES]\033[0m"
core_deps=("tmux" "python3")
for dep in "${core_deps[@]}"; do
    echo -n "    $dep... "
    if command -v "$dep" &>/dev/null; then
        echo -e "\033[0;32m✓ ($(command -v "$dep"))\033[0m"
    else
        echo -e "\033[0;31m✗ REQUIRED\033[0m"
    fi
done

# 3. Profile Status
echo ""
echo -e "\033[1;37m[USER PROFILE]\033[0m"
PROFILE_FILE="$HOME/.nexus/profile.yaml"
if [[ -f "$PROFILE_FILE" ]]; then
    echo -e "    \033[0;32m✓ Profile exists\033[0m"
    
    # Show configured roles
    if command -v python3 &>/dev/null; then
        python3 -c "
import yaml
try:
    with open('$PROFILE_FILE') as f:
        data = yaml.safe_load(f)
    print('    Configured roles:')
    for role, tool in data.get('roles', {}).items():
        print(f'      {role}: {tool}')
except: pass
" 2>/dev/null
    fi
else
    echo -e "    \033[0;33m○ No profile (run 'nxs wizard')\033[0m"
fi

# 4. Detected Tools
echo ""
echo -e "\033[1;37m[DETECTED TOOLS]\033[0m"
if declare -f detect_as_json &>/dev/null; then
    detect_as_json | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    roles = data.get('roles', {})
    for role in ['editor', 'explorer', 'chat', 'terminal', 'viewer', 'search']:
        tool = roles.get(role, '')
        if tool:
            print(f'    ✓ {role}: {tool}')
        else:
            print(f'    ○ {role}: not found')
except: pass
" 2>/dev/null
else
    # Fallback tool list (Portable)
    for role in editor explorer chat terminal viewer search; do
        found=""
        for tool in $(get_tools_for_role "$role"); do
            if command -v "$tool" &>/dev/null; then
                found="$tool"
                break
            fi
        done
        if [[ -n "$found" ]]; then
            echo -e "    \033[0;32m✓ $role: $found\033[0m"
        else
            echo -e "    \033[0;33m○ $role: not found\033[0m"
        fi
    done
fi

# 5. Extension Status
echo ""
echo -e "\033[1;37m[EXTENSIONS]\033[0m"
if [[ -f "$NEXUS_HOME/extensions/loader.sh" ]]; then
    "$NEXUS_HOME/extensions/loader.sh" list 2>/dev/null | head -20
else
    echo -e "    \033[0;33m○ Extension system not found\033[0m"
fi

# 6. Python Venv Check
echo ""
echo -e "\033[1;37m[PYTHON ENVIRONMENT]\033[0m"
PYTHON_BIN=""
if [[ -x "$NEXUS_HOME/.venv/bin/python3" ]]; then
    PYTHON_BIN="$NEXUS_HOME/.venv/bin/python3"
    echo -e "    \033[0;32m✓ Venv (.venv)\033[0m"
elif [[ -x "$(command -v python3)" ]]; then
    PYTHON_BIN="$(command -v python3)"
    echo -e "    \033[0;33m○ Using system Python\033[0m"
else
    echo -e "    \033[0;31m✗ No Python found\033[0m"
fi

# 7. Tmux Version
echo ""
echo -e "\033[1;37m[TMUX]\033[0m"
if command -v tmux &>/dev/null; then
    TMUX_VER=$(tmux -V 2>/dev/null | cut -d' ' -f2)
    echo -n "    Version $TMUX_VER... "
    if [[ "$TMUX_VER" == "next-"* ]]; then
        echo -e "\033[0;32m✓ (Master)\033[0m"
    elif [[ $(echo "$TMUX_VER >= 3.2" | awk '{if($1 >= $3) print 1; else print 0}' 2>/dev/null) -eq 1 ]]; then
        echo -e "\033[0;32m✓\033[0m"
    else
        echo -e "\033[0;33m⚠ (Recommend 3.2+)\033[0m"
    fi
else
    echo -e "    \033[0;31m✗ Not installed\033[0m"
fi

# 8. Recommendations
echo ""
echo -e "\033[1;37m[RECOMMENDATIONS]\033[0m"
if [[ ! -f "$PROFILE_FILE" ]]; then
    echo -e "    Run \033[1;36mnxs wizard\033[0m to set up your profile"
fi

# Check for missing core tools
missing_roles=()
for role in editor explorer chat; do
    found=0
    for tool in $(get_tools_for_role "$role"); do
        command -v "$tool" &>/dev/null && { found=1; break; }
    done
    [[ $found -eq 0 ]] && missing_roles+=("$role")
done

if [[ ${#missing_roles[@]} -gt 0 ]]; then
    echo -e "    Missing tools for: ${missing_roles[*]}"
    echo -e "    Run \033[1;36mnxs extension list\033[0m to see available options"
fi

echo "----------------------------------------------------"
echo -e "\033[1;36m[+] Diagnostics Complete.\033[0m"
