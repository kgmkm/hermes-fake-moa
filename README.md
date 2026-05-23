# hermes-fake-moa

Multi-LLM parallel orchestrator for Hermes Agent — 複数 LLM に同一プロンプトを並列送信し、回答を比較するためのスキル。

「本物の MoA（Mixture of Agents）」ではなく、**手動オーケストレーションによる並列モデル実行**（Fake MoA）です。

## 特徴

- **12プロバイダ対応**: OpenCode Go / Nous Portal / OpenRouter / Google AI Studio / Gemini OAuth / xAI Grok / NVIDIA NIM / Ollama Cloud / LM Studio / GitHub Copilot / HuggingFace / OpenAI Codex
- **600+モデル**: 全プロバイダの利用可能モデルを一覧化（テキスト生成モデルのみ）
- **free/paid 表示**: 無料モデル159種を明示
- **パネル選択**: 2〜5モデルを選んで設定保存
- **並列送信**: 同一プロンプトを全モデルに同時送信、結果を集約
- **汎用設計**: 小説推敲・コードレビュー・翻訳比較・企画ブレスト等、分野不問
- **Windows 対応**: `python3` / `python` 自動解決（スクリプト内部は `sys.executable`）

## なぜ手動オーケストレーションか

Hermes Agent の組み込み `mixture_of_agents` ツールは以下の制約があるため、汎用並列実行には手動オーケストレーションを推奨する：

| 項目 | 組み込み moa | Fake MoA（本スキル） |
|--------|-------------|---------------------|
| プロバイダ | **OpenRouter 固定**（`OPENROUTER_API_KEY`必須） | 任意（ユーザの契約プロバイダ全6種） |
| デフォルトモデル | 汎用推論向け（ハードコード） | ユーザが自由に選択・変更可能 |
| モデル指定 | コード内ハードコード | CLI 引数 / panels.json で柔軟に |
| スキル配布適合性 | ❌（プロバイダ依存） | ✅（ユーザ環境に適応） |
| 実行方式 | delegat_task（親モデル継承） | hermes chat -q（独立セッション） |
| 同一モデル制約 | なし（同一モデル宣言可能） | 同一モデル不可（MoAの意味を損なうため警告） |

**一番の違い**: 組み込み moa は集約モデル（aggregator）が最終回答を生成するが、本スキルは人間が各モデルの回答を比較・判断する。LLMの「意見が偏る」リスクを回避できる。

## 前提

- Hermes Agent が動作する環境
- 1つ以上の LLM プロバイダが設定済み
- Python 3.10+（Windows では `python` コマンドを使用）

> **Windows (PowerShell) 環境**: コマンド例の `python3` を `python` に読み替えてください。スクリプト内部のサブプロセス呼び出し（`select-panel.py` → `list-models.py`）は `sys.executable` を使用しており、環境差異は自動解決されます。

## 推奨プロバイダー（2026年5月時点）

モデル名は変遷が激しいため推奨しません。プロバイダ選定基準のみを示します。
実運用の際は `python3 scripts/list-models.py` で最新の利用可能モデルを確認してください。

### 選定基準

| 基準 | 説明 |
|------|------|
| マルチモデル | 1 プロバイダで複数モデルを利用可能（MoA 4 エージェントの異モデル割当に有利） |
| フラッグシップ対応 | GPT-5 / Claude-4 / Gemini-3 等の最上位モデルが利用可能 |
| Hermes 親和性 | 公式対応または動作実績があり、認証が安定している |
| 無料枠 | 無料モデルまたは期間限定無料枠がある（試行コスト低減） |
| 料金 | 有料でも低価格帯（$10〜20/月程度の定額または従量課金で手頃） |

### おすすめ（コア）

| プロバイダ | 特徴 |
|-----------|------|
| **OpenCode Go** | 月 $10 定額。モデル名指定がシンプル（プロバイダプレフィックス不要）。MoA の最初の足として最も手軽 |
| **OpenRouter** | 350+ モデル。従量課金。全主要モデルにアクセス可能。MoA のモデル選択肢が最大 |
| **Nous Portal** | Nous Research 公式。Hermes Agent との親和性が最も高い。deepseek-v4-flash 等が無料 |
| **Google AI Studio** | Gemini 系モデルが無料枠で利用可能。長文コンテキストに強い |
| **Gemini OAuth** | Cloud Code Assist 経由。API Key 不要、OAuth 認証のみ |

### 追加候補

