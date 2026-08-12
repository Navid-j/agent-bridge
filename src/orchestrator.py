"""agent-bridge — glue between a task manager and a coding agent.

The orchestrator runs the pipeline:

    next task
        -> worker.run(task)   (coding agent)
        -> result report
        -> manager.get_next_task(report)   (task manager)
        -> next task
        -> ...

It is intentionally small and dependency-light: Managers and Workers are
injected, so any combination works.
"""

from __future__ import annotations

import sys

from .config import defaults, load_config
from .managers import build_manager
from .utils import append_history, clear_history, log, write_report
from .workers import build_worker
from .workers.base import WorkerResult

DONE_SENTINELS = {"DONE", "done", "DONE."}


class Bridge:
    """High-level pipeline controller."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.worker = build_worker(config)
        self.manager = build_manager(config)
        self.verbose = config.get("verbose", True)
        self.iterations = int(config.get("loop", {}).get("iterations", 0))

    def run_once(self, task: str) -> WorkerResult:
        """Run one task through worker, report to manager-side history."""
        log(f"--- executing task ---", self.verbose)
        result = self.worker.run(task)
        report = result.to_markdown()
        write_report(report)
        append_history("coder", report)
        return result

    def loop(self, first_task: str | None = None) -> int:
        """Run the bridge until the manager says DONE or iterations run out.

        Behaviour depends on the manager type:

        * **Manual manager** — the user edits ``sessions/next_task.txt``
          between runs, so exactly one task is executed per invocation and
          control returns to the shell.
        * **Auto managers (api / web / agent)** — the loop continues
          in-process: the manager's reply becomes the next task until it
          returns ``DONE`` or the iteration limit is reached.
        """
        from .managers.base import ManualManager

        count = 0
        task = first_task if first_task is not None else self.manager.get_next_task("")
        report = None

        while True:
            if task is None:
                task = self.manager.get_next_task("")
            if task.strip() in DONE_SENTINELS:
                log("manager said DONE; stopping", self.verbose)
                break

            result = self.run_once(task)
            if result.exit_code != 0:
                log(f"worker FAILED (exit {result.exit_code}); passing to manager", self.verbose)
            count += 1

            if isinstance(self.manager, ManualManager):
                log(
                    "manual mode: paste sessions/result_report.txt into your "
                    "manager, save its reply as sessions/next_task.txt, re-run.",
                    self.verbose,
                )
                break

            next_task = self.manager.get_next_task(result.to_markdown())
            append_history("manager", next_task)
            if self.iterations and count >= self.iterations:
                log(f"reached iteration limit ({self.iterations})", self.verbose)
                break
            task = next_task

        log(f"pipeline finished after {count} task(s)", self.verbose)
        return 0

    def close(self) -> None:
        close = getattr(self.manager, "close", None)
        if close is not None:
            close()