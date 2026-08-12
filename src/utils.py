"""Shared helpers: logging, session files, history."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION_DIR = ROOT / "sessions"
REPORT_PATH = SESSION_DIR / "result_report.txt"
TASK_PATH = SESSION_DIR / "next_task.txt"
CONVERSATION_PATH = SESSION_DIR / "conversation_history.jsonl"


def ensure_session_dir() -> None:
    SESSION_DIR.mkdir(exist_ok=True)


def log(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def write_report(text: str) -> None:
    ensure_session_dir()
    REPORT_PATH.write_text(text, encoding="utf-8")


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