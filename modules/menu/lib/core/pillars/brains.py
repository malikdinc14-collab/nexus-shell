import os
import json
from pathlib import Path


def render(context, config, paths):
    """
    Renders the 'Brains' pillar and its sub-contexts.
    """
    output = []
    LIBRARY_ROOT = paths.get("LIBRARY_ROOT", "")
    NEXUS_SCRIPTS = os.getenv(
        "NEXUS_SCRIPTS", os.path.expanduser("~/.config/nexus-shell/scripts")
    )

    # 1. Main Brains Hub (The Command Center)
    if context == "brains":
        # -- Section 1: Pulse & Real-time Status --
        output.append(
            {
                "label": "📊 Intelligence Dashboard",
                "type": "ACTION",
                "path": f"execute({str(LIBRARY_ROOT)}/actions/intel/dashboard && read)",
            }
        )

        # Resource Guard Toggle
        is_guarded = os.path.exists("/tmp/px-resource-guard.pid")
        output.append(
            {
                "label": f"🛡️  Resource Guard: {'✅ ON' if is_guarded else '❌ OFF'}",
                "type": "ACTION",
                "path": f"execute(export ACTION={'stop' if is_guarded else 'start'}; {str(LIBRARY_ROOT)}/actions/intel/resource-guard && read)",
            }
        )

        output.append(
            {"label": "⚙️  Ghost Settings", "type": "FOLDER", "payload": "intel:ghost"}
        )
        output.append({"label": "------------------------------", "type": "SEPARATOR"})

        # -- Section 2: Model Management --
        output.append(
            {"label": "📁 Local Model Registry", "type": "FOLDER", "payload": "models"}
        )
        output.append(
            {
                "label": "📁 Compute Engines (Intel)",
                "type": "FOLDER",
                "payload": "library:actions:intel",
            }
        )
        output.append({"label": "------------------------------", "type": "SEPARATOR"})

        # -- Section 3: Advanced Cognitive Layers --
        output.append(
            {
                "label": "📁 Tiered Memory (Letta)",
                "type": "FOLDER",
                "payload": "intel:letta",
            }
        )
        output.append(
            {
                "label": "📁 Cognitive Evolution (MemEvolve)",
                "type": "FOLDER",
                "payload": "intel:memevolve",
            }
        )
        output.append(
            {
                "label": "📁 Infinite Context (RLM)",
                "type": "FOLDER",
                "payload": "intel:rlm",
            }
        )
        output.append({"label": "------------------------------", "type": "SEPARATOR"})

        # -- Section 4: The Lab --
        output.append(
            {
                "label": "🧪 HuggingFace Lab",
                "type": "ACTION",
                "path": f"execute({str(LIBRARY_ROOT)}/actions/intel/hf-lab && read)",
            }
        )
        output.append(
            {
                "label": "📺 Visualisation Hub",
                "type": "FOLDER",
                "payload": "intel:visual",
            }
        )
        output.append(
            {
                "label": "🖼️  Visual Renderer (Mermaid)",
                "type": "ACTION",
                "path": f"execute({str(LIBRARY_ROOT)}/actions/intel/install-visual && read)",
            }
        )
        output.append({"label": "------------------------------", "type": "SEPARATOR"})

        # -- Section 5: Emergency --
        output.append(
            {
                "label": "🛑 Kill Active Brain (8080)",
                "type": "ACTION",
                "path": f"execute(export PORT=8080; {str(LIBRARY_ROOT)}/actions/intel/kill-brain && read)",
            }
        )
        output.append(
            {
                "label": "🛑 Kill Active Brain (8081)",
                "type": "ACTION",
                "path": f"execute(export PORT=8081; {str(LIBRARY_ROOT)}/actions/intel/kill-brain && read)",
            }
        )
        output.append(
            {
                "label": "📉 Unload All Brains",
                "type": "ACTION",
                "path": f"execute({str(NEXUS_SCRIPTS)}/unload_brains.sh && read)",
            }
        )
        return output

    # 4. Letta Context
    elif context == "intel:letta":
        output.append(
            {
                "label": "🚀 Start Letta Server",
                "type": "ACTION",
                "path": f"execute(export ACTION=start; {str(LIBRARY_ROOT)}/actions/intel/letta)",
            }
        )
        output.append(
            {
                "label": "🔗 Link OpenCode to Letta",
                "type": "ACTION",
                "path": f"execute(export ACTION=link; {str(LIBRARY_ROOT)}/actions/intel/bridge-opencode && read)",
            }
        )
        output.append(
            {
                "label": "💬 Chat with Letta",
                "type": "ACTION",
                "path": f"execute(export ACTION=chat; {str(LIBRARY_ROOT)}/actions/intel/letta)",
            }
        )
        output.append(
            {
                "label": "📥 Install/Update Letta",
                "type": "ACTION",
                "path": f"execute(export ACTION=install; {str(LIBRARY_ROOT)}/actions/intel/letta)",
            }
        )
        return output

    # 5. MemEvolve Context
    elif context == "intel:memevolve":
        output.append(
            {
                "label": "🧠 Evolve Active Session",
                "type": "ACTION",
                "path": f"execute(export ACTION=optimize; {str(LIBRARY_ROOT)}/actions/intel/memevolve)",
            }
        )
        output.append(
            {
                "label": "📊 Show Memory Status",
                "type": "ACTION",
                "path": f"execute(export ACTION=status; {str(LIBRARY_ROOT)}/actions/intel/memevolve && read)",
            }
        )
        output.append(
            {
                "label": "📥 Install Dependencies",
                "type": "ACTION",
                "path": f"execute(export ACTION=install; {str(LIBRARY_ROOT)}/actions/intel/memevolve)",
            }
        )
        return output

    # 6. RLM Context
    elif context == "intel:rlm":
        output.append(
            {
                "label": "🔄 Run Recursive Inference",
                "type": "ACTION",
                "path": f"execute(export ACTION=run; {str(LIBRARY_ROOT)}/actions/intel/rlm)",
            }
        )
        output.append(
            {
                "label": "📥 Install RLM Scaffolds",
                "type": "ACTION",
                "path": f"execute(export ACTION=install; {str(LIBRARY_ROOT)}/actions/intel/rlm)",
            }
        )
        output.append(
            {
                "label": "❓ RLM Info",
                "type": "ACTION",
                "path": f"execute(export ACTION=status; {str(LIBRARY_ROOT)}/actions/intel/rlm && read)",
            }
        )
        output.append(
            {
                "label": "🔧 Setup AI LSP (Neovim)",
                "type": "ACTION",
                "path": f"execute({str(LIBRARY_ROOT)}/actions/intel/setup-lsp && read)",
            }
        )
        return output

    # 7. Ghost Orchestration Context
    elif context == "intel:ghost":
        # Toggle Auto-Exec
        auto_exec = os.getenv("PX_AGENT_AUTO_EXEC", "true")
        output.append(
            {
                "label": f"⚡ Auto-Execute: {'✅ ON' if auto_exec == 'true' else '❌ OFF'}",
                "type": "ACTION",
                "path": f"execute(export PX_AGENT_AUTO_EXEC={'false' if auto_exec == 'true' else 'true'}; px-register set PX_AGENT_AUTO_EXEC {'false' if auto_exec == 'true' else 'true'} && read)",
            }
        )

        # Toggle Live-Edit mode
        live_edit = os.getenv("PX_AGENT_LIVE_EDIT", "overwrite")
        output.append(
            {
                "label": f"📝 Edit Mode: {live_edit.upper()}",
                "type": "ACTION",
                "path": f"execute(export PX_AGENT_LIVE_EDIT={'diff' if live_edit == 'overwrite' else 'overwrite'}; px-register set PX_AGENT_LIVE_EDIT {'diff' if live_edit == 'overwrite' else 'overwrite'} && read)",
            }
        )

        # Toggle Trace Mode
        trace_mode = os.getenv("PX_AGENT_TRACE_MODE", "clean")
        output.append(
            {
                "label": f"📈 Trace Mode: {trace_mode.upper()}",
                "type": "ACTION",
                "path": f"execute(export PX_AGENT_TRACE_MODE={'raw' if trace_mode == 'clean' else 'clean'}; px-register set PX_AGENT_TRACE_MODE {'raw' if trace_mode == 'clean' else 'clean'} && read)",
            }
        )

        output.append({"label": "------------------------------", "type": "SEPARATOR"})
        output.append(
            {
                "label": "🛑 Kill Active Agents",
                "type": "ACTION",
                "path": f"execute({str(NEXUS_SCRIPTS)}/kill_agent.sh && read)",
            }
        )
        output.append(
            {
                "label": "📉 Unload All Brains",
                "type": "ACTION",
                "path": f"execute({str(NEXUS_SCRIPTS)}/unload_brains.sh && read)",
            }
        )

        return output

    # 7. Ghost Orchestration Context
    elif context == "intel:ghost":
        # ... existing ghost logic ...
        # (keeping it simple for the edit)
        return output

    # 8. Visualisation Context
    elif context == "intel:visual":
        output.append(
            {
                "label": "🖥️  Open Monitor Window (Alt+M)",
                "type": "ACTION",
                "path": "execute(tmux select-window -t :2)",
            }
        )
        output.append(
            {
                "label": "📊 Pop-up mactop",
                "type": "ACTION",
                "path": "execute(px-pop mactop)",
            }
        )
        output.append(
            {
                "label": "📈 Pop-up Agent Logs",
                "type": "ACTION",
                "path": "execute(px-pop 'tail -f /tmp/px-agent-trace.log')",
            }
        )
        output.append(
            {
                "label": "🔍 Pop-up Resource Guard",
                "type": "ACTION",
                "path": "execute(px-pop 'tail -f /tmp/px-resource-guard.log')",
            }
        )
        output.append({"label": "------------------------------", "type": "SEPARATOR"})
        output.append(
            {
                "label": "🔄 Switch Center to Monitor",
                "type": "ACTION",
                "path": "execute(px-view-switch monitor)",
            }
        )
        output.append(
            {
                "label": "📝 Switch Center to Editor",
                "type": "ACTION",
                "path": "execute(px-view-switch editor)",
            }
        )

        return output
        output.append({"label": "📁 LLM", "type": "FOLDER", "payload": "models:llm"})
        output.append(
            {"label": "📁 Vision", "type": "FOLDER", "payload": "models:vision"}
        )
        output.append(
            {"label": "📁 Audio", "type": "FOLDER", "payload": "models:audio"}
        )
        output.append(
            {"label": "📁 Embeddings", "type": "FOLDER", "payload": "models:embeddings"}
        )
        return output

    # 3. Dynamic Model Hierarchy
    elif context.startswith("models:"):
        parts = context.split(":")

        # Level 2: Format Selection (models:llm -> GGUF/MLX)
        if len(parts) == 2:
            capability = parts[1]
            output.append(
                {
                    "label": "📁 GGUF",
                    "type": "FOLDER",
                    "payload": f"models:{capability}:gguf",
                }
            )
            output.append(
                {
                    "label": "📁 MLX",
                    "type": "FOLDER",
                    "payload": f"models:{capability}:mlx",
                }
            )
            return output

        # Level 3: The Actual Models (models:llm:gguf)
        elif len(parts) == 3:
            capability = parts[1]
            fmt = parts[2]

            # Action logic based on format
            actions = []
            if fmt == "gguf":
                actions = [
                    ("📥 Import to Ollama", f"px-models import-gguf '{{model}}'"),
                    ("💬 Chat with Ollama", f"ollama run '{{model_name}}'"),
                    ("🧠 Serve with Ollama", f"ollama serve '{{model_name}}'"),
                ]
            elif fmt == "mlx":
                actions = [
                    (
                        "🚀 Serve with MLX",
                        f"ACTION=start MODEL='{{model}}' library/actions/intel/mlx",
                    ),
                    (
                        "💬 Chat with MLX",
                        f"ACTION=chat MODEL='{{model}}' library/actions/intel/mlx",
                    ),
                ]

            # Resolve Public Bin (where px-models lives)
            # BIN_DIR passed in is lib/exec, so we go up twice to .parallax, then into bin
            import subprocess
            from pathlib import Path

            BIN_DIR = Path(paths["BIN_DIR"])
            # PX_MODELS is simply in the bin directory
            PX_MODELS = BIN_DIR / "px-models"

            # Fallback for dev environment (Projects/parallax/bin)
            if not PX_MODELS.exists():
                # Try typical dev path resolved relative to this file?
                # Or just check /usr/local/bin
                if Path("/usr/local/bin/px-models").exists():
                    PX_MODELS = Path("/usr/local/bin/px-models")

            if PX_MODELS.exists():
                try:
                    # px-models list <capability> <fmt>
                    # output format: model_name
                    cmd = [str(PX_MODELS), "list", capability, fmt]
                    result = (
                        subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
                        .decode()
                        .strip()
                    )

                    if not result:
                        output.append(
                            {
                                "label": f"(No {capability} {fmt} models found)",
                                "type": "DISABLED",
                            }
                        )
                    else:
                        for line in result.split("\n"):
                            if not line.strip():
                                continue
                            model_name = line.strip()

                            # Determine primary action based on format
                            if fmt == "gguf":
                                # Quick Action: Import
                                is_imported = False
                                # Check if imported (this might be slow, maybe skip check or optimize)
                                # For now, provide the Import action as primary
                                output.append(
                                    {
                                        "label": f"📦 {model_name}",
                                        "type": "ACTION",
                                        "path": f"execute(px-models import-gguf '{model_name}' && echo '>>> Done.' && read)",
                                    }
                                )
                            elif fmt == "mlx":
                                # Quick Action: Serve
                                output.append(
                                    {
                                        "label": f"🚀 {model_name}",
                                        "type": "ACTION",
                                        "path": f"execute(export ACTION=start MODEL='{model_name}'; {str(LIBRARY_ROOT)}/actions/intel/mlx)",
                                    }
                                )
                except Exception as e:
                    output.append(
                        {"label": f"Error scanning models: {e}", "type": "DISABLED"}
                    )
            else:
                output.append(
                    {"label": "Error: px-models binary not found", "type": "DISABLED"}
                )

            return output

    return None