| プロバイダ | 特徴 |
|-----------|------|
| **NVIDIA NIM** | Nemotron 系モデル。無料枠あり。123モデル |
| **xAI / Grok** | Grok シリーズ。SuperGrok 課金が必要だが強力 |
| **NovitaAI** | GPU Cloud + Model API。エージェントサンドボックスあり。無料枠あり |
| **Ollama Cloud** | クラウドホストのオープンモデル。ollama.com/v1。無料枠あり |
| **LM Studio** | ローカル LLM。完全無料。独自モデル・LoRA の実験に最適 |

### モデル名の形式（プロバイダごとに異なる）

| プロバイダ | 形式 | 例 |
|-----------|------|-----|
| opencode-go | `モデル名`（そのまま） | `mimo-v2.5-pro` |
| nous | `プロバイダ/モデル名` | `deepseek/deepseek-v4-flash` |
| openrouter | `プロバイダ/モデル名` | `anthropic/claude-sonnet-4.6` |
| google | `モデル名`（そのまま） | `gemini-2.5-flash` |
| gemini-cli | `モデル名`（そのまま） | `gemini-2.5-flash` |
| xai | `モデル名`（そのまま） | `grok-4.3` |
| nvidia | `プロバイダ/モデル名` | `deepseek-ai/deepseek-v4-flash` |
| ollama-cloud | `model:tag` | `deepseek-v4-flash`, `gemma4:31b` |
| lmstudio | `モデル名`（そのまま） | `qwen3.6-27b-uncensored-hauhaucs-balanced` |
| copilot | `モデル名`（そのまま） | `gpt-4o`, `claude-sonnet-4.6` |
| huggingface | `owner/model` | `deepseek-ai/DeepSeek-V4-Flash` |
| openai-codex | `モデル名`（そのまま） | `gpt-5`, `o4-mini`（プラン依存） |

**404エラーが出た場合、モデル名の形式が誤っている可能性が高い。** `list-models.py` で正しい ID を確認すること。

## クイックスタート

```bash
# 1. モデル一覧取得
python3 scripts/list-models.py > models.md

# 2. パネル選択（2〜5モデル）
# 対話モード:
python3 scripts/select-panel.py --name my-panel

# 非対話モード（エージェント・スクリプト用）:
python3 scripts/select-panel.py --name my-panel \
  --models "mimo-v2.5-pro:opencode-go,deepseek/deepseek-v4-flash:nous,gemini-2.5-flash:google"

# 3. 並列実行
python3 scripts/multi-chat.py --panel my-panel --prompt "質問文"

# panels.json / results/ の場所を指定する場合:
python3 scripts/multi-chat.py --panel my-panel --file prompt.txt --cwd /path/to/project
```

## インストール

```bash
git clone https://github.com/kgmkm/hermes-fake-moa.git ~/.hermes/skills/hermes-fake-moa
```

## ファイル構成

| パス | 用途 |
|------|------|
| `SKILL.md` | スキル定義・使い方 |
| `scripts/list-models.py` | モデル一覧出力（MD / JSON） |
| `scripts/select-panel.py` | パネル選択（対話 / 非対話） |
| `scripts/multi-chat.py` | 並列プロンプト送信 + 結果集約 |
| `templates/panels.default.json` | パネル設定テンプレート |
| `references/provider-quirks.md` | プロバイダ別注意点・OS環境差異 |

## 対応プロバイダ

| プロバイダ | `--provider` 名 | 認証 | モデル数 |
|-----------|----------------|------|---------|
| OpenCode Go | `opencode-go` | 不要 | 15 |
| Nous Portal | `nous` | OAuth | 250+ |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | 350 |
| Google AI Studio | `google` | `GOOGLE_API_KEY` | 35 |
| Gemini OAuth | `gemini-cli` | OAuth (Code Assist) | 35 |
| xAI Grok | `xai` | `XAI_API_KEY` | 8 |
| NVIDIA NIM | `nvidia` | `NVIDIA_API_KEY` | 123 |
| Ollama Cloud | `ollama-cloud` | `OLLAMA_API_KEY` | 39 |
| LM Studio | `lmstudio` | 不要（ローカル） | ユーザ依存 |
| GitHub Copilot | `copilot` | GH_TOKEN (gh CLI) | 22 |
| HuggingFace | `huggingface` | `HF_TOKEN` | 128 |
| OpenAI Codex | `openai-codex` | OAuth | ChatGPT Plus/Pro要 |

## ライセンス

0BSD