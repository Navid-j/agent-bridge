"""git integration — append a concise diff/status summary to the report.

Small, read-only helper: it never stages, commits or mutates the repo. It
runs ``git status --short`` and (optionally) ``git diff --stat`` to show
what the worker changed, so the manager can judge the actual impact.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_summary(project_path: str | Path, *, max_files: int = 25) -> str:
    """Return a markdown block describing the current git state of a repo.

    Returns an empty string when the folder is not a git repository or git
    is unavailable — the report stays valid either way.
    """
    path = str(Path(project_path))
    status = _run_git(["status", "--short", "--untracked-files=all"], path)
    if status is None:
        return ""

    lines = [line for line in status.splitlines() if line.strip()]
    lines = lines[:max_files]
    if not lines:
        return "**git:** working tree clean\n"

    diff_stat = _run_git(["diff", "--stat"], path)
    block = ["**git changes:**", "", "```"]
    block.extend(lines)
    if diff_stat:
        block.append("")
        block.extend(diff_stat.splitlines()[:15])
    block.append("```")
    return "\n".join(block) + "\n"


def _run_git(args: list[str], cwd: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout