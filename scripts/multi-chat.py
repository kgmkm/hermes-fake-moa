#!/usr/bin/env python3
"""
選択されたパネル（2〜5モデル）に同一プロンプトを並列送信し、結果を集約する。

Usage:
  python3 multi-chat.py --panel novel-revision --prompt "質問文"
  python3 multi-chat.py --panel default --file prompt.txt
  python3 multi-chat.py --panel default < prompt.txt
  python3 multi-chat.py --panel default --file prompt.txt --cwd /path/to/project
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

TIMEOUT = 300  # 1プロセスあたりの最大秒数
MAX_TURNS = 3  # ツール呼び出し制限


def resolve_panels_file(cwd: str | None = None) -> Path:
    """panels.json のパスを解決。
    --cwd 指定時はそのディレクトリ、未指定時はカレントディレクトリ。"""
    if cwd:
        return Path(cwd) / "panels.json"
    return Path.cwd() / "panels.json"


def resolve_results_dir(cwd: str | None = None) -> Path:
    """results/ のパスを解決。"""
    base = Path(cwd) if cwd else Path.cwd()
    return base / "results"


def load_panel(name: str, cwd: str | None = None) -> list[dict]:
    """panels.json から指定パネルを読み込み。"""
    panels_file = resolve_panels_file(cwd)
    if not panels_file.exists():
        print(f"❌ {panels_file} が見つかりません。先に select-panel.py を実行してください。")
        sys.exit(1)
    data = json.loads(panels_file.read_text())
    panels = data.get("panels", {})
    if name not in panels:
        avail = ", ".join(panels.keys()) if panels else "(なし)"
        print(f"❌ パネル '{name}' は存在しません。利用可能: {avail}")
        sys.exit(1)
    return panels[name]


def run_model(model_id: str, provider: str, prompt: str, idx: int) -> dict:
    """1モデルに hermes chat -q を投げ、結果を返す。
    
    subprocess.run のリスト引数を使うため、プロンプトの改行はそのまま渡せる。
    シェルを経由しないのでエスケープは不要。
    """
    label = f"[{idx}] {model_id}"
    print(f"🚀 {label} 送信中...", file=sys.stderr)

    cmd = [
        "hermes", "chat", "-q", prompt,
        "-m", model_id,
        "--provider", provider,
        "-Q", "--yolo",
        "--max-turns", str(MAX_TURNS),
    ]

    start = time.time()
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=TIMEOUT
        )
        elapsed = time.time() - start
        output = r.stdout.strip()
        stderr_out = r.stderr.strip()

        # セッションID抽出
        session_id = ""
        for line in output.splitlines():
            if line.startswith("session_id:"):
                session_id = line.replace("session_id:", "").strip()

        # スピナー行等のノイズ除去
        clean_lines = []
        for line in output.splitlines():
            if any(skip in line for skip in [
                "Loading weights:", "Batches:", "session_id:",
            ]):
                continue
            clean_lines.append(line)
        clean_output = "\n".join(clean_lines).strip()

        status = "✅" if r.returncode == 0 else "❌"
        print(f"{status} {label} ({elapsed:.0f}s)", file=sys.stderr)

        return {
            "model": model_id,
            "provider": provider,
            "exit_code": r.returncode,
            "elapsed": round(elapsed, 1),
            "output": clean_output,
            "error": stderr_out if r.returncode != 0 else "",
            "session_id": session_id,
        }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"⏰ {label} タイムアウト ({TIMEOUT}s)", file=sys.stderr)
        return {
            "model": model_id,
            "provider": provider,
            "exit_code": -1,
            "elapsed": round(elapsed, 1),
            "output": "[TIMEOUT]",
            "error": f"Timeout after {TIMEOUT}s",
            "session_id": "",
        }
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ {label} 例外: {e}", file=sys.stderr)
        return {
            "model": model_id,
            "provider": provider,
            "exit_code": -2,
            "elapsed": round(elapsed, 1),
            "output": f"[ERROR: {e}]",
            "error": str(e),
            "session_id": "",
        }


def run_parallel(panel: list[dict], prompt: str) -> list[dict]:
    """全モデルを並列起動し、全完了を待つ。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []
    with ThreadPoolExecutor(max_workers=len(panel)) as executor:
        futures = {
            executor.submit(run_model, m["id"], m["provider"], prompt, i + 1): m
            for i, m in enumerate(panel)
        }
        for future in as_completed(futures):
            results.append(future.result())

    # 投入順に並べ替え
    order = {m["id"]: i for i, m in enumerate(panel)}
    results.sort(key=lambda r: order.get(r["model"], 99))
    return results


