# Example configurations

Copy the file that matches your setup to `configs/config.json`, set your
project path, then run. All three need a coding agent on your `PATH`
(opencode, or any CLI if you switch `worker.type` to `generic`).

## 1. API manager — you have an API key

```bash
cp examples/api-manager.example.json configs/config.json
python -m src
```

Works with OpenAI, DeepSeek, OpenRouter, Ollama, any OpenAI-compatible
endpoint. Set `OPENAI_API_KEY` in your environment, or paste the key
directly into `manager.api.api_key`.

## 2. Web manager — you only have the website (no API)

```bash
pip install playwright && playwright install chromium   # one time
cp examples/web-manager.example.json configs/config.json   # ChatGPT
python -m src
```

First run: a browser opens; log into the site once — the login is kept
in `sessions/browser_profile/` and reused on later runs. The whole loop is
then automatic.

### Web manager with DeepSeek (chat.deepseek.com)

```bash
cp examples/web-deepseek.example.json configs/config.json   # DeepSeek
python -m src
```

Same workflow, different site. Set `manager.web.site` to `chatgpt`,
`deepseek`, or `auto` (detected from the URL). If a site changes its UI,
you can override selectors without touching code:

```json
{
  "manager": {
    "type": "web",
    "web": {
      "url": "https://chat.deepseek.com/",
      "site": "deepseek",
      "selectors": {
        "inputs": ["textarea#chat-input", "textarea[placeholder]"],
        "responses": [".ds-markdown", "[data-bot-message]"],
        "new_thread_labels": ["New conversation", "新对话"]
      }
    }
  }
}
```

## 3. Agent manager — agent-to-agent, no human and no vendor

```bash
cp examples/agent-manager.example.json configs/config.json
python -m src
```

One agent (the manager) decides the next task, another agent (the worker)
implements it. Fully hands-off.

## 4. Manual — a plain text file, works anywhere

```bash
python -m src --project /path/to/your/project --manager manual
```

1. Write the task in `sessions/next_task.txt`.
2. Run; the report lands in `sessions/result_report.txt`.
3. Paste it into your manager, save the reply as `sessions/next_task.txt`.
4. Run again. Repeat until the manager says `DONE`.

## Useful flags (work with any config)

```bash
--dry-run              plan without invoking the worker
--git-check            include git status/diff in reports
--tag NAME             group archived reports under NAME
--resume               continue after a crash
--max-report-len N     clip long reports
--iterations N         cap the number of tasks
```
