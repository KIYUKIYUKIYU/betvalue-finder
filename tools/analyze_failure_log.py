#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失敗ログ分析ツール
mapping_failures.jsonl を分析し、頻出パターンを抽出
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict, Counter


class FailureLogAnalyzer:
    """失敗ログを分析し、統計レポートを生成"""

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.entries: List[Dict] = []

    def load_log(self, days: int = 7) -> int:
        """
        ログファイルを読み込み、指定日数分をフィルター

        Args:
            days: 過去何日分を分析するか

        Returns:
            読み込んだエントリ数
        """
        if not self.log_path.exists():
            print(f"⚠️  ログファイルが存在しません: {self.log_path}")
            return 0

        cutoff_date = datetime.now() - timedelta(days=days)
        self.entries = []

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        timestamp = datetime.fromisoformat(entry["timestamp"])

                        if timestamp >= cutoff_date:
                            self.entries.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        # 不正な行はスキップ
                        continue

            return len(self.entries)

        except Exception as e:
            print(f"❌ ログファイル読み込みエラー: {e}")
            return 0

    def analyze(self) -> Dict:
        """
        失敗ログを分析し、統計レポートを生成

        Returns:
            {
                "api_team_name": {
                    "api_occurrences": int,
                    "user_inputs": {"日本語名": count},
                    "most_common_input": str,
                    "first_seen": str,
                    "last_seen": str,
                    "failure_types": {"not_in_db": count, "no_match": count}
                }
            }
        """
        if not self.entries:
            return {}

        # api_teamごとにグループ化
        grouped = defaultdict(lambda: {
            "api_occurrences": 0,
            "user_inputs": Counter(),
            "timestamps": [],
            "failure_types": Counter()
        })

        for entry in self.entries:
            api_team = entry.get("api_team", "")
            user_input = entry.get("user_input", "")
            timestamp = entry.get("timestamp", "")
            failure_type = entry.get("failure_type", "unknown")

            if not api_team:
                continue

            grouped[api_team]["api_occurrences"] += 1
            grouped[api_team]["user_inputs"][user_input] += 1
            grouped[api_team]["timestamps"].append(timestamp)
            grouped[api_team]["failure_types"][failure_type] += 1

        # 統計レポート生成
        report = {}
        for api_team, data in grouped.items():
            # 最頻出のユーザー入力を取得
            most_common = data["user_inputs"].most_common(1)
            most_common_input = most_common[0][0] if most_common else ""

            # タイムスタンプをソート
            timestamps = sorted(data["timestamps"])

            report[api_team] = {
                "api_occurrences": data["api_occurrences"],
                "user_inputs": dict(data["user_inputs"]),
                "most_common_input": most_common_input,
                "first_seen": timestamps[0] if timestamps else "",
                "last_seen": timestamps[-1] if timestamps else "",
                "failure_types": dict(data["failure_types"])
            }

        return report

    def analyze_last_7_days(self) -> Dict:
        """過去7日分を分析（便利メソッド）"""
        self.load_log(days=7)
        return self.analyze()

    def print_report(self, report: Dict, top_n: int = 10):
        """レポートを見やすく表示"""
        if not report:
            print("📊 分析結果: データなし")
            return

        print("\n" + "=" * 80)
        print(f"📊 失敗ログ分析レポート (Top {top_n})")
        print("=" * 80)

        # 出現頻度順にソート
        sorted_teams = sorted(
            report.items(),
            key=lambda x: x[1]["api_occurrences"],
            reverse=True
        )

        for i, (api_team, data) in enumerate(sorted_teams[:top_n], 1):
            print(f"\n{i}. {api_team}")
            print(f"   API出現: {data['api_occurrences']}回")
            print(f"   最頻出入力: 「{data['most_common_input']}」")

            # ユーザー入力の内訳
            if len(data['user_inputs']) > 1:
                print(f"   入力バリエーション:")
                for user_input, count in sorted(
                    data['user_inputs'].items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    print(f"     - 「{user_input}」: {count}回")

            # 失敗タイプ
            failure_summary = ", ".join(
                f"{ftype}({count})"
                for ftype, count in data['failure_types'].items()
            )
            print(f"   失敗タイプ: {failure_summary}")

        print("\n" + "=" * 80)
        print(f"総チーム数: {len(report)}")
        print(f"総失敗回数: {sum(d['api_occurrences'] for d in report.values())}")

    def save_report(self, report: Dict, output_path: str):
        """レポートをJSONファイルに保存"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"💾 レポート保存: {output_file}")


def main():
    """CLIとして実行"""
    import argparse

    parser = argparse.ArgumentParser(description="失敗ログ分析ツール")
    parser.add_argument(
        "--log",
        default="logs/mapping_failures.jsonl",
        help="ログファイルパス"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="過去何日分を分析するか"
    )
    parser.add_argument(
        "--output",
        help="レポートの出力先（JSON）"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="表示する上位N件"
    )

    args = parser.parse_args()

    print(f"🔍 失敗ログ分析開始")
    print(f"   対象: {args.log}")
    print(f"   期間: 過去{args.days}日")

    analyzer = FailureLogAnalyzer(args.log)
    loaded = analyzer.load_log(days=args.days)

    print(f"   読み込み: {loaded}エントリ")

    if loaded == 0:
        print("\n⚠️  分析対象のログエントリがありません")
        return

    report = analyzer.analyze()
    analyzer.print_report(report, top_n=args.top)

    if args.output:
        analyzer.save_report(report, args.output)


if __name__ == "__main__":
    main()
