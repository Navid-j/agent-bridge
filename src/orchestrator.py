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
import time
from datetime import datetime

from .config import defaults, load_config
from .managers import build_manager
from .report import build_report
from .utils import (
    append_history,
    clear_history,
    is_done,
    load_state,
    log,
    save_state,
    write_report,
)
from .workers import build_worker
from .workers.base import WorkerResult


class Bridge:
    """High-level pipeline controller."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.worker = build_worker(config)
        self.manager = build_manager(config)
        self.verbose = config.get("verbose", True)
        self.iterations = int(config.get("loop", {}).get("iterations", 0))
        self.max_report_len = int(config.get("loop", {}).get("max_report_len", 0) or 0)
        self.resume = bool(config.get("loop", {}).get("resume", False))
        self.tag = str(config.get("tag", "") or "")

    def run_once(self, task: str, index: int = 0) -> WorkerResult:
        """Run one task through worker, report to manager-side history."""
        log(f"--- executing task {index + 1} ---", self.verbose)
        save_state({"phase": "running", "task": task, "index": index, "ts": datetime.now().isoformat()})
        started = time.monotonic()
        result = self.worker.run(task)
        elapsed = time.monotonic() - started

        status = "ok" if result.exit_code == 0 else f"FAILED (exit {result.exit_code})"
        extra: list[str] = []
        if self.config.get("git_check"):
            extra.append(self._git_summary())
        report = build_report(
            task=task, status=status, summary=result.summary,
            elapsed_s=elapsed, extra_blocks=extra,
        )
        if self.max_report_len > 0 and len(report) > self.max_report_len:
            report = self._clip_report(report)
        write_report(report, tag=self.tag)
        append_history("coder", report)
        save_state({"phase": "idle", "task": task, "index": index, "ts": datetime.now().isoformat()})
        return result

    def _git_summary(self) -> str:
        """Read-only git status/diff summary; empty string on any failure."""
        try:
            from .git_check import git_summary

            return git_summary(self.config.get("project_path", ""))
        except Exception as exc:
            log(f"git check skipped: {exc}", self.verbose)
            return ""

    def _clip_report(self, report: str) -> str:
        """Truncate an overly long report (--max-report-len)."""
        kept, dropped = report[: self.max_report_len], len(report) - self.max_report_len
        log(f"report clipped to {self.max_report_len} chars (dropped {dropped})", self.verbose)
        return kept + f"\n\n_[truncated: {dropped} chars omitted]_"

    def loop(self, first_task: str | None = None) -> int:
        """Run the bridge until the manager says DONE or iterations run out.

        Behaviour depends on the manager type:

        * **Manual manager** — the user edits ``sessions/next_task.txt``
          between runs, so exactly one task is executed per invocation and
          control returns to the shell.
        * **Auto managers (api / web / agent)** — the loop continues
          in-process: the manager's reply becomes the next task until it
          returns ``DONE`` or the iteration limit is reached.

        With ``loop.resume`` enabled, an interrupted run is picked up from
        the task stored in ``sessions/state.json``.
        """
        from .managers.base import ManualManager

        count = 0
        failed = 0
        state = load_state()

        # Resume support: if the last run died mid-task, redo that task.
        if self.resume and state.get("phase") == "running":
            first_task = state.get("task")
            count = int(state.get("index", 0))
            log(f"resuming interrupted task #{count + 1}", self.verbose)

        task = first_task if first_task is not None else self.manager.get_next_task("")
        report = None

        while True:
            if task is None:
                task = self.manager.get_next_task("")
            if is_done(task):
                log("manager said DONE; stopping", self.verbose)
                break

            result = self.run_once(task, index=count)
            if result.exit_code != 0:
                failed += 1
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
            if is_done(next_task):
                log("manager said DONE; stopping", self.verbose)
                break
            if self.iterations and count >= self.iterations:
                log(f"reached iteration limit ({self.iterations})", self.verbose)
                break
            task = next_task

        log(f"pipeline finished after {count} task(s)", self.verbose)
        self._print_summary(count, failed)
        return 0

    def _print_summary(self, total: int, failed: int) -> None:
        """Print a final human-readable session summary."""
        if not self.verbose:
            return
        ok = total - failed
        line = "═" * 44
        print(f"\n{line}")
        print(f"  agent-bridge session complete")
        print(f"{line}")
        print(f"  tasks run     : {total}")
        print(f"  succeeded     : {ok}  ✅")
        if failed:
            print(f"  failed        : {failed}  ❌")
        if total:
            print(f"  success rate  : {ok / total:.0%}")
        print(f"{line}")

    def close(self) -> None:
        close = getattr(self.manager, "close", None)
        if close is not None:
            close()