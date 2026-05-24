---
name: hermes-fake-moa
description: Multi-LLM parallel orchestrator — list available models across all configured providers, select 2–5 models into a panel, and send the same prompt to all of them simultaneously. NOT true MoA (no aggregator model). Results are collected side-by-side for human comparison.
version: 1.1.2
tags: [llm, multi-model, orchestration, parallel, moa, comparison, panel]
---

# Hermes Fake MoA — マルチLLM並列オーケストレーター

複数の LLM に同じ質問を同時に投げ、回答を比較するためのスキル。
「本物の MoA（Mixture of Agents）」ではなく、**手動オーケストレーションによる並列モデル実行**です。

## ⚠️ 最重要警告：Hermes Agent ビルトイン `moa` ツールを絶対に使わないこと

Hermes Agent には **ビルトインの `mixture_of_agents` ツール**（以下「ビルトイン moa」）が存在する。
これは **4つの参照モデル + 1つの集約モデルを OpenRouter 経由で呼び出す** もので、
hermes-fake-moa とは **全く別物** である。

**ビルトイン moa を使ってはならない理由**:

1. **高額な API コスト**: OpenRouter 経由で最大5モデルを呼ぶため、1回の実行で $1〜$5 以上の課金が発生しうる（実害: $5.80 の損失）
2. **モデル選択不可**: ビルトイン moa は自動でモデルを選ぶため、ユーザの希望するモデル構成にならない
3. **hermes-fake-moa との競合**: ビルトイン moa が有効だと、エージェントが意図せずそちらを使ってしまう

**絶対ルール**:

- `mixture_of_agents()` 関数を **絶対に呼ばない**
- ツール一覧に `moa` が表示されている場合、`hermes config set toolsets` で **無効化する**
- 複数 LLM の並列実行には **必ず hermes-fake-moa の `multi-chat.py` を使用する**
- 「MoA」「複数モデル」「並列実行」といった指示に対して、**ビルトイン moa にフォールバックしない**

**無効化コマンド**（moa ツールセットが有効な場合）:
```bash
# 現在のツールセット設定を確認
hermes config get toolsets

# moa を除外して再設定（例: 他のツールセットはそのまま）
hermes config set toolsets "terminal,file,web,skills,search,patch,delegation"
```

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

### Step 2: どのプロバイダ/モデルを使うかユーザに相談

必ずユーザに、models.md を読むことと、そこからMoAとして使いたいプロバイダ/モデルを３～５つ選ぶよう伝える。
その上で、モデルの違いが分かりづらいユーザもいるため、おすすめプロバイダ/モデルも３つほど提案する。

提案の条件は以下。

**おすすめプロバイダ/モデル選定基準** :
- 定額で使えるプロバイダ（opencode go, Ollama Cloud, codex, claude codeなど）のフラグシップorミッドシップモデル
- クレジット型課金だが比較的安価で新しいモデル
- 無料で使えてコンテキストも長めなモデル

なお、エージェント側で勝手にモデルを選び、選定して送信してはならない。勝手にユーザのクレジットを使う事は責任問題につながる。

### Step 3: パネル（モデルセット）の選択

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

### Step 4: 並列送信

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

## ファイル構成

| パス | 用途 |
|------|------|
| `scripts/list-models.py` | モデル一覧出力（MD / JSON） |
| `scripts/select-panel.py` | 対話型パネル選択 |
| `scripts/multi-chat.py` | 並列プロンプト送信 + 結果集約 |
| `templates/panels.default.json` | パネル設定テンプレート |
| `references/provider-quirks.md` | プロバイダ固有の注意点・モデル名形式・認証方式 |

## 制限事項
  モデル一覧の取得・選択・並列実行には `hermes-fake-moa` スキルを使用する。
- Hermes Agent 内部からの実行に限る（`hermes chat -q` に依存）
- 基本は3モデル同時実行、最大5モデルまで（数モデルの審査拒否やエラーを許容するため多めに送信することを認める）
- ユーザに断りなくエージェント側で勝手にモデルを選び、送信してはならない
- **ビルトイン `mixture_of_agents` ツール（moa ツールセット）は絶対に使用禁止**。OpenRouter 経由で高額課金が発生するため（実害 $5.80）。複数 LLM 実行には必ず本スキルの `multi-chat.py` を使用すること
