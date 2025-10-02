# -*- coding: utf-8 -*-
"""
DateResolver - 競技別日付解決クラス
カード配布日から適切なAPI取得日付への変換を行う
"""

from datetime import datetime, timedelta
from typing import List, Optional
from .time_parser import time_parser


class DateResolver:
    """競技別の日付解決を行うクラス"""
    
    @staticmethod
    def get_api_dates_with_time(sport: str, card_date: str, time_str: Optional[str] = None) -> List[str]:
        """
        時刻情報を考慮したAPI取得日付リストを返す (拡張版)

        Args:
            sport: "npb", "mlb", "soccer"
            card_date: "YYYY-MM-DD" 形式のカード配布日
            time_str: "25:30", "14:45" などの時刻文字列（省略可）

        Returns:
            API取得用日付リスト ["YYYY-MM-DD", ...]
        """
        if time_str:
            # 時刻情報がある場合はTimeParserを使用
            try:
                return time_parser.get_search_date_range(time_str, card_date, sport)
            except Exception:
                # TimeParser失敗時は従来ロジックにフォールバック
                pass

        # 従来ロジック（時刻情報なし、またはTimeParser失敗時）
        return DateResolver.get_api_dates(sport, card_date)

    @staticmethod
    def get_api_dates(sport: str, card_date: str) -> List[str]:
        """
        カード配布日から適切なAPI取得日付リストを返す
        
        Args:
            sport: "npb", "mlb", "soccer"
            card_date: "YYYY-MM-DD" 形式のカード配布日
            
        Returns:
            API取得用日付リスト ["YYYY-MM-DD", ...]
        """
        sport = sport.lower()
        
        try:
            base_date = datetime.strptime(card_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {card_date}. Expected YYYY-MM-DD")
        
        if sport == "npb":
            # NPB: カード日付 = API日付（同日開催）
            return [card_date]
            
        elif sport == "mlb":
            # MLB: 当日優先 + 翌日バックアップ（連戦対応）
            # 修正内容 (2025-09-14): 従来は翌日のみ検索していたが、
            # パドレス vs ロッキーズ問題で判明した通り、当日を優先検索する必要がある
            # return [api_date.strftime("%Y-%m-%d")]  # 修正前: 翌日のみ
            api_date = base_date + timedelta(days=1)
            return [card_date, api_date.strftime("%Y-%m-%d")]  # 修正後: 当日優先, 翌日バックアップ
            
        elif sport == "soccer":
            # サッカー: 当面は手動指定推奨
            # 暫定で当日±1日の範囲検索
            prev_date = base_date - timedelta(days=1)
            next_date = base_date + timedelta(days=1)
            return [
                prev_date.strftime("%Y-%m-%d"),
                card_date,
                next_date.strftime("%Y-%m-%d")
            ]
            
        else:
            # 不明な競技は当日のみ
            return [card_date]
    
    @staticmethod
    def get_display_info(sport: str, card_date: str) -> str:
        """日付変換の説明文を返す"""
        api_dates = DateResolver.get_api_dates(sport, card_date)
        sport = sport.lower()
        
        if sport == "npb":
            return f"NPB: {card_date} 当日開催の試合を参照"
        elif sport == "mlb":
            if len(api_dates) == 2:
                return f"MLB: {card_date} カード → {api_dates[0]}(優先) または {api_dates[1]} の試合を参照"
            else:
                return f"MLB: {card_date} カード → {api_dates[0]} 日本時間開催の試合を参照"
        elif sport == "soccer":
            return f"サッカー: {api_dates[0]} ～ {api_dates[2]} の範囲で検索"
        else:
            return f"{sport.upper()}: {card_date} の試合を参照"


# 使用例とテスト用関数
if __name__ == "__main__":
    resolver = DateResolver()
    
    test_cases = [
        ("npb", "2025-09-07"),
        ("mlb", "2025-09-07"),
        ("soccer", "2025-09-07")
    ]
    
    for sport, date in test_cases:
        api_dates = resolver.get_api_dates(sport, date)
        info = resolver.get_display_info(sport, date)
        print(f"{sport.upper()}: {date} → {api_dates}")
        print(f"  {info}")
        print()