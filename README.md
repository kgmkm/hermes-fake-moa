# hermes-fake-moa

Multi-LLM parallel orchestrator for Hermes Agent — 複数 LLM に同一プロンプトを並列送信し、回答を比較するためのスキル。

「本物の MoA（Mixture of Agents）」ではなく、**手動オーケストレーションによる並列モデル実行**（Fake MoA）です。

## 特徴

- **6プロバイダ対応**: OpenCode Go / Nous Portal / OpenRouter / Google AI Studio / xAI Grok / NVIDIA NIM
- **456モデル**: 全プロバイダの利用可能モデルを一覧化（テキスト生成モデルのみ）
- **free/paid 表示**: 無料モデル159種を明示
- **パネル選択**: 2〜5モデルを選んで設定保存
- **並列送信**: 同一プロンプトを全モデルに同時送信、結果を集約
- **汎用設計**: 小説推敲・コードレビュー・翻訳比較・企画ブレスト等、分野不問

## 前提

- Hermes Agent
- Python 3.10+
- 1つ以上の LLM プロバイダ設定済み

## クイックスタート

```bash
# 1. モデル一覧取得
python3 scripts/list-models.py > models.md

# 2. パネル選択（2〜5モデル）
python3 scripts/select-panel.py --name my-panel

# 3. 並列実行
python3 scripts/multi-chat.py --panel my-panel --prompt "質問文"
```

## インストール

```bash
# Hermes Agent のスキルディレクトリにコピー
cp -r hermes-fake-moa ~/.hermes/skills/

# または Hermes skills install（サポート時）
hermes skills install hermes-fake-moa
```

## ファイル構成

| パス | 用途 |
|------|------|
| `SKILL.md` | スキル定義・使い方 |
| `scripts/list-models.py` | モデル一覧出力（MD / JSON） |
| `scripts/select-panel.py` | 対話型パネル選択 |
| `scripts/multi-chat.py` | 並列プロンプト送信 + 結果集約 |
| `templates/panels.default.json` | パネル設定テンプレート |
| `references/provider-quirks.md` | プロバイダ別注意点 |

## 対応プロバイダ

| プロバイダ | `--provider` 名 | 認証 | モデル数 |
|-----------|----------------|------|---------|
| OpenCode Go | `opencode-go` | 不要 | 15 |
| Nous Portal | `nous` | OAuth | 250+ |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` | 350 |
| Google AI Studio | `google` | `GOOGLE_API_KEY` | 35 |
| xAI Grok | `xai` | `XAI_API_KEY` | 8 |
| NVIDIA NIM | `nvidia` | `NVIDIA_API_KEY` | 123 |

## ライセンス

0BSD
