"""Interactive setup wizard — build/edit a multi-project config without
editing JSON by hand.

Each run of ``--init`` creates (or extends) ``configs/config.json`` with one
project. You can re-run the wizard with a different project name to add more.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import defaults, list_projects
from .utils import slugify

CONFIG_TARGET = Path(__file__).resolve().parents[1] / "configs" / "config.json"


def _ask(prompt: str, default: str = "") -> str:
    tail = f" [{default}]" if default else ""
    value = input(f"{prompt}{tail}: ").strip()
    return value or default


def _choose(prompt: str, options: list[str], default: str) -> str:
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        mark = " <- default" if opt == default else ""
        print(f"  {i}) {opt}{mark}")
    while True:
        raw = input(f"choice [1-{len(options)}]: ").strip()
        try:
            idx = int(raw) - 1
        except ValueError:
            idx = -1
        if 0 <= idx < len(options):
            return options[idx]
        print("invalid choice, try again.")


def _project_config() -> dict:
    """Gather the interactive answers into one project's config."""
    cfg = defaults()

    project = _ask("target project path")
    if project:
        cfg["project_path"] = project

    manager = _choose(
        "How will the MANAGER (task source) work?",
        ["manual", "api", "web", "agent"],
        "manual",
    )
    cfg["manager"]["type"] = manager

    if manager == "api":
        base = _ask("API base URL", "https://api.openai.com/v1")
        model = _ask("model", "gpt-4o")
        key = _ask("API key (or leave empty to use ${OPENAI_API_KEY})", "${OPENAI_API_KEY}")
        cfg["manager"]["api"] = {
            "base_url": base,
            "api_key": key,
            "model": model,
            "temperature": 0.7,
            "max_tokens": 1024,
        }
    elif manager == "web":
        url = _ask("website URL", "https://chatgpt.com/")
        cfg["manager"]["web"] = {"url": url, "headless": False}
        print("\nNote: web mode needs Playwright. Install with:")
        print("  pip install playwright && playwright install chromium")
    elif manager == "agent":
        binary = _ask("manager agent binary", "opencode")
        cfg["manager"]["agent"] = {"binary": binary, "args": ["run", "--format", "json"]}

    worker = _choose("How will the WORKER (coding agent) run?", ["opencode", "generic"], "opencode")
    cfg["worker"]["type"] = worker
    cfg["worker"]["binary"] = _ask("worker binary", "opencode")
    model = _ask("worker model (e.g. provider/model; empty = default)", "")
    if model:
        cfg["worker"]["model"] = model

    iterations = _ask("max iterations (0 = run until DONE)", "0")
    cfg["loop"]["iterations"] = int(iterations)

    return cfg


def run_wizard() -> int:
    """Run the interactive wizard and update ``configs/config.json``."""
    print("=== agent-bridge setup ===\n")

    projects = list_projects(CONFIG_TARGET)
    existing = sorted(projects)
    if existing:
        print(f"already configured projects: {', '.join(existing)}")

    name = _ask("project name", existing[0] if len(existing) == 1 else "")
    if not name:
        name = input("project name: ").strip() or "default"
    name = slugify(name)

    print(f"\n--- configuring project: {name} ---")
    project = _project_config()
    project.pop("project_name", None)

    CONFIG_TARGET.parent.mkdir(exist_ok=True)
    if CONFIG_TARGET.exists():
        data = json.loads(CONFIG_TARGET.read_text(encoding="utf-8"))
    else:
        data = {"active_project": name, "projects": {}}

    projects_map = data.setdefault("projects", {})
    projects_map[name] = project
    data["active_project"] = name
    # normalize any legacy flat config into the projects format
    for key in ("project_path", "manager", "worker", "loop"):
        data.pop(key, None)

    CONFIG_TARGET.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nConfig written to {CONFIG_TARGET}")
    print(f"Run: python -m src {name}")
    return 0