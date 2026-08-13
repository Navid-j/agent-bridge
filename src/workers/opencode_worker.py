"""OpenCode worker — run tasks with the opencode CLI.

opencode is the default coding agent. It is invoked non-interactively with
``--format json`` so the transcript is machine-parseable, and ``--auto`` so
the pipeline never stalls on permission prompts.
"""

from __future__ import annotations

import json
import subprocess

from ..utils import ensure_session_dir, log
from .base import Worker, WorkerResult


class OpenCodeWorker(Worker):
    def __init__(
        self,
        *,
        binary: str = "opencode",
        project_path: str = "",
        model: str = "",
        extra_args: list[str] | None = None,
        timeout: int = 1800,
        verbose: bool = True,
    ) -> None:
        self.binary = binary
        self.project_path = project_path
        self.model = model
        self.extra_args = list(extra_args or [])
        self.timeout = timeout
        self.verbose = verbose

    def run(self, task: str) -> WorkerResult:
        cmd = [self.binary, "run", "--format", "json", "--dir", self.project_path, "--print-logs"]
        if self.model:
            cmd += ["--model", self.model]
        cmd += self.extra_args
        cmd += ["--auto"]
        cmd.append(task)

        log(f"worker (opencode) starting: {self.project_path}", self.verbose)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=self.timeout
        )
        transcript = (proc.stdout or "") + "\n----- STDERR -----\n" + (proc.stderr or "")
        self._save_transcript(proc.returncode, transcript)
        return WorkerResult(
            exit_code=proc.returncode,
            summary=_summarize(transcript),
            transcript=transcript,
        )

    def _save_transcript(self, exit_code: int, transcript: str) -> None:
        d = ensure_session_dir()
        path = d / f"opencode_run_{exit_code}.txt"
        path.write_text(transcript, encoding="utf-8")
        log(f"transcript saved: {path}", self.verbose)


def _summarize(transcript: str) -> str:
    """Extract assistant text from the NDJSON event stream."""
    pieces: list[str] = []
    for line in transcript.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = _event_text(event)
        if text:
            pieces.append(text)
    text = "\n".join(p for p in pieces if p)
    return (text or transcript[-3000:])[:4000]


def _event_text(event: dict) -> str | None:
    etype = event.get("type")
    if etype == "part":
        part = event.get("part") or {}
        if part.get("type") == "text":
            return str(part.get("text", "")).strip() or None
        return None
    if etype == "message":
        text = event.get("text")
        return str(text).strip() if text else None
    return None