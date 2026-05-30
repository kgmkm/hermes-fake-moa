---
name: hermes-fake-moa
description: Multi-LLM parallel orchestrator — list available models across all configured providers, select 2–5 models into a panel, and send the same prompt to all of them simultaneously. NOT true MoA (no aggregator model). Results are collected side-by-side for human comparison.
version: 1.3.1
tags: [llm, multi-model, orchestration, parallel, moa, comparison, panel]
---

# Hermes Fake MoA — Multi-LLM Parallel Orchestrator

**Hermes Agent Exclusive Skill**

A skill for sending the same question to multiple LLMs simultaneously and comparing their responses.
This is **NOT true MoA (Mixture of Agents)** — it is **manual orchestration with parallel model execution**.

## ⚠️ CRITICAL: Never Use the Built-in Hermes Agent `moa` Tool

Hermes Agent ships with a **built-in `mixture_of_agents` tool** (hereafter "built-in moa").
It calls **4 reference models + 1 aggregator model via OpenRouter** and is **completely different** from hermes-fake-moa.

**Why you must NOT use the built-in moa**:

1. **High API costs**: Calling up to 5 models via OpenRouter can incur $1–$5+ per run (actual damage: $5.80 loss)
2. **No model selection**: The built-in moa auto-selects models; you cannot choose your preferred configuration
3. **Conflicts with hermes-fake-moa**: When the built-in moa toolset is enabled, agents may accidentally use it

**Absolute rules**:

- **Never call** the `mixture_of_agents()` function
- If `moa` appears in your toolsets, **disable it** with `hermes config set toolsets`
- For multi-LLM parallel execution, **always use hermes-fake-moa's `multi-chat.py`**
- Never fall back to the built-in moa when you see instructions like "MoA", "multiple models", or "parallel execution"

**Disable command** (if the moa toolset is enabled):
```bash
# Check current toolset configuration
hermes config get toolsets

# Reconfigure excluding moa (keep other toolsets as-is)
hermes config set toolsets "terminal,file,web,skills,search,patch,delegation"
```

## Prerequisites

- Hermes Agent running environment
- At least one LLM provider configured
- Python 3.10+ (use `python` on Windows)

> **Windows (PowerShell)**: Replace `python3` with `python` in command examples.
> Script-internal subprocess calls (`select-panel.py` → `list-models.py`) use `sys.executable`,
> so environment differences are resolved automatically.

## Supported Providers (as of May 2026)

| Provider | `--provider` name | Auth | Notes |
|----------|-------------------|------|-------|
| OpenCode Go | `opencode-go` | None | 15 models, $10/mo flat rate |
| Nous Portal | `nous` | OAuth | 250+ models, free tier |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | 350 models, pay-per-token |
| Google AI Studio | `google` | `GOOGLE_API_KEY` | 35 models, free tier |
| Gemini OAuth | `gemini-cli` | OAuth (Code Assist) | 35 models, no API key needed |
| xAI / Grok | `xai` | `XAI_API_KEY` | 8 models, subscription required |
| NVIDIA NIM | `nvidia` | `NVIDIA_API_KEY` | 123 models, free tier |
| Ollama Cloud | `ollama-cloud` | `OLLAMA_API_KEY` | 39 models, ollama.com/v1 |
| LM Studio | `lmstudio` | None (local) | Local models, port 1234 |
| GitHub Copilot | `copilot` | GH_TOKEN (gh CLI) | 22 models, reasoning effort support |
| HuggingFace | `huggingface` | `HF_TOKEN` | 128 models, Inference Providers |
| OpenAI Codex | `openai-codex` | OAuth | Requires ChatGPT Plus/Pro, reasoning effort support |

## Workflow

### Step 1: List available models

```bash
python3 scripts/list-models.py > models.md
```

Outputs all available models across all providers as a Markdown table in `models.md`.

JSON output also available:
```bash
python3 scripts/list-models.py --json > models.json
```

### Step 2: Consult the user on which provider/model to use

Always ask the user to review `models.md` and select 3–5 providers/models for their MoA panel.
Some users may find model differences hard to parse — also suggest about 3 recommended options.

**Recommended provider/model selection criteria**:
- Flat-rate providers (OpenCode Go, Ollama Cloud, Codex, etc.) flagship or midship models
- Credit-based but relatively inexpensive and recent models
- Free-tier models with reasonably long context windows

