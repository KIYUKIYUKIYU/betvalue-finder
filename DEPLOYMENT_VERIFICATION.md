# デプロイ検証ガイド

## 🎯 目的

BetValue Finder が Railway で正しくデプロイされ、一貫して動作していることを確認する。

---

## ✅ チェックリスト

### 1. Railway デプロイ状態確認

#### 1.1 デプロイステータス
- [ ] Railway ダッシュボードにアクセス
- [ ] Deployments タブを開く
- [ ] 最新のデプロイが **"Success"** と表示されている
- [ ] コミットハッシュが最新 (現在: `1385a98`) と一致している

#### 1.2 環境変数確認
```bash
# Railway Variables タブで確認
✅ ODDS_API_KEY=設定済み
✅ DISCORD_WEBHOOK_URL=設定済み（オプション）
```

---

### 2. API エンドポイント確認

#### 2.1 ヘルスチェック

**方法1: ブラウザ**
```
https://betvalue-finder-production.up.railway.app/docs
```
→ FastAPI の Swagger UI が表示されれば ✅

**方法2: コマンドライン**
```bash
curl -s https://betvalue-finder-production.up.railway.app/docs | grep -q "swagger" && echo "✅ 成功" || echo "❌ 失敗"
```

#### 2.2 環境変数デバッグ（一時的）
```bash
curl -s https://betvalue-finder-production.up.railway.app/debug/env | jq
```

**期待される出力:**
```json
{
  "ODDS_API_KEY": "設定済み",
  "API_SPORTS_KEY": "未設定",
  "DISCORD_WEBHOOK_URL": "設定済み"
}
```

---

### 3. API 機能テスト

#### 3.1 今日の試合データを取得

**STEP 1: The Odds API から今日の試合を確認**
```bash
# ブラウザで以下にアクセス（API key を YOUR_KEY に置き換え）
https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=YOUR_KEY&regions=eu&markets=h2h
```

または

```bash
# スクリプトを実行（プロジェクトディレクトリで）
python3 scripts/lean_collect_teams.py
```

**STEP 2: 取得したチーム名をメモ**
例:
```
Arsenal vs Chelsea
Manchester City vs Liverpool
```

#### 3.2 API エンドポイントテスト

**テンプレート:**
```bash
curl -X POST "https://betvalue-finder-production.up.railway.app/analyze_paste" \
  -H "Content-Type: application/json" \
  -d '{
    "paste_text": "チームA\nチームB<ハンディキャップ>",
    "sport_hint": "soccer",
    "jp_odds": 1.9,
    "rakeback": 0
  }' | jq
```

**実例（今日の試合に置き換えて実行）:**
```bash
curl -X POST "https://betvalue-finder-production.up.railway.app/analyze_paste" \
  -H "Content-Type: application/json" \
  -d '{
    "paste_text": "アーセナル\nチェルシー<1.5>",
    "sport_hint": "soccer"
  }' | jq
```

**成功時の出力例:**
```json
[
  {
    "game_date": "10/13 20:00",
    "sport": "soccer_epl",
    "home_team_jp": "アーセナル",
    "away_team_jp": "チェルシー",
    "match_confidence": 1.0,
    "jp_line": "1.5",
    "pinnacle_line": 1.5,
    "home_team_odds": {
      "raw_pinnacle_odds": 1.95,
      "fair_odds": 2.05,
      "ev_percentage": 5.2,
      "verdict": "Recommended"
    },
    "away_team_odds": {
      "raw_pinnacle_odds": 1.85,
      "fair_odds": 1.95,
      "ev_percentage": -2.5,
      "verdict": "Not Recommended"
    }
  }
]
```

**失敗パターンと原因:**

