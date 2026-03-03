#!/bin/bash
# Create Persona
# @param NAME: Persona name (My Agent)

echo "🎭 Persona Workshop..."

if [[ -z "$NAME" ]]; then
    echo "❌ NAME is required."
    exit 1
fi

FILENAME=$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
TARGET="library/agents/personas/$FILENAME.yaml"

if [[ -f "$TARGET" ]]; then
    echo "⚠️ Persona already exists."
    exit 1
fi

mkdir -p "$(dirname "$TARGET")"

cat <<EOF > "$TARGET"
name: "$NAME"
persona: |
  I am $NAME. 
  Describe your personality here...
EOF

echo "✅ Persona '$NAME' created at $TARGET"
echo "📝 Edit with: \$EDITOR $TARGET"
