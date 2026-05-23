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
| xai | `モデル名`（prefix不要） | `grok-4.3` |
| nvidia | `owner/model` | `deepseek-ai/deepseek-v4-flash` |

**自動正規化**: opencode-go では `deepseek/deepseek-v4-flash` と指定しても自動的に `deepseek-v4-flash` に変換される。他のプロバイダも同様の可能性あり。

## 認証方式

| プロバイダ | 方式 | 保存場所 | 有効期限 |
|-----------|------|---------|---------|
| opencode-go | 不要 | — | — |
| nous | OAuth (agent_key) | `~/.hermes/auth.json` | 15分（自動更新あり） |
| openrouter | API Key | `~/.hermes/.env` (`OPENROUTER_API_KEY`) | なし |
| google | API Key | `~/.hermes/.env` (`GOOGLE_API_KEY`) | なし |
| xai | OAuth (access_token) + API Key | `~/.hermes/auth.json` + `.env` | OAuth: 6h / API Key: なし |
| nvidia | API Key | `~/.hermes/.env` (`NVIDIA_API_KEY`) | なし |

## 料金モデル

| プロバイダ | 無料枠 | 有料 |
|-----------|--------|------|
| opencode-go | なし | $10/月 定額 |
| nous | deepseek-v4-flash 等が無料 | 有料モデルはクレジット要 |
| openrouter | 一部モデル無料 | 従量課金 |
| google | AI Studio 無料枠（レート制限あり） | 従量課金（APIキー設定で自動） |
| xai | なし | SuperGrok 課金要 |
| nvidia | 無料枠あり（NIM トライアル） | 従量課金 |

## モデルが使えない場合の典型エラー

| エラー | 原因 | 対処 |
|--------|------|------|
| `HTTP 404: credits too low` | Nous Portal のクレジット不足 | 無料モデルを使う or クレジット追加 |
| `Incorrect API key provided` | xAI 直APIキー未設定 | `XAI_API_KEY` を `.env` に設定 |
| `Model not found` | モデル名の形式違い | provider に合った形式に修正 |
| `Token expired` | Nous OAuth トークン切れ | `hermes auth` で再認証 |

## hermes chat -q の安全な使い方

- プロンプトに改行を含める場合は `\n` でエスケープする（一行化）
- `--max-turns 2` でツール呼び出しループを防止
- `--yolo` で危険コマンド承認プロンプトをスキップ
- `-Q`（quiet）でスピナー・バナーを抑制

## 同時実行数の制限

- Hermes Agent は最大3プロセスまで同時推奨
- 4〜5モデルの場合は 3→2 の2バッチに分けることを推奨
- `multi-chat.py` は ThreadPoolExecutor で並列実行するため、プロセス制限はかからないが、APIレート制限に注意
