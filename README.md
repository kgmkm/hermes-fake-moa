# hermes-fake-moa

**Hermes Agent Exclusive Skill**

Multi-LLM parallel orchestrator for Hermes Agent — send the same prompt to multiple LLMs simultaneously and compare their responses side-by-side.

This is **NOT true MoA (Mixture of Agents)** — it is **manual orchestration with parallel model execution** (Fake MoA).

## Features

- **12 providers supported**: OpenCode Go / Nous Portal / OpenRouter / Google AI Studio / Gemini OAuth / xAI Grok / NVIDIA NIM / Ollama Cloud / LM Studio / GitHub Copilot / HuggingFace / OpenAI Codex
- **600+ models**: List all available models across all providers (text generation models only)
- **free/paid indicator**: 159+ free models clearly marked
- **Panel selection**: Choose 2–5 models and save the configuration
- **Parallel dispatch**: Send the same prompt to all selected models simultaneously, collect results
- **General-purpose**: Code review, translation comparison, brainstorming, content evaluation — field-agnostic
- **Windows support**: `python3` / `python` auto-resolution (scripts use `sys.executable` internally)

## Why Manual Orchestration

Hermes Agent's built-in `mixture_of_agents` tool has the following constraints that make manual orchestration preferable for general-purpose parallel execution:

