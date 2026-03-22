"""
Async resolver for Live Source nodes in the Command Graph.

Provides a registry for live source resolvers and async resolution
with timeout handling and TTL-based caching.
"""

import asyncio
import logging
import os
import time
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class LiveSourceRegistry:
    """Registry for live source resolver functions."""

    def __init__(self):
        self._resolvers: Dict[str, Callable] = {}
        self._register_builtins()

    def register(self, name: str, resolver_fn: Callable):
        """Register a resolver function by name."""
        self._resolvers[name] = resolver_fn

    def get(self, name: str) -> Optional[Callable]:
        """Return registered resolver or None."""
        return self._resolvers.get(name)

    def _register_builtins(self):
        """Pre-register all built-in resolvers."""
        self.register("nexus.live.current_composition", _resolve_current_composition)
        self.register("nexus.live.current_profile", _resolve_current_profile)
        self.register("nexus.live.suggested_packs", _resolve_suggested_packs)
        self.register("nexus.live.enabled_packs", _resolve_enabled_packs)
        self.register("nexus.live.active_tabs", _resolve_active_tabs)
        self.register("nexus.live.processes", _resolve_processes)
        self.register("nexus.live.ports", _resolve_ports)
        self.register("nexus.live.git_status", _resolve_git_status)
        self.register("nexus.live.connectors", _resolve_connectors)
        self.register("nexus.live.agent_status", _resolve_agent_status)


# ---------------------------------------------------------------------------
# Helper: run a subprocess and return stdout as a stripped string
# ---------------------------------------------------------------------------

async def _run_cmd(*args: str) -> str:
    """Run a command via asyncio subprocess and return stripped stdout."""
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode("utf-8", errors="replace").strip()


# ---------------------------------------------------------------------------
# Built-in resolvers
# ---------------------------------------------------------------------------

async def _resolve_current_composition() -> str:
    """Get active tmux session name as the current composition."""
    try:
        name = await _run_cmd("tmux", "display-message", "-p", "#S")
        return name if name else "(default)"
    except Exception:
        return "(default)"


async def _resolve_current_profile() -> str:
    """Check NEXUS_PROFILE env var for the active profile."""
    try:
        profile = os.environ.get("NEXUS_PROFILE", "")
        return profile if profile else "(none)"
    except Exception:
        return "(none)"


async def _resolve_suggested_packs() -> str:
    """Scan cwd for pack marker files and return a count."""
    try:
        markers = [
            "Pipfile", "Cargo.toml", "Dockerfile", "package.json",
            "go.mod", "Makefile", "pyproject.toml", "Gemfile",
            "composer.json", "pom.xml",
        ]
        cwd = os.getcwd()
        found = sum(1 for m in markers if os.path.exists(os.path.join(cwd, m)))
        return f"{found} suggested" if found > 0 else "(none)"
    except Exception:
        return "(none)"


async def _resolve_enabled_packs() -> str:
    """Check NEXUS_PACKS env var for enabled packs."""
    try:
        packs = os.environ.get("NEXUS_PACKS", "")
        if not packs:
            return "(none enabled)"
        items = [p.strip() for p in packs.split(",") if p.strip()]
        return f"{len(items)} enabled" if items else "(none enabled)"
    except Exception:
        return "(none enabled)"


async def _resolve_active_tabs() -> str:
    """Count tmux panes as active tabs."""
    try:
        output = await _run_cmd("tmux", "list-panes", "-F", "#{pane_id}")
        if not output:
            return "(no tabs)"
        count = len(output.splitlines())
        return f"{count} panes" if count > 0 else "(no tabs)"
    except Exception:
        return "(no tabs)"


async def _resolve_processes() -> str:
    """Count child processes across tmux panes."""
    try:
        output = await _run_cmd("tmux", "list-panes", "-F", "#{pane_pid}")
        if not output:
            return "0 running"
        count = len(output.splitlines())
        return f"{count} running"
    except Exception:
        return "0 running"


async def _resolve_ports() -> str:
    """Find listening TCP ports via lsof."""
    try:
        output = await _run_cmd("lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n")
        if not output:
            return "(none open)"
        ports = set()
        for line in output.splitlines()[1:]:  # skip header
            parts = line.split()
            for part in parts:
                if ":" in part and part.split(":")[-1].isdigit():
                    ports.add(part.split(":")[-1])
        if not ports:
            return "(none open)"
        sorted_ports = sorted(ports, key=int)
        return ",".join(sorted_ports)
    except Exception:
        return "(none open)"


