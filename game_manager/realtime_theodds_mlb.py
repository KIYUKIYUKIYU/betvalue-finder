# -*- coding: utf-8 -*-
"""
The Odds API integration for MLB (Major League Baseball)
Provides fresh Pinnacle odds data with reverse team matching
"""
from .realtime_game_manager import RealtimeGameManager
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from converter.comprehensive_team_translator import ComprehensiveTeamTranslator


class RealtimeTheOddsMLBGameManager(RealtimeGameManager):
    """The Odds API implementation for MLB"""

    API_BASE = "https://api.the-odds-api.com/v4"
    SPORT_KEY = "baseball_mlb"  # MLB sport key

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, cache_dir="data/theodds_mlb", **kwargs)
        self.team_translator = ComprehensiveTeamTranslator()
        self._events_cache = {}  # Cache events to avoid redundant API calls

        # 逆引きマッチャーを初期化
        from converter.reverse_team_matcher import get_reverse_matcher
        self.reverse_matcher = get_reverse_matcher()

        # マーケット戦略を初期化 (NEW: Strategy Pattern)
        from .market_strategy_factory import MarketStrategyFactory, MarketType
        market_type = kwargs.get("market_type", MarketType.ALTERNATE_SPREADS)
        self.market_strategy, self.fallback_strategy = MarketStrategyFactory.create_with_fallback(
            market_type, self.logger
        )

    def get_sport_name(self) -> str:
        return "THEODDS_MLB"

    def _prepare_headers(self, headers: Dict) -> Dict:
        """The Odds API doesn't use headers for authentication"""
        return headers

    async def _fetch_games_async(self, date: datetime, **kwargs) -> List[Dict]:
        """
        Fetch MLB games from The Odds API
        Note: The Odds API returns games + odds in a single call
        """
        params = {
            "apiKey": self.api_key,
            "regions": "us",  # US bookmakers (MLB is primarily US-based)
            "markets": "spreads",  # Run Line
            "bookmakers": "pinnacle",  # Pinnacle only
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }

        url = f"{self.API_BASE}/sports/{self.SPORT_KEY}/odds"

        try:
            self.logger.info(f"🔍 THE ODDS API: Fetching {self.SPORT_KEY}")
            data = await self._http_get_async(url, params=params)

            # Cache events for later odds retrieval
            for event in data:
                event_id = event.get("id")
                if event_id:
                    self._events_cache[event_id] = event

            games = [self._format_game_data(event) for event in data if event]

            self.logger.info(f"🔍 THE ODDS API: {self.SPORT_KEY} → {len(games)} games")

            # Log remaining requests
            if hasattr(self, '_last_response_headers'):
                remaining = self._last_response_headers.get('x-requests-remaining')
                if remaining:
                    self.logger.info(f"📊 The Odds API requests remaining: {remaining}")

        except Exception as e:
            self.logger.error(f"❌ The Odds API fetch failed for {self.SPORT_KEY}: {e}")
            return []

        return games

    async def _fetch_odds_async(self, game_id: str, **kwargs) -> Optional[Dict]:
        """
        Fetch fresh odds for a specific MLB game using strategy pattern
        """
        self.logger.info(f"🎯 THE ODDS API _fetch_odds_async called for game_id={game_id}")
        try:
            event_id = kwargs.get("event_id", game_id)
            theodds_event = kwargs.get("_theodds_event") or self._events_cache.get(event_id)

            if not theodds_event:
                self.logger.warning(f"⚠️ No event metadata for {event_id}")
                return None

            await self._ensure_session()

            odds_data = await self.market_strategy.fetch_odds(
                session=self._session,
                api_key=self.api_key,
                sport_key=self.SPORT_KEY,
                event_id=event_id,
                regions="us",
                bookmakers="pinnacle"
            )

            if not odds_data and self.fallback_strategy:
                self.logger.info(f"🔄 PRIMARY strategy failed, trying FALLBACK strategy")
                odds_data = await self.fallback_strategy.fetch_odds(
                    session=self._session,
                    api_key=self.api_key,
                    sport_key=self.SPORT_KEY,
                    event_id=event_id,
                    regions="us",
                    bookmakers="pinnacle"
                )

            if odds_data:
                outcome_count = self._count_outcomes(odds_data)
                self.logger.info(f"✅ Odds retrieved: {outcome_count} outcome(s)")

            return odds_data

        except Exception as e:
            self.logger.warning(f"⚠️ The Odds API odds fetch failed for {game_id}: {e}")
            return None

    def match_teams(self, teams: List[str], games: List[Dict]) -> Optional[Dict]:
        """
        逆引きマッチング: APIの英語チーム名 → 日本語候補に変換してユーザー入力とマッチング
        """
        team_a_name, team_b_name = teams[0], teams[1]
        if not team_a_name or not team_b_name:
            return None

        self.logger.info(f"🔍 THE ODDS API MLB MATCH_TEAMS (REVERSE): Input teams {teams}")
        self.logger.info(f"🔍 Searching through {len(games)} available games")

        user_teams = [team_a_name, team_b_name]

        for game in games:
            home_name = game.get("home_team", "")
            away_name = game.get("away_team", "")

            if not home_name or not away_name:
                continue

            # 逆引きマッチャーを使ってマッチング
            home_matches_a = self.reverse_matcher.match(home_name, [team_a_name])
            home_matches_b = self.reverse_matcher.match(home_name, [team_b_name])
            away_matches_a = self.reverse_matcher.match(away_name, [team_a_name])
            away_matches_b = self.reverse_matcher.match(away_name, [team_b_name])

            # 両方向でチェック
            match_found = False
            if (home_matches_a and away_matches_b) or (home_matches_b and away_matches_a):
                match_found = True

            if match_found:
                match_datetime = game.get('datetime', '')
                self.logger.info(f"✅ THE ODDS API MLB SUCCESS (REVERSE): {team_a_name} vs {team_b_name} -> Game ID {game.get('id')}")
                self.logger.info(f"   Matched API: {home_name} vs {away_name}")
                self.logger.info(f"   Match Date/Time: {match_datetime}")

                home_candidates = self.reverse_matcher.get_japanese_candidates(home_name)
                away_candidates = self.reverse_matcher.get_japanese_candidates(away_name)
                self.logger.info(f"   Home candidates: {list(home_candidates)[:3]}")
                self.logger.info(f"   Away candidates: {list(away_candidates)[:3]}")

                return game

        self.logger.warning(f"❌ No match found (REVERSE) for: {team_a_name} vs {team_b_name}")
        self.logger.warning(f"   Total games searched: {len(games)}")
        return None

    def _format_game_data(self, event: Dict) -> Optional[Dict]:
        """Convert The Odds API event to standard game format"""
        try:
            return {
                "id": event.get("id"),
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "sport_key": event.get("sport_key"),
                "commence_time": event.get("commence_time"),
                "datetime": event.get("commence_time"),
                "status": "Not Started",
                "_theodds_event": event
            }
        except (KeyError, TypeError):
            return None

    def _count_outcomes(self, odds_data: Dict) -> int:
        """Count total outcomes in odds data (for logging)"""
        count = 0
        for bookmaker in odds_data.get('bookmakers', []):
            for bet in bookmaker.get('bets', []):
                count += len(bet.get('values', []))
        return count

    def fetch_games(self, date: datetime, **kwargs) -> List[Dict]:
        """Synchronous wrapper for async fetch_games"""
        return asyncio.run(self.get_games_realtime(date, **kwargs))

    def fetch_odds(self, game_id: str, **kwargs) -> Optional[Dict]:
        """Synchronous wrapper for async fetch_odds"""
        return asyncio.run(self.get_odds_realtime(game_id, **kwargs))
