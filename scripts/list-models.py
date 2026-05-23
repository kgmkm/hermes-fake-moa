#!/usr/bin/env python3
"""
全プロバイダの利用可能モデル一覧を Markdown 表 または JSON で出力する。
hermes-fake-moa スキル用。

対応プロバイダ:
  - OpenCode Go   (opencode-go)  — 認証不要
  - Nous Portal   (nous)         — OAuth (auth.json)
  - OpenRouter    (openrouter)   — OPENROUTER_API_KEY (.env)
  - Google AI     (google)       — GOOGLE_API_KEY (.env)
  - xAI / Grok    (xai)          — OAuth (auth.json) or XAI_API_KEY (.env)
  - NVIDIA NIM    (nvidia)       — NVIDIA_API_KEY (.env)

【他 LLM プロバイダを使う場合／API が変わった場合の改定方法】
  1. 対象 LLM の公式 API ドキュメントで /v1/models エンドポイントを確認する
  2. 認証方式（API Key, OAuth Bearer, 不要）を確認する
  3. レスポンス JSON の構造（data[].id, pricing, context_length 等）を確認する
  4. fetch_*() 関数を参考に、新しい fetch_yourprovider() を実装する
  5. main() に追加して動作確認する

Usage:
  python3 list-models.py              # Markdown 出力
  python3 list-models.py --json       # JSON 出力
  python3 list-models.py --json --all # JSON + 全モデル（上限なし）
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

AUTH_PATH = Path.home() / ".hermes" / "auth.json"
ENV_PATH = Path.home() / ".hermes" / ".env"

PROVIDER_COLORS = {
    "opencode-go": "🟢",
    "nous": "🔵",
    "openrouter": "🟠",
    "google": "🟣",
    "xai": "⚫",
    "nvidia": "🟤",
}


# ── 認証ヘルパー ──────────────────────────────────────────

def _load_env() -> dict[str, str]:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:]
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and v:
                env[k] = v
    return env


def _nous_token() -> str | None:
    try:
        return json.loads(AUTH_PATH.read_text())["providers"]["nous"]["agent_key"]
    except Exception:
        return None


def _xai_token() -> str | None:
    try:
        return json.loads(AUTH_PATH.read_text())["providers"]["xai-oauth"]["tokens"]["access_token"]
    except Exception:
        return None


# ── API フェッチ ──────────────────────────────────────────

def fetch_opencode() -> list[dict]:
    try:
        r = subprocess.run(
            ["curl", "-s", "https://opencode.ai/zen/go/v1/models"],
            capture_output=True, text=True, timeout=10)
        models = json.loads(r.stdout).get("data", [])
        return [{"id": m["id"], "provider": "opencode-go"} for m in models]
    except Exception as e:
        print(f"⚠ opencode-go: {e}", file=sys.stderr)
        return []


def fetch_nous() -> list[dict]:
    token = _nous_token()
    if not token:
        print("⚠ nous: token not found", file=sys.stderr)
        return []
    try:
        r = subprocess.run(
            ["curl", "-s", "https://inference-api.nousresearch.com/v1/models",
             "-H", f"Authorization: Bearer {token}"],
            capture_output=True, text=True, timeout=15)
        return _parse_rich(json.loads(r.stdout).get("data", []), "nous")
    except Exception as e:
        print(f"⚠ nous: {e}", file=sys.stderr)
        return []


def fetch_openrouter() -> list[dict]:
    key = _load_env().get("OPENROUTER_API_KEY")
    if not key:
        print("⚠ openrouter: OPENROUTER_API_KEY not set", file=sys.stderr)
        return []
    try:
        r = subprocess.run(
            ["curl", "-s", "https://openrouter.ai/api/v1/models",
             "-H", f"Authorization: Bearer {key}"],
            capture_output=True, text=True, timeout=15)
        return _parse_rich(json.loads(r.stdout).get("data", []), "openrouter")
    except Exception as e:
        print(f"⚠ openrouter: {e}", file=sys.stderr)
        return []


def fetch_google() -> list[dict]:
    key = _load_env().get("GOOGLE_API_KEY")
    if not key:
        print("⚠ google: GOOGLE_API_KEY not set", file=sys.stderr)
        return []
    try:
        r = subprocess.run(
            ["curl", "-s",
             f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"],
            capture_output=True, text=True, timeout=15)
        data = json.loads(r.stdout)
        models = data.get("models", [])
        result = []
        for m in models:
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            name = m["name"].replace("models/", "")
            result.append({
                "id": name,
                "provider": "google",
                "name": name,
                "pricing": {"prompt": "0", "completion": "0"},
                "context_length": m.get("inputTokenLimit"),
                "max_tokens": m.get("outputTokenLimit"),
            })
        return result
    except Exception as e:
        print(f"⚠ google: {e}", file=sys.stderr)
        return []


def fetch_xai() -> list[dict]:
    token = _xai_token()
    if not token:
        token = _load_env().get("XAI_API_KEY")
    if not token:
        print("⚠ xai: no token/key found", file=sys.stderr)
        return []
    try:
        r = subprocess.run(
            ["curl", "-s", "https://api.x.ai/v1/models",
             "-H", f"Authorization: Bearer {token}"],
            capture_output=True, text=True, timeout=15)
        data = json.loads(r.stdout)
        if "error" in data:
            print(f"⚠ xai: {data['error']}", file=sys.stderr)
            return []
        return _parse_rich(data.get("data", []), "xai")
    except Exception as e:
        print(f"⚠ xai: {e}", file=sys.stderr)
        return []


def fetch_nvidia() -> list[dict]:
    key = _load_env().get("NVIDIA_API_KEY")
    if not key:
        print("⚠ nvidia: NVIDIA_API_KEY not set", file=sys.stderr)
        return []
    try:
        r = subprocess.run(
            ["curl", "-s", "https://integrate.api.nvidia.com/v1/models",
             "-H", f"Authorization: Bearer {key}"],
            capture_output=True, text=True, timeout=15)
        return _parse_rich(json.loads(r.stdout).get("data", []), "nvidia")
    except Exception as e:
        print(f"⚠ nvidia: {e}", file=sys.stderr)
        return []


def _parse_rich(raw: list[dict], provider: str) -> list[dict]:
    result = []
    for m in raw:
        if m["id"].startswith("~"):
            continue
        pricing = m.get("pricing", {})
        top = m.get("top_provider", {})
        result.append({
            "id": m["id"],
            "provider": provider,
            "name": m.get("name", m["id"]),
            "pricing": pricing,
            "context_length": m.get("context_length") or top.get("context_length"),
            "max_tokens": top.get("max_completion_tokens"),
        })
    return result


# ── 整形 ──────────────────────────────────────────────────

def _price_usd_per_mtok(raw) -> str:
    if raw is None:
        return ""
    try:
        p = float(raw)
    except (ValueError, TypeError):
        return str(raw)
    if p == 0:
        return "free"
    usd_per_m = p * 1_000_000
    if usd_per_m >= 10:
        return f"${usd_per_m:.0f}/M"
    elif usd_per_m >= 1:
        return f"${usd_per_m:.2f}/M"
    else:
        return f"${usd_per_m:.2f}/M"


def _is_free(pricing: dict | None) -> bool:
    if not pricing:
        return True
    try:
        return float(pricing.get("prompt", 0)) == 0 and float(pricing.get("completion", 0)) == 0
    except (ValueError, TypeError):
        return False


def fmt_pricing(pricing: dict | None) -> str:
    if not pricing:
        return ""
    inp = _price_usd_per_mtok(pricing.get("prompt"))
    out = _price_usd_per_mtok(pricing.get("completion"))
    if inp and out:
        if inp == out:
            return inp
        return f"in:{inp} out:{out}"
    return inp or out


def fmt_n(n: int | None) -> str:
    if n is None:
        return ""
    if n >= 1_000_000:
        return f"{n/1_000_000:.0f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


# ── フィルタ ──────────────────────────────────────────────

SKIP_KEYWORDS = [
    "image", "tts", "transcribe", "embed", "whisper", "chirp",
    "veo", "sora", "flux", "seedance", "kling", "wan-", "recraft",
    "kokoro", "zonos", "csm-", "orpheus", "rerank", "grok-imagine",
    "grok-voice", "voxtral-mini-tts", "lyria", "hailuo",
    "gpt-4o-audio", "gpt-audio", "ui-tars", "safeguard",
    "asr", "ocr", "seedream", "solidity", "guard", "switchpoint",
    "spotlight", "codex", "preview-tts",
    # NVIDIA の非テキスト系
    "fuyu", "deplot", "starcoder",  # 画像・コード専用
]


def is_text(m: dict) -> bool:
    for kw in SKIP_KEYWORDS:
        if kw in m["id"].lower():
            return False
    return True


# ── メイン ────────────────────────────────────────────────

def short_id(full_id: str) -> str:
    return full_id.split("/")[-1]


def build(args):
    print("🔍 プロバイダAPIを照会中...\n", file=sys.stderr)

    fetchers = [
        ("opencode-go", fetch_opencode),
        ("nous", fetch_nous),
        ("openrouter", fetch_openrouter),
        ("google", fetch_google),
        ("xai", fetch_xai),
        ("nvidia", fetch_nvidia),
    ]

    all_raw: list[dict] = []
    for pname, fn in fetchers:
        models = fn()
        print(f"   {pname:15s}: {len(models)} models", file=sys.stderr)
        all_raw.extend(models)

    merged: dict[str, dict] = {}

    for m in all_raw:
        uid = m["id"]
        if uid in merged:
            merged[uid]["providers"].add(m["provider"])
            if m.get("pricing") and not merged[uid].get("pricing"):
                merged[uid]["pricing"] = m["pricing"]
            if m.get("context_length") and not merged[uid].get("context_length"):
                merged[uid]["context_length"] = m["context_length"]
            if m.get("max_tokens") and not merged[uid].get("max_tokens"):
                merged[uid]["max_tokens"] = m["max_tokens"]
        else:
            merged[uid] = {
                "id": uid,
                "name": m.get("name", uid),
                "pricing": m.get("pricing"),
                "context_length": m.get("context_length"),
                "max_tokens": m.get("max_tokens"),
                "providers": {m["provider"]},
            }

    entries = [e for e in merged.values() if is_text(e)]
    entries.sort(key=lambda e: (-len(e["providers"]), e.get("name", "")))

    return entries


def output_markdown(entries: list[dict], limit: int = 100):
    print("## 利用可能なテキスト生成モデル一覧\n")
    print("| # | ID | プロバイダ | 料金($/M) | コンテキスト | 最大出力 |")
    print("|---|-----|-----------|-----------|------------|---------|")

    for i, e in enumerate(entries[:limit], 1):
        prov_tags = " ".join(
            f"{PROVIDER_COLORS.get(p, '')}`{p}`" for p in sorted(e["providers"])
        )
        price = fmt_pricing(e.get("pricing"))
        ctx = fmt_n(e.get("context_length"))
        out = fmt_n(e.get("max_tokens"))
        print(f"| {i} | `{e['id']}` | {prov_tags} | {price} | {ctx} | {out} |")

    print(f"\n*{len(entries)} モデル中、上位{min(limit, len(entries))}件を表示。*")
    print("*プロバイダ: 🟢opencode-go 🔵nous 🟠openrouter 🟣google ⚫xai 🟤nvidia*")
    print("*料金: free=無料、$0.43/M=100万トークンあたり$0.43*")


def output_json(entries: list[dict]):
    out = []
    for e in entries:
        free = _is_free(e.get("pricing"))
        out.append({
            "id": e["id"],
            "name": e.get("name", e["id"]),
            "providers": sorted(e["providers"]),
            "free": free,
            "pricing": e.get("pricing"),
            "context_length": e.get("context_length"),
            "max_tokens": e.get("max_tokens"),
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="List available LLM models across providers")
    parser.add_argument("--json", action="store_true", help="JSON output instead of Markdown")
    parser.add_argument("--all", action="store_true", help="Show all models (no limit)")
    parser.add_argument("--limit", type=int, default=100, help="Max models in Markdown mode")
    args = parser.parse_args()

    entries = build(args)

    if args.json:
        output_json(entries)
    else:
        output_markdown(entries, limit=9999 if args.all else args.limit)


if __name__ == "__main__":
    main()
