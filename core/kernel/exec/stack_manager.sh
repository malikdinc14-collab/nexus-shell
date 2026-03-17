#!/bin/bash
# core/kernel/exec/stack_manager.sh
# The Universal Controller for all Stacks in Nexus Shell.
# Usage: nxs-stack <category> [initial_query]

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
export NEXUS_CORE="${NEXUS_CORE:-$NEXUS_HOME/core}"
STATE_ENGINE="${NEXUS_CORE}/state/state_engine.sh"
EDIT_HELPER="${NEXUS_CORE}/exec/edit_helper.sh"

CATEGORY="${1:-roles}"
QUERY="${2}"

while true; do
    # 1. Resolve Stack, Type and Environment
    case "$CATEGORY" in
        "roles")
            # Role Selection Mode (The "Serious IDE" Path)
            TYPE="ROLE"
            HEADER="Assign Sovereign Role"
            # Display name -> Internal key mapping
            OPTIONS=$(cat << EOF
Editor (editor)
Explorer (files)
Chat (chat)
Menu (menu)
Terminal (terminal)
EOF
)
            ;;
        "chat"|"editor"|"files"|"terminal"|"menu")
            # Logic Stack (Tools)
            STACK_PATH="ui.stacks.$CATEGORY"
            TYPE="TOOL"
            HEADER="Switch $CATEGORY Tool"
            # Load defaults from user_stacks.yaml
            USER_STACKS="$NEXUS_HOME/config/user_stacks.yaml"
            if [[ -f "$USER_STACKS" ]]; then
                DEFAULTS=($(python3 -c "import yaml; print('\n'.join(yaml.safe_load(open('$USER_STACKS'))['stacks'].get('$CATEGORY', [])))" 2>/dev/null))
            fi
            ;;
        "models")
            # Inference Stack (Sovereign Models)
            STACK_PATH="project.stacks.models"
            TYPE="MODEL"
            HEADER="🌌 Sovereign Model Registry"
            ;;
        "docs"|"notes"|"specs"|"gap")
            # Knowledge Stack (Markdown)
            TYPE="DOC"
            HEADER="📚 $CATEGORY Explorer"
            # Source from directory
            case "$CATEGORY" in
                "gap") SEARCH_DIR="$PROJECT_ROOT/.gap" ;;
                "specs") SEARCH_DIR="$PROJECT_ROOT/specs" ;;
                *) SEARCH_DIR="$PROJECT_ROOT/docs" ;;
            esac
            ;;
        "content"|"graph")
            # Ascent Knowledge Graph
            TYPE="DOC"
            HEADER="🎓 Ascent Content"
            SEARCH_DIR="$PROJECT_ROOT/school-content"
            ;;
        "prompts")
            # Ascent/Inference Prompts
            TYPE="DOC"
            HEADER="🧬 Prompt Templates"
            SEARCH_DIR="$PROJECT_ROOT/engine/prompts"
            ;;
        "learners"|"personas")
            # Global/Project Learner Profiles
            TYPE="DOC"
            HEADER="👤 Learner Personas"
            SEARCH_DIR="$PROJECT_ROOT/learners"
            ;;
        "config"|"settings")
            # System Configuration
            TYPE="CONFIG"
            HEADER="⚙️ Nexus Configuration"
            # Discovery of active config files (State is project-local, others are global)
            ACTIVE_PROFILE=$("$STATE_ENGINE" get project.profile 2>/dev/null || echo "ascent")
            ACTIVE_COMP=$("$STATE_ENGINE" get ui.active_composition 2>/dev/null || echo "vscodelike")
            
            OPTIONS=$(cat << EOF
[Project State] .nexus/state.json
[Active Profile] config/profiles/${ACTIVE_PROFILE}.yaml
[Active Composition] compositions/${ACTIVE_COMP}.json
[Global Registry] core/engine/api/registry.json
EOF
)
            ;;
        "actions"|"build")
            # Activity Stack (Scripts)
            TYPE="ACTION"
            HEADER="🏗️ Project Actions"
            SEARCH_DIR="$PROJECT_ROOT/.nexus/actions"
            ;;
        "media"|"images"|"vision")
            # Media Stack
            TYPE="VISION"
            HEADER="🖼️ Media Explorer"
            SEARCH_DIR="$PROJECT_ROOT/media"
            [[ ! -d "$SEARCH_DIR" ]] && SEARCH_DIR="$PROJECT_ROOT/assets"
            ;;
        *)
            # Generic Fallback
            STACK_PATH="ui.stacks.$CATEGORY"
            TYPE="GENERIC"
            HEADER="Stack: $CATEGORY"
            ;;
    esac

    # 2. Extract Data
    if [[ "$TYPE" == "CONFIG" ]]; then
        # OPTIONS already set above
        OPTIONS="$OPTIONS"
    elif [[ "$TYPE" == "DOC" || "$TYPE" == "ACTION" || "$TYPE" == "VISION" ]]; then
        if [[ ! -d "$SEARCH_DIR" ]]; then
            # Create it if it's a standard path but missing
            mkdir -p "$SEARCH_DIR"
        fi
        EXTS="*.md *.txt *.sh *.png *.jpg *.jpeg *.gif *.svg"
        OPTIONS=$(find "$SEARCH_DIR" -maxdepth 2 $(printf -- "-name %s -o " $EXTS | sed 's/-o $//') | sed "s|$PROJECT_ROOT/||")
    else
        # Pull from State Engine
        OPTIONS=$("$STATE_ENGINE" get "$STACK_PATH" | jq -r '.[]' 2>/dev/null)
        # Merge with Defaults
        if [[ -n "$DEFAULTS" ]]; then
            OPTIONS=$(printf "%s\n%s" "$OPTIONS" "$(printf "%s\n" "${DEFAULTS[@]}")" | sort -u | grep -v "^$")
        fi
    fi

    # Add System Options (except for roles list)
    if [[ "$TYPE" != "ROLE" ]]; then
        OPTIONS=$(printf "%s\n---\nNexus Menu\nBash Shell" "$OPTIONS")
    fi

    # 3. Interactive Selector (FZF)
    if [[ "$TYPE" == "ROLE" ]]; then
        # Enter: Perform Primary Action (Launch Default Tool for this Role)
        # Alt-E: Enter Modification Mode (Drill-down to Tool List)
        BIND_EDIT="--bind \"alt-e:become(echo drill:\$(echo {} | sed -n 's/.*(\(.*\)).*/\\1/p'))\""
    elif [[ "$TYPE" == "DOC" || "$TYPE" == "ACTION" || "$TYPE" == "VISION" || "$TYPE" == "CONFIG" ]]; then
        # Enter: Primary Action (Open/Run)
        # Alt-E: Modify/Source (Edit in Editor)
        # We assume project-local files unless CATEGORY is config/settings
        if [[ "$CATEGORY" == "config" || "$CATEGORY" == "settings" ]]; then
            REF_DIR="$NEXUS_HOME"
        else
            REF_DIR="$PROJECT_ROOT"
        fi
        BIND_EDIT="--bind \"alt-e:execute($NEXUS_EDITOR $REF_DIR/{})+reload(echo '$OPTIONS')\" " 
    elif [[ -n "$STACK_PATH" ]]; then
        # Enter: Primary Action (Select & Launch)
        # Alt-E: Modify/Source (Edit definition)
        BIND_EDIT="--bind \"alt-e:execute($EDIT_HELPER $STACK_PATH 'Stack [$CATEGORY]')+reload($STATE_ENGINE get $STACK_PATH | jq -r '.[]')\""
    fi

    CHOICE=$(echo "$OPTIONS" | fzf \
        --header="$HEADER (Enter: Action | Alt-E: Modify/Drill-Down)" \
        --reverse --height=15 \
        --query="$QUERY" \
        $BIND_EDIT)

    [[ -z "$CHOICE" || "$CHOICE" == "---" ]] && exit 0

    # Drill-down logic for ROLEs (Triggered by Alt-E via become)
    if [[ "$CHOICE" == drill:* ]]; then
        CATEGORY="${CHOICE#drill:}"
        QUERY=""
        DEFAULTS=()
        STACK_PATH=""
        TYPE=""
        continue
    fi

    # Exit loop on normal Enter choice
    break