| エラーメッセージ | 原因 | 解決方法 |
|-----------------|------|---------|
| `ODDS_API_KEY not configured` | 環境変数未設定 | Railway Variables で設定 |
| `チーム名を認識できません` | 古い/存在しない試合 | 今日の実際の試合データを使用 |
| `No odds available` | オッズデータなし | 試合開始が近い別の試合を試す |
| `Connection timeout` | サーバーダウン | Railway でログ確認 |

---

### 4. フロントエンド確認

#### 4.1 Web UI アクセス
```
https://betvalue-finder-production.up.railway.app
```

**確認項目:**
- [ ] ページが正常に表示される
- [ ] スポーツ選択ドロップダウンが機能する
- [ ] テキストエリアに入力できる
- [ ] 「分析開始」ボタンが表示される

#### 4.2 フロントエンドからテスト

**手順:**
1. 上記 URL にアクセス
2. テキストエリアに以下を入力（今日の試合に置き換え）:
   ```
   アーセナル
   チェルシー<1.5>
   ```
3. スポーツを「soccer」に選択
4. 「分析開始」をクリック
5. 結果が表示されることを確認

**成功時:**
- ✅ 結果テーブルが表示される
- ✅ EV パーセンテージが表示される
- ✅ 推奨判定（Recommended/Not Recommended）が表示される

**失敗時:**
- ❌ エラーメッセージが表示される → 上記「失敗パターン」を参照

---

### 5. ログ確認

#### 5.1 Railway ログ確認

**Railway ダッシュボード:**
1. Deployments タブ
2. 最新のデプロイをクリック
3. "View Logs" をクリック

**確認すべきログ:**
```
✅ INFO: Application startup complete
✅ INFO: Uvicorn running on http://0.0.0.0:$PORT
❌ ERROR: ... (エラーがあれば表示される)
```

#### 5.2 ローカルログ確認（開発環境）
```bash
# プロジェクトディレクトリで
tail -f logs/pipeline.log
tail -f logs/mapping_failures.jsonl
```

---

### 6. 自律マッピングシステム確認

#### 6.1 失敗ログ記録の確認
```bash
# ローカル環境で
cat logs/mapping_failures.jsonl | tail -5
```

**期待される出力:**
```json
{"timestamp": "2025-10-13T...", "api_team": "...", "user_input": "...", "failure_type": "..."}
```

#### 6.2 手動パイプライン実行（週次タスク）
```bash
# Railway CLI をインストール済みの場合
railway run python3 scripts/autonomous_mapping_pipeline.py

# または SSH 経由で Railway コンテナに接続して実行
```

#### 6.3 Discord 通知テスト（オプション）
```bash
# ローカル環境で
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python3 tools/discord_notifier.py --test
```

**成功時:**
- ✅ Discord チャンネルにテスト通知が届く

---

### 7. パフォーマンステスト

#### 7.1 レスポンスタイム測定
```bash
time curl -X POST "https://betvalue-finder-production.up.railway.app/analyze_paste" \
  -H "Content-Type: application/json" \
  -d '{"paste_text":"アーセナル\nチェルシー<1.5>","sport_hint":"soccer"}' \
  -s -o /dev/null
```

**期待値:**
- ✅ 初回: 5-10秒
- ✅ 2回目以降（キャッシュあり）: 1-3秒

#### 7.2 同時リクエストテスト
```bash
# 5つの同時リクエスト
for i in {1..5}; do
  curl -X POST "https://betvalue-finder-production.up.railway.app/analyze_paste" \
    -H "Content-Type: application/json" \
    -d '{"paste_text":"アーセナル\nチェルシー<1.5>","sport_hint":"soccer"}' \
    -s &
done
wait
```

**期待値:**
- ✅ すべてのリクエストが成功
- ✅ Railway でエラーログが出ない

---

### 8. セキュリティ確認

#### 8.1 環境変数の保護
- [ ] `.env` ファイルが `.gitignore` に含まれている
- [ ] GitHub リポジトリに API キーが含まれていない
- [ ] Railway Variables が暗号化されている（自動）

