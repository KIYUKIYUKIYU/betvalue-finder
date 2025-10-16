# -*- coding: utf-8 -*-
"""
AlternateSpreadsStrategy: alternate_spreadsマーケット戦略（新方式）

特徴:
- エンドポイント: /v4/sports/{sport}/events/{eventId}/odds
- マーケット: alternate_spreads
- 結果: 複数ライン（18～22アウトカム）
- 用途: 線形補間を不要にする高精度EV計算

ライン数の目安:
- サッカー: 18アウトカム（-1.5 ~ +1.5、0.25刻み、9種類×2チーム）
- NBA: 22アウトカム（-10.0 ~ +10.0、0.5刻み、11種類×2チーム）
- MLB/NPB: スポーツ依存
"""

from typing import Dict, Optional
import aiohttp
import logging
from .market_strategy import MarketStrategy


class AlternateSpreadsStrategy(MarketStrategy):
    """alternate_spreadsマーケット戦略（新規: 複数ライン）"""

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
        alternate_spreadsマーケットからオッズを取得

        エンドポイント: /v4/sports/{sport}/events/{eventId}/odds
        結果: 複数ライン（18～22アウトカム）

        Args:
            session: aiohttpセッション
            api_key: The Odds API キー
            sport_key: スポーツキー
            event_id: イベントID
            **kwargs: 追加パラメータ

        Returns:
            API-Sports互換形式のオッズデータ、またはNone
        """
        # イベント単位のエンドポイント
        url = f"{self.api_base}/sports/{sport_key}/events/{event_id}/odds"
        params = {
            "apiKey": api_key,
            "regions": kwargs.get("regions", "us"),
            "markets": "alternate_spreads",  # ← 複数ライン取得
            "bookmakers": kwargs.get("bookmakers", "pinnacle"),
            "oddsFormat": "decimal",
            "dateFormat": "iso"
        }

        self._log_fetch_attempt(url, {**params, "apiKey": "***"})

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    event = await response.json()

                    # イベント単位エンドポイントは直接イベントオブジェクトを返す
                    if not event or not isinstance(event, dict):
                        self.logger.warning(
                            f"⚠️ Invalid response format for event {event_id}"
                        )
                        return None

                    # ホーム/アウェイチーム名を取得
                    home_team = event.get("home_team", "")
                    away_team = event.get("away_team", "")

                    if not home_team or not away_team:
                        self.logger.warning(
                            f"⚠️ Missing team names in event {event_id}"
                        )
                        return None

                    # ブックメーカーデータの確認
                    bookmakers = event.get("bookmakers", [])
                    if not bookmakers:
                        self.logger.warning(
                            f"⚠️ No bookmakers data for event {event_id}"
                        )
                        return None

                    # フォーマット変換
                    odds_data = self._format_odds_data(event, home_team, away_team)

                    # ログ出力
                    lines_count = self._count_outcomes(odds_data)
                    self._log_fetch_success(lines_count)

                    # 品質チェック
                    if lines_count < 10:
                        self.logger.warning(
                            f"⚠️ Unexpectedly low outcome count ({lines_count}) for alternate_spreads"
                        )

                    return odds_data

                elif response.status == 422:
                    # alternate_spreads未対応のスポーツ/リーグ
                    error_text = await response.text()
                    self.logger.warning(
                        f"⚠️ alternate_spreads not supported for {sport_key}: {error_text}"
                    )
                    return None

                else:
                    self.logger.warning(
                        f"⚠️ API returned status {response.status} for event {event_id}"
                    )
                    return None

        except aiohttp.ClientError as e:
            self._log_fetch_error(e)
            return None
        except Exception as e:
            self.logger.error(
                f"❌ Unexpected error fetching alternate_spreads for {event_id}: {e}",
                exc_info=True
            )
            return None

    def get_market_name(self) -> str:
        """マーケット名を返す"""
        return "alternate_spreads"

    def supports_multiple_lines(self) -> bool:
        """複数ライン対応か（True: 複数ライン）"""
        return True

    def _count_outcomes(self, odds_data: Dict) -> int:
        """オッズデータ内のアウトカム数をカウント"""
        count = 0
        for bookmaker in odds_data.get('bookmakers', []):
            for bet in bookmaker.get('bets', []):
                count += len(bet.get('values', []))
        return count
