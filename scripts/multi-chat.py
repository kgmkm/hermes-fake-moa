#!/usr/bin/env python3
"""
選択されたパネル（2〜5モデル）に同一プロンプトを並列送信し、結果を集約する。

Usage:
  python3 multi-chat.py --panel my-panel --prompt "質問文"
  python3 multi-chat.py --panel default --file prompt.txt
  python3 multi-chat.py --panel default < prompt.txt
  python3 multi-chat.py --panel default --file prompt.txt --cwd /path/to/project
  python3 multi-chat.py --panel my-panel --prompt "..." --delay 0.8
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

TIMEOUT = 300  # 1プロセスあたりの最大秒数
MAX_TURNS = 3  # ツール呼び出し制限
ARG_MAX_THRESHOLD = 30000  # このサイズを超えるプロンプトは一時ファイル経由で渡す


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
    
    プロンプトが ARG_MAX_THRESHOLD (30KB) を超える場合、
    内容を一時ファイルに書き出し、-q には read_file 指示のみ渡す。
    これにより OS の ARG_MAX 制限 (E2BIG / Errno 7) を回避する。
    
    Windows 環境では hermes が PATH にある必要がある。
    hermes が見つからない場合は hermes.bat またはフルパスを使用。"""
    label = f"[{idx}] {model_id}"
    print(f"🚀 {label} 送信中...", file=sys.stderr)

    # Windows 環境では hermes の実行ファイル名が異なる場合がある
    hermes_cmd = "hermes"
    if sys.platform == "win32":
        # PowerShell / CMD では hermes.bat または hermes.exe
        hermes_cmd = "hermes"

    # ARG_MAX 回避: プロンプトが大きい場合は一時ファイル経由で渡す
    tmpfile = None
    if len(prompt) > ARG_MAX_THRESHOLD:
        tmpfile = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', prefix='moa_prompt_',
            delete=False, encoding='utf-8'
        )
        tmpfile.write(prompt)
        tmpfile.close()

        instruction = (
            f"read_file で {tmpfile.name} を読み、"
            f"内容に従ってください。"
            f"ファイルの指示に従い回答のみを出力してください。"
            f"前説や前置きは不要です。"
        )
        turns = MAX_TURNS + 2  # read_file + 回答のための余裕
        cmd = [
            hermes_cmd, "chat", "-q", instruction,
            "-m", model_id,
            "--provider", provider,
            "-Q", "--yolo",
            "--max-turns", str(turns),
        ]
        print(f"   📄 大規模プロンプト({len(prompt)}chars): 一時ファイル経由", file=sys.stderr)
    else:
        cmd = [
            hermes_cmd, "chat", "-q", prompt,
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
    finally:
        # 一時ファイルの後始末
        if tmpfile:
            try:
                os.unlink(tmpfile.name)
            except OSError:
                pass


def run_parallel(panel: list[dict], prompt: str, delay: float = 0.0) -> list[dict]:
    """全モデルを並列起動し、全完了を待つ。
    
    delay > 0 の場合、同一プロバイダのモデル間で遅延を入れる。
    これにより API レート制限（429 Too Many Requests）を緩和する。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    results = []
    submit_lock = threading.Lock()

    # プロバイダごとにグルーピングして最後の投入時刻を追跡
    last_submit: dict[str, float] = {}

    def submit_with_delay(model: dict, idx: int):
        """同一プロバイダのモデル間で delay 秒の間隔を空けて投入。"""
        nonlocal last_submit
        provider = model["provider"]
        with submit_lock:
            now = time.time()
            last = last_submit.get(provider, 0)
            wait = delay - (now - last)
            if wait > 0:
                time.sleep(wait)
            last_submit[provider] = time.time()
        return run_model(model["id"], model["provider"], prompt, idx)

    with ThreadPoolExecutor(max_workers=len(panel)) as executor:
        futures = {
            executor.submit(submit_with_delay, m, i + 1): m
            for i, m in enumerate(panel)
        }
        for future in as_completed(futures):
            results.append(future.result())

    # 投入順に並べ替え
    order = {m["id"]: i for i, m in enumerate(panel)}
    results.sort(key=lambda r: order.get(r["model"], 99))
    return results


def save_results(results: list[dict], panel_name: str, prompt: str, cwd: str | None = None):
    """結果を results/ に保存。個別ファイル + サマリー MD。"""
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

    # サマリーファイル（Markdown）
    summary = f"# Fake MoA Results — `{panel_name}`\n\n"
    summary += f"**Time**: {ts}  \n"
    summary += f"**Models**: {len(results)}  \n"
    summary += f"**Prompt** ({len(prompt)} chars):\n"
    summary += f"> {prompt[:300]}{'...' if len(prompt)>300 else ''}\n\n"

    # ステータス表
    summary += "## Status\n\n"
    summary += "| # | Model | Provider | Status | Time |\n"
    summary += "|---|-------|----------|--------|------|\n"
    for i, r in enumerate(results, 1):
        status = "✅" if r["exit_code"] == 0 else "❌"
        summary += f"| {i} | `{r['model']}` | {r['provider']} | {status} | {r['elapsed']}s |\n"
    summary += "\n"

    # 比較表（成功したモデルのみ、最初の120文字をプレビュー）
    ok_results = [r for r in results if r["exit_code"] == 0]
    if len(ok_results) >= 2:
        summary += "## Comparison\n\n"
        summary += "| Model | Preview |\n"
        summary += "|-------|--------|\n"
        for r in ok_results:
            preview = r["output"][:120].replace("\n", " ").replace("|", "\\|")
            summary += f"| `{r['model']}` | {preview}... |\n"
        summary += "\n"

    # 各モデルの回答全文
    summary += "## Responses\n\n"
    for r in results:
        status_icon = "✅" if r["exit_code"] == 0 else "❌"
        summary += f"### {status_icon} {r['model']} (`{r['provider']}` — {r['elapsed']}s)\n\n"
        if r["exit_code"] == 0:
            summary += f"{r['output']}\n\n"
        else:
            summary += f"```\n{r['output']}\n```\n"
            if r["error"]:
                summary += f"**Error**: `{r['error'][:200]}`\n"
        summary += "\n---\n\n"

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
    parser.add_argument("--delay", "-d", type=float, default=0.0,
                        help="同一プロバイダのモデル間の投入遅延（秒）。レート制限緩和に有効（推奨: 0.5〜1.0）")
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

    print(f"\n📡 Fake MoA: {args.panel} ({len(panel)}モデル)", file=sys.stderr)
    if args.delay > 0:
        print(f"   ⏱️  プロバイダ間遅延: {args.delay}s", file=sys.stderr)
    print(file=sys.stderr)
    for m in panel:
        print(f"   `{m['id']}` @ {m['provider']}", file=sys.stderr)
    print(file=sys.stderr)

    results = run_parallel(panel, prompt, delay=args.delay)
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
