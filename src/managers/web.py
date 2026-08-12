"""Web manager — task decisions from chatgpt.com via browser automation.

This is the "I only have the website, no API" option. Playwright drives a
persistent browser profile; on the first run the user logs in once and the
session is remembered. A single thread is kept alive so ChatGPT retains the
whole project context as the ongoing task manager.
"""

from __future__ import annotations

import re

from ..config import defaults
from ..utils import ROOT, log
from .base import Manager

REQUIRED_MSG = (
    "Playwright is required for web mode. Install it with:\n"
    "  pip install playwright\n"
    "  playwright install chromium\n"
)


class WebManager(Manager):
    """ChatGPT website task manager via Playwright."""

    def __init__(self, *, url: str | None = None, headless: bool | None = None, verbose: bool = True) -> None:
        d = defaults()["manager"]["web"]
        self.url = url or d["url"]
        self.headless = d.get("headless", False) if headless is None else headless
        self.verbose = verbose
        self._page = None
        self._playwright = None
        self._thread_started = False
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(REQUIRED_MSG) from exc

    def get_next_task(self, report: str) -> str:
        reply = self._ask(report, new_thread=not self._thread_started)
        self._thread_started = True
        return reply.strip()

    def _ensure_page(self) -> None:
        if self._page is not None:
            return
        from playwright.sync_api import sync_playwright

        profile_dir = ROOT / "sessions" / "browser_profile"
        self._playwright = sync_playwright().start()
        context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir), headless=self.headless
        )
        self._page = context.pages[0] if context.pages else context.new_page()
        self._page.goto(self.url, wait_until="networkidle")
        self._page.wait_for_selector("textarea#prompt-textarea", timeout=90_000)
        log("chatgpt ready", self.verbose)

    def _new_thread(self) -> None:
        buttons = self._page.get_by_role("button", name=re.compile("New chat", re.IGNORECASE))
        if buttons.count() > 0:
            buttons.first.click()
            self._page.wait_for_timeout(1500)

    def _ask(self, message: str, new_thread: bool = False) -> str:
        self._ensure_page()
        if new_thread:
            self._new_thread()
        self._page.fill("#prompt-textarea", message)
        self._page.wait_for_timeout(300)
        self._page.keyboard.press("Enter")
        self._page.wait_for_timeout(1500)
        try:
            self._page.wait_for_function(
                """() => {
                  const btn = document.querySelector(
                    'button[data-testid="send-button"], button[aria-label*="Stop"]');
                  return !!btn && btn.getAttribute('disabled') === null;
                }""",
                timeout=180_000,
            )
        except Exception:
            log("send/progress indicator timeout; continuing", self.verbose)
        self._page.wait_for_selector("article", timeout=60_000)
        self._page.wait_for_timeout(2000)
        return self._page.locator("article").last.inner_text()

    def close(self) -> None:
        if self._playwright is not None:
            try:
                self._playwright.stop()
            finally:
                self._playwright = None
                self._page = None