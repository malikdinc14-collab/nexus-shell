#!/bin/bash
# Nexus Shell Health Check (Doctor)

echo -e "\033[1;36m[+] Nexus Shell Doctor: Running Diagnostics...\033[0m"
echo "----------------------------------------------------"

# 1. Environment Check
echo -n "[*] Checking NEXUS_HOME... "
if [[ -d "$NEXUS_HOME" ]]; then
    echo -e "\033[0;32mOK ($NEXUS_HOME)\033[0m"
else
    echo -e "\033[0;31mFAILED\033[0m"
fi

# 2. Dependency Check
deps=("tmux" "fzf" "fd" "rg" "python3" "nvim" "shellcheck" "ruff")
for dep in "${deps[@]}"; do
    echo -n "[*] Checking $dep... "
    if command -v "$dep" &>/dev/null; then
        echo -e "\033[0;32mOK ($(command -v "$dep"))\033[0m"
    else
        echo -e "\033[0;31mNOT FOUND\033[0m"
    fi
done

# 3. Python Venv Check
echo -n "[*] Checking Python Venv... "
PYTHON_BIN=""
if [[ -x "$NEXUS_HOME/.venv/bin/python3" ]]; then
    PYTHON_BIN="$NEXUS_HOME/.venv/bin/python3"
    echo -e "\033[0;32mOK (.venv)\033[0m"
elif [[ -x "$Python_BIN" ]]; then
    PYTHON_BIN="$Python_BIN"
    echo -e "\033[0;32mOK (nexus_env)\033[0m"
else
    echo -e "\033[0;33mWARNING (No local venv found, using system Python)\033[0m"
fi

# 4. Tmux Version
if command -v tmux &>/dev/null; then
    TMUX_VER=$(tmux -V | cut -d' ' -f2)
    echo -n "[*] Tmux Version $TMUX_VER... "
    if [[ "$TMUX_VER" == "next-"* ]]; then
        echo -e "\033[0;32mOK (Master Branch)\033[0m"
    elif [[ $(echo "$TMUX_VER >= 3.2" | awk '{if($1 >= $3) print 1; else print 0}') -eq 1 ]]; then
        echo -e "\033[0;32mOK\033[0m"
    else
        echo -e "\033[0;33mWARNING (Recommend 3.2+)\033[0m"
    fi
fi

echo "----------------------------------------------------"
echo "[+] Diagnostics Complete."
