"""API manager — task decisions from any OpenAI-compatible chat API.

Works with OpenAI, DeepSeek, OpenRouter, Ollama, local LLMs, etc. It keeps
a rolling conversation history (from
``sessions/<project>/conversation_history.jsonl``) so the manager has
context across tasks, just like a human would.
"""

from __future__ import annotations

import json
import urllib.request

from ..config import defaults
from ..utils import read_history
from .base import Manager


class ApiManager(Manager):
    """Chat-completions task manager."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system_prompt: str | None = None,
    ) -> None:
        d = defaults()["manager"]["api"]
        self.base_url = (base_url or d["base_url"]).rstrip("/")
        self.api_key = api_key or d["api_key"]
        self.model = model or d["model"]
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or defaults()["manager"]["system_prompt"]

    def get_next_task(self, report: str) -> str:
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}]
        for turn in read_history():
            role = "assistant" if turn["role"] == "manager" else "user"
            messages.append({"role": role, "content": turn["content"]})
        messages.append({"role": "user", "content": report})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        body = self._post(payload)
        return body["choices"][0]["message"]["content"].strip() or "DONE"

    def _post(self, payload: dict) -> dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        request = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))