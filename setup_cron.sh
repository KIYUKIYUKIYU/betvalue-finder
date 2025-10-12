#!/bin/bash
# cron設定スクリプト

echo "📋 cron設定を開始します"
echo ""

# 現在のcron設定を確認
echo "現在のcron設定:"
crontab -l 2>/dev/null || echo "  (まだ設定なし)"
echo ""

# 新しいcron設定
PROJECT_DIR="/mnt/c/Users/yfuku/Desktop/betvalue-finder"
PYTHON_BIN="/usr/bin/python3"

CRON_LINE="0 3 * * 0 cd $PROJECT_DIR && $PYTHON_BIN scripts/autonomous_mapping_pipeline.py >> logs/pipeline.log 2>&1"

echo "追加するcron設定:"
echo "  $CRON_LINE"
echo ""
echo "説明:"
echo "  - 毎週日曜日 午前3時に実行"
echo "  - 実行ログ: logs/pipeline.log"
echo ""

read -p "この設定を追加しますか？ (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    # 既存のcron設定を取得（なければ空）
    crontab -l 2>/dev/null > /tmp/current_cron || touch /tmp/current_cron

    # 重複チェック
    if grep -q "autonomous_mapping_pipeline.py" /tmp/current_cron; then
        echo "⚠️  既に同様の設定が存在します"
        cat /tmp/current_cron | grep "autonomous_mapping_pipeline.py"
    else
        # 新しい設定を追加
        echo "$CRON_LINE" >> /tmp/current_cron
        crontab /tmp/current_cron
        echo "✅ cron設定を追加しました"
    fi

    # 確認
    echo ""
    echo "現在のcron設定:"
    crontab -l

    rm /tmp/current_cron
else
    echo "❌ キャンセルしました"
fi

echo ""
echo "手動でcron設定を編集する場合:"
echo "  crontab -e"
