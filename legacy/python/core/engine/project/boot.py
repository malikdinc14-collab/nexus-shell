"""Boot runner — executes project boot lists on workspace attach."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BootProcess:
    """A tracked background process started by a boot list."""

    label: str
    pid: int
    process: subprocess.Popen

    def is_alive(self) -> bool:
        return self.process.poll() is None

    def kill(self, timeout: float = 5.0) -> None:
        """Gracefully terminate, then force kill."""
        if not self.is_alive():
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=2.0)
        except Exception:
            logger.warning("Failed to kill boot process %s (pid %d)", self.label, self.pid)


@dataclass
class BootResult:
    """Result of a boot sequence execution."""

    total: int = 0
    completed: int = 0
    failed: int = 0
    background: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.failed == 0


class BootRunner:
    """Executes boot list items and tracks background processes."""

    def __init__(
        self,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ):
        self._processes: List[BootProcess] = []
        self._on_progress = on_progress

    @property
    def processes(self) -> List[BootProcess]:
        """Currently tracked background processes."""
        return list(self._processes)

    def run(
        self,
        items: List[Dict[str, Any]],
        cwd: str = "",
        env_override: Optional[Dict[str, str]] = None,
    ) -> BootResult:
        """Execute boot items sequentially.

        - `wait: true` items block until complete.
        - `wait: false` items start in the background and are tracked.
        - If a `wait: true` item fails, subsequent items still execute
          but the failure is recorded.
        """
        result = BootResult(total=len(items))
        work_dir = cwd or os.getcwd()

        for i, item in enumerate(items):
            label = item.get("label", f"boot-{i}")
            command = item["run"]
            wait = item.get("wait", False)
            item_env = dict(os.environ)
            if env_override:
                item_env.update(env_override)
            if item.get("env"):
                item_env.update(item["env"])

            self._report_progress(i + 1, result.total, label)

            try:
                if wait:
                    self._run_blocking(label, command, work_dir, item_env, result)
                else:
                    self._run_background(label, command, work_dir, item_env, result)
            except Exception as e:
                result.failed += 1
                result.errors.append(f"{label}: {e}")
                logger.error("Boot item '%s' raised: %s", label, e)

        return result

    def shutdown(self) -> int:
        """Kill all tracked background processes. Returns count killed."""
        killed = 0
        for bp in self._processes:
            if bp.is_alive():
                logger.info("Shutting down boot process: %s (pid %d)", bp.label, bp.pid)
                bp.kill()
                killed += 1
        self._processes.clear()
        return killed

    def _run_blocking(
        self,
        label: str,
        command: str,
        cwd: str,
        env: Dict[str, str],
        result: BootResult,
    ) -> None:
        """Run a command and wait for completion."""
        logger.info("Boot [blocking]: %s", label)
        proc = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max for blocking items
        )
        if proc.returncode == 0:
            result.completed += 1
            logger.info("Boot [blocking] OK: %s", label)
        else:
            result.failed += 1
            stderr = proc.stderr.strip()[:200] if proc.stderr else "(no stderr)"
            result.errors.append(f"{label}: exit {proc.returncode} — {stderr}")
            logger.warning("Boot [blocking] FAILED: %s (exit %d)", label, proc.returncode)

    def _run_background(
        self,
        label: str,
        command: str,
        cwd: str,
        env: Dict[str, str],
        result: BootResult,
    ) -> None:
        """Start a command in the background and track it."""
        logger.info("Boot [background]: %s", label)
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        bp = BootProcess(label=label, pid=proc.pid, process=proc)
        self._processes.append(bp)
        result.background += 1
        result.completed += 1
        logger.info("Boot [background] started: %s (pid %d)", label, proc.pid)

    def _report_progress(self, current: int, total: int, label: str) -> None:
        """Report progress to callback if registered."""
        if self._on_progress:
            try:
                self._on_progress(current, total, label)
            except Exception:
                pass
