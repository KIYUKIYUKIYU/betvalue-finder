# -*- coding: utf-8 -*-
"""
MarketStrategy: オッズマーケット取得戦略の抽象基底クラス

設計原則:
- Strategy Pattern: マーケット取得方法を抽象化
- 拡張性: 新しいマーケットタイプを容易に追加可能
- 互換性: すべての戦略が同じデータ形式を返す
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import aiohttp
import logging


class MarketStrategy(ABC):
    """オッズマーケット取得戦略の抽象基底クラス"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Args:
            logger: ロガーインスタンス（Noneの場合は新規作成）
        """
        self.logger = logger or logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api_base = "https://api.the-odds-api.com/v4"

    @abstractmethod
    async def fetch_odds(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        sport_key: str,
        event_id: str,
        **kwargs
    ) -> Optional[Dict]:
        """
        オッズデータを取得

        Args:
            session: aiohttpセッション
            api_key: The Odds API キー
            sport_key: スポーツキー（例: soccer_epl, basketball_nba）
            event_id: イベントID（The Odds APIのUUID形式）
            **kwargs: 追加パラメータ
                - regions: 地域（デフォルト: us）
                - bookmakers: ブックメーカー（デフォルト: pinnacle）
                - oddsFormat: オッズ形式（デフォルト: decimal）

        Returns:
            API-Sports互換形式のオッズデータ、またはNone
            {
                'fixture_id': str,
                'bookmakers': [{
                    'id': int,
                    'name': str,
                    'bets': [{
                        'id': int,
                        'name': str,
                        'values': [{
                            'value': str,  # "Home -0.5"
                            'odd': str     # "1.95"
                        }]
                    }]
                }]
            }
        """
        pass

    @abstractmethod
    def get_market_name(self) -> str:
        """
        マーケット名を返す

        Returns:
            マーケット名（例: "spreads", "alternate_spreads"）
        """
        pass

    @abstractmethod
    def supports_multiple_lines(self) -> bool:
        """
        複数ハンディキャップライン対応か

        Returns:
            True: 複数ライン取得可能
            False: 1ラインのみ
        """
        pass

    def _format_odds_data(self, event: Dict, home_team: str, away_team: str) -> Dict:
        """
        The Odds API形式をAPI-Sports互換形式に変換

        Args:
            event: The Odds APIイベントデータ
            home_team: ホームチーム名
            away_team: アウェイチーム名

        Returns:
            API-Sports互換形式のオッズデータ
        """
        self.logger.debug(f"📥 Formatting odds data for event {event.get('id')}")

        bookmakers = []

        for bm in event.get("bookmakers", []):
            if bm.get("key") != "pinnacle":
                continue

            bets = []

            for market in bm.get("markets", []):
                if market.get("key") not in ["spreads", "alternate_spreads"]:
                    continue

                values = []

                for outcome in market.get("outcomes", []):
                    team_name = outcome.get("name", "")
                    point = outcome.get("point", 0)
                    price = outcome.get("price", 0)

                    # ホーム/アウェイの判定
                    if team_name == home_team:
                        side = "Home"
                    elif team_name == away_team:
                        side = "Away"
                    else:
                        side = team_name

                    # "Home +0.25" または "Away -0.25" の形式
                    value_str = f"{side} {point:+.2f}".replace("+-", "-")

                    values.append({
                        "value": value_str,
                        "odd": str(price)
                    })

                if values:
                    bets.append({
                        "id": 4,  # Asian Handicap ID (API-Sports互換)
                        "name": "Asian Handicap",
                        "values": values
                    })

            if bets:
                bookmakers.append({
                    "id": 4,  # Pinnacle ID (API-Sports互換)
                    "name": "Pinnacle",
                    "bets": bets
                })

        result = {
            "fixture_id": event.get("id"),
            "bookmakers": bookmakers
        }

        # ログ出力
        lines_count = sum(
            len(bet.get('values', []))
            for bm in bookmakers
            for bet in bm.get('bets', [])
        )
        self.logger.debug(
            f"📤 Formatted {len(bookmakers)} bookmakers, {lines_count} total outcomes"
        )

        return result

    def _log_fetch_attempt(self, url: str, params: Dict) -> None:
        """API取得試行をログ出力"""
        self.logger.info(f"🔍 {self.get_market_name().upper()}: {url}")
        self.logger.debug(f"   Params: {params}")

    def _log_fetch_success(self, lines_count: int) -> None:
        """API取得成功をログ出力"""
        market_name = self.get_market_name()
        self.logger.info(
            f"✅ {market_name} fetched: {lines_count} outcome(s)"
        )

    def _log_fetch_error(self, error: Exception) -> None:
        """API取得エラーをログ出力"""
        market_name = self.get_market_name()
        self.logger.warning(f"❌ {market_name} fetch failed: {error}")
