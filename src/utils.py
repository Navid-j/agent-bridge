"""Shared helpers: logging, session files, history."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT / "sessions"
REPORT_PATH = SESSION_DIR / "result_report.txt"
TASK_PATH = SESSION_DIR / "next_task.txt"
CONVERSATION_PATH = SESSION_DIR / "conversation_history.jsonl"
REPORTS_DIR = SESSION_DIR / "reports"
STATE_PATH = SESSION_DIR / "state.json"


def ensure_session_dir() -> None:
    SESSION_DIR.mkdir(exist_ok=True)


def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def write_report(text: str, tag: str = "") -> Path:
    """Write the latest report and also a tagged/timestamped copy under
    ``sessions/reports/``.

    When ``tag`` is given, the archived filename becomes
    ``<tag>_<timestamp>.md`` so a session's reports group together.
    Returns the archived report path.
    """
    ensure_session_dir()
    REPORT_PATH.write_text(text, encoding="utf-8")
    REPORTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = f"{tag}_" if tag else ""
    timed_path = REPORTS_DIR / f"{label}report_{stamp}.md"
    timed_path.write_text(text, encoding="utf-8")
    return timed_path


def write_task(text: str) -> None:
    ensure_session_dir()
    TASK_PATH.write_text(text, encoding="utf-8")


def read_task() -> str:
    ensure_session_dir()
    content = TASK_PATH.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("task file is empty")
    return content


def append_history(role: str, content: str) -> None:
    ensure_session_dir()
    entry = {"role": role, "ts": datetime.now().isoformat(), "content": content}
    with open(CONVERSATION_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_history() -> list[dict]:
    ensure_session_dir()
    if not CONVERSATION_PATH.exists():
        return []
    out: list[dict] = []
    for line in CONVERSATION_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def clear_history() -> None:
    ensure_session_dir()
    if CONVERSATION_PATH.exists():
        CONVERSATION_PATH.write_text("", encoding="utf-8")


def is_done(text: str) -> bool:
    """True when a manager reply unambiguously means "stop the pipeline"."""
    clean = re.sub(r"[.!…\s]+$", "", text.strip()).upper()
    return clean == "DONE"


def save_state(payload: dict) -> None:
    """Persist pipeline state (resume point) to ``sessions/state.json``."""
    ensure_session_dir()
    STATE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_state() -> dict:
    """Load the last pipeline state; empty dict when absent/invalid."""
    ensure_session_dir()
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}