done

# 4. Polymorphic Dispatch
case "$CHOICE" in
    "Nexus Menu")
        CMD="$NEXUS_HOME/modules/menu/bin/nexus-menu"
        ;;
    "Bash Shell")
        CMD="/bin/zsh -i"
        ;;
    *)
        case "$TYPE" in
            "ROLE")
                # Extract internal role from "Display Name (internal_role)"
                ROLE=$(echo "$CHOICE" | sed -n 's/.*(\(.*\)).*/\1/p')
                # Update logical slot so that respawn uses the correct role
                tmux set-option -p -t "$PANE_ID" "@nexus_role" "$ROLE"
                # Get the default tool for this role from environment
                case "$ROLE" in
                    "editor") CMD="$NEXUS_EDITOR" ;;
                    "files") CMD="$NEXUS_FILES" ;;
                    "chat") CMD="$NEXUS_CHAT" ;;
                    "menu") CMD="$NEXUS_MENU" ;;
                    "terminal") CMD="$NEXUS_TERMINAL" ;;
                    *) CMD="/bin/zsh -i" ;;
                esac
                # Title the pane
                tmux select-pane -t "$PANE_ID" -T "$ROLE"
                ;;
            "TOOL")
                CMD="$CHOICE"
                # Update logical slot assignment
                "$STATE_ENGINE" set "ui.slots.$CATEGORY.tool" "$CHOICE"
                # Also ensure the pane now carries this role
                tmux set-option -p -t "$PANE_ID" "@nexus_role" "$CATEGORY"
                tmux select-pane -t "$PANE_ID" -T "$CATEGORY"
                ;;
            "MODEL")
                # Bridge to Sovereign-Inference
                CMD="sov host $CHOICE"
                "$STATE_ENGINE" set "project.active_model" "$CHOICE"
                ;;
            "DOC")
                # Open in editor (Project Relative)
                CMD="$NEXUS_EDITOR $PROJECT_ROOT/$CHOICE"
                ;;
            "ACTION")
                # Execute script (Project Relative)
                CMD="$PROJECT_ROOT/$CHOICE"
                ;;
            "CONFIG")
                # Open in editor (Nexus Home and Project Local handling)
                CLEAN_PATH=$(echo "$CHOICE" | sed 's/\[.*\] //')
                if [[ "$CLEAN_PATH" == ".nexus/state.json" ]]; then
                    CMD="$NEXUS_EDITOR $PROJECT_ROOT/$CLEAN_PATH"
                else
                    CMD="$NEXUS_EDITOR $NEXUS_HOME/$CLEAN_PATH"
                fi
                ;;
            "VISION")
                # Image rendering in terminal
                if command -v chafa >/dev/null 2>&1; then
                    CMD="chafa $PROJECT_ROOT/$CHOICE; read -n 1 -p 'Press any key...'"
                else
                    CMD="echo 'Install: brew install chafa'; sleep 2"
                fi
                ;;
            *)
                CMD="$CHOICE"
                ;;
        esac
        ;;
esac

# 5. Execution Logic
# If in a tmux context, respawn or run. Else just run.
if [[ -n "$PANE_ID" ]]; then
tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_CORE/boot/pane_wrapper.sh ${NEXUS_HOME}/core/kernel/exec/guard.sh $CMD"
else
clear
"${NEXUS_HOME}/core/kernel/exec/guard.sh" "$CMD"
fi
