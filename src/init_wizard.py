"""Interactive setup wizard — build a config without editing JSON by hand."""

from __future__ import annotations

import json
from pathlib import Path

from .config import defaults

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


def run_wizard() -> int:
    """Run the interactive wizard and write ``configs/config.json``."""
    cfg = defaults()

    print("=== agent-bridge setup ===\n")

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

    CONFIG_TARGET.parent.mkdir(exist_ok=True)
    CONFIG_TARGET.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nConfig written to {CONFIG_TARGET}")
    return 0