#!/bin/bash

# ============================================
# AVITORA Frontend - Post-Deploy Monitoring
# ============================================
# 目的: デプロイ後の自動監視（0-24時間）
# 実行: chmod +x scripts/post-deploy-monitor.sh && ./scripts/post-deploy-monitor.sh <prod-url>

set -e

PROD_URL=${1:-""}

if [[ -z "$PROD_URL" ]]; then
  echo "使用方法: ./scripts/post-deploy-monitor.sh <prod-url>"
  echo "例: ./scripts/post-deploy-monitor.sh https://avitora.com"
  exit 1
fi

# 末尾のスラッシュを削除
PROD_URL=${PROD_URL%/}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 AVITORA Frontend - Post-Deploy Monitor"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "監視対象URL: $PROD_URL"
echo "開始時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ログディレクトリ作成
LOG_DIR="logs/post-deploy-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"

# ============================================
# ヘルスチェック関数
# ============================================
check_health() {
  local url=$1
  local name=$2
  local start_time=$(date +%s%3N)

  if curl -f -s -o /dev/null -w "%{http_code}" "$url" > /tmp/status_code 2>&1; then
    local end_time=$(date +%s%3N)
    local duration=$((end_time - start_time))
    local status_code=$(cat /tmp/status_code)

    if [ "$status_code" = "200" ] || [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
      echo "  ✅ $name - ${duration}ms (HTTP $status_code)"
      return 0
    else
      echo "  ⚠️  $name - ${duration}ms (HTTP $status_code)"
      return 1
    fi
  else
    echo "  ❌ $name - FAILED"
    return 1
  fi
}

# ============================================
# フェーズ1: 0-15分監視（高頻度）
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏱️  フェーズ1: 0-15分監視（30秒間隔）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PHASE1_DURATION=900  # 15分 = 900秒
PHASE1_INTERVAL=30   # 30秒間隔
PHASE1_START=$(date +%s)
PHASE1_ERRORS=0

while [ $(($(date +%s) - PHASE1_START)) -lt $PHASE1_DURATION ]; do
  echo "[$(date '+%H:%M:%S')] チェック中..."

  check_health "$PROD_URL/" "Landing" || ((PHASE1_ERRORS++))
  check_health "$PROD_URL/auth/login" "Login" || ((PHASE1_ERRORS++))
  check_health "$PROD_URL/auth/signup" "Signup" || ((PHASE1_ERRORS++))
  check_health "$PROD_URL/dashboard" "Dashboard" || ((PHASE1_ERRORS++))

  # エラー率チェック
  TOTAL_CHECKS=$((4 * (($(date +%s) - PHASE1_START) / PHASE1_INTERVAL + 1)))
  ERROR_RATE=$((PHASE1_ERRORS * 100 / TOTAL_CHECKS))

  if [ $ERROR_RATE -gt 10 ]; then
    echo ""
    echo "⚠️  警告: エラー率が${ERROR_RATE}%です（閾値: 10%）"
    echo "   ロールバックを検討してください: ./scripts/rollback.sh"
    echo ""
  fi

  echo "  エラー率: ${ERROR_RATE}% ($PHASE1_ERRORS/$TOTAL_CHECKS)"
  echo ""

  sleep $PHASE1_INTERVAL
done

echo "✅ フェーズ1完了 - 総エラー: $PHASE1_ERRORS"
echo ""

# ============================================
# フェーズ2: 15-60分監視（中頻度）
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏱️  フェーズ2: 15-60分監視（5分間隔）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

PHASE2_DURATION=2700  # 45分 = 2700秒
PHASE2_INTERVAL=300   # 5分間隔
PHASE2_START=$(date +%s)
PHASE2_ERRORS=0

while [ $(($(date +%s) - PHASE2_START)) -lt $PHASE2_DURATION ]; do
  echo "[$(date '+%H:%M:%S')] チェック中..."

  check_health "$PROD_URL/" "Landing" || ((PHASE2_ERRORS++))
  check_health "$PROD_URL/auth/login" "Login" || ((PHASE2_ERRORS++))
  check_health "$PROD_URL/auth/signup" "Signup" || ((PHASE2_ERRORS++))
  check_health "$PROD_URL/dashboard" "Dashboard" || ((PHASE2_ERRORS++))
  check_health "$PROD_URL/dashboard/games" "Games" || ((PHASE2_ERRORS++))
  check_health "$PROD_URL/dashboard/settings" "Settings" || ((PHASE2_ERRORS++))
  check_health "$PROD_URL/dashboard/subscription" "Subscription" || ((PHASE2_ERRORS++))

  echo ""
  sleep $PHASE2_INTERVAL
done

echo "✅ フェーズ2完了 - 総エラー: $PHASE2_ERRORS"
echo ""

# ============================================
# フェーズ3: 1-24時間監視（低頻度）
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏱️  フェーズ3: 1-24時間監視（1時間間隔）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "長時間監視のためバックグラウンド実行を推奨します:"
echo ""
echo "  nohup ./scripts/post-deploy-monitor.sh $PROD_URL > monitor.log 2>&1 &"
echo ""

PHASE3_DURATION=82800  # 23時間 = 82800秒
PHASE3_INTERVAL=3600   # 1時間間隔
PHASE3_START=$(date +%s)
PHASE3_ERRORS=0

while [ $(($(date +%s) - PHASE3_START)) -lt $PHASE3_DURATION ]; do
  echo "[$(date '+%H:%M:%S')] 定期チェック中..."

  check_health "$PROD_URL/" "Landing" || ((PHASE3_ERRORS++))
  check_health "$PROD_URL/auth/login" "Login" || ((PHASE3_ERRORS++))
  check_health "$PROD_URL/auth/signup" "Signup" || ((PHASE3_ERRORS++))
  check_health "$PROD_URL/dashboard" "Dashboard" || ((PHASE3_ERRORS++))

  # Lighthouse監査（CI環境のみ）
  if command -v node &> /dev/null; then
    echo "  Lighthouse監査実行中..."
    if node scripts/lhci.mjs > "$LOG_DIR/lighthouse_$(date +%Y%m%d_%H%M%S).log" 2>&1; then
      echo "  ✅ Lighthouse監査完了"
    else
      echo "  ⚠️  Lighthouse監査スキップ（環境制限）"
    fi
  fi

  echo ""
  sleep $PHASE3_INTERVAL
done

echo "✅ フェーズ3完了 - 総エラー: $PHASE3_ERRORS"
echo ""

# ============================================
# 最終レポート
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 24時間監視完了レポート"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "監視対象URL: $PROD_URL"
echo "監視期間: 24時間"
echo "終了時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "エラーサマリー:"
echo "  フェーズ1 (0-15分): $PHASE1_ERRORS エラー"
echo "  フェーズ2 (15-60分): $PHASE2_ERRORS エラー"
echo "  フェーズ3 (1-24時間): $PHASE3_ERRORS エラー"
echo "  合計: $((PHASE1_ERRORS + PHASE2_ERRORS + PHASE3_ERRORS)) エラー"
echo ""

TOTAL_ERRORS=$((PHASE1_ERRORS + PHASE2_ERRORS + PHASE3_ERRORS))

if [ $TOTAL_ERRORS -eq 0 ]; then
  echo "✅ ステータス: 正常（エラーなし）"
elif [ $TOTAL_ERRORS -lt 10 ]; then
  echo "⚠️  ステータス: 注意（軽微なエラーあり）"
else
  echo "❌ ステータス: 要対応（エラー多数）"
fi

echo ""
echo "ログ保存先: $LOG_DIR"
echo ""
