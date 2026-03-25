"""HUD Module framework — pack-driven status bar widgets."""
from dataclasses import dataclass
from typing import Dict, Optional, Callable
import logging
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class HudModuleResult:
    """Result from a HUD module resolver."""
    text: str
    color: Optional[str] = None
    icon: Optional[str] = None


# Built-in resolver functions

def _git_branch() -> HudModuleResult:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=2
        ).stdout.strip()
        return HudModuleResult(text=branch or "no-repo", icon="branch")
    except Exception:
        return HudModuleResult(text="no-repo")


def _clock() -> HudModuleResult:
    from datetime import datetime
    return HudModuleResult(text=datetime.now().strftime("%H:%M"))


def _python_version() -> HudModuleResult:
    import sys
    return HudModuleResult(text=f"py{sys.version_info.major}.{sys.version_info.minor}")


def _word_count() -> HudModuleResult:
    # Counts words in current tmux pane's file (placeholder)
    return HudModuleResult(text="words: --")


def _cpu() -> HudModuleResult:
    try:
        import sys as _sys
        load = subprocess.run(
            ["sysctl", "-n", "vm.loadavg"] if _sys.platform == "darwin"
            else ["cat", "/proc/loadavg"],
            capture_output=True, text=True, timeout=2
        ).stdout.strip().split()[0].strip("{}")
        return HudModuleResult(text=f"cpu:{load}")
    except Exception:
        return HudModuleResult(text="cpu:--")


def _memory() -> HudModuleResult:
    # Simple memory usage placeholder
    return HudModuleResult(text="mem:--")


# Registry of built-in resolvers
BUILTIN_RESOLVERS: Dict[str, Callable[[], HudModuleResult]] = {
    "git_branch": _git_branch,
    "clock": _clock,
    "python_version": _python_version,
    "word_count": _word_count,
    "cpu": _cpu,
    "memory": _memory,
}


def resolve_module(module_id: str) -> HudModuleResult:
    """Resolve a HUD module by ID. Returns placeholder if unknown."""
    resolver = BUILTIN_RESOLVERS.get(module_id)
    if resolver:
        try:
            return resolver()
        except Exception:
            logger.warning("HUD resolver %s failed", module_id, exc_info=True)
    return HudModuleResult(text=f"{module_id}:--")
