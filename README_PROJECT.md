📋 現状整理とREADME更新
これまでの議論のまとめ
1. 問題の発見と解決

問題: Pinnacleのデータ形式が想定と異なる

想定: "handicap": -1.0
実際: "value": "Home -1", "odd": "2.81"


解決: parse_handicap_values関数を両形式対応に修正

2. 補間システムの設計

0の計算: ±1.0のペアから中間値として算出（ホーム視点で統一）
0.05刻み: 0と実データ間を線形補間
データ不足時: 優先順位（±0.5 → ±1.0 → 最小ペア）

3. 変換表の拡張性

パターン確認: 全81エントリが完全に一貫性あり
無限拡張可能: バスケの大きな値（10.5、15.5）にも対応

4. 設計方針

内部処理: すべてピナクル値（数値）で統一
キャッシュ不要: 毎回新しいオッズで計算
精度管理: 小数点4桁で統一


📝 README_PROJECT.md 更新版
markdown# 📑 完全版 README_PROJECT.md (2025-08-23更新)
# BET_HUNTER / betvalue-finder

## 🔄 更新履歴
- 2025-08-23: Pinnacleデータ形式対応、補間システム設計追加

## 1) 前提・環境
- OS: Windows 11
- 実行環境: `cmd.exe` 固定（PowerShell不可）
- 仮想環境: `venv`
- 言語: Python 3.13
- プロジェクトパス: `C:\Users\yfuku\Desktop\betvalue-finder`
- APIキー: `API_SPORTS_KEY`（環境変数）

---

## 2) ディレクトリ構造
betvalue-finder/
├─ README_PROJECT.md          ← このドキュメント
├─ README_DEV.md              ← 開発ログ（新規）
│
├─ app/
│  ├─ main.py                 # FastAPI エントリポイント
│  ├─ converter.py            # 日本式⇔ピナクル変換
│  └─ static/                 # UI用静的ファイル
│
├─ converter/
│  ├─ baseball_rules.py       # EV計算、補間ロジック
│  ├─ paste_parser.py         # 貼り付けテキストパーサー
│  ├─ team_names.py           # チーム名正規化（新規）
│  └─ handicap_interpolator.py # 補間モジュール（計画中）
│
├─ debug/                      # デバッグ用スクリプト（新規）
│  ├─ test_odds_debug.py
│  ├─ test_pinnacle_details.py
│  └─ verify_conversion_pattern.py
│
├─ data/                       # 取得した生データ
├─ scripts/                    # CLIスクリプト類
└─ 「## 1. 変換表（ピナクル → 日本式）.txt」

---

## 3) 技術的発見事項（2025-08-23）

### 3.1 Pinnacleデータ形式
```json
// 実際のPinnacle形式
{
  "value": "Home -1",  // ホーム視点のライン
  "odd": "2.81"        // オッズ
}
3.2 補間システム設計
ライン0の計算方法
python# ±1.0のペアから0を計算（ホーム視点統一）
if -1.0 and +1.0 exist:
    prob_home_at_minus1 = fair_prob(odds[-1.0])
    prob_home_at_plus1 = fair_prob(odds[+1.0])
    prob_home_at_0 = (prob_home_at_minus1 + prob_home_at_plus1) / 2
0.05刻みの補間

利用可能ライン: [1.0, 1.5, 2.0, 2.5, 3.0]
ライン0を計算（上記方法）
0.05は0と1.0の間を線形補間

データ不足時の優先順位

±0.5のペア（最も信頼性高い）
±1.0のペア
最小の対称ペア
エラーまたは最小ライン使用

3.3 変換表の拡張性
パターン（確認済み）:
X.00 → X
X.05 → X.1
X.10 → X.2
...
X.50 → X半
X.55 → X半1
...
X.95 → X半9

このパターンで無限拡張可能（バスケの10.5 → "10半"）

4) 設計方針
内部処理

数値統一: 内部計算はすべてピナクル値（float）
ホーム視点: すべてのラインはホームチーム視点で統一
精度: 小数点4桁（PRECISION = 4）

キャッシュ戦略

不要: 毎回新しいオッズで計算するため

エラー処理

欠損ライン: 線形補間で補完
精度問題: round(value, 4)で統一


5) parse_handicap_values関数の修正内容
修正前（動作しない）
python# "handicap"フィールドを探す（存在しない）
if "handicap" in v and v["handicap"] is not None:
修正後（両形式対応）
python# 方式1: 他のブックメーカー形式
if "handicap" in v:
    # 処理...

# 方式2: Pinnacle形式
elif "value" in v and "odd" in v:
    # "Home -1" をパース
    match = re.search(r'(Home|Away)\s*([+-]?\d+(?:\.\d+)?)', v["value"])

6) 次の実装計画
HandicapInterpolatorモジュール
pythonconverter/handicap_interpolator.py
- ライン0の計算
- 0.05刻み補間
- スポーツ非依存設計
- エラーハンドリング
実装優先順位

parse_handicap_values修正 → 本番適用
HandicapInterpolatorモジュール作成
全体統合テスト
サッカー、バスケへの拡張


7) コマンド集（Windows cmd.exe）
サーバー起動
doscd C:\Users\yfuku\Desktop\betvalue-finder
venv\Scripts\activate
set API_SPORTS_KEY=あなたのAPIキー
python -m uvicorn app.main:app --port 8002 --reload
デバッグ実行
doscd C:\Users\yfuku\Desktop\betvalue-finder
venv\Scripts\activate
python debug\test_pinnacle_details.py

8) 確認済み事項

✅ Pinnacle ID = 4（正しい）
✅ チーム名正規化システム動作
✅ タイムゾーン問題解決
✅ 変換表パターンの一貫性
✅ 補間ロジックの動作確認


9) 注意事項

常に README_PROJECT.md が唯一の正
新仕様は必ず 合意 → README追記 → コード実装 の順
実行コマンドは必ず Windows cmd.exe 向けに記載
推測禁止、事実のみ記載


### ファイル保存手順

```dos
:: 1. バックアップ作成
cd C:\Users\yfuku\Desktop\betvalue-finder
copy README_PROJECT.md README_PROJECT_backup_20250823.md

:: 2. 新しいREADMEを保存
notepad README_PROJECT.md
:: 上記の内容を貼り付けて保存（UTF-8）
これでプロジェクトの現状が正確に文書化されました。次のステップに進む準備ができています。