#!/usr/bin/env python3
"""
全プロバイダの利用可能モデル一覧を Markdown 表 または JSON で出力する。
hermes-fake-moa スキル用。

対応プロバイダ:
  - OpenCode Go       (opencode-go)    — 認証不要
  - Nous Portal       (nous)           — OAuth (auth.json)
  - OpenRouter        (openrouter)     — OPENROUTER_API_KEY (.env)
  - Google AI Studio  (google)         — GOOGLE_API_KEY (.env)
  - Gemini OAuth      (gemini-cli)     — OAuth (Cloud Code Assist, API Key 不要)
  - xAI / Grok        (xai)            — OAuth (auth.json) or XAI_API_KEY (.env)
  - NVIDIA NIM        (nvidia)         — NVIDIA_API_KEY (.env)
  - Ollama Cloud      (ollama-cloud)   — OLLAMA_API_KEY (.env)
  - LM Studio         (lmstudio)       — ローカルサーバー (port 1234)

Usage:
  python3 list-models.py              # Markdown 出力
  python3 list-models.py --json       # JSON 出力
  python3 list-models.py --json --all # JSON + 全モデル（上限なし）
"""

import argparse
import json
import ssl
import sys
import urllib.request
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
ENV_PATH = HERMES_HOME / ".env"
AUTH_PATH = HERMES_HOME / "auth.json"

CONTEXT_SIZE = {
    "opencode-go": {"default": 131_072, "mimo-v2.5-pro": 1_000_000},
    "openrouter": {},
    "nous": {},
    "google": {},
    "gemini-cli": {},
    "xai": {},
    "nvidia": {},
    "ollama-cloud": {},
    "lmstudio": {},
}

PRICE_OVERRIDES = {
    "nous": {},
    "opencode-go": {},
}


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


def fetch_opencode_go(env: dict) -> list[dict]:
    """OpenCode Go: curl を使う（urllib は 403 になる）。"""
    import subprocess
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
            max_out = m.get("max_output_tokens")
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
    models = []
    for m in data.get("data", []):
        mid = m["id"]
        ctx = m.get("context_length", 131_072)
        pricing = {"prompt": "0", "completion": "0"}
        models.append({
            "id": mid, "context_length": ctx, "max_output_tokens": None,
            "pricing": pricing, "provider_specific": {},
        })
    return models


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
        methods = m.get("supportedGenerationMethods", [])
        if "generateContent" not in methods:
            continue
        mid = m.get("name", "").replace("models/", "")
        ctx = m.get("inputTokenLimit", 1_048_576)
        max_out = m.get("outputTokenLimit", 65_536)
        pricing = {}
        if "inputTokenLimit" in m:
            pricing = {"prompt": "0", "completion": "0"}
        models.append({
            "id": mid, "context_length": ctx, "max_output_tokens": max_out,
            "pricing": pricing, "provider_specific": {},
        })
    return models


def fetch_gemini_cli(auth: dict, env: dict) -> list[dict]:
    """Gemini OAuth (Cloud Code Assist) — same model set as google, different auth."""
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
        ctx = ssl.create_default_context()
        r = urllib.request.urlopen(req, timeout=10, context=ctx)
        data = json.load(r)
        models = []
        for m in data.get("data", []):
            if not m.get("id", "").startswith("grok"):
                continue
            mid = m["id"]
            models.append({
                "id": mid, "context_length": 131_072, "max_output_tokens": None,
                "pricing": {"prompt": "0", "completion": "0"},
                "provider_specific": {},
            })
        return models
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
        ctx = ssl.create_default_context()
        r = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.load(r)
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            if "embed" in mid.lower() or "rerank" in mid.lower() or "audio" in mid.lower():
                continue
            ctx_len = m.get("context_length", 131_072)
            max_out = m.get("max_output_tokens")
            pricing = {}
            if "pricing" in m:
                pricing = {
                    "prompt": m["pricing"].get("prompt", "0"),
                    "completion": m["pricing"].get("completion", "0"),
                }
            models.append({
                "id": mid, "context_length": ctx_len, "max_output_tokens": max_out,
                "pricing": pricing, "provider_specific": {},
            })
        return models
    except Exception:
        return []


def fetch_ollama_cloud(env: dict) -> list[dict]:
    """Ollama Cloud — cloud-hosted open models via ollama.com/v1."""
    key = env.get("OLLAMA_API_KEY")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://ollama.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
        )
        ctx = ssl.create_default_context()
        r = urllib.request.urlopen(req, timeout=15, context=ctx)
        data = json.load(r)
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            ctx_len = m.get("context_length", 131_072)
            max_out = m.get("max_output_tokens")
            pricing = {}
            if "pricing" in m:
                pricing = {
                    "prompt": m["pricing"].get("prompt", "0"),
                    "completion": m["pricing"].get("completion", "0"),
                }
            models.append({
                "id": mid, "context_length": ctx_len, "max_output_tokens": max_out,
                "pricing": pricing, "provider_specific": {},
            })
        return models
    except Exception:
        return []


