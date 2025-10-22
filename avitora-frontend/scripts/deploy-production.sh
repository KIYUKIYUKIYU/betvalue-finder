#!/bin/bash

# ============================================
# AVITORA Frontend - Production Deployment
# ============================================
# 目的: 本番環境へのデプロイ自動化
# 実行: chmod +x scripts/deploy-production.sh && ./scripts/deploy-production.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 AVITORA Frontend - Production Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# 1. 確認プロンプト
# ============================================
echo "⚠️  本番デプロイを実行しようとしています。"
echo ""
read -p "本当にデプロイしますか？ (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "❌ デプロイを中止しました"
  exit 0
fi

echo ""

# ============================================
# 2. バージョン確認
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 バージョン確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

CURRENT_VERSION=$(node -p "require('./package.json').version")
echo "現在のバージョン: $CURRENT_VERSION"
echo ""
read -p "新しいバージョン番号 (例: 0.1.0): " NEW_VERSION

if [[ -z "$NEW_VERSION" ]]; then
  echo "❌ バージョン番号が空です"
  exit 1
fi

echo ""

# ============================================
# 3. バージョンタグ作成
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏷️  バージョンタグ作成"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

npm version "$NEW_VERSION" -m "Release v$NEW_VERSION: AVITORA Frontend"

echo "✅ バージョンタグ v$NEW_VERSION を作成しました"
echo ""

# ============================================
# 4. プラットフォーム選択
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 デプロイプラットフォーム選択"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "デプロイプラットフォームを選択してください:"
echo "  1) Vercel (推奨)"
echo "  2) Railway"
echo "  3) Fly.io"
echo ""
read -p "選択 (1-3): " PLATFORM

case $PLATFORM in
  1)
    echo "✅ Vercel を選択しました"
    PLATFORM_NAME="vercel"
    ;;
  2)
    echo "✅ Railway を選択しました"
    PLATFORM_NAME="railway"
    ;;
  3)
    echo "✅ Fly.io を選択しました"
    PLATFORM_NAME="fly"
    ;;
  *)
    echo "❌ 無効な選択です"
    exit 1
    ;;
esac

echo ""

# ============================================
# 5. 環境変数の確認
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 環境変数の確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "本番API URL: " PROD_API_URL

if [[ -z "$PROD_API_URL" ]]; then
  echo "❌ API URLが空です"
  exit 1
fi

if [[ "$PROD_API_URL" == *"localhost"* ]] || [[ "$PROD_API_URL" == *"staging"* ]]; then
  echo "⚠️  警告: 本番URLにlocalhostまたはstagingが含まれています"
  read -p "本当にこのURLでデプロイしますか？ (yes/no): " CONFIRM_URL
  if [ "$CONFIRM_URL" != "yes" ]; then
    echo "❌ デプロイを中止しました"
    exit 1
  fi
fi

echo "✅ NEXT_PUBLIC_API_BASE_URL=$PROD_API_URL"
echo ""

# ============================================
# 6. 本番デプロイ実行
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 本番デプロイ開始"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$PLATFORM_NAME" = "vercel" ]; then
  # Vercel
  echo "Vercelへ本番デプロイ中..."

  # 環境変数設定
  vercel env add NEXT_PUBLIC_API_BASE_URL production <<EOF
$PROD_API_URL
EOF

  # 本番デプロイ
  vercel --prod

  echo ""
  echo "✅ Vercelへの本番デプロイが完了しました"

elif [ "$PLATFORM_NAME" = "railway" ]; then
  # Railway
  echo "Railwayへ本番デプロイ中..."

  # 環境変数設定
  railway variables set NEXT_PUBLIC_API_BASE_URL="$PROD_API_URL"

  # 本番デプロイ
  railway up --environment production

  echo ""
  echo "✅ Railwayへの本番デプロイが完了しました"

elif [ "$PLATFORM_NAME" = "fly" ]; then
  # Fly.io
  echo "Fly.ioへ本番デプロイ中..."

  # 環境変数設定
  fly secrets set NEXT_PUBLIC_API_BASE_URL="$PROD_API_URL"

  # 本番デプロイ
  fly deploy --config fly.production.toml

  echo ""
  echo "✅ Fly.ioへの本番デプロイが完了しました"
fi

echo ""

# ============================================
# 7. Gitタグプッシュ
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏷️  Gitタグをプッシュ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

git push origin main --tags

echo "✅ タグをリモートにプッシュしました"
echo ""

# ============================================
# 8. 完了
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 本番デプロイ完了 (v$NEW_VERSION)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "次のステップ:"
echo "  1. 本番URLにアクセスして動作確認"
echo "  2. ポストデプロイ監視を開始 (0-15分、15-60分、1-24時間)"
echo "  3. エラーレートとレスポンスタイムを監視"
echo "  4. 問題があればロールバック: ./scripts/rollback.sh"
echo ""
echo "監視ダッシュボード:"
echo "  - Uptime: (設定してください)"
echo "  - Errors: (設定してください)"
echo "  - Analytics: (設定してください)"
echo ""
