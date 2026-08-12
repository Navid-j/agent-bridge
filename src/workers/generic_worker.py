"""Generic worker — run any CLI command as the coding agent.

For advanced users who want to plug in a different agent (Codex, Aider,
Claude Code, a custom script...). The task is appended to the command
argv; stdout/stderr become the report.
"""

from __future__ import annotations

import subprocess

from ..utils import SESSION_DIR, log
from .base import Worker, WorkerResult


class GenericWorker(Worker):
    def __init__(
        self,
        *,
        binary: str,
        args: list[str] | None = None,
        cwd: str = "",
        timeout: int = 1800,
        verbose: bool = True,
    ) -> None:
        self.binary = binary
        self.args = list(args or [])
        self.cwd = cwd
        self.timeout = timeout
        self.verbose = verbose

    def run(self, task: str) -> WorkerResult:
        cmd = [self.binary] + self.args + [task]
        log(f"worker (generic: {self.binary}) starting", self.verbose)
        proc = subprocess.run(
            cmd, cwd=self.cwd or None, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=self.timeout,
        )
        transcript = (proc.stdout or "") + "\n----- STDERR -----\n" + (proc.stderr or "")
        SESSION_DIR.mkdir(exist_ok=True)
        (SESSION_DIR / f"worker_run_{proc.returncode}.txt").write_text(transcript, encoding="utf-8")
        return WorkerResult(
            exit_code=proc.returncode,
            summary=(transcript.strip() or "no output")[:4000],
            transcript=transcript,
        )