#### 8.2 HTTPS 確認
```bash
curl -I https://betvalue-finder-production.up.railway.app
```

**確認項目:**
- [ ] `HTTP/2 200` が返る
- [ ] `strict-transport-security` ヘッダーがある（Railway 自動設定）

---

### 9. データ永続性確認

#### 9.1 データベースファイル
```bash
# ローカル環境で確認
ls -lh database/unified_teams.json
ls -lh data/league_names_mapping.json
```

**重要:**
- ⚠️ Railway は再デプロイ時にファイルシステムをリセット
- ✅ `database/unified_teams.json` は Git で管理されている
- ✅ 更新時は必ず commit & push

#### 9.2 バックアップ確認
```bash
# ローカル環境で
ls -lh backups/
```

---

### 10. トラブルシューティング

#### 10.1 デプロイ失敗時
```bash
# Railway ログで確認すべきエラー
ERROR: Module not found
→ requirements.txt に依存関係を追加

ERROR: Permission denied
→ ファイルパーミッション確認（railway_startup.sh など）

ERROR: Port already in use
→ Railway が自動的に $PORT を設定（問題なし）
```

#### 10.2 API エラー時
```bash
# /debug/env で環境変数を確認
curl -s https://betvalue-finder-production.up.railway.app/debug/env | jq

# 期待される出力
{
  "ODDS_API_KEY": "設定済み",  # ← これが "未設定" なら Railway で設定
  ...
}
```

#### 10.3 チーム名認識エラー時
```bash
# 1. The Odds API で今日の試合を確認
curl "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=YOUR_KEY&regions=eu" | jq

# 2. 取得したチーム名（英語）をそのまま使う
# 例: "Arsenal" → "アーセナル" に変換して入力
```

---

## 📋 定期確認チェックリスト（週次）

### 毎週日曜日
- [ ] Railway デプロイステータス確認
- [ ] 自律マッピングパイプライン手動実行
  ```bash
  railway run python3 scripts/autonomous_mapping_pipeline.py
  ```
- [ ] Discord 通知確認
- [ ] `logs/mapping_failures.jsonl` の件数確認
- [ ] `database/unified_teams.json` 更新があれば commit & push

### 毎月1回
- [ ] Railway 利用料金確認
- [ ] The Odds API クレジット残高確認
- [ ] バックアップファイル整理（30日以上古いものを削除）
- [ ] パフォーマンス指標レビュー

---

## 🚨 緊急時の対応

### Railway がダウンした場合
1. Railway Status ページ確認: https://status.railway.app
2. Deployments タブで "Redeploy" 実行
3. 問題が続く場合: Settings → "Restart" 実行

### API キーが漏洩した場合
1. The Odds API で即座にキーを無効化
2. 新しいキーを生成
3. Railway Variables で `ODDS_API_KEY` を更新
4. 自動的に再デプロイ開始

### データベースが破損した場合
1. Git から最新の `database/unified_teams.json` を取得
2. ローカルで `backups/` から復元
3. commit & push で Railway に反映

---

## 📊 成功基準

### ✅ システムが正常に動作している状態

1. **API レスポンス**: 10秒以内
2. **成功率**: 95%以上（実際の試合データで）
3. **Railway Uptime**: 99%以上
4. **エラーログ**: 1日あたり5件以下
5. **チーム名マッピング成功率**: 85%以上

### ❌ 問題がある状態

- API が 30秒以上応答しない
- エラー率が 10%を超える
- Railway で頻繁に再起動が発生
- チーム名認識が 50%を下回る

---

## 📞 サポート

### 問題が解決しない場合

1. **Railway ログを確認**
2. **GitHub Issues を検索**
3. **このドキュメントのトラブルシューティングセクションを参照**
4. **必要に応じて Railway サポートに問い合わせ**

---

**最終更新**: 2025-10-13
**検証者**: Claude Code
**ステータス**: 本番稼働中
