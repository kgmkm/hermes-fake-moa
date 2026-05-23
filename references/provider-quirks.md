# プロバイダ固有の注意点

## Python / OS 環境

| 環境 | Python コマンド | 備考 |
|------|----------------|------|
| WSL / Linux | `python3` | スクリプトの shebang も `#!/usr/bin/env python3` |
| macOS | `python3` | Homebrew Python を想定 |
| Windows (PowerShell) | `python` | `python3` は存在しないことが多い。`python` を使用 |
| Windows (Git Bash) | `python` | 同上 |

スクリプト内部のサブプロセス呼び出し（`select-panel.py` → `list-models.py`）は `sys.executable` を使用するため、現在動いている Python と同じバイナリが起動される。環境差異は自動解決される。

`hermes` コマンドは PATH に含まれている必要がある。Windows では `hermes` は npm global install の `.cmd` ラッパーとして提供される。

## モデル名形式

| プロバイダ | 形式 | 例 |
|-----------|------|-----|
| opencode-go | `モデル名`（prefix不要） | `mimo-v2.5-pro` |
| nous | `owner/model` | `deepseek/deepseek-v4-flash` |
| openrouter | `owner/model` | `anthropic/claude-sonnet-4.6` |
| google | `モデル名`（prefix不要） | `gemini-2.5-flash` |
| gemini-cli | `モデル名`（prefix不要） | `gemini-2.5-flash` |
| xai | `モデル名`（prefix不要） | `grok-4.3` |
| nvidia | `owner/model` | `deepseek-ai/deepseek-v4-flash` |
| ollama-cloud | `model:tag` | `deepseek-v4-flash`, `gemma4:31b` |
| lmstudio | `モデル名`（そのまま） | `qwen3.6-27b-uncensored-hauhaucs-balanced` |

**自動正規化**: opencode-go では `deepseek/deepseek-v4-flash` と指定しても自動的に `deepseek-v4-flash` に変換される。他のプロバイダも同様の可能性あり。

**注意**: ollama-cloud はコロン付きタグ（`:31b`, `:120b` 等）を含むモデル名が標準。

## 認証方式

| プロバイダ | 方式 | 保存場所 | 有効期限 |
|-----------|------|---------|---------|
| opencode-go | 不要 | — | — |
| nous | OAuth (agent_key) | `~/.hermes/auth.json` | 15分（自動更新あり） |
| openrouter | API Key | `~/.hermes/.env` (`OPENROUTER_API_KEY`) | なし |
| google | API Key | `~/.hermes/.env` (`GOOGLE_API_KEY`) | なし |
| gemini-cli | OAuth (Cloud Code Assist) | `~/.hermes/auth.json` | 自動更新 |
| xai | OAuth (access_token) + API Key | `~/.hermes/auth.json` + `.env` | OAuth: 6h / API Key: なし |
| nvidia | API Key | `~/.hermes/.env` (`NVIDIA_API_KEY`) | なし |
| ollama-cloud | API Key | `~/.hermes/.env` (`OLLAMA_API_KEY`) | なし |
| lmstudio | 不要（ローカル） | — | — |

## 料金モデル

| プロバイダ | 無料枠 | 有料 |
|-----------|--------|------|
| opencode-go | なし | $10/月 定額 |
| nous | deepseek-v4-flash 等が無料 | 有料モデルはクレジット要 |
| openrouter | 一部モデル無料 | 従量課金 |
| google | AI Studio 無料枠（レート制限あり） | 従量課金 |
| gemini-cli | OAuth 無料（Code Assist 経由） | — |
| xai | なし | SuperGrok 課金要 |
| nvidia | 無料枠あり（NIM トライアル） | 従量課金 |
| ollama-cloud | 無料枠あり | 従量課金 |
| lmstudio | 完全無料（ローカル実行） | — |

## モデルが使えない場合の典型エラー

| エラー | 原因 | 対処 |
|--------|------|------|
| `HTTP 404: credits too low` | Nous Portal のクレジット不足 | 無料モデルを使う or クレジット追加 |
| `Incorrect API key provided` | xAI 直APIキー未設定 | `XAI_API_KEY` を `.env` に設定 |
| `Model not found` | モデル名の形式違い | provider に合った形式に修正 |
| `Token expired` | Nous OAuth トークン切れ | `hermes auth` で再認証 |
| `No models loaded` | LM Studio でモデル未ロード | LM Studio でモデルをロード |
| `Connection refused` | LM Studio 未起動 | LM Studio を起動（port 1234） |

## 同時実行数の制限

- `multi-chat.py` は `ThreadPoolExecutor` で最大5モデルまで並列実行可能
- ただし API レート制限に注意。4〜5モデル同時の場合、プロバイダごとにレート制限がかかる可能性あり
- Hermes Agent 経由の `delegate_task` は最大3プロセス推奨（本スキルの対象外）

## タイムアウト

- `multi-chat.py` のデフォルトタイムアウト: 300秒（`--timeout` で変更可能）
- 広範な「全チェック」指示を出すとタイムアウトしやすい → **TOP-5 指摘**などスコープを絞る
- プロンプトが長すぎる場合もタイムアウト要因になる → 章ごとに分割して送信
- LM Studio はローカル実行のためレスポンスが遅い可能性あり → `--timeout` を延長推奨

## ファイル読み込み

- 各 `hermes chat -q` 呼び出しは独立セッション → 小説本文のファイルパスをプロンプト内で明示
- 長大なファイルをプロンプトに埋め込むとトークン制限に達する → 章ごとに分割して送信

## 例外処理

`multi-chat.py` 実行中に発生しうるエラーと対応:

| 現象 | 原因 | 対処 |
|------|------|------|
| タイムアウト（300s） | プロンプト長すぎ/モデル応答遅延 | `--timeout` で延長 or スコープ縮小 |
| `HTTP 404: Model not found` | モデル名の形式違い | `list-models.py` で正しい ID を確認 |
| `credits too low` | Nous Portal 有料モデルのクレジット不足 | 無料モデルを使う or クレジット追加 |
| `Incorrect API key` | API キー未設定 or 無効 | `.env` または `hermes auth` で設定 |
| `Token expired` | Nous OAuth トークン切れ | `hermes auth` で再認証 |
| 空応答 | モデルがコンテンツポリシーで拒否 | プロンプトを調整 or 別モデルで再実行 |
| `Connection refused` | LM Studio 未起動 | LM Studio を起動 |

**禁止事項**: 自動リトライ、ユーザに黙ったままの代替モデル選択、エラーを無視した集計。

## hermes chat -q の安全な使い方

- `--max-turns 2` でツール呼び出しループを防止
- `--yolo` で危険コマンド承認プロンプトをスキップ
- `-Q`（quiet）でスピナー・バナーを抑制
- `multi-chat.py` はプロンプトを `subprocess.run` のリスト引数で渡すため、改行や引用符のエスケープは不要