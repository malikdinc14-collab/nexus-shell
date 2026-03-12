#!/bin/bash
# core/exec/stack_manager.sh
# The Universal Controller for all Stacks in Nexus Shell.
# Usage: nxs-stack <category> [initial_query]

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NEXUS_HOME="${NEXUS_HOME:-$(cd "$SCRIPT_DIR/../../" && pwd)}"
export NEXUS_CORE="${NEXUS_CORE:-$NEXUS_HOME/core}"
STATE_ENGINE="${NEXUS_CORE}/state/state_engine.sh"
EDIT_HELPER="${NEXUS_CORE}/exec/edit_helper.sh"

# 1. Resolve Stack, Type and Environment
if [[ -z "$CATEGORY" ]]; then
    # Auto-detect based on directory
    if [[ -d ".gap" ]]; then CATEGORY="gap";
    elif [[ -d "school-content" ]]; then CATEGORY="content";
    elif [[ -f "pyproject.toml" && -d "engine" ]]; then CATEGORY="actions";
    elif [[ -f "package.json" ]]; then CATEGORY="build";
    else CATEGORY="docs"; fi
fi

case "$CATEGORY" in
    "chat"|"editor"|"files")
        # Logic Stack (Tools)
        STACK_PATH="ui.stacks.$CATEGORY"
        TYPE="TOOL"
        HEADER="Switch $CATEGORY Tool"
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
[Global Registry] core/api/registry.json
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
fi

# Add System Options
OPTIONS=$(printf "%s\n---\nNexus Menu\nBash Shell" "$OPTIONS")

# 3. Interactive Selector (FZF)
# Alt-E polymorphic binding:
# - If it's a state path, use edit_helper.sh
# - If it's a file-based stack, use the editor directly on the selection
if [[ "$TYPE" == "DOC" || "$TYPE" == "ACTION" || "$TYPE" == "VISION" || "$TYPE" == "CONFIG" ]]; then
    BIND_EDIT="--bind \"alt-e:execute($NEXUS_EDITOR $NEXUS_HOME/{})+reload(\" " # Reload logic not needed for static config list
elif [[ -n "$STACK_PATH" ]]; then
    BIND_EDIT="--bind \"alt-e:execute($EDIT_HELPER $STACK_PATH 'Stack [$CATEGORY]')+reload($STATE_ENGINE get $STACK_PATH | jq -r '.[]')\""
fi

CHOICE=$(echo "$OPTIONS" | fzf \
    --header="$HEADER (Alt-E: Edit Selected)" \
    --reverse --height=15 \
    --query="$QUERY" \
    $BIND_EDIT)

[[ -z "$CHOICE" || "$CHOICE" == "---" ]] && exit 0

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
            "TOOL")
                CMD="$CHOICE"
                # Update logical slot assignment
                "$STATE_ENGINE" set "ui.slots.$CATEGORY.tool" "$CHOICE"
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
    tmux respawn-pane -k -t "$PANE_ID" "$NEXUS_CORE/boot/pane_wrapper.sh ${NEXUS_HOME}/core/exec/guard.sh $CMD"
else
    clear
    "${NEXUS_HOME}/core/exec/guard.sh" "$CMD"
fi