def save_results(results: list[dict], panel_name: str, prompt: str, cwd: str | None = None):
    """結果を results/ に保存。"""
    results_dir = resolve_results_dir(cwd)
    results_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = results_dir / f"{panel_name}_{ts}"

    # 個別ファイル
    for r in results:
        fname = f"{base}_{r['model'].replace('/','_')}.txt"
        content = f"Model: {r['model']}\nProvider: {r['provider']}\n"
        content += f"Exit: {r['exit_code']}  Time: {r['elapsed']}s\n"
        content += f"Session: {r['session_id']}\n{'='*60}\n\n"
        content += r['output']
        if r['error']:
            content += f"\n\n{'='*60}\nSTDERR:\n{r['error']}"
        Path(fname).write_text(content)

    # サマリーファイル
    summary = f"# Fake MoA Results — {panel_name}\n\n"
    summary += f"**Time**: {ts}\n\n"
    summary += f"**Prompt** ({len(prompt)} chars):\n> {prompt[:300]}{'...' if len(prompt)>300 else ''}\n\n"
    summary += "## Models\n\n"
    for r in results:
        status = "✅" if r["exit_code"] == 0 else "❌"
        summary += f"- {status} `{r['model']}` @ {r['provider']} ({r['elapsed']}s)\n"
    summary += f"\n## Responses\n\n"
    for r in results:
        summary += f"### {r['model']}\n\n{r['output']}\n\n---\n\n"
    Path(f"{base}_summary.md").write_text(summary)

    return base


def main():
    global MAX_TURNS, TIMEOUT

    parser = argparse.ArgumentParser(description="Hermes Fake MoA — 並列マルチLLM実行")
    parser.add_argument("--panel", "-p", required=True, help="パネル名")
    parser.add_argument("--prompt", "-q", help="プロンプト文字列")
    parser.add_argument("--file", "-f", help="プロンプトファイル")
    parser.add_argument("--cwd", "-c", help="panels.json / results/ の配置ディレクトリ（未指定時はカレント）")
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS, help="ツール呼び出し上限")
    parser.add_argument("--timeout", type=int, default=TIMEOUT, help="タイムアウト秒数")
    args = parser.parse_args()

    MAX_TURNS = args.max_turns
    TIMEOUT = args.timeout

    # プロンプト取得
    if args.file:
        prompt = Path(args.file).read_text().strip()
    elif args.prompt:
        prompt = args.prompt
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    else:
        print("❌ --prompt か --file か標準入力でプロンプトを指定してください")
        sys.exit(1)

    if not prompt:
        print("❌ プロンプトが空です")
        sys.exit(1)

    panel = load_panel(args.panel, cwd=args.cwd)

    print(f"\n📡 Fake MoA: {args.panel} ({len(panel)}モデル)\n", file=sys.stderr)
    for m in panel:
        print(f"   `{m['id']}` @ {m['provider']}", file=sys.stderr)
    print(file=sys.stderr)

    results = run_parallel(panel, prompt)
    base = save_results(results, args.panel, prompt, cwd=args.cwd)

    # 標準出力にサマリー
    print(f"\n{'='*60}")
    print(f"Fake MoA Results — {args.panel}")
    print(f"Saved: {base}_*")
    print(f"{'='*60}\n")
    for r in results:
        status = "✅" if r["exit_code"] == 0 else "❌"
        print(f"{status} `{r['model']}` @ {r['provider']} ({r['elapsed']}s)")
        if r["output"] and r["output"] != "[TIMEOUT]" and not r["output"].startswith("[ERROR"):
            preview = r["output"][:200]
            print(f"   {preview}{'...' if len(r['output'])>200 else ''}")
        elif r["error"]:
            print(f"   ❌ {r['error'][:150]}")
        print()


if __name__ == "__main__":
    main()