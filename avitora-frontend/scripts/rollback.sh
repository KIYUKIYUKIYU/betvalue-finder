#!/bin/bash

# ============================================
# AVITORA Frontend - Emergency Rollback
# ============================================
# 目的: 本番環境の緊急ロールバック
# 実行: chmod +x scripts/rollback.sh && ./scripts/rollback.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  AVITORA Frontend - Emergency Rollback"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# 1. ロールバック理由の確認
# ============================================
echo "⚠️  本番環境をロールバックしようとしています。"
echo ""
echo "ロールバック基準:"
echo "  ✓ サイトが完全にダウン（5分以上）"
echo "  ✓ 重大なJSエラーが10%以上のユーザーに影響"
echo "  ✓ 認証が完全に機能しない"
echo "  ✓ 決済/サブスクリプションの失敗"
echo "  ✓ API 5xxエラーが50%以上"
echo ""
read -p "ロールバックする理由: " ROLLBACK_REASON

if [[ -z "$ROLLBACK_REASON" ]]; then
  echo "❌ ロールバック理由が必要です"
  exit 1
fi

echo ""
read -p "本当にロールバックしますか？ (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "❌ ロールバックを中止しました"
  exit 0
fi

echo ""

# ============================================
# 2. プラットフォーム選択
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 プラットフォーム選択"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "デプロイプラットフォームを選択してください:"
echo "  1) Vercel"
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
# 3. ロールバック実行
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏮️  ロールバック実行"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$PLATFORM_NAME" = "vercel" ]; then
  # Vercel
  echo "現在のデプロイ一覧を取得中..."
  vercel ls --prod

  echo ""
  read -p "ロールバック先のデプロイURL（上記から選択）: " DEPLOYMENT_URL

  if [[ -z "$DEPLOYMENT_URL" ]]; then
    echo "❌ デプロイURLが空です"
    exit 1
  fi

  echo ""
  echo "ロールバック実行中..."
  vercel rollback "$DEPLOYMENT_URL"

  echo "✅ Vercelでロールバック完了"

elif [ "$PLATFORM_NAME" = "railway" ]; then
  # Railway
  echo "ロールバック実行中..."
  railway rollback

  echo "✅ Railwayでロールバック完了"

elif [ "$PLATFORM_NAME" = "fly" ]; then
  # Fly.io
  echo "現在のリリース一覧を取得中..."
  fly releases

  echo ""
  read -p "ロールバック先のバージョン番号（例: v2）: " VERSION

  if [[ -z "$VERSION" ]]; then
    echo "❌ バージョン番号が空です"
    exit 1
  fi

  echo ""
  echo "ロールバック実行中..."
  fly releases rollback "$VERSION"

  echo "✅ Fly.ioでロールバック完了"
fi

echo ""

# ============================================
# 4. ロールバック検証
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ロールバック検証"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "本番URL: " PROD_URL

if [[ -n "$PROD_URL" ]]; then
  echo "主要ページの動作確認中..."
  echo ""

  # ランディングページ
  if curl -f "$PROD_URL/" > /dev/null 2>&1; then
    echo "✅ / (Landing) - OK"
  else
    echo "❌ / (Landing) - FAILED"
  fi

  # ログインページ
  if curl -f "$PROD_URL/auth/login" > /dev/null 2>&1; then
    echo "✅ /auth/login - OK"
  else
    echo "❌ /auth/login - FAILED"
  fi

  # サインアップページ
  if curl -f "$PROD_URL/auth/signup" > /dev/null 2>&1; then
    echo "✅ /auth/signup - OK"
  else
    echo "❌ /auth/signup - FAILED"
  fi

  # ダッシュボード（401リダイレクト確認）
  if curl -f "$PROD_URL/dashboard" > /dev/null 2>&1; then
    echo "✅ /dashboard - OK"
  else
    echo "❌ /dashboard - FAILED"
  fi

  echo ""
fi

# ============================================
# 5. インシデント記録
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 インシデント記録"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

INCIDENT_FILE="incidents/rollback_$(date +%Y%m%d_%H%M%S).md"
mkdir -p incidents

cat > "$INCIDENT_FILE" <<EOF
# Rollback Incident Report

## 基本情報
- **日時:** $(date '+%Y-%m-%d %H:%M:%S')
- **実行者:** $(git config user.name) <$(git config user.email)>
- **プラットフォーム:** $PLATFORM_NAME

## ロールバック理由
$ROLLBACK_REASON

## 影響範囲
- 影響を受けたユーザー数: [記入してください]
- ダウンタイム: [記入してください]
- エラー率: [記入してください]

## 対応内容
- ロールバック実行時刻: $(date '+%Y-%m-%d %H:%M:%S')
- ロールバック先: [記入してください]
- 検証結果: [上記のチェック結果を記入]

## 根本原因
[後で記入してください]

## 再発防止策
[後で記入してください]

## 次のアクション
- [ ] ホットフィックスの作成
- [ ] QAテストの強化
- [ ] モニタリングの改善
- [ ] チーム共有

## タイムライン
- [時刻] 問題発生
- [時刻] ロールバック判断
- [時刻] ロールバック実行
- [時刻] 復旧確認
EOF

echo "✅ インシデントレポートを作成しました: $INCIDENT_FILE"
echo ""

# ============================================
# 6. チーム通知
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📢 チーム通知"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "以下の内容をチームに通知してください:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "[緊急] AVITORA Frontend ロールバック実施"
echo ""
echo "理由: $ROLLBACK_REASON"
echo "実施日時: $(date '+%Y-%m-%d %H:%M:%S')"
echo "プラットフォーム: $PLATFORM_NAME"
echo "ステータス: ロールバック完了"
echo ""
echo "次のアクション:"
echo "  1. 問題の根本原因分析"
echo "  2. ホットフィックスの準備"
echo "  3. 再デプロイ前のQA強化"
echo ""
echo "詳細: $INCIDENT_FILE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "✅ ロールバック手順完了"
echo ""
