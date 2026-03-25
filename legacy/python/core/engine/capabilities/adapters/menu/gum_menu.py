import os
import subprocess
import shutil
from typing import List, Optional
from ...base import MenuCapability, AdapterManifest, CapabilityType

class GumMenuAdapter(MenuCapability):
    """Implementation of MenuCapability using the bash 'gum' tool."""

    manifest = AdapterManifest(
        name="gum",
        capability_type=CapabilityType.MENU,
        binary="gum",
        priority=80,
    )

    @property
    def capability_type(self):
        from ...base import CapabilityType
        return CapabilityType.MENU

    @property
    def capability_id(self): return "gum"

    def is_available(self) -> bool:
        return shutil.which("gum") is not None

    def show_menu(self, options: List[str], prompt: str = "Select:") -> Optional[str]:
        if not options:
            return None

        try:
            import tempfile
            # Gum renders TUI via /dev/tty. We must NOT capture stdout/stderr
            # with subprocess.PIPE — that swallows the TUI rendering.
            # Instead, redirect gum's stdout to a temp file in the shell command.
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.out') as f:
                out_name = f.name
            items_str = "\n".join(options)
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(items_str)
                in_name = f.name
            cmd = f"gum choose --header {shutil.quote(prompt)} {' '.join(shutil.quote(o) for o in options)} > {out_name}"
            result = subprocess.run(cmd, shell=True)
            os.unlink(in_name)
            if result.returncode == 0 and os.path.exists(out_name):
                answer = open(out_name).read().strip()
                os.unlink(out_name)
                return answer if answer else None
            if os.path.exists(out_name):
                os.unlink(out_name)
            return None
        except Exception:
            return None

    def pick(self, context: str, items_json: List[str]) -> Optional[str]:
        if not items_json:
            return None

        import json
        import sys

        try:
            parsed_items = [json.loads(line) for line in items_json if line.strip()]
        except json.JSONDecodeError as e:
            print(f"[INVARIANT] GumMenu.pick: JSON parse failed on items. "
                  f"Context: '{context}', First item: {items_json[0][:80] if items_json else 'empty'}, "
                  f"Error: {e}", file=sys.stderr)
            return None

        labels = [item.get("label", "Unknown") for item in parsed_items]
        labels_str = "\n".join(labels)

        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(labels_str)
                temp_name = f.name

            # CRITICAL: Do NOT use stdout=PIPE or stderr=PIPE — that swallows
            # gum's TUI rendering. Gum renders via /dev/tty when stdout is not
            # a terminal, but Python's PIPE prevents this. Instead, redirect
            # gum's stdout to a temp file in the shell command itself.
            import tempfile as _tf
            with _tf.NamedTemporaryFile(mode='w', delete=False, suffix='.out') as of:
                out_name = of.name

            gum_cmd = (
                f"gum filter"
                f" --placeholder='Nexus Pulse: {context}...'"
                f" --indicator='→'"
                f" --match.foreground='#00FFFF'"
                f" < {temp_name} > {out_name}"
            )
            process = subprocess.run(gum_cmd, shell=True)
            os.unlink(temp_name)

            if process.returncode == 0 and os.path.exists(out_name):
                selected_label = open(out_name).read().strip()
                os.unlink(out_name)
                for line in items_json:
                    if json.loads(line).get("label") == selected_label:
                        return line
                # ── Negative Space: selected label didn't match any item ──
                print(f"[INVARIANT] GumMenu.pick: User selected '{selected_label}' but no item matched. "
                      f"Available labels: {labels[:5]}{'...' if len(labels) > 5 else ''}",
                      file=sys.stderr)
            elif process.returncode == 130:
                if os.path.exists(out_name): os.unlink(out_name)
                return None  # User pressed Esc/Ctrl-C — normal cancellation
            else:
                if os.path.exists(out_name): os.unlink(out_name)
                print(f"[INVARIANT] gum filter exited with code {process.returncode}. "
                      f"Context: '{context}'",
                      file=sys.stderr)
            return None
        except Exception as e:
            print(f"[INVARIANT] GumMenu.pick exception: {e}. "
                  f"Context: '{context}', items_count: {len(items_json)}",
                  file=sys.stderr)
            return None

