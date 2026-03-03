import os
from pathlib import Path


def render(context, config, paths):
    """
    Renders the 'Workflow' pillar for Requirements, Design, and Tasks.
    """
    output = []
    LIBRARY_ROOT = paths.get("LIBRARY_ROOT", "")
    PROJECT_ROOT = Path(os.getcwd())
    WORKFLOW_DIR = PROJECT_ROOT / "docs" / "workflow"

    if context == "workflow":
        output.append(
            {
                "label": "📁 Requirements",
                "type": "FOLDER",
                "payload": "workflow:requirements",
            }
        )
        output.append(
            {"label": "🎨 Design Docs", "type": "FOLDER", "payload": "workflow:design"}
        )
        output.append(
            {"label": "✅ Tasks", "type": "FOLDER", "payload": "workflow:tasks"}
        )
        output.append({"label": "------------------------------", "type": "SEPARATOR"})
        output.append(
            {
                "label": "🏗️  Design Mode (Scaffolding)",
                "type": "FOLDER",
                "payload": "workflow:scaffold",
            }
        )
        output.append(
            {
                "label": "📊 Intelligence Dashboard",
                "type": "ACTION",
                "path": f"execute(library/actions/intel/dashboard && read)",
            }
        )
        return output

    elif context == "workflow:scaffold":
        output.append(
            {
                "label": "✨ New Requirement",
                "type": "ACTION",
                "path": "execute(px-workflow new requirement REQ-NEW 'Title')",
            }
        )
        output.append(
            {
                "label": "🎨 New Design",
                "type": "ACTION",
                "path": "execute(px-workflow new design DSN-NEW 'Title')",
            }
        )
        output.append(
            {
                "label": "✅ New Task",
                "type": "ACTION",
                "path": "execute(px-workflow new task TSK-NEW 'Title')",
            }
        )
        return output

    elif context.startswith("workflow:"):
        sub_type = context.split(":")[1]
        target_dir = WORKFLOW_DIR / sub_type

        NEXUS_STATE = os.getenv("NEXUS_STATE", f"/tmp/nexus_{os.getenv('USER')}")
        LAST_PATH_FILE = Path(NEXUS_STATE) / "last_path"

        if not target_dir.exists():
            output.append({"label": f"(No {sub_type} found)", "type": "DISABLED"})
            return output

        # List markdown files in the directory
        for f in sorted(target_dir.glob("*.md")):
            if f.name == "README.md":
                continue

            status = "Unknown"
            links = []
            with open(f, "r") as content:
                for line in content:
                    if "Status:" in line:
                        status = line.split("Status:")[1].strip()
                    # Parse Markdown links: [LABEL](PATH)
                    import re

                    matches = re.findall(r"\[(.*?)\]\((.*?)\)", line)
                    for label, path in matches:
                        if (
                            label.startswith("REQ-")
                            or label.startswith("DSN-")
                            or label.startswith("TSK-")
                        ):
                            links.append(label)

            label_str = f"📄 {f.name}"
            if links:
                label_str += f" 🔗 {','.join(links)}"

            output.append(
                {
                    "label": f"{label_str:<40} [{status}]",
                    "type": "ACTION",
                    "path": f"execute(echo {str(f)} > {str(LAST_PATH_FILE)})",
                }
            )
            # Add action to open in Editor Tab
            output.append(
                {
                    "label": f"  ↳ 📝 Open as Editor Tab",
                    "type": "ACTION",
                    "path": f"execute(nvim --server $NEXUS_PIPE --remote-send '<Esc>:tabedit {str(f)}<CR>')",
                }
            )

        # Action to create new item
        output.append(
            {
                "label": f"✨ New {sub_type[:-1].title()}",
                "type": "ACTION",
                "path": f"execute(touch {str(target_dir)}/NEW.md && ${{EDITOR:-vi}} {str(target_dir)}/NEW.md)",
            }
        )

        return output

    return None
