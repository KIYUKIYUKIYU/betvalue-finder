#!/bin/bash

# ============================================
# AVITORA Frontend - Pre-Production Gate
# ============================================
# 目的: 本番デプロイ前の最終確認
# 実行: chmod +x scripts/pre-prod-gate.sh && ./scripts/pre-prod-gate.sh

set -e  # エラー時に即停止

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 AVITORA Frontend - Pre-Production Gate"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# 1. 環境変数チェック
# ============================================
echo "📋 Step 1/5: 環境変数チェック"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f .env.production.local ]; then
  echo "✅ .env.production.local が存在します"

  if grep -q "NEXT_PUBLIC_API_BASE_URL" .env.production.local; then
    API_URL=$(grep "NEXT_PUBLIC_API_BASE_URL" .env.production.local | cut -d '=' -f 2)
    echo "✅ NEXT_PUBLIC_API_BASE_URL: $API_URL"

    if [[ "$API_URL" == *"localhost"* ]]; then
      echo "⚠️  警告: 本番URLがlocalhostです。本番APIに変更してください！"
      exit 1
    fi
  else
    echo "❌ NEXT_PUBLIC_API_BASE_URL が設定されていません"
    exit 1
  fi
else
  echo "⚠️  .env.production.local が存在しません"
  echo "   .env.example をコピーして作成してください:"
  echo "   cp .env.example .env.production.local"
  exit 1
fi

echo ""

# ============================================
# 2. TypeScriptコンパイルチェック
# ============================================
echo "📋 Step 2/5: TypeScriptコンパイルチェック"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

npx tsc --noEmit
echo "✅ TypeScriptエラーなし"
echo ""

# ============================================
# 3. Design System監査
# ============================================
echo "📋 Step 3/5: Design System v1 監査"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

npx ts-node scripts/audit-design-system.ts
echo ""

# ============================================
# 4. 本番ビルド
# ============================================
echo "📋 Step 4/5: 本番ビルド"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

npm run build
echo "✅ 本番ビルド成功"
echo ""

# ============================================
# 5. 本番サーバー起動テスト
# ============================================
echo "📋 Step 5/5: 本番サーバー起動テスト"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "次のコマンドで本番モードサーバーを起動してください:"
echo ""
echo "  npm run start"
echo ""
echo "起動後、以下のページをブラウザで確認してください:"
echo ""
echo "  ✓ http://localhost:3000/              (Landing)"
echo "  ✓ http://localhost:3000/auth/login    (Login)"
echo "  ✓ http://localhost:3000/auth/signup   (Signup)"
echo "  ✓ http://localhost:3000/dashboard     (Dashboard - 401リダイレクト確認)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Pre-Production Gate 完了"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "次のステップ:"
echo "  1. npm run start でローカル確認"
echo "  2. vercel (ステージングデプロイ)"
echo "  3. ステージングスモークテスト実施"
echo "  4. vercel --prod (本番デプロイ)"
echo ""
