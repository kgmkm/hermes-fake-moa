#!/usr/bin/env python3
"""
モデル一覧から 2〜5 モデルを選択し、panels.json に保存する。

Usage:
  python3 select-panel.py                          # 対話選択
  python3 select-panel.py --name novel-revision    # パネル名指定
  python3 select-panel.py --list                   # 既存パネル一覧
  python3 select-panel.py --delete novel-revision  # パネル削除
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LIST_MODELS = SKILL_DIR / "scripts" / "list-models.py"
PANELS_FILE = Path("panels.json")

PROVIDER_ORDER = ["opencode-go", "nous", "openrouter", "google", "xai", "nvidia"]
PROVIDER_EMOJI = {
    "opencode-go": "🟢",
    "nous": "🔵",
    "openrouter": "🟠",
    "google": "🟣",
    "xai": "⚫",
    "nvidia": "🟤",
}


def load_panels() -> dict:
    if PANELS_FILE.exists():
        return json.loads(PANELS_FILE.read_text())
    return {"version": 1, "active": None, "panels": {}}


def save_panels(data: dict):
    PANELS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def fetch_models() -> list[dict]:
    """list-models.py --json の結果を取得。"""
    r = subprocess.run(
        [sys.executable, str(LIST_MODELS), "--json"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        print("❌ モデル一覧の取得に失敗しました", file=sys.stderr)
        sys.exit(1)
    # stderr が混ざっている場合を考慮
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("["):
            return json.loads(line)
    return json.loads(r.stdout)


def print_model_list(models: list[dict], max_show: int = 50):
    """モデル一覧を対話的に表示。"""
    print("\n📋 利用可能モデル（free優先、プロバイダ数順）\n")
    print(f"{'#':<4} {'free':<5} {'ID':<45} {'providers':<35} {'価格($/M)':<20}")
    print("-" * 115)
    for i, m in enumerate(models[:max_show], 1):
        free_tag = "🆓" if m.get("free") else "💲"
        provs = " ".join(
            f"{PROVIDER_EMOJI.get(p,'')}{p}" for p in m.get("providers", [])
        )
        pricing = m.get("pricing", {})
        if pricing:
            inp = pricing.get("prompt", "")
            out = pricing.get("completion", "")
            price_str = f"in:{_fmt(inp)} out:{_fmt(out)}" if inp else ""
        else:
            price_str = ""
        print(f"{i:<4} {free_tag:<5} {m['id']:<45} {provs:<35} {price_str:<20}")

    if len(models) > max_show:
        print(f"\n... 他 {len(models) - max_show} モデル（--all で全表示）")


def _fmt(raw) -> str:
    try:
        p = float(raw)
        if p == 0:
            return "free"
        return f"${p*1_000_000:.2f}/M"
    except (ValueError, TypeError):
        return str(raw)


def interactive_select(models: list[dict]) -> list[dict]:
    """対話的に 2〜5 モデルを選択。"""
    selected = []
    print("\n🎯 モデルを番号で選択してください（2〜5個）。")
    print("   入力例: 1 5 12  または  free で無料のみ表示")
    print("   終了: done または空Enter\n")

    show_all = False

    while len(selected) < 5:
        if show_all:
            print_model_list(models, max_show=200)
        else:
            free_only = [m for m in models if m.get("free")]
            print_model_list(free_only, max_show=50)

        print(f"\n現在の選択 ({len(selected)}/5): ", end="")
        if selected:
            print(", ".join(m["id"] for m in selected))
        else:
            print("なし")

        cmd = input("> ").strip()

        if cmd == "" or cmd == "done":
            if len(selected) >= 2:
                break
            print("⚠ 最低2モデル選択してください")
            continue

        if cmd == "free":
            continue

        if cmd == "all":
            show_all = True
            continue

        if cmd == "paid":
            show_all = True
            continue

        # 番号パース
        try:
            nums = [int(x) for x in cmd.split()]
        except ValueError:
            print("⚠ 番号を入力してください")
            continue

        current_list = models if show_all else [m for m in models if m.get("free")]

        for n in nums:
            if 1 <= n <= len(current_list):
                m = current_list[n - 1]
                if m not in selected:
                    selected.append(m)
                    print(f"  ✅ {m['id']} を追加")
            else:
                print(f"  ❌ 番号 {n} は範囲外")

    return selected


def cmd_list():
    """既存パネル一覧。"""
    data = load_panels()
    panels = data.get("panels", {})
    if not panels:
        print("パネル未登録。`python3 select-panel.py` で作成してください。")
        return
    active = data.get("active")
    for name, models in panels.items():
        tag = " ★アクティブ" if name == active else ""
        print(f"\n📦 {name}{tag}")
        for m in models:
            pid = m["id"]
            pv = m["provider"]
            emoji = PROVIDER_EMOJI.get(pv, "")
            print(f"   {emoji} `{pid}` @ {pv}")


def cmd_select(name: str):
    """対話選択して保存。"""
    print("モデル一覧を取得中...", file=sys.stderr)
    models = fetch_models()
    # free優先ソート
    models.sort(key=lambda m: (not m.get("free"), -len(m.get("providers", []))))

    selected = interactive_select(models)

    if len(selected) < 2:
        print("❌ 最低2モデル必要です。キャンセルしました。")
        return

    panel = []
    for m in selected:
        # Google/xAI models → 直API用に provider を解決
        provs = m.get("providers", [])
        # 優先: opencode-go > nous > openrouter > google > xai
        chosen = None
        for p in PROVIDER_ORDER:
            if p in provs:
                chosen = p
                break
        if not chosen:
            chosen = provs[0]

        panel.append({"id": m["id"], "provider": chosen})

    data = load_panels()
    data["panels"][name] = panel
    data["active"] = name
    save_panels(data)

    print(f"\n✅ パネル '{name}' を保存しました（{len(panel)}モデル）")
    for m in panel:
        print(f"   {PROVIDER_EMOJI.get(m['provider'],'')} `{m['id']}` @ {m['provider']}")
    print(f"\n実行: python3 scripts/multi-chat.py --panel {name}")


def cmd_delete(name: str):
    data = load_panels()
    if name not in data.get("panels", {}):
        print(f"❌ パネル '{name}' は存在しません")
        return
    del data["panels"][name]
    if data.get("active") == name:
        data["active"] = next(iter(data["panels"]), None)
    save_panels(data)
    print(f"🗑 パネル '{name}' を削除しました")


def main():
    parser = argparse.ArgumentParser(description="Hermes Fake MoA — モデルパネル選択")
    parser.add_argument("--name", "-n", default="default", help="パネル名")
    parser.add_argument("--list", "-l", action="store_true", help="既存パネル一覧")
    parser.add_argument("--delete", "-d", help="パネル削除")
    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.delete:
        cmd_delete(args.delete)
    else:
        cmd_select(args.name)


if __name__ == "__main__":
    main()
