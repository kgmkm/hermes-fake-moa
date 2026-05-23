---
name: hermes-fake-moa
description: Multi-LLM parallel orchestrator — list available models across all configured providers, select 2–5 models into a panel, and send the same prompt to all of them simultaneously. NOT true MoA (no aggregator model). Results are collected side-by-side for human comparison.
version: 1.0.0
tags: [llm, multi-model, orchestration, parallel, moa, comparison, panel]
---

# Hermes Fake MoA — マルチLLM並列オーケストレーター

複数の LLM に同じ質問を同時に投げ、回答を比較するためのスキル。
「本物の MoA（Mixture of Agents）」ではなく、**手動オーケストレーションによる並列モデル実行**です。

## 前提

- Hermes Agent が動作する環境
- 1つ以上の LLM プロバイダが設定済み
- Python 3.10+（Windows では `python` コマンドを使用）

> **Windows (PowerShell) 環境**: コマンド例の `python3` を `python` に読み替えてください。
> スクリプト内部のサブプロセス呼び出し（`select-panel.py` → `list-models.py`）は `sys.executable` を使用しており、環境差異は自動解決されます。

## 対応プロバイダ（2026年5月時点）

| プロバイダ | `--provider` 名 | 認証 | 備考 |
|-----------|----------------|------|------|
| OpenCode Go | `opencode-go` | 不要 | 15モデル、$10/月定額 |
| Nous Portal | `nous` | OAuth | 250+モデル、free枠あり |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | 350モデル、従量課金 |
| Google AI Studio | `google` | `GOOGLE_API_KEY` | 35モデル、無料枠あり |
| Gemini OAuth | `gemini-cli` | OAuth (Code Assist) | 35モデル、OAuth認証でAPI Key不要 |
| xAI / Grok | `xai` | `XAI_API_KEY` | 8モデル、課金要 |
| NVIDIA NIM | `nvidia` | `NVIDIA_API_KEY` | 123モデル、無料枠あり |
| Ollama Cloud | `ollama-cloud` | `OLLAMA_API_KEY` | 39モデル、ollama.com/v1 |
| LM Studio | `lmstudio` | 不要（ローカル） | ローカルモデル、port 1234 |
| GitHub Copilot | `copilot` | GH_TOKEN (gh CLI) | 22モデル、reasoning effort対応 |
| HuggingFace | `huggingface` | `HF_TOKEN` | 128モデル、Inference Providers |
| OpenAI Codex | `openai-codex` | OAuth | ChatGPT Plus/Pro要、reasoning effort対応 |

## ワークフロー

### Step 1: モデル一覧の取得

```bash
python3 scripts/list-models.py > models.md
```

`models.md` に全プロバイダの利用可能モデル一覧が Markdown 表で出力される。

JSON 出力も可能:
```bash
python3 scripts/list-models.py --json > models.json
```

### Step 2: パネル（モデルセット）の選択

**対話モード**（人間がターミナルで操作）:
```bash
python3 scripts/select-panel.py --name novel-revision
```

**非対話モード**（エージェント・スクリプトから使用）:
```bash
python3 scripts/select-panel.py --name novel-revision \
  --models "mimo-v2.5-pro:opencode-go,deepseek/deepseek-v4-flash:nous,gemini-2.5-flash:google"
```

`--models` 形式: `model_id:provider` をカンマ区切り。provider 省略時は自動選択。

または手動で `panels.json` を編集:
```json
{
  "version": 1,
  "panels": {
    "novel-revision": [
      {"id": "mimo-v2.5-pro", "provider": "opencode-go"},
      {"id": "deepseek/deepseek-v4-flash", "provider": "nous"},
      {"id": "gemini-2.5-flash", "provider": "google"}
    ]
  }
}
```

### Step 3: 並列送信

```bash
python3 scripts/multi-chat.py --panel novel-revision --prompt "あなたの質問"
```

またはファイルからプロンプトを読み込み:
```bash
python3 scripts/multi-chat.py --panel novel-revision --file prompt.txt
```

**panels.json / results/ の配置場所**:
- デフォルト: カレントディレクトリ
- `--cwd /path/to/project` で指定可能（Hermes Agent 内から実行する場合に推奨）

結果は `results/` ディレクトリにタイムスタンプ付きで保存される。

## 結果の読み方

各モデルの回答は個別ファイルに保存され、サマリーが標準出力に表示される。
複数モデルが共通して指摘した項目は特に重要。

## 制限事項

- Hermes Agent 内部からの実行に限る（`hermes chat -q` に依存）
- 最大5モデルまで同時実行
- Nous Portal の有料モデルはクレジット要
- xAI 直API は `XAI_API_KEY` の設定が必要
- 回答は「モデルごとの独立した」結果であり、モデル間の合議は行われない

## ファイル構成

| パス | 用途 |
|------|------|
| `scripts/list-models.py` | モデル一覧出力（MD / JSON） |
| `scripts/select-panel.py` | 対話型パネル選択 |
| `scripts/multi-chat.py` | 並列プロンプト送信 + 結果集約 |
| `templates/panels.default.json` | パネル設定テンプレート |
| `references/provider-quirks.md` | プロバイダ固有の注意点・モデル名形式・認証方式 |

## 参照元

このスキルは `novel2hermes` の MoA 推敲ワークフローから抽出・汎用化された。
