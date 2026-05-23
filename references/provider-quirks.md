# プロバイダ固有の注意点

## Python / OS 環境

| 環境 | Python コマンド | 備考 |
|------|----------------|------|
| WSL / Linux | `python3` | スクリプトの shebang も `#!/usr/bin/env python3` |
| macOS | `python3` | Homebrew Python を想定 |
| Windows (PowerShell) | `python` | `python3` は存在しないことが多い。`python` を使用 |
| Windows (Git Bash) | `python` | 同上 |

スクリプト内部のサブプロセス呼び出しは `sys.executable` を使用。環境差異は自動解決。
`hermes` コマンドは PATH に必要。Windows では npm global install の `.cmd` ラッパー。

## モデル名形式

| プロバイダ | 形式 | 例 |
|-----------|------|-----|
| opencode-go | `モデル名` | `mimo-v2.5-pro` |
| nous | `owner/model` | `deepseek/deepseek-v4-flash` |
| openrouter | `owner/model` | `anthropic/claude-sonnet-4.6` |
| google | `モデル名` | `gemini-2.5-flash` |
| gemini-cli | `モデル名` | `gemini-2.5-flash` |
| xai | `モデル名` | `grok-4.3` |
| nvidia | `owner/model` | `deepseek-ai/deepseek-v4-flash` |
| ollama-cloud | `model:tag` | `deepseek-v4-flash`, `gemma4:31b` |
| lmstudio | `モデル名` | `qwen3.6-27b-uncensored-hauhaucs-balanced` |
| copilot | `モデル名` | `gpt-4o`, `claude-sonnet-4.6`, `gpt-5.4` |
| huggingface | `owner/model` | `deepseek-ai/DeepSeek-V4-Flash` |
| openai-codex | `モデル名` | `gpt-5`, `o4-mini`（ChatGPT プラン依存） |

**注意**:
- ollama-cloud はコロン付きタグ（`:31b`, `:120b` 等）を含むモデル名が標準
- copilot は `claude-sonnet-4.6` 等、他社モデルも利用可能
- openai-codex は ChatGPT Plus/Pro プランで利用可能なモデルが異なる

## 認証方式

| プロバイダ | 方式 | 保存場所 | 備考 |
|-----------|------|---------|------|
| opencode-go | 不要 | — | — |
| nous | OAuth | `auth.json` | 15分有効、自動更新 |
| openrouter | API Key | `.env` `OPENROUTER_API_KEY` | — |
| google | API Key | `.env` `GOOGLE_API_KEY` | — |
| gemini-cli | OAuth | `auth.json` | Cloud Code Assist |
| xai | OAuth + API Key | `auth.json` + `.env` | OAuth: 6h |
| nvidia | API Key | `.env` `NVIDIA_API_KEY` | — |
| ollama-cloud | API Key | `.env` `OLLAMA_API_KEY` | — |
| lmstudio | 不要 | — | ローカル |
| copilot | gh CLI Token | `~/.config/gh/hosts.yml` | `gh auth login` で設定 |
| huggingface | API Key | `.env` `HF_TOKEN` | — |
| openai-codex | OAuth | `auth.json` | ChatGPT Plus/Pro 要 |

## 料金モデル

| プロバイダ | 無料枠 | 有料 |
|-----------|--------|------|
| opencode-go | なし | $10/月 定額 |
| nous | deepseek-v4-flash 等 | 有料モデルはクレジット要 |
| openrouter | 一部無料 | 従量課金 |
| google | AI Studio 無料枠 | 従量課金 |
| gemini-cli | OAuth 無料 | — |
| xai | なし | SuperGrok 課金要 |
| nvidia | NIM トライアル | 従量課金 |
| ollama-cloud | 無料枠あり | 従量課金 |
| lmstudio | 完全無料 | — |
| copilot | — | GitHub Copilot 課金要 |
| huggingface | 無料枠あり | 従量課金 |
| openai-codex | — | ChatGPT Plus/Pro ($20〜/月) |

## Copilot / Codex の reasoning effort

GitHub Copilot と OpenAI Codex は `reasoning_effort` レベルをサポート:

| レベル | 説明 |
|--------|------|
| `low` | 高速・低コスト。簡単なタスク向け |
| `medium` | バランス。デフォルト |
| `high` | 深い推論。複雑なタスク向け |

`hermes chat -q` では `--reasoning-effort` フラグで指定可能（プロバイダ対応時）。
指定なしの場合はプロバイダのデフォルト（通常 `medium`）。

## モデルが使えない場合の典型エラー

| エラー | 原因 | 対処 |
|--------|------|------|
| `HTTP 404: credits too low` | Nous Portal クレジット不足 | 無料モデル or クレジット追加 |
| `Model not found` | モデル名の形式違い | `list-models.py` で確認 |
| `Token expired` | OAuth トークン切れ | `hermes auth` で再認証 |
| `No models loaded` | LM Studio でモデル未ロード | LM Studio でモデルをロード |
| `Connection refused` | LM Studio 未起動 | LM Studio を起動（port 1234） |
| `model_not_supported` | Codex で非対応モデル | ChatGPT プランを確認 |
| `model_not_found` | HF で存在しないモデル | `list-models.py` で正しい ID を確認 |

## 同時実行数

- `multi-chat.py` は最大5モデル並列（`ThreadPoolExecutor`）
- API レート制限に注意（特に HF 無料枠、NVIDIA NIM トライアル）

## タイムアウト

- デフォルト 300秒（`--timeout` で変更）
- LM Studio はローカル実行のため遅延あり → `--timeout` 延長推奨
- HuggingFace はモデルのコールドスタートで初回遅延あり

## hermes chat -q の安全な使い方

- `--max-turns 2` でツール呼び出しループ防止
- `--yolo` で承認プロンプトスキップ
- `-Q` でスピナー・バナー抑制
- `subprocess.run` リスト引数なので改行エスケープ不要