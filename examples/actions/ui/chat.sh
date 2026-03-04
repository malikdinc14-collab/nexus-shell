#!/bin/bash
# @parallax-action
# @name: Open Chat UI
# @id: ui:chat
# @description: Launches Open WebUI (Docker) connected to local Ollama.
# @icon: message-square

if ! command -v docker >/dev/null; then
    echo "❌ Docker is required but not installed."
    echo "   Please install Docker Desktop."
    exit 1
fi

# Auto-Start Docker on Mac
if ! docker info > /dev/null 2>&1; then
    echo "🐳 Docker is sleeping. Waking it up (this takes a moment)..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open -a Docker
        # Wait up to 60s for daemon to be ready
        TIMEOUT=60
        while ! docker info > /dev/null 2>&1; do
            if [[ $TIMEOUT -le 0 ]]; then echo "❌ Docker failed to start."; exit 1; fi
            sleep 1
            ((TIMEOUT--))
        done
        echo "✅ Docker is online."
    else
        echo "❌ Docker Daemon is not running. Please start it."
        exit 1
    fi
fi

CONTAINER_NAME="px-chat-ui"

case "$ACTION" in
    stop)
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "🛑 Stopping Chat UI Container..."
            docker stop "$CONTAINER_NAME"
            echo "✅ Chat UI stopped."
        else
            echo "⚠️  Chat UI is not running."
        fi
        ;;
    status)
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "✅ Chat UI is running on port 3001"
        else
            echo "⚠️  Chat UI is not running."
        fi
        ;;
    *)
        # Default: Start / Open
        # Check if running
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "⚠️  Chat UI is already running."
            echo "   Opening http://127.0.0.1:3001..."
            open "http://127.0.0.1:3001"
            exit 0
        fi

        # Check if stopped (exists but exited)
        if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            echo "🔄 Refreshing container environment..."
            docker rm "$CONTAINER_NAME" >/dev/null
        fi
        
        echo "🚀 Launching Open WebUI Container..."
        # Multi-Engine Bridge: Discover everything active on the host
        URLS=""
        KEYS=""

        # 1. MLX (Raw Apple Silicon Engine) - PRIORITY
        if lsof -i :8080 > /dev/null 2>&1; then
            echo "🚀 Bridging MLX (Engine) -> WebUI..."
            [[ -n "$URLS" ]] && URLS="${URLS};" && KEYS="${KEYS};"
            URLS="${URLS}http://host.docker.internal:8080/v1"
            KEYS="${KEYS}mlx"
        fi

        # 2. Ollama (GGUF Engine)
        if lsof -i :11434 > /dev/null 2>&1; then
            echo "🦙 Bridging Ollama (Engine) -> WebUI..."
            [[ -n "$URLS" ]] && URLS="${URLS};" && KEYS="${KEYS};"
            URLS="${URLS}http://host.docker.internal:11434/v1"
            KEYS="${KEYS}ollama"
        fi

        WEBUI_ENV="-e OPENAI_API_BASE_URLS=${URLS} -e OPENAI_API_KEYS=${KEYS} -e ENABLE_OLLAMA_API=false -e OLLAMA_BASE_URL='' -e OLLAMA_API_BASE_URL=''"
        [[ -z "$URLS" ]] && WEBUI_ENV=""

        docker run -d \
          -p 3001:8080 \
          --add-host=host.docker.internal:host-gateway \
          $WEBUI_ENV \
          -v px-open-webui:/app/backend/data \
          --name "$CONTAINER_NAME" \
          --restart always \
          ghcr.io/open-webui/open-webui:main

        echo "✅ UI Launched."
        echo "   Waiting for startup..."
        sleep 5
        echo "🌐 Opening http://127.0.0.1:3001..."
        open "http://127.0.0.1:3001"
        ;;
esac
