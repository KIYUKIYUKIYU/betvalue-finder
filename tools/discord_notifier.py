#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord通知機能
中信頼度マッピング候補をDiscordに通知
"""

import json
import os
from typing import Dict, List
from datetime import datetime
import requests


class DiscordNotifier:
    """Discord Webhook経由で通知を送信"""

    def __init__(self, webhook_url: str = None):
        """
        Args:
            webhook_url: Discord Webhook URL
                         環境変数 DISCORD_WEBHOOK_URL からも取得可能
        """
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

        if not self.webhook_url:
            raise ValueError(
                "Discord Webhook URLが設定されていません。\n"
                "環境変数 DISCORD_WEBHOOK_URL を設定するか、\n"
                "引数で webhook_url を指定してください。"
            )

    def send_mapping_review_request(self, candidates: Dict) -> bool:
        """
        マッピングレビュー依頼を送信

        Args:
            candidates: {
                "api_team": {
                    "japanese": "カタカナ名",
                    "confidence": 85.5,
                    "source": "user_input"
                }
            }

        Returns:
            送信成功したか
        """
        if not candidates:
            return True  # 送信不要

        # Embed形式でメッセージ構築
        embed = self._build_review_embed(candidates)

        payload = {
            "content": "🔔 **マッピング更新レビュー依頼**",
            "embeds": [embed]
        }

        return self._send_webhook(payload)

    def send_auto_update_notification(self, updates: Dict) -> bool:
        """
        自動適用通知を送信

        Args:
            updates: 自動適用されたマッピング

        Returns:
            送信成功したか
        """
        if not updates:
            return True

        embed = self._build_auto_update_embed(updates)

        payload = {
            "content": "✅ **マッピング自動更新完了**",
            "embeds": [embed]
        }

        return self._send_webhook(payload)

    def send_rollback_alert(self, reason: str, details: Dict = None) -> bool:
        """
        ロールバックアラートを送信

        Args:
            reason: ロールバック理由
            details: 詳細情報

        Returns:
            送信成功したか
        """
        embed = {
            "title": "🚨 自動ロールバック実行",
            "description": reason,
            "color": 15158332,  # 赤色
            "fields": [],
            "timestamp": datetime.utcnow().isoformat()
        }

        if details:
            for key, value in details.items():
                embed["fields"].append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })

        payload = {
            "content": "@everyone",  # メンション
            "embeds": [embed]
        }

        return self._send_webhook(payload)

    def _build_review_embed(self, candidates: Dict) -> Dict:
        """レビュー依頼Embed構築"""
        fields = []

        # 候補を信頼度順にソート
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: x[1]["confidence"],
            reverse=True
        )

        for api_team, data in sorted_candidates[:10]:  # 最大10件
            japanese = data["japanese"]
            confidence = data["confidence"]
            source = data["source"]

            # ソースの日本語表記
            source_ja = {
                "user_input": "ユーザー入力",
                "transliteration": "音訳",
                "pattern": "既存パターン"
            }.get(source, source)

            field_value = (
                f"日本語: **{japanese}**\n"
                f"信頼度: `{confidence:.1f}点`\n"
                f"出典: {source_ja}"
            )

            fields.append({
                "name": f"🔹 {api_team}",
                "value": field_value,
                "inline": False
            })

        embed = {
            "title": "中信頼度マッピング候補",
            "description": (
                f"**{len(candidates)}件**の候補が見つかりました。\n\n"
                "24時間以内に異議がなければ自動適用されます。\n"
                "異議がある場合は👎リアクションをお願いします。"
            ),
            "color": 16776960,  # 黄色
            "fields": fields,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "自律マッピング更新システム"
            }
        }

        return embed

    def _build_auto_update_embed(self, updates: Dict) -> Dict:
        """自動適用通知Embed構築"""
        fields = []

        # 更新を信頼度順にソート
        sorted_updates = sorted(
            updates.items(),
            key=lambda x: x[1]["confidence"],
            reverse=True
        )

        for api_team, data in sorted_updates[:10]:  # 最大10件
            japanese = data["japanese"]
            confidence = data["confidence"]

            field_value = f"**{japanese}** (信頼度: `{confidence:.1f}点`)"

            fields.append({
                "name": f"✅ {api_team}",
                "value": field_value,
                "inline": False
            })

        embed = {
            "title": "高信頼度マッピング自動適用完了",
            "description": f"**{len(updates)}件**のマッピングが自動適用されました。",
            "color": 5763719,  # 緑色
            "fields": fields,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "自律マッピング更新システム"
            }
        }

        return embed

    def _send_webhook(self, payload: Dict) -> bool:
        """Webhook送信"""
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 204:
                return True
            else:
                print(f"⚠️  Discord送信失敗: HTTP {response.status_code}")
                print(f"   レスポンス: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print("⚠️  Discord送信タイムアウト")
            return False
        except Exception as e:
            print(f"⚠️  Discord送信エラー: {e}")
            return False


def main():
    """CLIとして実行（テスト用）"""
    import argparse

    parser = argparse.ArgumentParser(description="Discord通知テスト")
    parser.add_argument(
        "--webhook",
        help="Discord Webhook URL（または環境変数 DISCORD_WEBHOOK_URL）"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="テスト通知を送信"
    )

    args = parser.parse_args()

    try:
        notifier = DiscordNotifier(webhook_url=args.webhook)

        if args.test:
            print("📤 テスト通知送信中...")

            # テスト候補
            test_candidates = {
                "Brighton": {
                    "japanese": "ブライトン",
                    "confidence": 85.5,
                    "source": "user_input"
                },
                "Atlético Madrid": {
                    "japanese": "アトレティコ・マドリード",
                    "confidence": 78.2,
                    "source": "transliteration"
                }
            }

            success = notifier.send_mapping_review_request(test_candidates)

            if success:
                print("✅ テスト通知送信成功")
            else:
                print("❌ テスト通知送信失敗")

    except ValueError as e:
        print(f"❌ {e}")
        print("\n使用例:")
        print("  export DISCORD_WEBHOOK_URL='https://discord.com/api/webhooks/...'")
        print("  python3 tools/discord_notifier.py --test")


if __name__ == "__main__":
    main()
