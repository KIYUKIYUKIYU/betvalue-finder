# -*- coding: utf-8 -*-
"""
SimpleSpreadsStrategy: spreadsマーケット戦略（現行方式）

特徴:
- エンドポイント: /v4/sports/{sport}/odds
- マーケット: spreads
- 結果: 各試合1ライン（2アウトカム）
- 用途: 後方互換性、フォールバック
"""

from typing import Dict, Optional
import aiohttp
import logging
from .market_strategy import MarketStrategy


class SimpleSpreadsStrategy(MarketStrategy):
    """spreadsマーケット戦略（現行: 1ライン）"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)

    async def fetch_odds(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        sport_key: str,
        event_id: str,
        **kwargs
    ) -> Optional[Dict]:
        """
        spreadsマーケットからオッズを取得

        エンドポイント: /v4/sports/{sport}/odds?eventIds={event_id}
        結果: 1ライン（2アウトカム）のみ

        Args:
            session: aiohttpセッション
            api_key: The Odds API キー
            sport_key: スポーツキー
            event_id: イベントID
            **kwargs: 追加パラメータ

        Returns:
            API-Sports互換形式のオッズデータ、またはNone
        """
        url = f"{self.api_base}/sports/{sport_key}/odds"
        params = {
            "apiKey": api_key,
            "regions": kwargs.get("regions", "us"),
            "markets": "spreads",
            "bookmakers": kwargs.get("bookmakers", "pinnacle"),
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "eventIds": event_id  # 特定イベントのみ取得
        }

        self._log_fetch_attempt(url, {**params, "apiKey": "***"})

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if not data or len(data) == 0:
                        self.logger.warning(
                            f"⚠️ No data returned for event {event_id}"
                        )
                        return None

                    # 最初のイベント（eventIds指定なので1つのみ）
                    event = data[0]

                    # ホーム/アウェイチーム名を取得
                    home_team = event.get("home_team", "")
                    away_team = event.get("away_team", "")

                    if not home_team or not away_team:
                        self.logger.warning(
                            f"⚠️ Missing team names in event {event_id}"
                        )
                        return None

                    # フォーマット変換
                    odds_data = self._format_odds_data(event, home_team, away_team)

                    # ログ出力
                    lines_count = self._count_outcomes(odds_data)
                    self._log_fetch_success(lines_count)

                    return odds_data

                else:
                    self.logger.warning(
                        f"⚠️ API returned status {response.status} for event {event_id}"
                    )
                    return None

        except Exception as e:
            self._log_fetch_error(e)
            return None

    def get_market_name(self) -> str:
        """マーケット名を返す"""
        return "spreads"

    def supports_multiple_lines(self) -> bool:
        """複数ライン対応か（False: 1ラインのみ）"""
        return False

    def _count_outcomes(self, odds_data: Dict) -> int:
        """オッズデータ内のアウトカム数をカウント"""
        count = 0
        for bookmaker in odds_data.get('bookmakers', []):
            for bet in bookmaker.get('bets', []):
                count += len(bet.get('values', []))
        return count
