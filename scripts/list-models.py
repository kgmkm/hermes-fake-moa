#!/usr/bin/env python3
"""
全プロバイダの利用可能モデル一覧を Markdown 表 または JSON で出力する。
hermes-fake-moa スキル用。

対応プロバイダ:
  - OpenCode Go         (opencode-go)     — 認証不要
  - Nous Portal         (nous)            — OAuth (auth.json)
  - OpenRouter          (openrouter)      — OPENROUTER_API_KEY (.env)
  - Google AI Studio    (google)          — GOOGLE_API_KEY (.env)
  - Gemini OAuth        (gemini-cli)      — OAuth (Cloud Code Assist)
  - xAI / Grok          (xai)             — XAI_API_KEY (.env)
  - NVIDIA NIM          (nvidia)          — NVIDIA_API_KEY (.env)
  - Ollama Cloud        (ollama-cloud)    — OLLAMA_API_KEY (.env)
  - LM Studio           (lmstudio)        — ローカル (port 1234)
  - GitHub Copilot      (copilot)         — GH_TOKEN (gh CLI)
  - HuggingFace Inference (huggingface)   — HF_TOKEN (.env)
  - OpenAI Codex        (openai-codex)    — OAuth (ChatGPT Plus/Pro要)

Usage:
  python3 list-models.py              # Markdown 出力
  python3 list-models.py --json       # JSON 出力
  python3 list-models.py --json --all # JSON + 全モデル（上限なし）
"""

import argparse
import json
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
ENV_PATH = HERMES_HOME / ".env"
AUTH_PATH = HERMES_HOME / "auth.json"


