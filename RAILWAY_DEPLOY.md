# Railway デプロイガイド

## 🚀 Railway での本番デプロイ手順

### 前提条件
- Railway アカウント: https://railway.app
- GitHub リポジトリとの連携
- The Odds API キー取得済み

---

## 📋 デプロイ手順

### 1. Railway プロジェクト作成

1. Railway ダッシュボードにアクセス
2. "New Project" をクリック
3. "Deploy from GitHub repo" を選択
4. `betvalue-finder` リポジトリを選択

---

### 2. 環境変数設定

Railway ダッシュボードで以下の環境変数を設定:

#### 🔑 必須環境変数

```bash
# The Odds API
ODDS_API_KEY=your_odds_api_key_here

# Discord通知（自律マッピングシステム用）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

#### 🔧 オプション環境変数（課金システム使用時）

```bash
# JWT設定
SECRET_KEY=your-secret-key-min-32-characters

# Stripe設定
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# メール設定
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@betvaluefinder.com
FROM_NAME=BetValue Finder

# アプリ設定
APP_URL=https://your-railway-app.up.railway.app
```

---

### 3. Railway 設定確認

以下のファイルが正しく設定されていることを確認:

#### `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install --upgrade pip && pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2",
    "healthcheckPath": "/docs",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

#### `Procfile`
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
```

#### `runtime.txt`
```
python-3.12.3
```

---

### 4. デプロイ実行

1. **自動デプロイ**:
   - GitHub に push すると自動的にデプロイ開始

2. **手動デプロイ**:
   - Railway ダッシュボードで "Deploy" をクリック

3. **デプロイログ確認**:
   - Railway ダッシュボードの "Deployments" タブでログを確認

---

### 5. デプロイ後の確認

#### ヘルスチェック
```bash
curl https://your-app.up.railway.app/docs
```

#### API動作確認
```bash
curl -X POST https://your-app.up.railway.app/api/scrape-and-analyze \
  -H "Content-Type: application/json" \
  -d '{
    "html": "<html>...</html>",
    "sport": "soccer"
  }'
```

---

## 🔧 Railway 特有の設定

### ポート設定
- Railway は自動的に `$PORT` 環境変数を設定
- `uvicorn` の `--port $PORT` で自動対応

### ワーカー数
- `--workers 2`: Railway の無料/Hobby プランに最適
- Pro プランでは `--workers 4` に増やすことを推奨

### ヘルスチェック
- `healthcheckPath: "/docs"`: FastAPI の自動ドキュメントをヘルスチェックに使用
- `healthcheckTimeout: 300`: 初回起動に時間がかかる場合に備えて5分に設定

---

## 📊 自律マッピングシステムの設定

Railway では cron が使えないため、以下のいずれかを選択:

### オプション 1: Railway Cron（推奨）
```bash
# Railway ダッシュボードで Cron Job を追加
# スケジュール: 0 3 * * 0 (毎週日曜 3:00 AM)
# コマンド: python3 scripts/autonomous_mapping_pipeline.py
```

### オプション 2: 外部 Cron サービス
- **GitHub Actions** を使用して定期実行
- **EasyCron** などの外部サービスを使用

### オプション 3: 手動実行
```bash
# Railway CLI をインストール
npm install -g @railway/cli

# ログイン
railway login

# プロジェクト選択
railway link

# コマンド実行
railway run python3 scripts/autonomous_mapping_pipeline.py
```

---

## 🗄️ データ永続化

### データベースファイル
Railway のエフェメラルファイルシステムでは、再デプロイ時にデータが消失します。

#### 解決策 1: Railway Volume（推奨）
```bash
# Railway ダッシュボードで Volume を追加
# マウントパス: /app/data
# データベースパス: /app/data/unified_teams.json
```

#### 解決策 2: GitHub 連携
- `database/unified_teams.json` を Git で管理
- 更新時は自動コミット・プッシュ

#### 解決策 3: 外部ストレージ
- AWS S3 / Google Cloud Storage を使用
- 起動時にダウンロード、更新時にアップロード

---

## 🚨 トラブルシューティング

### ビルド失敗
```bash
# requirements.txt の依存関係を確認
pip install -r requirements.txt

# ローカルで動作確認
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### メモリ不足
```bash
# ワーカー数を減らす
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

### タイムアウト
```bash
# healthcheckTimeout を延長
"healthcheckTimeout": 600  # 10分
```

### ログ確認
```bash
# Railway CLI でログ確認
railway logs
```

---

## 📈 パフォーマンス最適化

### 1. キャッシュ活用
- The Odds API のレスポンスをキャッシュ
- Redis を Railway に追加してキャッシュストア化

### 2. ワーカー数調整
```bash
# Hobby プラン: --workers 2
# Pro プラン: --workers 4
# Pro+ プラン: --workers 8
```

### 3. データベース最適化
- SQLite → PostgreSQL に移行（大規模運用時）
- Railway PostgreSQL プラグイン使用

---

## 💰 コスト見積もり

### Railway プラン
- **Hobby ($5/月)**: 個人利用・テスト環境
  - 512MB RAM
  - 1GB ディスク
  - $5 クレジット付与

- **Pro ($20/月)**: 本番運用推奨
  - 8GB RAM
  - 100GB ディスク
  - $20 クレジット付与

### The Odds API
- **無料枠**: 500リクエスト/月
- **Starter ($50/月)**: 10,000リクエスト/月
- **Pro ($200/月)**: 50,000リクエスト/月

---

## 🔐 セキュリティ

### 環境変数の管理
- Railway の環境変数は暗号化保存
- `.env` ファイルは Git にコミットしない（`.gitignore` に追加済み）

### API キーの保護
- Stripe Webhook Secret は必ず設定
- Discord Webhook URL は外部に漏らさない

### HTTPS
- Railway は自動的に HTTPS 証明書を発行
- カスタムドメイン対応

---

## 📚 参考リンク

- [Railway Docs](https://docs.railway.app/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [The Odds API Docs](https://the-odds-api.com/liveapi/guides/v4/)

---

## ✅ デプロイチェックリスト

- [ ] Railway アカウント作成
- [ ] GitHub リポジトリ連携
- [ ] 環境変数設定（ODDS_API_KEY）
- [ ] 環境変数設定（DISCORD_WEBHOOK_URL）
- [ ] デプロイ実行
- [ ] ヘルスチェック確認（/docs）
- [ ] API動作確認（/api/scrape-and-analyze）
- [ ] データ永続化設定（Volume または GitHub 連携）
- [ ] 自律マッピングシステム設定（Cron または手動実行）
- [ ] カスタムドメイン設定（オプション）

---

**🎉 Railway デプロイ完了！**
