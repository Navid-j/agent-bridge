"""Worker factory — build the configured worker."""

from __future__ import annotations

from ..utils import log
from .base import Worker
from .generic_worker import GenericWorker
from .opencode_worker import OpenCodeWorker


def build_worker(config: dict) -> Worker:
    """Instantiate a Worker based on ``config["worker"]``."""
    w = config["worker"]
    wtype = w["type"]
    if wtype == "opencode":
        log(f"worker: opencode (model={w.get('model') or 'default'})")
        return OpenCodeWorker(
            binary=w.get("binary", "opencode"),
            project_path=config.get("project_path", ""),
            model=w.get("model", ""),
            extra_args=w.get("extra_args"),
            timeout=int(w.get("timeout", 1800)),
            verbose=config.get("verbose", True),
        )
    if wtype == "generic":
        log(f"worker: generic ({w.get('binary', '?')})")
        return GenericWorker(
            binary=w["binary"],
            args=w.get("args"),
            cwd=config.get("project_path", ""),
            timeout=int(w.get("timeout", 1800)),
            verbose=config.get("verbose", True),
        )
    raise ValueError(f"unknown worker type: {wtype}")