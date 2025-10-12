#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動検証・ロールバック機能
マッピング更新後の失敗率をチェックし、悪化していればロールバック
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional


class AutoValidator:
    """マッピング更新の自動検証"""

    def __init__(self, log_path: str = None):
        """
        Args:
            log_path: mapping_failures.jsonl のパス
        """
        self.base_dir = Path(__file__).parent.parent
        self.log_path = Path(log_path) if log_path else self.base_dir / "logs" / "mapping_failures.jsonl"

    def validate_update(
        self,
        update_datetime: datetime,
        before_days: int = 7,
        after_hours: int = 1,
        threshold: float = 0.05
    ) -> Dict:
        """
        更新前後の失敗率を比較し、悪化していないかチェック

        Args:
            update_datetime: 更新実行日時
            before_days: 更新前の比較期間（日数）
            after_hours: 更新後の比較期間（時間）
            threshold: 許容する失敗率増加（0.05 = 5%）

        Returns:
            {
                "failure_rate_increased": bool,
                "before_rate": float,
                "after_rate": float,
                "delta": float,
                "recommendation": str
            }
        """
        # 更新前の失敗率（過去N日の平均）
        before_rate = self._calculate_failure_rate(
            end_date=update_datetime,
            days=before_days
        )

        # 更新後の失敗率（最新Nホラ）
        after_rate = self._calculate_failure_rate(
            start_date=update_datetime,
            hours=after_hours
        )

        # 差分
        delta = after_rate - before_rate

        # 判定
        failure_rate_increased = delta > threshold

        result = {
            "failure_rate_increased": failure_rate_increased,
            "before_rate": before_rate,
            "after_rate": after_rate,
            "delta": delta,
            "threshold": threshold
        }

        # 推奨アクション
        if failure_rate_increased:
            result["recommendation"] = "rollback"
            result["reason"] = f"失敗率が{delta*100:.1f}%増加（閾値: {threshold*100:.1f}%）"
        else:
            result["recommendation"] = "keep"
            result["reason"] = f"失敗率の増加は許容範囲内（{delta*100:.1f}%）"

        return result

    def _calculate_failure_rate(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: Optional[int] = None,
        hours: Optional[int] = None
    ) -> float:
        """
        指定期間の失敗率を計算

        Args:
            start_date: 開始日時
            end_date: 終了日時
            days: 日数（end_dateから遡る）
            hours: 時間数（start_dateから進む）

        Returns:
            失敗率（0.0-1.0）
        """
        if not self.log_path.exists():
            return 0.0

        # 期間設定
        if days is not None and end_date:
            start_date = end_date - timedelta(days=days)
        elif hours is not None and start_date:
            end_date = start_date + timedelta(hours=hours)
        elif start_date is None:
            start_date = datetime.min
        if end_date is None:
            end_date = datetime.max

        # ログから該当期間のエントリを抽出
        failures = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(entry["timestamp"])

                        if start_date <= timestamp <= end_date:
                            failures.append(entry)

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        except Exception as e:
            print(f"⚠️  ログ読み込みエラー: {e}")
            return 0.0

        # 失敗率計算（簡易版）
        # 実際の運用では、総マッチング試行数を取得する必要がある
        # ここでは失敗回数のみで代用

        failure_count = len(failures)

        # TODO: 実際の運用では総試行数を取得
        # 仮の総試行数（失敗数の10倍と仮定）
        total_attempts = max(failure_count * 10, 100)

        failure_rate = failure_count / total_attempts if total_attempts > 0 else 0.0

        return failure_rate

    def get_failure_statistics(self, days: int = 7) -> Dict:
        """
        過去N日の失敗統計を取得

        Args:
            days: 日数

        Returns:
            統計情報
        """
        if not self.log_path.exists():
            return {
                "total_failures": 0,
                "failure_rate": 0.0,
                "period_days": days
            }

        cutoff_date = datetime.now() - timedelta(days=days)
        failures = []

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(entry["timestamp"])

                        if timestamp >= cutoff_date:
                            failures.append(entry)

                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        except Exception:
            pass

        failure_count = len(failures)
        total_attempts = max(failure_count * 10, 100)  # 仮の総試行数
        failure_rate = failure_count / total_attempts

        return {
            "total_failures": failure_count,
            "failure_rate": failure_rate,
            "period_days": days,
            "avg_failures_per_day": failure_count / days if days > 0 else 0
        }


def main():
    """CLIとして実行（テスト用）"""
    import argparse

    parser = argparse.ArgumentParser(description="自動検証ツール")
    parser.add_argument(
        "--log",
        default="logs/mapping_failures.jsonl",
        help="ログファイルパス"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="失敗統計を表示"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="統計期間（日数）"
    )

    args = parser.parse_args()

    validator = AutoValidator(log_path=args.log)

    if args.stats:
        print("📊 失敗統計")
        print("=" * 60)

        stats = validator.get_failure_statistics(days=args.days)

        print(f"   期間: 過去{stats['period_days']}日")
        print(f"   総失敗数: {stats['total_failures']}回")
        print(f"   失敗率: {stats['failure_rate']*100:.2f}%")
        print(f"   1日平均: {stats['avg_failures_per_day']:.1f}回")
        print("=" * 60)

    else:
        # デフォルト: 検証デモ
        print("🧪 検証デモ（仮想更新）")
        print("=" * 60)

        # 仮想の更新日時（現在時刻の1時間前）
        update_time = datetime.now() - timedelta(hours=1)

        result = validator.validate_update(
            update_datetime=update_time,
            before_days=7,
            after_hours=1,
            threshold=0.05
        )

        print(f"   更新前失敗率: {result['before_rate']*100:.2f}%")
        print(f"   更新後失敗率: {result['after_rate']*100:.2f}%")
        print(f"   差分: {result['delta']*100:+.2f}%")
        print(f"   閾値: {result['threshold']*100:.2f}%")
        print()

        if result["failure_rate_increased"]:
            print(f"   ❌ 推奨: ロールバック")
            print(f"   理由: {result['reason']}")
        else:
            print(f"   ✅ 推奨: 維持")
            print(f"   理由: {result['reason']}")

        print("=" * 60)


if __name__ == "__main__":
    main()