| Aspect | Built-in moa | Fake MoA (this skill) |
|--------|-------------|----------------------|
| Provider | **OpenRouter only** (`OPENROUTER_API_KEY` required) | Any (all user-configured providers) |
| Default models | Hardcoded for general reasoning | User freely selects and changes |
| Model specification | Hardcoded in source | CLI args / panels.json — fully flexible |
| Skill portability | ❌ (provider-dependent) | ✅ (adapts to user's environment) |
| Execution method | delegate_task (inherits parent model) | hermes chat -q (independent sessions) |
| Same-model constraint | None (same model can be declared) | Same-model disallowed (warned — defeats MoA purpose) |

**The biggest difference**: The built-in moa has an aggregator model produce a final answer, while this skill lets **you, the human**, compare and judge each model's response. This avoids the risk of LLM "opinion bias."

## Prerequisites

- Hermes Agent running environment
- At least one LLM provider configured
- Python 3.10+ (use `python` on Windows)

> **Windows (PowerShell)**: Replace `python3` with `python` in command examples. Script-internal subprocess calls (`select-panel.py` → `list-models.py`) use `sys.executable`, so environment differences are resolved automatically.

## Recommended Providers (as of May 2026)

Model names change rapidly, so we don't recommend specific models. Use `python3 scripts/list-models.py` to see the latest available models before running.

### Selection Criteria

| Criterion | Description |
|-----------|-------------|
| Multi-model | Single provider supports multiple models (good for assigning different models to MoA agents) |
| Flagship support | Top-tier models (GPT-5 / Claude 4 / Gemini 3 etc.) available |
| Hermes compatibility | Officially supported or proven working, stable authentication |
| Free tier | Free models or limited-time free tiers available (reduces trial cost) |
| Pricing | Affordable even when paid (~$10–20/mo flat rate or reasonable pay-per-token) |

### Core Recommendations

| Provider | Highlights |
|----------|------------|
| **OpenCode Go** | $10/mo flat rate. Simple model names (no provider prefix needed). Easiest first leg for MoA |
| **OpenRouter** | 350+ models. Pay-per-token. Access to all major models. Maximum model choice for MoA |
| **Nous Portal** | Official Nous Research. Highest Hermes Agent compatibility. deepseek-v4-flash etc. free |
| **Google AI Studio** | Gemini models available on free tier. Strong at long-context tasks |
| **Gemini OAuth** | Via Cloud Code Assist. No API key needed, OAuth only |

### Additional Candidates

| Provider | Highlights |
|----------|------------|
| **NVIDIA NIM** | Nemotron models. Free tier. 123 models |
| **xAI / Grok** | Grok series. Requires SuperGrok subscription but powerful |
| **Ollama Cloud** | Cloud-hosted open models. ollama.com/v1. Free tier |
| **LM Studio** | Local LLMs. Completely free. Ideal for custom model/LoRA experiments |

### Model Name Formats (varies by provider)

| Provider | Format | Example |
|----------|--------|---------|
| opencode-go | `model-name` (as-is) | `mimo-v2.5-pro` |
| nous | `provider/model-name` | `deepseek/deepseek-v4-flash` |
| openrouter | `provider/model-name` | `anthropic/claude-sonnet-4.6` |
| google | `model-name` (as-is) | `gemini-2.5-flash` |
| gemini-cli | `model-name` (as-is) | `gemini-2.5-flash` |
| xai | `model-name` (as-is) | `grok-4.3` |
| nvidia | `provider/model-name` | `deepseek-ai/deepseek-v4-flash` |
| ollama-cloud | `model:tag` | `deepseek-v4-flash`, `gemma4:31b` |
| lmstudio | `model-name` (as-is) | `qwen3.6-27b-uncensored-hauhaucs-balanced` |
| copilot | `model-name` (as-is) | `gpt-4o`, `claude-sonnet-4.6` |
| huggingface | `owner/model` | `deepseek-ai/DeepSeek-V4-Flash` |
| openai-codex | `model-name` (as-is) | `gpt-5`, `o4-mini` (plan-dependent) |

**If you get a 404 error, the model name format is likely wrong.** Use `list-models.py` to verify the correct ID.

## Quick Start

```bash
# 1. List available models
python3 scripts/list-models.py > models.md

# 2. Select a panel (2–5 models)
# Interactive mode:
python3 scripts/select-panel.py --name my-panel

# Non-interactive mode (for agents/scripts):
python3 scripts/select-panel.py --name my-panel \
  --models "mimo-v2.5-pro:opencode-go,deepseek/deepseek-v4-flash:nous,gemini-2.5-flash:google"

# 3. Run in parallel
python3 scripts/multi-chat.py --panel my-panel --prompt "Your question"

# Specify panels.json / results/ location:
python3 scripts/multi-chat.py --panel my-panel --file prompt.txt --cwd /path/to/project
```

## Installation

```bash
git clone https://github.com/kgmkm/hermes-fake-moa.git ~/.hermes/skills/hermes-fake-moa
```

## File Structure

| Path | Purpose |
|------|---------|
| `SKILL.md` | Skill definition and usage |
| `scripts/list-models.py` | List available models (MD / JSON) |
| `scripts/select-panel.py` | Panel selection (interactive / non-interactive) |
| `scripts/multi-chat.py` | Parallel prompt dispatch + result collection |
| `templates/panels.default.json` | Panel configuration template |
| `references/provider-quirks.md` | Provider-specific notes, OS environment differences |
| `references/large-prompt-workaround.md` | ARG_MAX limit workaround for large prompts (>30KB) |

## Supported Providers

| Provider | `--provider` name | Auth | Model count |
|----------|-------------------|------|-------------|
| OpenCode Go | `opencode-go` | None | 15 |
| Nous Portal | `nous` | OAuth | 250+ |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | 350 |
| Google AI Studio | `google` | `GOOGLE_API_KEY` | 35 |
| Gemini OAuth | `gemini-cli` | OAuth (Code Assist) | 35 |
| xAI Grok | `xai` | `XAI_API_KEY` | 8 |
| NVIDIA NIM | `nvidia` | `NVIDIA_API_KEY` | 123 |
| Ollama Cloud | `ollama-cloud` | `OLLAMA_API_KEY` | 39 |
| LM Studio | `lmstudio` | None (local) | User-dependent |
| GitHub Copilot | `copilot` | GH_TOKEN (gh CLI) | 22 |
| HuggingFace | `huggingface` | `HF_TOKEN` | 128 |
| OpenAI Codex | `openai-codex` | OAuth | Requires ChatGPT Plus/Pro |

## Call for Contributions

I do not have a Claude subscription. If you have access to either of the following and are interested in contributing, please send a pull request — I'd appreciate it! (And of course, **do not push any sensitive information** like API keys or tokens.)

### Wanted: Anthropic Provider Support

**1. Claude Pro / Max subscription (OAuth login)**

Implement an `anthropic-oauth` provider in `list-models.py` that authenticates via Anthropic's OAuth flow and lists available Claude models from the user's subscription.

**2. Anthropic API key (pay-per-token)**

Implement an `anthropic` provider in `list-models.py` that uses `ANTHROPIC_API_KEY` to call the Anthropic Messages API and lists available models.

Both should follow the same pattern as existing providers in `scripts/list-models.py` — add a provider function, wire it into the provider registry, and document any quirks in `references/provider-quirks.md`.

## License

0BSD
