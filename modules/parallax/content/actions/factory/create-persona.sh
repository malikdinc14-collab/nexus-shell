#!/bin/bash
# Create Agent Persona
# Creates a new agent personality configuration.
# @param AGENT_NAME: Agent identifier (jarvis)
# @param AGENT_ROLE: Agent's primary role (assistant)
# @param AGENT_STYLE: Communication style [formal, casual, technical]

echo "🤖 Creating Agent Persona..."

[[ -z "$AGENT_NAME" ]] && { echo "❌ AGENT_NAME is required"; exit 1; }
[[ -z "$AGENT_ROLE" ]] && AGENT_ROLE="assistant"
[[ -z "$AGENT_STYLE" ]] && AGENT_STYLE="casual"

AGENT_DIR="$HOME/.parallax/content/agents/ghosts/$AGENT_NAME"
mkdir -p "$AGENT_DIR"

cat <<EOF > "$AGENT_DIR/persona.yaml"
# $AGENT_NAME Persona Configuration
name: $AGENT_NAME
role: $AGENT_ROLE
style: $AGENT_STYLE

system_prompt: |
  You are $AGENT_NAME, a $AGENT_ROLE agent.
  Communication style: $AGENT_STYLE.
  
  [Add custom instructions here]

capabilities:
  - file_operations
  - command_execution
  - web_search

constraints:
  - Always ask for confirmation before destructive actions
  - Prioritize user safety and data integrity
EOF

echo "✅ Agent '$AGENT_NAME' created at $AGENT_DIR"
echo "💡 Edit $AGENT_DIR/persona.yaml to customize the persona."