async def _resolve_git_status() -> str:
    """Get git branch and modified/untracked counts."""
    try:
        cwd = os.getcwd()
        branch = await _run_cmd("git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD")
        if not branch:
            return "(not a repo)"
        porcelain = await _run_cmd("git", "-C", cwd, "status", "--porcelain")
        if not porcelain:
            return f"{branch} (clean)"
        lines = porcelain.splitlines()
        modified = sum(1 for l in lines if l and l[0] in ("M", "A", "D", "R", "C"))
        untracked = sum(1 for l in lines if l.startswith("?"))
        return f"{branch} +{modified}/-{untracked}"
    except Exception:
        return "(not a repo)"


async def _resolve_connectors() -> str:
    """Check NEXUS_CONNECTORS env or count .yaml files in .nexus/connectors/."""
    try:
        env_val = os.environ.get("NEXUS_CONNECTORS", "")
        if env_val:
            items = [c.strip() for c in env_val.split(",") if c.strip()]
            return f"{len(items)} active"
        connectors_dir = os.path.join(os.getcwd(), ".nexus", "connectors")
        if os.path.isdir(connectors_dir):
            yamls = [f for f in os.listdir(connectors_dir) if f.endswith(".yaml")]
            return f"{len(yamls)} active"
        return "(0 active)"
    except Exception:
        return "(0 active)"


async def _resolve_agent_status() -> str:
    """Check if an AI agent process (opencode) is running."""
    try:
        output = await _run_cmd("pgrep", "-f", "opencode")
        if output:
            return "opencode"
        return "(idle)"
    except Exception:
        return "(idle)"


# Cache: maps resolver_name -> (result, timestamp)
_cache: Dict[str, tuple] = {}

# Default registry instance
_registry = LiveSourceRegistry()


def get_registry() -> LiveSourceRegistry:
    """Return the default LiveSourceRegistry instance."""
    return _registry


async def resolve_live_source(
    node_id: str,
    resolver_name: str,
    timeout_ms: int = 3000,
    cache_ttl_s: int = 30,
) -> str:
    """Resolve a single live source node.

    Looks up resolver_name in the registry, calls it with a timeout,
    and caches results by resolver_name for cache_ttl_s seconds.
    """
    now = time.monotonic()

    # Check cache
    if resolver_name in _cache:
        cached_result, cached_at = _cache[resolver_name]
        if now - cached_at < cache_ttl_s:
            return cached_result

    resolver_fn = _registry.get(resolver_name)
    if resolver_fn is None:
        logger.warning("No resolver registered for '%s' (node=%s)", resolver_name, node_id)
        return "(error)"

    try:
        result = await asyncio.wait_for(
            resolver_fn(),
            timeout=timeout_ms / 1000.0,
        )
    except asyncio.TimeoutError:
        logger.warning("Resolver '%s' timed out after %dms (node=%s)", resolver_name, timeout_ms, node_id)
        return "(loading...)"
    except Exception:
        logger.warning("Resolver '%s' failed (node=%s)", resolver_name, node_id, exc_info=True)
        return "(error)"

    _cache[resolver_name] = (result, time.monotonic())
    return result


async def resolve_all_live_sources(
    nodes: List[dict],
    timeout_ms: int = 3000,
) -> Dict[str, str]:
    """Resolve all live source nodes in parallel.

    Each node dict should have: node_id, resolver, and optionally
    timeout_ms and cache_ttl_s.
    """
    if not nodes:
        return {}

    async def _resolve_one(node: dict) -> tuple:
        node_id = node["node_id"]
        resolver = node["resolver"]
        t = node.get("timeout_ms", timeout_ms)
        ttl = node.get("cache_ttl_s", 30)
        result = await resolve_live_source(node_id, resolver, t, ttl)
        return (node_id, result)

    results = await asyncio.gather(*[_resolve_one(n) for n in nodes])
    return dict(results)


def clear_cache():
    """Clear the resolution cache. Useful for testing."""
    _cache.clear()
