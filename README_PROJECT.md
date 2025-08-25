# BET_HUNTER / betvalue-finder — 統合指示書（WSL2統一版）

## 1) 前提・環境

- **OS**: Windows 11 + WSL2 (Ubuntu)
- **開発環境**: WSL2内で全作業を実施
- **シェル**: bash（WSL2内）
- **Python**: 3.12
- **仮想環境**: venv
- **プロジェクトパス**: `~/betvalue-finder` (WSL2内)
- **APIキー（環境変数）**: 
  - `API_SPORTS_KEY`（API-SPORTS Baseball v1 用）
  - `.bashrc`に設定済み
- **タイムゾーン**: Asia/Tokyo（JST）
- **共通ルール**: 「📜【永久保存版】AIアシスタントへのプロジェクト共通指示書」を厳守

### 環境設定済み項目
- GitHubトークン: `GITHUB_TOKEN`（.bashrcに設定済み）
- エイリアス: `gitpush`でコミット＆プッシュ可能

---

## 2) システム目的（要約）

Pinnacle オッズを基準に、日本式ハンデ（配当固定 1.9）の期待値を算出し、個別ラインの有利／不利を自動判定

**対象競技**: MLB / サッカー / NBAに汎用化

**評価フロー**:
- マージン除去（各ラインの公正化）
- 線形補間（0.05刻み・変換表に準拠）
- 公正オッズ→期待値（1.9固定）
- verdict 付与：clear_plus / plus / fair / minus（閾値は合意済み値）

---

## 3) ディレクトリ構造

```
betvalue-finder/
├─ README_PROJECT.md              # 本ドキュメント
├─ app/
│  ├─ main.py                    # FastAPI: /map, /evaluate, /ingest
│  └─ converter.py               # 日本式⇄ピナクル変換
├─ converter/                    # 変換・EV計算ロジック
│  └─ baseball_rules.py         # MLB用EVルール
├─ game_manager/                 # 【新】試合管理モジュール
│  ├─ base.py                   # 基底クラス
│  └─ mlb.py                    # MLB実装
├─ data/
│  ├─ mlb/
│  │  ├─ games_YYYYMMDD.json   # 試合データ
│  │  └─ odds_YYYYMMDD.json    # オッズデータ
│  └─ soccer/
│      └─ odds_YYYYMMDD.json    # サッカーオッズ
├─ input/                        # 貼り付けテキスト置き場
├─ scripts/
│  ├─ update_games.py           # 【新】毎日の試合更新
│  ├─ process_paste_new.py      # 【新】新貼り付け処理
│  ├─ mlb_from_paste_compare.py # 従来の貼り付け処理
│  ├─ dump_spreads_csv.py       # CSVダンプ
│  └─ output/                   # 出力ファイル
├─ docs/                         # ドキュメント類
│  └─ HANDOVER_YYYYMMDD.md     # 引き継ぎ書
├─ bet_snapshots.sqlite3
├─ 「## 1. 変換表（ピナクル → 日本式）.txt」
└─ 「📜【永久保存版】AIアシスタントへのプロジェクト共通指示書.txt」
```

---

## 4) セットアップ手順（WSL2）

### 初回セットアップ

```bash
# 1. WSL2を起動（Windowsターミナルなどから）
wsl

# 2. プロジェクトをクローン
cd ~
git clone https://github.com/KIYUKIYUKIYU/betvalue-finder.git
cd betvalue-finder

# 3. Python仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 4. 依存パッケージをインストール
pip install -r requirements.txt

# 5. 環境変数を設定（.bashrcに追加）
echo 'export API_SPORTS_KEY="あなたのAPIキー"' >> ~/.bashrc
echo 'export GITHUB_TOKEN="あなたのGitHubトークン"' >> ~/.bashrc
source ~/.bashrc

# 6. Gitエイリアスを設定（オプション）
echo 'alias gitpush="git add . && git commit -m \"Update\" && git push"' >> ~/.bashrc
source ~/.bashrc
```

### 日常の作業開始

```bash
# WSL2を起動
wsl

# プロジェクトに移動
cd ~/betvalue-finder

# 仮想環境を有効化
source venv/bin/activate

# 最新版を取得
git pull
```

---

## 5) MLBパイプライン（GameManager版）

### 5.1 試合データ更新（毎日実行）

```bash
# 今日の試合を取得
python scripts/update_games.py --sport mlb

# 特定日の試合を取得
python scripts/update_games.py --sport mlb --date 2025-08-25
```

### 5.2 貼り付け処理＆EV計算

```bash
# 1. 貼り付けファイルを作成
nano input/paste_20250825.txt

# 内容例：
# ヤンキース<0.1>
# レッドソックス
#
# カージナルス
# ブルージェイズ<1.2>

# 2. 処理実行（レーキバック1.5%）
python scripts/process_paste_new.py \
  input/paste_20250825.txt \
  --date 2025-08-25 \
  --rakeback 0.015
```

### 5.3 全スプレッドダンプ（分析用）

```bash
python scripts/dump_spreads_csv.py --sport mlb
# 出力: scripts/output/mlb_spreads_dump_YYYYMMDD.csv
```

---

## 6) レーキバック仕様

- **方式**: Turnoverのみ（賭け金に対する返還）
- **範囲**: 0〜3%
- **刻み**: 0.5%単位（0.005刻み）
- **指定方法**: `--rakeback 0.015`（1.5%の場合）
- **計算式**: 
  - `EV% = (p * O - 1 + r) * 100`
  - `実効配当 O_eff = O + r/p`

---

## 7) 既知の問題と対応

### チーム名マッチング問題
- **問題**: "St.Louis Cardinals" vs "St. Louis Cardinals"
- **対応**: game_manager/mlb.pyで正規化処理実装予定

---

## 8) コマンド集（コピペ用）

```bash
# 環境準備
cd ~/betvalue-finder && source venv/bin/activate

# 試合更新（毎日）
python scripts/update_games.py --sport mlb

# 貼り付け処理
python scripts/process_paste_new.py input/paste_$(date +%Y%m%d).txt

# API起動（開発用）
python -m uvicorn app.main:app --reload --port 8001

# Git更新
git pull && git status

# Git保存（エイリアス使用）
gitpush
```

---

## 9) 今後のフェーズ

- **フェーズ1**: ✅ GameManager実装完了
- **フェーズ2**: チーム名正規化＆EV計算完全実装（進行中）
- **フェーズ3**: FastAPI完全統合
- **フェーズ4**: Webサービス化（GCP予定）
- **フェーズ5**: 販売形態検討

---

## 10) API使用状況

- **API-Sports残量**: 約75,000/100,000（2025-08-25時点）
- **1日の使用目安**: 試合取得50回 + オッズ取得100回程度

---

## 11) 注意事項

- 常に **README_PROJECT.md が唯一の正**
- 新仕様は必ず **合意 → README追記 → コード実装** の順
- WSL2内で全作業を完結（Windowsファイルシステムとの直接操作は避ける）
- GitHub更新は`gitpush`エイリアスで簡単実行可能

### 効率的なコード確認フロー
1. AIが「○○のコードを確認したい」と言う
2. AIが具体的なRaw URLを提示：
   例：`https://raw.githubusercontent.com/KIYUKIYUKIYU/betvalue-finder/main/[ファイルパス]`
3. ユーザーがそのURLをコピペして返信
4. AIがweb_fetchで自動読み込み

**メリット**：
- ユーザーはURLをコピペするだけ
- AIは最新のコードを確実に取得
- ローカルの変更も反映される（push済みなら）
