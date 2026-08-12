"""Web manager — task decisions from any chat website via browser automation.

This is the "I only have the website, no API" option. Playwright drives a
persistent browser profile; on the first run the user logs in once and the
session is remembered. A single thread is kept alive so the site retains
the whole project context as the ongoing task manager.

Two presets ship out of the box:

* ``chatgpt``  -> chatgpt.com
* ``deepseek`` -> chat.deepseek.com   (DeepSeek's web chat)

Selectors are centralised in ``SITE_PRESETS`` and can be overridden via
``manager.web.selectors`` in the config, so an untouched site can usually
be added without code changes.
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


class SitePreset:
    """Selector set + behaviour for one chat website."""

    def __init__(self, *, url: str, inputs: list[str], responses: list[str],
                 new_thread_labels: list[str] | None = None) -> None:
        self.url = url
        self.inputs = inputs                      # candidate input selectors, tried in order
        self.responses = list(responses)          # candidate response selectors, tried in order
        self.new_thread_labels = new_thread_labels or []


SITE_PRESETS: dict[str, SitePreset] = {
    "chatgpt": SitePreset(
        url="https://chatgpt.com/",
        inputs=["textarea#prompt-textarea", "textarea[data-testid='prompt-textarea']",
                "div[contenteditable='true']"],
        responses=["article"],
        new_thread_labels=["new chat", "new conversation"],
    ),
    "deepseek": SitePreset(
        url="https://chat.deepseek.com/",
        inputs=["textarea#chat-input", "#chat-input", "textarea[placeholder]",
                "div[contenteditable='true']"],
        responses=[".ds-markdown", "[data-bot-message]", ".ds-chat-reply",
                   "div[class*='markdown']"],
        new_thread_labels=["new conversation", "new chat", "新对话"],
    ),
}


class WebManager(Manager):
    """Browser-automation task manager for chat websites."""

    def __init__(self, *, url: str | None = None, headless: bool | None = None,
                 site: str | None = None, selectors: dict | None = None,
                 verbose: bool = True) -> None:
        d = defaults()["manager"]["web"]

        self.site = (site or "auto").lower()
        url = url or d.get("url") or ""
        selectors = selectors or d.get("selectors") or {}

        preset = _pick_preset(self.site, url)
        self.preset_name = preset.root_name
        self.url = url or preset.preset.url
        self._inputs = selectors.get("inputs") or list(preset.preset.inputs)
        self._responses = selectors.get("responses") or list(preset.preset.responses)
        self._new_thread_labels = selectors.get("new_thread_labels") or list(preset.preset.new_thread_labels)

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

    # --- page lifecycle -------------------------------------------------

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
        log(f"opening {self.url} (preset: {self.preset_name})", self.verbose)
        self._page.goto(self.url, wait_until="networkidle")
        log("waiting for the chat input…", self.verbose)
        self._first(self._inputs, timeout=90_000)
        log("chat ready", self.verbose)

    def close(self) -> None:
        if self._playwright is not None:
            try:
                self._playwright.stop()
            finally:
                self._playwright = None
                self._page = None

    # --- helpers --------------------------------------------------------

    def _first(self, selectors: list[str], timeout: int = 30_000):
        """Wait for the first selector that matches and return its locator."""
        try:
            return self._page.wait_for_selector(selectors[0], timeout=timeout)
        except Exception:
            for sel in selectors[1:]:
                locator = self._page.locator(sel)
                try:
                    if locator.first.wait_for(timeout=timeout) is not None:
                        return locator.first
                except Exception:
                    continue
            raise

    def _new_thread(self) -> None:
        if not self._new_thread_labels:
            return
        pattern = "|".join(re.escape(label) for label in self._new_thread_labels)
        buttons = self._page.get_by_role("button", name=re.compile(pattern, re.IGNORECASE))
        if buttons.count() > 0:
            buttons.first.click()
            self._page.wait_for_timeout(1500)

    def _send_message(self, message: str) -> None:
        box = self._first(self._inputs)
        try:
            box.fill(message)
        except Exception:
            box.click()
            self._page.keyboard.type(message)
        self._page.wait_for_timeout(300)
        self._page.keyboard.press("Enter")

    def _wait_for_done(self, response_count: int) -> None:
        """Wait until the last response stops growing (any chat UI)."""
        last_text = ""
        try:
            latest = self._page.locator(self._responses[0])
            latest.first.wait_for(timeout=60_000)
        except Exception:
            log("response element not found; returning what we have", self.verbose)
            return
        for _ in range(60):  # ~ up to 60s
            self._page.wait_for_timeout(1000)
            try:
                text = self._page.locator(self._responses[0]).last.inner_text()
            except Exception:
                text = last_text
            if text == last_text and text.strip():
                break
            last_text = text

    def _read_response(self) -> str:
        for selector in self._responses:
            locator = self._page.locator(selector).last
            try:
                text = locator.inner_text().strip()
            except Exception:
                continue
            if text:
                return text
        return ""

    def _ask(self, message: str, new_thread: bool = False) -> str:
        self._ensure_page()
        if new_thread:
            self._new_thread()
        self._send_message(message)
        self._wait_for_done(0)
        return self._read_response()


def _pick_preset(site: str, url: str) -> "PresetSelection":
    """Resolve the preset for the requested site / url."""
    if site in SITE_PRESETS:
        return PresetSelection(root_name=site, preset=SITE_PRESETS[site])
    lower = url.lower()
    for name, preset in SITE_PRESETS.items():
        if name in lower:
            return PresetSelection(root_name=name, preset=preset)
    return PresetSelection(root_name="chatgpt", preset=SITE_PRESETS["chatgpt"])


class PresetSelection:
    __slots__ = ("root_name", "preset")

    def __init__(self, *, root_name: str, preset: SitePreset) -> None:
        self.root_name = root_name
        self.preset = preset