def fetch_lmstudio() -> list[dict]:
    """LM Studio — local server, no auth required."""
    try:
        r = urllib.request.urlopen("http://127.0.0.1:1234/v1/models", timeout=5)
        data = json.load(r)
        models = []
        for m in data.get("data", []):
            mid = m.get("id", "")
            if "embed" in mid.lower():
                continue
            models.append({
                "id": mid, "context_length": 32_768, "max_output_tokens": None,
                "pricing": {"prompt": "0", "completion": "0"},
                "provider_specific": {"local": True},
            })
        return models
    except Exception:
        return []


PROVIDERS = [
    ("opencode-go",  "OpenCode Go",       lambda env, auth: fetch_opencode_go(env)),
    ("nous",         "Nous Portal",       lambda env, auth: fetch_nous(auth)),
    ("openrouter",   "OpenRouter",        lambda env, auth: fetch_openrouter(env)),
    ("google",       "Google AI Studio",  lambda env, auth: fetch_google(env)),
    ("gemini-cli",   "Gemini OAuth",      lambda env, auth: fetch_gemini_cli(auth, env)),
    ("xai",          "xAI / Grok",        lambda env, auth: fetch_xai(auth, env)),
    ("nvidia",       "NVIDIA NIM",        lambda env, auth: fetch_nvidia(env)),
    ("ollama-cloud", "Ollama Cloud",      lambda env, auth: fetch_ollama_cloud(env)),
    ("lmstudio",     "LM Studio",         lambda env, auth: fetch_lmstudio()),
]

PROVIDER_EMOJI = {
    "opencode-go": "🟢",
    "nous": "🔵",
    "openrouter": "🟠",
    "google": "🟣",
    "gemini-cli": "💎",
    "xai": "⚫",
    "nvidia": "🟤",
    "ollama-cloud": "🦙",
    "lmstudio": "🏠",
}

TEXT_PRICE_PER_M = {"nous": 1.0, "opencode-go": 1.0 / 15}


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
                    "id": mid,
                    "context_length": m.get("context_length"),
                    "max_output_tokens": m.get("max_output_tokens"),
                    "pricing": m.get("pricing", {}),
                    "providers": [],
                    "free": False,
                    "provider_specific": m.get("provider_specific", {}),
                }
            aggregated[mid]["providers"].append(provider_id)
            pricing = m.get("pricing", {})
            prompt_price = pricing.get("prompt", "0")
            try:
                if float(prompt_price) == 0:
                    aggregated[mid]["free"] = True
            except (ValueError, TypeError):
                pass
            if provider_id in PRICE_OVERRIDES and mid in PRICE_OVERRIDES[provider_id]:
                aggregated[mid]["pricing"] = PRICE_OVERRIDES[provider_id][mid]
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
    paid_count = len(models) - free_count
    lines.append(f"- **無料モデル**: {free_count}")
    lines.append(f"- **有料モデル**: {paid_count}\n")

    lines.append("| # | free | ID | providers | コンテキスト | 価格($/M) |")
    lines.append("|---|------|-----|-----------|------------|----------|")

    sorted_models = sorted(
        models,
        key=lambda m: (
            not m.get("free"),
            -len(m.get("providers", [])),
            m["id"],
        ),
    )

    limit = len(sorted_models) if show_all else 200
    for i, m in enumerate(sorted_models[:limit], 1):
        free_tag = "🆓" if m.get("free") else "💲"
        mid = m["id"]
        provs = " ".join(
            f"{PROVIDER_EMOJI.get(p,'')}{p}" for p in m.get("providers", [])
        )
        ctx = m.get("context_length")
        if ctx is None:
            ctx_str = "—"
        elif ctx >= 1_000_000:
            ctx_str = f"{ctx/1_000_000:.0f}M"
        elif ctx >= 1_000:
            ctx_str = f"{ctx/1_000:.0f}K"
        else:
            ctx_str = str(ctx)
        pricing = m.get("pricing", {})
        inp = pricing.get("prompt", "0")
        out = pricing.get("completion", "0")
        price_str = f"in:{_fmt_price(inp)} out:{_fmt_price(out)}" if inp else ""
        lines.append(f"| {i} | {free_tag} | `{mid}` | {provs} | {ctx_str} | {price_str} |")

    if not show_all and len(sorted_models) > limit:
        lines.append(f"\n*... 他 {len(sorted_models) - limit} モデル（`--all` で全件表示）*")

    lines.append(f"\n---\n*Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    return "\n".join(lines) + "\n"


def _fmt_price(raw) -> str:
    try:
        p = float(raw)
        if p == 0:
            return "free"
        return f"${p*1_000_000:.2f}"
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