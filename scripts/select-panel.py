#!/usr/bin/env python3
"""
モデル一覧から 2〜5 モデルを選択し、panels.json に保存する。

使い方:
  対話選択（人間がターミナルで操作）:
    python3 select-panel.py --name novel-revision

  非対話選択（エージェントやスクリプトから使用）:
    python3 select-panel.py --name novel-revision --models "mimo-v2.5-pro:opencode-go,deepseek/deepseek-v4-flash:nous,gemini-2.5-flash:google"

  パネル一覧:
    python3 select-panel.py --list

  パネル削除:
    python3 select-panel.py --delete novel-revision

  panels.json の直接編集も可能。形式:
    {
      "version": 1,
      "active": "novel-revision",
      "panels": {
        "novel-revision": [
          {"id": "mimo-v2.5-pro", "provider": "opencode-go"},
          {"id": "deepseek/deepseek-v4-flash", "provider": "nous"}
        ]
      }
    }
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
LIST_MODELS = SKILL_DIR / "scripts" / "list-models.py"

PROVIDER_ORDER = ["opencode-go", "nous", "openrouter", "google", "xai", "nvidia"]
PROVIDER_EMOJI = {
    "opencode-go": "🟢",
    "nous": "🔵",
    "openrouter": "🟠",
    "google": "🟣",
    "xai": "⚫",
    "nvidia": "🟤",
}


def resolve_panels_file(cwd: str | None = None) -> Path:
    """panels.json のパスを解決。
    --cwd 指定時はそのディレクトリ、未指定時はカレントディレクトリ。"""
    if cwd:
        return Path(cwd) / "panels.json"
    return Path.cwd() / "panels.json"


def load_panels(cwd: str | None = None) -> dict:
    panels_file = resolve_panels_file(cwd)
    if panels_file.exists():
        return json.loads(panels_file.read_text())
    return {"version": 1, "active": None, "panels": {}}


def save_panels(data: dict, cwd: str | None = None):
    panels_file = resolve_panels_file(cwd)
    panels_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def fetch_models() -> list[dict]:
    """list-models.py --json の結果を取得。"""
    r = subprocess.run(
        [sys.executable, str(LIST_MODELS), "--json"],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        print("❌ モデル一覧の取得に失敗しました", file=sys.stderr)
        sys.stderr.write(r.stderr)
        sys.exit(1)
    # JSON部分を抽出（stderrの進捗メッセージを除外）
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        # stdout内からJSON開始位置を探す
        for i, line in enumerate(r.stdout.splitlines()):
            if line.strip().startswith("["):
                return json.loads("\n".join(r.stdout.splitlines()[i:]))
        print("❌ モデル一覧のパースに失敗しました", file=sys.stderr)
        sys.exit(1)


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
    """対話的に 2〜5 モデルを選択。人間のターミナル操作専用。"""
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


def cmd_list(cwd: str | None = None):
    """既存パネル一覧。"""
    data = load_panels(cwd)
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


def cmd_select_from_models(models_str: str, name: str, cwd: str | None = None):
    """--models 引数からパネルを作成（エージェント・スクリプト用）。
    
    models_str 形式: "model_id:provider,model_id:provider,..."
    例: "mimo-v2.5-pro:opencode-go,deepseek/deepseek-v4-flash:nous"
    """
    entries = []
    for pair in models_str.split(","):
        pair = pair.strip()
        if ":" in pair:
            model_id, provider = pair.rsplit(":", 1)
        else:
            # provider が省略された場合、list-models.py の結果から推測
            model_id = pair
            provider = None
        entries.append((model_id, provider))

    # provider 未指定のモデルを解決
    all_models = fetch_models()
    model_map = {m["id"]: m for m in all_models}
    
    panel = []
    for model_id, provider in entries:
        if model_id not in model_map:
            print(f"⚠ モデル '{model_id}' が見つかりません。スキップします。", file=sys.stderr)
            continue
        
        m = model_map[model_id]
        if provider is None:
            # 優先順位で provider を自動選択
            provs = m.get("providers", [])
            provider = None
            for p in PROVIDER_ORDER:
                if p in provs:
                    provider = p
                    break
            if provider is None:
                provider = provs[0] if provs else "unknown"
        
        panel.append({"id": model_id, "provider": provider})

    if len(panel) < 2:
        print("❌ 最低2モデル必要です。キャンセルしました。", file=sys.stderr)
        sys.exit(1)

    data = load_panels(cwd)
    data["panels"][name] = panel
    data["active"] = name
    save_panels(data, cwd)

    print(f"\n✅ パネル '{name}' を保存しました（{len(panel)}モデル）")
    for m in panel:
        print(f"   {PROVIDER_EMOJI.get(m['provider'],'')} `{m['id']}` @ {m['provider']}")
    print(f"\n実行: python3 scripts/multi-chat.py --panel {name}")


def cmd_select_interactive(name: str, cwd: str | None = None):
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
        provs = m.get("providers", [])
        chosen = None
        for p in PROVIDER_ORDER:
            if p in provs:
                chosen = p
                break
        if not chosen:
            chosen = provs[0]

        panel.append({"id": m["id"], "provider": chosen})

    data = load_panels(cwd)
    data["panels"][name] = panel
    data["active"] = name
    save_panels(data, cwd)

    print(f"\n✅ パネル '{name}' を保存しました（{len(panel)}モデル）")
    for m in panel:
        print(f"   {PROVIDER_EMOJI.get(m['provider'],'')} `{m['id']}` @ {m['provider']}")
    print(f"\n実行: python3 scripts/multi-chat.py --panel {name}")


def cmd_delete(name: str, cwd: str | None = None):
    data = load_panels(cwd)
    if name not in data.get("panels", {}):
        print(f"❌ パネル '{name}' は存在しません")
        return
    del data["panels"][name]
    if data.get("active") == name:
        data["active"] = next(iter(data["panels"]), None)
    save_panels(data, cwd)
    print(f"🗑 パネル '{name}' を削除しました")


def main():
    parser = argparse.ArgumentParser(description="Hermes Fake MoA — モデルパネル選択")
    parser.add_argument("--name", "-n", default="default", help="パネル名")
    parser.add_argument("--models", "-m", help="非対話モード: 'model:provider,model:provider,...' 形式で直接指定")
    parser.add_argument("--list", "-l", action="store_true", help="既存パネル一覧")
    parser.add_argument("--delete", "-d", help="パネル削除")
    parser.add_argument("--cwd", "-c", help="panels.json の配置ディレクトリ（未指定時はカレント）")
    args = parser.parse_args()

    if args.list:
        cmd_list(cwd=args.cwd)
    elif args.delete:
        cmd_delete(args.delete, cwd=args.cwd)
    elif args.models:
        cmd_select_from_models(args.models, args.name, cwd=args.cwd)
    else:
        # 対話モード（人間のターミナル操作専用）
        if not sys.stdin.isatty():
            print("❌ 非対話環境です。--models 引数でモデルを指定してください。", file=sys.stderr)
            print("例: python3 select-panel.py --name my-panel --models 'mimo-v2.5-pro:opencode-go,deepseek/deepseek-v4-flash:nous'", file=sys.stderr)
            sys.exit(1)
        cmd_select_interactive(args.name, cwd=args.cwd)


if __name__ == "__main__":
    main()