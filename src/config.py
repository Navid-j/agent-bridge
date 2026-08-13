"""Configuration loading, validation and env-var expansion.

Two formats are supported:

1. **Multi-project** (recommended)::

       {
         "active_project": "test-project",
         "projects": {
           "test-project": { "project_path": "...", "manager": {...}, ... }
         }
       }

   Each project carries its own ``manager`` / ``worker`` / ``loop`` so
   switching between DeepSeek and ChatGPT or between two repos only means
   selecting a different project name.

2. **Legacy flat**: a single ``{project_path, manager, worker, loop}``
   object. It is still accepted and treated as one project named after
   its path.

``load_config(path, project_name)`` resolves one project into an *effective*
config dict that downstream code consumes.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .utils import slugify

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "config.json"

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


def load_config(path: str | Path | None = None, project_name: str | None = None) -> dict:
    """Load a config file and resolve it into one project's effective config.

    Returns a dict with keys: ``project_name``, ``project_path``,
    ``manager``, ``worker``, ``loop``, ``verbose``.
    """
    path = Path(path) if path else CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    data = _expand(json.loads(path.read_text(encoding="utf-8")))

    if "projects" in data:
        return _resolve_multi(data, project_name)
    return _resolve_legacy(data)


def list_projects(path: str | Path | None = None) -> list[str]:
    """Return the project names defined in a config (empty for legacy)."""
    path = Path(path) if path else CONFIG_PATH
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    projects = data.get("projects")
    return list(projects.keys()) if isinstance(projects, dict) else []


def _resolve_multi(data: dict, project_name: str | None) -> dict:
    projects = data.get("projects") or {}
    if not projects:
        raise ValueError(f"config defines 'projects' but it is empty: {data}")

    name = project_name or data.get("active_project") or next(iter(projects))
    if str(name) not in projects:
        raise ValueError(
            f"unknown project {name!r}; available: {', '.join(projects)}"
        )
    project = projects[str(name)]

    cfg = _merge(defaults(), project)
    cfg["project_name"] = str(name)
    cfg["project_path"] = project.get("project_path", cfg.get("project_path", ""))
    return cfg


def _resolve_legacy(data: dict) -> dict:
    cfg = _merge(defaults(), data)
    path = cfg.get("project_path", "")
    cfg["project_name"] = slugify(Path(path).stem if path else "default")
    return cfg


def _merge(base: dict, overlay: dict) -> dict:
    """Recursively merge ``overlay`` onto ``base`` (overlay wins)."""
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def defaults() -> dict:
    """Default configuration — the minimal sane baseline."""
    return {
        "project_name": "default",
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
                "site": "auto",          # auto | chatgpt | deepseek
                "selectors": {},         # optional override, e.g. {"inputs": [...]}
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