"""Configuration loading, validation and env-var expansion."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "config.example.json"

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _expand(value: object) -> object:
    """Recursively expand ``${VAR}`` placeholders from the environment."""
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), m.group(0)), value)
    if isinstance(value, list):
        return [_expand(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    return value


def load_config(path: str | Path | None = None) -> dict:
    """Load the JSON config, merge defaults and expand env placeholders."""
    path = Path(path) if path else CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data = _expand(data)
    data = {**defaults(), **data}
    data["manager"] = {**defaults()["manager"], **(data.get("manager") or {})}
    data["worker"] = {**defaults()["worker"], **(data.get("worker") or {})}
    return data


def defaults() -> dict:
    """Default configuration — the minimal sane baseline."""
    return {
        "project_path": "",
        "manager": {
            "type": "manual",          # manual | api | web | agent
            "system_prompt": (
                "You are the technical task manager for an autonomous coding "
                "pipeline. You receive the coding agent's result report and "
                "must reply with ONLY the next concrete task. If the project "
                "is finished, reply exactly: DONE"
            ),
            "api": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "${OPENAI_API_KEY}",
                "model": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            "web": {
                "url": "https://chatgpt.com/",
                "headless": False,
            },
            "agent": {
                "binary": "opencode",
                "args": [],
            },
        },
        "worker": {
            "type": "opencode",        # opencode | generic
            "binary": "opencode",
            "model": "",
            "extra_args": [],
            "timeout": 1800,
        },
        "loop": {
            "iterations": 0,           # 0 = run forever
            "resume": False,           # resume interrupted runs from state.json
            "max_report_len": 0,       # clip reports longer than this (0 = unlimited)
        },
        "verbose": True,
    }