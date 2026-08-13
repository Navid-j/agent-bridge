"""CLI entry point for agent-bridge."""

from __future__ import annotations

import argparse
import sys

from .config import defaults, list_projects, load_config
from .orchestrator import Bridge
from .utils import clear_history, log, set_active_project
from .workers.base import WorkerResult


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent-bridge",
        description="Glue between a task manager (ChatGPT/API/another agent) "
                    "and a coding agent (opencode/any CLI).",
    )
    parser.add_argument(
        "name", nargs="?", default=None,
        help="name of a project defined in the config (selects its manager/worker/loop)",
    )
    parser.add_argument("--config", default=None, help="path to a JSON config file")
    parser.add_argument("--project", default=None, help="target project directory (overrides config)")
    parser.add_argument(
        "--list-projects", action="store_true",
        help="list the projects defined in the config and exit",
    )
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
    parser.add_argument(
        "--init", action="store_true",
        help="run the interactive setup wizard and exit",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="simulate one pipeline step without invoking the worker",
    )
    parser.add_argument(
        "--git-check", action="store_true",
        help="append a git status/diff summary to each result report",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="resume an interrupted run from sessions/<project>/state.json",
    )
    parser.add_argument(
        "--max-report-len", type=int, default=None,
        help="clip reports longer than this many chars (0 = unlimited)",
    )
    parser.add_argument(
        "--tag", default=None,
        help="session tag; archived reports become <tag>_report_<ts>.md",
    )
    return parser.parse_args(argv)


def _init_console() -> None:
    """Let the console print any script/UTF-8 text without crashing."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _init_console()

    if args.init:
        from .init_wizard import run_wizard

        return run_wizard()

    if args.list_projects:
        names = list_projects(args.config)
        if not names:
            log("no 'projects' section found in the config.", True)
            return 1
        print("\n".join(names))
        return 0

    config = load_config(args.config, project_name=args.name)
    set_active_project(config["project_name"])

    if args.project:
        config["project_path"] = args.project
    if not config.get("project_path"):
        log(
            "ERROR: no project path. Pass --project or set project_path "
            "for the selected project.",
            True,
        )
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
    if args.git_check:
        config["git_check"] = True
    if args.resume:
        config.setdefault("loop", {})["resume"] = True
    if args.max_report_len is not None:
        config.setdefault("loop", {})["max_report_len"] = args.max_report_len
    if args.tag:
        config["tag"] = args.tag
    if args.clear_history and config["manager"]["type"] == "api":
        clear_history(config["project_name"])
        log("conversation history cleared", config.get("verbose", True))

    bridge = Bridge(config)
    try:
        if args.dry_run:
            return _dry_run(config, bridge)
        return bridge.loop()
    except KeyboardInterrupt:
        log("interrupted by user", True)
        return 130
    finally:
        bridge.close()


def _dry_run(config: dict, bridge: Bridge) -> int:
    """Simulate one pipeline step: read the task, show the plan, no run."""
    from .utils import read_task

    try:
        task = read_task(config["project_name"])
    except (FileNotFoundError, ValueError) as exc:
        log(
            f"ERROR: {exc}. Put the first task into "
            f"sessions/{config['project_name']}/next_task.txt",
            True,
        )
        return 1

    print("\n=== DRY RUN ===")
    print(f"project      : {config['project_name']}")
    print(f"project path : {config.get('project_path')}")
    print(f"manager      : {config['manager']['type']}")
    print(f"worker       : {config['worker']['type']} -> {config['worker'].get('binary', '?')}")
    print(f"iterations   : {config.get('loop', {}).get('iterations', 0)}")
    print("task         :")
    print(task[:1000])
    print("\n(no worker invoked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())