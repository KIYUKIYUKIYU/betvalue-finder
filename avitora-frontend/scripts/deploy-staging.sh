#!/bin/bash

# ============================================
# AVITORA Frontend - Staging Deployment
# ============================================
# 目的: ステージング環境へのデプロイ自動化
# 実行: chmod +x scripts/deploy-staging.sh && ./scripts/deploy-staging.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 AVITORA Frontend - Staging Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# 1. プラットフォーム選択
# ============================================
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
# 2. 環境変数の確認
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 環境変数の確認"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "ステージングAPI URL: " STAGING_API_URL

if [[ -z "$STAGING_API_URL" ]]; then
  echo "❌ API URLが空です"
  exit 1
fi

echo "✅ NEXT_PUBLIC_API_BASE_URL=$STAGING_API_URL"
echo ""

# ============================================
# 3. デプロイ実行
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 ステージングデプロイ開始"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$PLATFORM_NAME" = "vercel" ]; then
  # Vercel
  echo "Vercelへデプロイ中..."

  # 環境変数設定
  vercel env add NEXT_PUBLIC_API_BASE_URL staging <<EOF
$STAGING_API_URL
EOF

  # デプロイ
  vercel

  echo ""
  echo "✅ Vercelへのデプロイが完了しました"
  echo ""
  echo "デプロイURL: 上記の出力を確認してください"

elif [ "$PLATFORM_NAME" = "railway" ]; then
  # Railway
  echo "Railwayへデプロイ中..."

  # 環境変数設定
  railway variables set NEXT_PUBLIC_API_BASE_URL="$STAGING_API_URL"

  # デプロイ
  railway up --environment staging

  echo ""
  echo "✅ Railwayへのデプロイが完了しました"

elif [ "$PLATFORM_NAME" = "fly" ]; then
  # Fly.io
  echo "Fly.ioへデプロイ中..."

  # 環境変数設定
  fly secrets set NEXT_PUBLIC_API_BASE_URL="$STAGING_API_URL"

  # デプロイ
  fly deploy

  echo ""
  echo "✅ Fly.ioへのデプロイが完了しました"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ステージングデプロイ完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "次のステップ:"
echo "  1. ステージングURLにアクセスして動作確認"
echo "  2. スモークテストを実施 (PRODUCTION_CHECKLIST.md参照)"
echo "  3. 問題なければ本番デプロイ: ./scripts/deploy-production.sh"
echo ""
