# -*- coding: utf-8 -*-
"""
TimeParser - 汎用時刻解析システム
全競技対応の深夜時刻・日付跨ぎ処理
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
import re
import logging


class TimeParser:
    """汎用時刻解析・日付変換システム"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 深夜時刻パターン (25:30, 24:45, 26:15 etc.)
        self.deep_night_pattern = re.compile(r'^([2-9]\d):([0-5]\d)$')
        # 通常時刻パターン (14:30, 09:45 etc.)
        self.normal_time_pattern = re.compile(r'^([0-1]?\d|2[0-3]):([0-5]\d)$')

    def parse_jp_time_notation(self, time_str: str, base_date: str) -> Tuple[str, str]:
        """
        日本式時刻表記を解析して正確な日付・時刻を返す

        Args:
            time_str: "25:30", "14:45" などの時刻文字列
            base_date: "2025-09-15" などの基準日付

        Returns:
            Tuple[実際の日付(YYYY-MM-DD), 実際の時刻(HH:MM)]

        Examples:
            parse_jp_time_notation("25:30", "2025-09-15") -> ("2025-09-16", "01:30")
            parse_jp_time_notation("14:45", "2025-09-15") -> ("2025-09-15", "14:45")
        """
        try:
            base_dt = datetime.strptime(base_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid base_date format: {base_date}")

        # 深夜時刻パターンの処理
        match = self.deep_night_pattern.match(time_str)
        if match:
            hour_raw = int(match.group(1))
            minute = int(match.group(2))

            # 24時間を超える時刻は翌日として処理
            if hour_raw >= 24:
                actual_hour = hour_raw - 24
                actual_date = base_dt + timedelta(days=1)
                actual_time = f"{actual_hour:02d}:{minute:02d}"

                self.logger.debug(f"Deep night time converted: {time_str} -> {actual_date.strftime('%Y-%m-%d')} {actual_time}")
                return actual_date.strftime("%Y-%m-%d"), actual_time
            else:
                # 22時や23時の場合は当日
                actual_time = f"{hour_raw:02d}:{minute:02d}"
                return base_date, actual_time

        # 通常時刻パターンの処理
        match = self.normal_time_pattern.match(time_str)
        if match:
            return base_date, time_str

        # パターンマッチしない場合
        raise ValueError(f"Invalid time format: {time_str}")

    def get_search_date_range(self, time_str: str, base_date: str, sport: str) -> list:
        """
        時刻表記に基づいて試合データ検索用の日付範囲を返す

        Args:
            time_str: "25:30", "14:45" などの時刻文字列
            base_date: "2025-09-15" などの基準日付
            sport: "mlb", "npb", "soccer"

        Returns:
            検索用日付リスト ["2025-09-15", "2025-09-16"]
        """
        try:
            actual_date, actual_time = self.parse_jp_time_notation(time_str, base_date)
            base_dt = datetime.strptime(base_date, "%Y-%m-%d")
            actual_dt = datetime.strptime(actual_date, "%Y-%m-%d")

            # 競技別の検索範囲調整
            if sport.lower() == "npb":
                # NPB: 当日のみ（日本国内なのでタイムゾーン問題少ない）
                return [actual_date]
            elif sport.lower() == "mlb":
                # MLB: 当日優先 + 前後1日（アメリカ時差考慮）
                prev_date = actual_dt - timedelta(days=1)
                next_date = actual_dt + timedelta(days=1)
                return [
                    prev_date.strftime("%Y-%m-%d"),
                    actual_date,
                    next_date.strftime("%Y-%m-%d")
                ]
            elif sport.lower() == "soccer":
                # Soccer: 実際の日付 + 基準日（両方検索）
                if actual_date != base_date:
                    return [base_date, actual_date]
                else:
                    # 通常時刻の場合は前後1日も検索
                    prev_date = base_dt - timedelta(days=1)
                    next_date = base_dt + timedelta(days=1)
                    return [
                        prev_date.strftime("%Y-%m-%d"),
                        base_date,
                        next_date.strftime("%Y-%m-%d")
                    ]
            else:
                # その他競技: 保守的に前後1日
                prev_date = actual_dt - timedelta(days=1)
                next_date = actual_dt + timedelta(days=1)
                return [
                    prev_date.strftime("%Y-%m-%d"),
                    actual_date,
                    next_date.strftime("%Y-%m-%d")
                ]

        except Exception as e:
            self.logger.warning(f"Failed to parse time {time_str}: {e}")
            # フォールバック: 基準日のみ
            return [base_date]

    def extract_time_from_text(self, text: str) -> Optional[str]:
        """
        テキストから時刻表記を抽出

        Args:
            text: "25:30", "ヴェローナ<0>\n25:30\nクレモネーゼ" などのテキスト

        Returns:
            抽出された時刻文字列、見つからない場合はNone
        """
        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            # 深夜時刻パターン
            if self.deep_night_pattern.match(line):
                return line
            # 通常時刻パターン
            if self.normal_time_pattern.match(line):
                return line
        return None

    def is_deep_night_time(self, time_str: str) -> bool:
        """深夜時刻（24時以降）かどうか判定"""
        match = self.deep_night_pattern.match(time_str)
        if match:
            hour = int(match.group(1))
            return hour >= 24
        return False


# グローバルインスタンス
time_parser = TimeParser()


if __name__ == "__main__":
    # テスト実行
    parser = TimeParser()

    test_cases = [
        ("25:30", "2025-09-15"),
        ("24:45", "2025-09-15"),
        ("26:15", "2025-09-15"),
        ("14:30", "2025-09-15"),
        ("23:59", "2025-09-15"),
    ]

    print("=== TimeParser テスト ===")
    for time_str, base_date in test_cases:
        try:
            actual_date, actual_time = parser.parse_jp_time_notation(time_str, base_date)
            print(f"{time_str} ({base_date}) -> {actual_date} {actual_time}")

            # 検索日付範囲テスト
            for sport in ["mlb", "npb", "soccer"]:
                ranges = parser.get_search_date_range(time_str, base_date, sport)
                print(f"  {sport}: {ranges}")
        except Exception as e:
            print(f"{time_str} -> エラー: {e}")
        print()