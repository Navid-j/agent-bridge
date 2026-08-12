"""CLI entry point for agent-bridge."""

from __future__ import annotations

import argparse
import sys

from .config import load_config
from .orchestrator import Bridge
from .utils import clear_history, log


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent-bridge",
        description="Glue between a task manager (ChatGPT/API/another agent) "
                    "and a coding agent (opencode/any CLI).",
    )
    parser.add_argument("--config", default=None, help="path to a JSON config file")
    parser.add_argument("--project", default=None, help="target project directory (overrides config)")
    parser.add_argument(
        "--manager", choices=["manual", "api", "web", "agent"], default=None,
        help="manager type (overrides config)",
    )
    parser.add_argument(
        "--worker", choices=["opencode", "generic"], default=None,
        help="worker type (overrides config)",
    )
    parser.add_argument("--iterations", type=int, default=None, help="max tasks to run (0 = forever)")
    parser.add_argument("--once", action="store_true", help="run exactly one task")
    parser.add_argument("--clear-history", action="store_true", help="reset the conversation history first")
    parser.add_argument("--headless", action="store_true", help="web mode: run the browser headless")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)

    if args.project:
        config["project_path"] = args.project
    if not config.get("project_path"):
        log("ERROR: no project path. Pass --project or set project_path in the config.", True)
        return 2

    if args.manager:
        config["manager"]["type"] = args.manager
    if args.worker:
        config["worker"]["type"] = args.worker
    if args.headless:
        config["manager"].setdefault("web", {})["headless"] = True
    if args.iterations is not None:
        config.setdefault("loop", {})["iterations"] = args.iterations
    if args.once:
        config.setdefault("loop", {})["iterations"] = 1
    if args.clear_history and config["manager"]["type"] == "api":
        clear_history()
        log("conversation history cleared", config.get("verbose", True))

    bridge = Bridge(config)
    try:
        return bridge.loop()
    except KeyboardInterrupt:
        log("interrupted by user", True)
        return 130
    finally:
        bridge.close()


if __name__ == "__main__":
    sys.exit(main())