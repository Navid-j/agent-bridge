<div align="center">

# 🔗 agent-bridge

**Glue between a task manager and a coding agent — fully automated.**

ChatGPT plans, an agent codes, and you stay out of the loop.

Python · Zero-dependency core · MIT

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](./pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

</div>

---

## What is it?

`agent-bridge` is a small orchestrator that runs an autonomous loop between
two AI sides:

```
   task manager                     coding agent
 ┌──────────────────┐   next task   ┌──────────────────┐
 │  ChatGPT / API / │ ────────────▶ │  opencode / any  │
 │  another agent   │               │  CLI agent       │
 └──────────────────┘ ◀──────────── └──────────────────┘
        result report
```

- The **Manager** decides *what to do next*.
- The **Worker** does the job in your project.
- The **bridge** moves the report and the next task between them.

You can plug in whatever you have:

| You have…                      | Use manager type | Fully automatic?        |
| ------------------------------ | ---------------- | ----------------------- |
| A **chat website** account (ChatGPT, DeepSeek…) | `web` | ✅ (browser automation) |
| An **API key** (OpenAI/DeepSeek/OpenRouter/Ollama…) | `api` | ✅ |
| Another **agent CLI** | `agent` | ✅ (agent↔agent) |
| Nothing — just a text file     | `manual`         | 🟡 (paste report/next task) |

And whatever you want to code with:

| You want to code with…  | Worker type  |
| ----------------------- | ------------ |
| **opencode** (recommended) | `opencode` |
| Claude Code / Aider / Codex / any script | `generic` |

---

## Why?

Solo developers often juggle this dance manually: copy the result to
ChatGPT, copy the next instruction back, run the agent, repeat. `agent-bridge`
removes the copy-paste loop and lets the two sides talk to each other — the
way a small team would, but with agents.

---

## Quick start

### 1. Requirements

- [Python 3.10+](https://www.python.org/downloads/)
- A coding agent CLI on your `PATH` — e.g. install [opencode](https://opencode.ai):
  ```bash
  npm i -g opencode-ai   # or: bun add -g opencode-ai
  ```

### 2. Clone & configure

```bash
git clone https://github.com/<you>/agent-bridge.git
cd agent-bridge
```

The config lives in [`configs/config.json`](configs/config.json) and can hold
**multiple projects** at once — each with its own `manager`, `worker` and
`loop` settings:

```json
{
  "active_project": "my-app",
  "projects": {
    "my-app":   { "project_path": "D:/repos/my-app",   "manager": {"type": "api"},   "worker": {"type": "opencode"} },
    "site-bot": { "project_path": "D:/repos/site-bot", "manager": {"type": "web"},    "worker": {"type": "opencode"} }
  }
}
```

Build it interactively (recommended) — it creates the config and can add more
projects on later runs:

```bash
python -m src --init
```

Or copy a working starter from [`configs/config.example.json`](configs/config.example.json)
and edit. Secrets can be referenced as env vars thanks to `${VAR}` expansion:

```json
{
  "active_project": "my-app",
  "projects": {
    "my-app": {
      "project_path": "./my-app",
      "manager": { "type": "api", "api": { "api_key": "${OPENAI_API_KEY}" } },
      "worker": { "type": "opencode" }
    }
  }
}
```

### 3. Run

Select a project by name — its own manager/worker/loop and session folder are
used automatically:

```bash
python -m src my-app --iterations 10
```

Omit the name to use `active_project`. Or pass everything on the CLI —
nothing to edit (name resolves the config, `--project` overrides the path):

```bash
python -m src my-app \
  --project /path/to/your/project \
  --manager api --worker opencode --iterations 10
```

### The `manual` workflow (no API, just a text editor)

```bash
python -m src test-project --manager manual
```

1. Write the first task in `sessions/test-project/next_task.txt`.
2. The bridge runs the worker and writes a clean report to `sessions/test-project/result_report.txt`.
3. Paste that report into your manager (e.g. ChatGPT).
4. Save the manager's reply as `sessions/test-project/next_task.txt`.
5. Run again. Repeat.

---

## Configuration reference

Full example: [`configs/config.example.json`](configs/config.example.json)

Top-level keys (any unrecognised keys in a project are ignored — unknown
projects in the map are fine, they're simply not active):

| Key | Default | Meaning |
| --- | --- | --- |
| `active_project` | first project | Which project runs when no name is given |
| `projects.<name>.project_path` | `""` | Target project directory |
| `projects.<name>.loop.iterations` | `0` | Max tasks (0 = run forever) |
| `projects.<name>.verbose` | `true` | Timestamped console logs |
| `projects.<name>.manager.type` | `manual` | `manual` \| `api` \| `web` \| `agent` |
| `projects.<name>.manager.system_prompt` | — | Instructions for the manager agent |
| `projects.<name>.manager.api.*` | — | `base_url`, `api_key`, `model`, `temperature`, `max_tokens` |
| `projects.<name>.manager.web.url` | chatgpt.com | Chat UI to automate |
| `projects.<name>.manager.web.headless` | `false` | Run the browser hidden |
| `projects.<name>.manager.agent.binary` | `opencode` | Manager CLI agent |
| `projects.<name>.worker.type` | `opencode` | `opencode` \| `generic` |
| `projects.<name>.worker.binary` | `opencode` | Worker command |
| `projects.<name>.worker.model` | — | Model for the worker (e.g. `provider/model`) |
| `projects.<name>.worker.extra_args` | `[]` | Extra args for the worker CLI |
| `projects.<name>.worker.timeout` | `1800` | Per-task timeout (seconds) |

Each project's session files (task, report, history, state) live in their own
folder under `sessions/`, so two projects never interfere.

### Manager types

- **`manual`** — tasks come from `sessions/<project>/next_task.txt`. Zero deps, works everywhere.
- **`api`** — any OpenAI-compatible chat API. Works with OpenAI, DeepSeek,
  OpenRouter, Ollama, local model servers… Keeps a rolling conversation
  history in `sessions/<project>/conversation_history.jsonl`.
- **`web`** — drives a chat website with Playwright. Ships presets for
  **ChatGPT** and **DeepSeek** (`manager.web.site = auto | chatgpt | deepseek`).
  One-time login, then fully automatic:
  ```bash
  pip install playwright && playwright install chromium
  python -m src my-app --manager web --iterations 20          # ChatGPT
  python -m src my-app --manager web --iterations 20          # set site in config
  ```
  If a site's UI changes, override the selectors in
  `manager.web.selectors` — no code changes needed.
- **`agent`** — a second CLI agent is the manager. True agent↔agent, no
  vendored LLM in the loop:
  ```bash
  python -m src my-app --manager agent --worker opencode
  ```

### Worker types

- **`opencode`** — calls the `opencode` CLI headlessly (`--format json`,
  `--auto`). Your existing opencode config/models are used as-is.
- **`generic`** — runs any command; the task is appended to argv
  (`binary + args + task`). stdout becomes the report.

---

## Session files (everything is local, per project)

```
sessions/
  browser_profile/         ← persisted login for web mode (shared)
  <project>/               ← one folder per project
    next_task.txt            the pending task (manual mode)
    result_report.txt        latest report for the manager
    reports/report_<ts>.md   timestamped report archive
    conversation_history.jsonl  rolling context for api manager
    opencode_run_<code>.txt  raw worker transcripts
    state.json               resume point for --resume
```

## CLI extras

| Command | What it does |
| --- | --- |
| `<name>` | Select a project defined in `configs/config.json` |
| `--list-projects` | List the configured project names and exit |
| `--init` | Interactive wizard that builds/extends `configs/config.json` |
| `--project X` | Override the selected project's directory |
| `--dry-run` | Show the config + pending task without invoking the worker |
| `--git-check` | Append a `git status --short` / `git diff --stat` summary to each report |
| `--resume` | Resume an interrupted run from `sessions/<project>/state.json` |
| `--max-report-len N` | Clip reports longer than `N` chars (0 = unlimited) |
| `--clear-history` | Reset the api-manager conversation history |

Examples:

```bash
python -m src --list-projects                     # see configured projects
python -m src test-project --dry-run              # plan only, no agent run
python -m src test-project --git-check            # reports include git impact
python -m src test-project --resume               # continue after a crash
python -m src test-project --max-report-len 8000  # keep reports short
```

The pipeline recognises `DONE` (or `DONE.` / trailing text) from **any**
manager — api, web, agent or manual — and stops cleanly.

## Architecture

```
src/
  cli.py                CLI + config overrides
  config.py             multi-project config loading, ${ENV} expansion
  orchestrator.py       the loop (Bridge)
  init_wizard.py        interactive --init setup
  git_check.py          read-only git status/diff for reports
  utils.py              per-project session files + history
  managers/
    base.py             Manager protocol + manual (file-based)
    api.py              OpenAI-compatible API
    web.py              Playwright browser automation (ChatGPT/DeepSeek presets)
    agent.py            another agent's CLI
  workers/
    base.py             Worker protocol + WorkerResult
    opencode_worker.py  opencode CLI
    generic_worker.py   any command
```

Adding a new backend is a small file implementing one method:

```python
class MyManager(Manager):
    def get_next_task(self, report: str) -> str:
        ...  # return the next task, or "DONE"
```

```python
class MyWorker(Worker):
    def run(self, task: str) -> WorkerResult:
        ...  # do the work, return a report
```

Then register it in `managers/__init__.py` / `workers/__init__.py`.

---

## Roadmap

- [x] Interactive `--init` wizard
- [x] `--dry-run` planning mode
- [x] `--git-check` report enrichment
- [x] Timestamped report archive in `sessions/<project>/reports/`
- [x] Per-project sessions (`sessions/<project>/`) and multi-project config
- [ ] `run.py` console entry point (no `-m src`)
- [ ] Test suite (pytest) for managers/workers

## License

[MIT](./LICENSE)

## Contributing

Pull requests are welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md).
Found a bug or missing integration? [Open an issue](https://github.com/<you>/agent-bridge/issues).