**Important**: The agent must NOT select models and send prompts without the user's explicit consent.
Using the user's credits without permission is a liability issue.

### Step 3: Select a panel (model set)

**Non-interactive mode** (for agents and scripts):
```bash
python3 scripts/select-panel.py --name my-panel \
  --models "mimo-v2.5-pro:opencode-go,deepseek/deepseek-v4-flash:nous,gemini-2.5-flash:google"
```

`--models` format: comma-separated `model_id:provider` pairs. Provider can be omitted for auto-selection.

Or manually edit `panels.json`:
```json
{
  "version": 1,
  "active": "my-panel",
  "panels": {
    "my-panel": [
      {"id": "mimo-v2.5-pro", "provider": "opencode-go"},
      {"id": "deepseek/deepseek-v4-flash", "provider": "nous"},
      {"id": "gemini-2.5-flash", "provider": "google"}
    ]
  }
}
```

> **Note**: The `"active"` field is set automatically by `select-panel.py`. `multi-chat.py` requires `--panel` explicitly and ignores `active`.

### Step 4: Send prompts in parallel

```bash
python3 scripts/multi-chat.py --panel my-panel --prompt "Your question here"
```

Or read the prompt from a file:
```bash
python3 scripts/multi-chat.py --panel my-panel --file prompt.txt
```

**Location of `panels.json` / `results/`**:
- Default: current working directory
- Use `--cwd /path/to/project` to specify (recommended when running from within Hermes Agent)

Results are saved in the `results/` directory with timestamps.

**Rate limiting prevention**: If multiple models share the same provider, use `--delay` to stagger launches and avoid API rate limits (429 errors):
```bash
python3 scripts/multi-chat.py --panel my-panel --file prompt.txt --delay 0.8
```

## Reading Results

Each model's response is saved to an individual `.txt` file.
A combined `_summary.md` Markdown file is also generated with:
- A status table (model, provider, result, elapsed time)
- A side-by-side comparison table (first 120 chars of each response)
- Full responses for each model

Items flagged by multiple models are especially noteworthy.

## File Structure

| Path | Purpose |
|------|---------|
| `scripts/list-models.py` | List all available models (MD / JSON) |
| `scripts/select-panel.py` | Interactive/non-interactive panel selection |
| `scripts/multi-chat.py` | Parallel prompt dispatch + result collection |
| `templates/panels.default.json` | Panel configuration template |
| `references/provider-quirks.md` | Provider-specific notes, model ID formats, auth methods |
| `references/large-prompt-workaround.md` | ARG_MAX limit workaround for large prompts (>30KB) |

## Limitations

- Model listing, selection, and parallel execution must use the `hermes-fake-moa` skill
- Hermes Agent internal execution only (depends on `hermes chat -q`)
- Recommended: 3 models, minimum 2, maximum 5 (sending extra models is allowed to tolerate rejections/errors from some)
- The agent must NOT select models and send prompts without the user's explicit consent
- **The built-in `mixture_of_agents` tool (moa toolset) is absolutely forbidden**. It causes high billing via OpenRouter (actual damage: $5.80). Always use this skill's `multi-chat.py` for multi-LLM execution

## Common Pitfalls

| Failure | Cause | Fix |
|---------|-------|-----|
| `[Errno 7] Argument list too long` | Prompt >67KB passed via `-q` exceeds ARG_MAX | multi-chat.py v1.1.1+ auto-switches to temp-file mode |
| Built-in moa used, $5.80 charged | moa toolset enabled + OpenRouter configured | `hermes config set toolsets` to exclude moa |
| Symlink broken, skill_view fails | Skill path changed / repo moved | `ln -sfn /actual/path ~/.hermes/skills/skill-name` |
| `mimo-v2.5-pro` times out (300s) | Large prompt (>25KB) causes mimo to hang | Use `deepseek-v4-pro` or `kimi-k2.6` + `glm-5.1` 2-model config instead |
| Follow-up questions lose context | multi-chat.py is stateless; each run is independent | Embed the previous analysis summary in the new prompt. Previous results persist in `results/` — use `read_file` to fetch and inject as context |
| `qwen3.6-plus` fails every time | Model loading issue in opencode-go (`Loading weights: 100%` → error) | Exclude this model from panels. See `references/provider-quirks.md` |
| 429 / rate limit errors | Multiple models on the same provider fire simultaneously | Use `--delay 0.8` (or higher) to stagger launches. See `--delay` option in Step 4 |
