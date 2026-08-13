"""Manager protocol — the source of tasks.

A Manager decides *what to do next*. It receives the coding agent's result
report and returns the next task (or ``DONE`` when the work is finished).
Implementations can be anything: a manual file, an LLM web chat, an
OpenAI-compatible API, or another agent's CLI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Manager(ABC):
    """Interface for the task-manager side of the bridge."""

    @abstractmethod
    def get_next_task(self, report: str) -> str:
        """Given the worker's report, return the next task string.

        Return the literal ``DONE`` to stop the pipeline.
        """
        raise NotImplementedError


class ManualManager(Manager):
    """Task source is the ``sessions/<project>/next_task.txt`` file.

    The user pastes ChatGPT's reply (or any manager output) into the file;
    the bridge does everything else.
    """

    def get_next_task(self, report: str) -> str:
        return read_task()


def read_task() -> str:
    from ..utils import read_task as _read_task

    return _read_task()