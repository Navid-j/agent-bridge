"""Shared helpers: logging, per-project session files, history.

Every session artefact lives under ``sessions/<project>/`` so that
different projects (and their tasks/reports/state) never mix. The active
project is set once at startup via ``set_active_project``.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSIONS_ROOT = ROOT / "sessions"

_ACTIVE_PROJECT = "default"


def set_active_project(name: str) -> None:
    """Point all session helpers at the given project's folder."""
    global _ACTIVE_PROJECT
    _ACTIVE_PROJECT = slugify(name or "default")


def active_project() -> str:
    return _ACTIVE_PROJECT


def command_prefix(binary: str) -> list[str]:
    """Resolve a CLI binary to an argv prefix subprocess can actually start.

    On Windows, npm installs shims as ``.cmd``/``.bat`` files, which
    ``subprocess`` cannot launch directly (CreateProcess needs an .exe), so
    they are invoked through ``cmd /c`` instead.
    """
    path = shutil.which(binary)
    if path is None:
        return [binary]
    if os.name == "nt" and path.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", path]
    return [path]


def slugify(text: str) -> str:
    """Turn an arbitrary project name/path into a safe folder name."""
    s = re.sub(r"[^A-Za-z0-9]+", "-", text.strip()).strip("-")
    return s.lower() or "default"


def project_dir(name: str | None = None) -> Path:
    """Session folder for a project (defaults to the active project)."""
    return SESSIONS_ROOT / slugify(name or _ACTIVE_PROJECT)


def ensure_session_dir(name: str | None = None) -> Path:
    d = project_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def reports_dir(name: str | None = None) -> Path:
    d = project_dir(name) / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# --- report / task -------------------------------------------------------


def write_report(text: str, tag: str = "", name: str | None = None) -> Path:
    """Write the latest report and a tagged/timestamped copy under the
    project's ``reports/`` folder. Returns the archived path."""
    d = ensure_session_dir(name)
    (d / "result_report.txt").write_text(text, encoding="utf-8")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = f"{tag}_" if tag else ""
    timed_path = reports_dir(name) / f"{label}report_{stamp}.md"
    timed_path.write_text(text, encoding="utf-8")
    return timed_path


def read_report(name: str | None = None) -> str:
    return (project_dir(name) / "result_report.txt").read_text(encoding="utf-8")


def write_task(text: str, name: str | None = None) -> None:
    ensure_session_dir(name)
    (project_dir(name) / "next_task.txt").write_text(text, encoding="utf-8")


def read_task(name: str | None = None) -> str:
    ensure_session_dir(name)
    content = (project_dir(name) / "next_task.txt").read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("task file is empty")
    return content


# --- conversation history -------------------------------------------------


def history_path(name: str | None = None) -> Path:
    return project_dir(name) / "conversation_history.jsonl"


def append_history(role: str, content: str, name: str | None = None) -> None:
    p = history_path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {"role": role, "ts": datetime.now().isoformat(), "content": content}
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history(name: str | None = None) -> list[dict]:
    p = history_path(name)
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def clear_history(name: str | None = None) -> None:
    p = history_path(name)
    if p.exists():
        p.write_text("", encoding="utf-8")


# --- misc -----------------------------------------------------------------


def is_done(text: str) -> bool:
    """True when a manager reply unambiguously means "stop the pipeline"."""
    clean = re.sub(r"[.!…\s]+$", "", text.strip()).upper()
    return clean == "DONE"


def save_state(payload: dict, name: str | None = None) -> None:
    """Persist pipeline state (resume point) under the project's session."""
    d = ensure_session_dir(name)
    (d / "state.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load_state(name: str | None = None) -> dict:
    p = project_dir(name) / "state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}