"""Manager factory — build the configured manager."""

from __future__ import annotations

from ..utils import log
from .agent import AgentManager
from .api import ApiManager
from .base import Manager, ManualManager
from .web import WebManager


def build_manager(config: dict) -> Manager:
    """Instantiate a Manager based on ``config["manager"]``."""
    m = config["manager"]
    mtype = m["type"]
    if mtype == "manual":
        log("manager: manual (sessions/<project>/next_task.txt)")
        return ManualManager()
    if mtype == "api":
        api = m["api"]
        log(f"manager: api ({api.get('model', '?')})")
        return ApiManager(
            base_url=api.get("base_url"),
            api_key=api.get("api_key"),
            model=api.get("model"),
            temperature=api.get("temperature", 0.7),
            max_tokens=api.get("max_tokens", 1024),
            system_prompt=m.get("system_prompt"),
        )
    if mtype == "web":
        web = m["web"]
        log(f"manager: web (site={web.get('site', 'auto')})")
        return WebManager(
            url=web.get("url"),
            headless=web.get("headless", False),
            site=web.get("site", "auto"),
            selectors=web.get("selectors"),
            verbose=config.get("verbose", True),
        )
    if mtype == "agent":
        agent = m["agent"]
        log(f"manager: agent ({agent.get('binary', '?')})")
        return AgentManager(
            binary=agent.get("binary"),
            args=agent.get("args"),
        )
    raise ValueError(f"unknown manager type: {mtype}")