def read_env() -> dict[str, str]:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def read_auth() -> dict:
    if AUTH_PATH.exists():
        try:
            return json.loads(AUTH_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _ctx():
    return ssl.create_default_context()


# ── Providers ──────────────────────────────────────────────────

def fetch_opencode_go(env: dict) -> list[dict]:
    """OpenCode Go: curl を使う（urllib は 403 になる）。"""
    try:
        r = subprocess.run(
            ["curl", "-s", "https://opencode.ai/zen/go/v1/models"],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(r.stdout)
        models = []
        for m in data.get("data", []):
            mid = m["id"]
            ctx = m.get("context_length", 131_072)
            pricing = m.get("pricing", {})
            models.append({
                "id": mid, "context_length": ctx, "max_output_tokens": None,
                "pricing": pricing, "provider_specific": {},
            })
        return models
    except Exception:
        return []


def fetch_nous(auth: dict) -> list[dict]:
    token = auth.get("providers", {}).get("nous", {}).get("agent_key")
    if not token:
        return []
    req = urllib.request.Request(
        "https://inference-api.nousresearch.com/v1/models",
        headers={"Authorization": f"Bearer {token}"},
    )
    r = urllib.request.urlopen(req, timeout=15)
    data = json.load(r)
    return [{
        "id": m["id"], "context_length": m.get("context_length", 131_072),
        "max_output_tokens": None,
        "pricing": {"prompt": "0", "completion": "0"}, "provider_specific": {},
    } for m in data.get("data", [])]


def fetch_openrouter(env: dict) -> list[dict]:
    key = env.get("OPENROUTER_API_KEY")
    if not key:
        return []
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    r = urllib.request.urlopen(req, timeout=15)
    data = json.load(r)
    models = []
    for m in data.get("data", []):
        mid = m["id"]
        ctx = m.get("context_length", 131_072)
        max_out = m.get("top_provider", {}).get("max_completion_tokens")
        pricing = {}
        if "pricing" in m:
            pricing = {
                "prompt": m["pricing"].get("prompt", "0"),
                "completion": m["pricing"].get("completion", "0"),
            }
        models.append({
            "id": mid, "context_length": ctx, "max_output_tokens": max_out,
            "pricing": pricing, "provider_specific": {},
        })
    return models


def fetch_google(env: dict) -> list[dict]:
    key = env.get("GOOGLE_API_KEY") or env.get("GEMINI_API_KEY")
    if not key:
        return []
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    r = urllib.request.urlopen(url, timeout=15)
    data = json.load(r)
    models = []
    for m in data.get("models", []):
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        mid = m.get("name", "").replace("models/", "")
        models.append({
            "id": mid, "context_length": m.get("inputTokenLimit", 1_048_576),
            "max_output_tokens": m.get("outputTokenLimit", 65_536),
            "pricing": {"prompt": "0", "completion": "0"}, "provider_specific": {},
        })
    return models


def fetch_gemini_cli(auth: dict, env: dict) -> list[dict]:
    return fetch_google(env)


def fetch_xai(auth: dict, env: dict) -> list[dict]:
    key = env.get("XAI_API_KEY")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://api.x.ai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        r = urllib.request.urlopen(req, timeout=10, context=_ctx())
        data = json.load(r)
        return [{
            "id": m["id"], "context_length": 131_072, "max_output_tokens": None,
            "pricing": {"prompt": "0", "completion": "0"}, "provider_specific": {},
        } for m in data.get("data", []) if m.get("id", "").startswith("grok")]
    except Exception:
        return []


def fetch_nvidia(env: dict) -> list[dict]:
    key = env.get("NVIDIA_API_KEY")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://integrate.api.nvidia.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        r = urllib.request.urlopen(req, timeout=15, context=_ctx())
        data = json.load(r)
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            if any(x in mid.lower() for x in ["embed", "rerank", "audio"]):
                continue
            pricing = {}
            if "pricing" in m:
                pricing = {
                    "prompt": m["pricing"].get("prompt", "0"),
                    "completion": m["pricing"].get("completion", "0"),
                }
            models.append({
                "id": mid, "context_length": m.get("context_length", 131_072),
                "max_output_tokens": m.get("max_output_tokens"),
                "pricing": pricing, "provider_specific": {},
            })
        return models
    except Exception:
        return []


def fetch_ollama_cloud(env: dict) -> list[dict]:
    key = env.get("OLLAMA_API_KEY")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://ollama.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        r = urllib.request.urlopen(req, timeout=15, context=_ctx())
        data = json.load(r)
        return [{
            "id": m.get("id", ""), "context_length": m.get("context_length", 131_072),
            "max_output_tokens": m.get("max_output_tokens"),
            "pricing": m.get("pricing", {}), "provider_specific": {},
        } for m in data.get("data", [])]
    except Exception:
        return []


def fetch_lmstudio() -> list[dict]:
    try:
        r = urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=5)
        data = json.load(r)
        return [{
            "id": m.get("id", ""), "context_length": 32_768, "max_output_tokens": None,
            "pricing": {"prompt": "0", "completion": "0"},
            "provider_specific": {"local": True},
        } for m in data.get("data", []) if "embed" not in m.get("id", "").lower()]
    except Exception:
        return []


def fetch_copilot() -> list[dict]:
    """GitHub Copilot: gh CLI のトークンを使用。"""
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        token = r.stdout.strip()
        if not token:
            return []
        req = urllib.request.Request("https://api.githubcopilot.com/models")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Editor-Version", "vscode/1.0")
        req.add_header("Copilot-Integration-Id", "vscode-chat")
        resp = urllib.request.urlopen(req, timeout=15, context=_ctx())
        data = json.load(resp)
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            if any(x in mid.lower() for x in ["embed", "rerank"]):
                continue
            # reasoning effort levels: low/medium/high
            models.append({
                "id": mid, "context_length": 128_000, "max_output_tokens": None,
                "pricing": {"prompt": "0", "completion": "0"},
                "provider_specific": {"reasoning_effort": ["low", "medium", "high"]},
            })
        return models
    except Exception:
        return []


def fetch_huggingface(env: dict) -> list[dict]:
    key = env.get("HF_TOKEN")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://router.huggingface.co/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        r = urllib.request.urlopen(req, timeout=15, context=_ctx())
        data = json.load(r)
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            if any(x in mid.lower() for x in ["embed", "rerank"]):
                continue
            ctx_len = m.get("context_length", 131_072)
            pricing = {}
            if "pricing" in m:
                pricing = {
                    "prompt": m["pricing"].get("prompt", "0"),
                    "completion": m["pricing"].get("completion", "0"),
                }
            models.append({
                "id": mid, "context_length": ctx_len, "max_output_tokens": None,
                "pricing": pricing, "provider_specific": {},
            })
        return models
    except Exception:
        return []


def fetch_codex() -> list[dict]:
    """OpenAI Codex: ChatGPT Plus/Pro 専用。モデル一覧は API で取得不可。
    ハードコードされた既知モデルを返す。"""
    # Codex uses codex_responses API mode; models depend on ChatGPT plan
    known = [
        "gpt-5", "gpt-5-mini", "gpt-5.2-codex", "gpt-5.3-codex",
        "gpt-5.4", "gpt-5.4-mini", "gpt-5.5",
        "gpt-4o", "gpt-4o-mini", "gpt-4.1",
        "o3", "o3-mini", "o4-mini",
    ]
    return [{
        "id": mid, "context_length": 128_000, "max_output_tokens": None,
        "pricing": {"prompt": "0", "completion": "0"},
        "provider_specific": {"note": "ChatGPT account dependent; availability varies by plan"},
    } for mid in known]


# ── Aggregation ────────────────────────────────────────────────

PROVIDERS = [
    ("opencode-go",   "OpenCode Go",          lambda e, a: fetch_opencode_go(e)),
    ("nous",          "Nous Portal",           lambda e, a: fetch_nous(a)),
    ("openrouter",    "OpenRouter",            lambda e, a: fetch_openrouter(e)),
    ("google",        "Google AI Studio",      lambda e, a: fetch_google(e)),
    ("gemini-cli",    "Gemini OAuth",          lambda e, a: fetch_gemini_cli(a, e)),
    ("xai",           "xAI / Grok",            lambda e, a: fetch_xai(a, e)),
    ("nvidia",        "NVIDIA NIM",            lambda e, a: fetch_nvidia(e)),
    ("ollama-cloud",  "Ollama Cloud",          lambda e, a: fetch_ollama_cloud(e)),
    ("lmstudio",      "LM Studio",             lambda e, a: fetch_lmstudio()),
    ("copilot",       "GitHub Copilot",        lambda e, a: fetch_copilot()),
    ("huggingface",   "HuggingFace",           lambda e, a: fetch_huggingface(e)),
    ("openai-codex",  "OpenAI Codex",          lambda e, a: fetch_codex()),
]

PROVIDER_EMOJI = {
    "opencode-go": "🟢", "nous": "🔵", "openrouter": "🟠", "google": "🟣",
    "gemini-cli": "💎", "xai": "⚫", "nvidia": "🟤", "ollama-cloud": "🦙",
    "lmstudio": "🏠", "copilot": "🐙", "huggingface": "🤗", "openai-codex": "🔷",
}


def load_all_models(quiet: bool = False) -> list[dict]:
    env = read_env()
    auth = read_auth()
    aggregated = {}
    if not quiet:
        print("🔍 プロバイダAPIを照会中...\n", file=sys.stderr)
    for provider_id, display_name, fetcher in PROVIDERS:
        try:
            raw = fetcher(env, auth)
        except Exception:
            raw = []
        if not quiet:
            status = f"{len(raw)} models" if raw else "skipped (no key/creds)"
            print(f"   {display_name:<20}: {status}", file=sys.stderr)
        if not raw:
            continue
        for m in raw:
            mid = m["id"]
            if mid not in aggregated:
                aggregated[mid] = {
                    "id": mid, "context_length": m.get("context_length"),
                    "max_output_tokens": m.get("max_output_tokens"),
                    "pricing": m.get("pricing", {}), "providers": [],
                    "free": False, "provider_specific": m.get("provider_specific", {}),
                }
            aggregated[mid]["providers"].append(provider_id)
            try:
                if float(m.get("pricing", {}).get("prompt", "0")) == 0:
                    aggregated[mid]["free"] = True
            except (ValueError, TypeError):
                pass
            if m.get("context_length"):
                existing = aggregated[mid].get("context_length")
                if existing is None or m["context_length"] > existing:
                    aggregated[mid]["context_length"] = m["context_length"]
    return list(aggregated.values())


def format_markdown_table(models: list[dict], show_all: bool = False) -> str:
    lines = []
    lines.append("# 利用可能モデル一覧\n")
    lines.append(f"**合計: {len(models)} テキスト生成モデル**\n")
    prov_stats = {}
    for m in models:
        for p in m.get("providers", []):
            prov_stats[p] = prov_stats.get(p, 0) + 1
    lines.append("| プロバイダ | モデル数 |")
    lines.append("|-----------|---------|")
    for provider_id, display_name, _ in PROVIDERS:
        cnt = prov_stats.get(provider_id, 0)
        if cnt > 0:
            emoji = PROVIDER_EMOJI.get(provider_id, "")
            lines.append(f"| {emoji} {display_name} | {cnt} |")
    lines.append("")
    free_count = sum(1 for m in models if m.get("free"))
    lines.append(f"- **無料モデル**: {free_count}")
    lines.append(f"- **有料モデル**: {len(models) - free_count}\n")
    lines.append("| # | free | ID | providers | コンテキスト | 価格($/M) |")
    lines.append("|---|------|-----|-----------|------------|----------|")
    sorted_models = sorted(models, key=lambda m: (not m.get("free"), -len(m.get("providers", [])), m["id"]))
    limit = len(sorted_models) if show_all else 200
    for i, m in enumerate(sorted_models[:limit], 1):
        free_tag = "🆓" if m.get("free") else "💲"
        provs = " ".join(f"{PROVIDER_EMOJI.get(p,'')}{p}" for p in m.get("providers", []))
        ctx = m.get("context_length")
        ctx_str = f"{ctx/1_000_000:.0f}M" if ctx and ctx >= 1_000_000 else (f"{ctx/1_000:.0f}K" if ctx and ctx >= 1_000 else str(ctx or "—"))
        pricing = m.get("pricing", {})
        inp, out = pricing.get("prompt", "0"), pricing.get("completion", "0")
        price_str = f"in:{_fmt(inp)} out:{_fmt(out)}" if inp else ""
        lines.append(f"| {i} | {free_tag} | `{m['id']}` | {provs} | {ctx_str} | {price_str} |")
    if not show_all and len(sorted_models) > limit:
        lines.append(f"\n*... 他 {len(sorted_models) - limit} モデル（`--all` で全件表示）*")
    import datetime
    lines.append(f"\n---\n*Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    return "\n".join(lines) + "\n"


def _fmt(raw) -> str:
    try:
        p = float(raw)
        return "free" if p == 0 else f"${p*1_000_000:.2f}"
    except (ValueError, TypeError):
        return str(raw)


def main():
    parser = argparse.ArgumentParser(description="全プロバイダの利用可能モデル一覧を出力")
    parser.add_argument("--json", action="store_true", help="JSON 出力")
    parser.add_argument("--all", action="store_true", help="全モデル表示（上限なし）")
    args = parser.parse_args()
    models = load_all_models()
    if args.json:
        print(json.dumps(models, ensure_ascii=False, indent=2))
    else:
        print(format_markdown_table(models, show_all=args.all))


if __name__ == "__main__":
    main()