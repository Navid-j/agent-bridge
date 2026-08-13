"""Agent manager — a second agent (CLI) acts as the task manager.

This makes the bridge fully agent-to-agent: one agent (the manager) decides
the next task, another agent (the worker) implements it. No human and no
LLM vendor is in the loop.
"""

from __future__ import annotations

import subprocess

from ..config import defaults
from ..utils import command_prefix
from .base import Manager


class AgentManager(Manager):
    """Drive any CLI agent as the task manager."""

    def __init__(self, *, binary: str | None = None, args: list[str] | None = None, model: str | None = None) -> None:
        d = defaults()["manager"]["agent"]
        self.binary = binary or d["binary"]
        self.args = list(args or d.get("args") or [])
        self.model = model

    def get_next_task(self, report: str) -> str:
        cmd = command_prefix(self.binary)
        if self.model:
            cmd += ["--model", self.model]
        cmd += self.args + [report]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if proc.returncode != 0:
            raise RuntimeError(f"manager agent failed ({proc.returncode}): {proc.stderr[-500:]}")
        out = (proc.stdout or "").strip()
        return out or "DONE"