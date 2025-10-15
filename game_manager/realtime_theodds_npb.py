# -*- coding: utf-8 -*-
"""
The Odds API integration for NPB (Nippon Professional Baseball) odds
Provides fresh Pinnacle odds data for Japanese baseball
"""
from .realtime_game_manager import RealtimeGameManager
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from converter.comprehensive_team_translator import ComprehensiveTeamTranslator


class RealtimeTheOddsNPBGameManager(RealtimeGameManager):
    """The Odds API implementation for NPB"""

    API_BASE = "https://api.the-odds-api.com/v4"
    SPORT_KEY = "baseball_npb"

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, cache_dir="data/theodds_npb", **kwargs)
        self.team_translator = ComprehensiveTeamTranslator()
        self._events_cache = {}  # Cache events to avoid redundant API calls

        # 逆引きマッチャーを初期化
        from converter.reverse_team_matcher import get_reverse_matcher
        self.reverse_matcher = get_reverse_matcher()

    def get_sport_name(self) -> str:
        return "THEODDS_NPB"

    def _prepare_headers(self, headers: Dict) -> Dict:
        """The Odds API doesn't use headers for authentication"""
        return headers

    async def _fetch_games_async(self, date: datetime, **kwargs) -> List[Dict]:
        """
        Fetch NPB games from The Odds API
        Note: The Odds API returns games + odds in a single call
        """
        url = f"{self.API_BASE}/sports/{self.SPORT_KEY}/odds"

        params = {
            "apiKey": self.api_key,
            "regions": "eu",  # European bookmakers
            "markets": "spreads",  # Asian Handicap only
            "bookmakers": "pinnacle",  # Pinnacle only
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }

        try:
            self.logger.info(f"🔍 THE ODDS API (NPB): Fetching {self.SPORT_KEY}")
            self.logger.info(f"🔍 THE ODDS API URL: {url}")
            self.logger.info(f"🔍 THE ODDS API PARAMS: {params}")

            data = await self._http_get_async(url, params=params)

            self.logger.info(f"🔍 THE ODDS API RESPONSE TYPE: {type(data)}")
            self.logger.info(f"🔍 THE ODDS API RESPONSE LENGTH: {len(data) if isinstance(data, list) else 'N/A (not a list)'}")

            # DEBUG: Log raw API response for first event
            if data and len(data) > 0:
                import json
                sample_event = data[0]
                self.logger.info(f"🔍 DEBUG RAW API EVENT (NPB): {json.dumps(sample_event, indent=2, ensure_ascii=False)}")

            # Cache events for later odds retrieval
            for event in data:
                event_id = event.get("id")
                if event_id:
                    self._events_cache[event_id] = event

            games = [self._format_game_data(event) for event in data if event]

            self.logger.info(f"🔍 THE ODDS API (NPB): {len(games)} games")

            # Log remaining requests
            if hasattr(self, '_last_response_headers'):
                remaining = self._last_response_headers.get('x-requests-remaining')
                if remaining:
                    self.logger.info(f"📊 The Odds API requests remaining: {remaining}")

            return games

        except Exception as e:
            self.logger.error(f"❌ The Odds API fetch failed for NPB: {e}")
            return []

    async def _fetch_odds_async(self, game_id: str, **kwargs) -> Optional[Dict]:
        """
        Fetch fresh odds for a specific NPB game in real-time
        Makes a new API call every time to get the latest odds
        """
        self.logger.info(f"🎯 THE ODDS API (NPB) _fetch_odds_async called for game_id={game_id}")
        try:
            # Extract event_id from the kwargs if available
            # The event_id is The Odds API's UUID format
            event_id = kwargs.get("event_id", game_id)
            self.logger.info(f"🎯 THE ODDS API (NPB) event_id={event_id}")

            # Try to get event from kwargs first (passed from match_teams)
            theodds_event = kwargs.get("_theodds_event")

            if not theodds_event:
                # Fallback to cache
                theodds_event = self._events_cache.get(event_id)

            if not theodds_event:
                self.logger.warning(f"⚠️ No event metadata for {event_id}")
                return None

            sport_key = theodds_event.get("sport_key")

            # Make fresh API call for latest odds
            url = f"{self.API_BASE}/sports/{sport_key}/odds"

            params = {
                "apiKey": self.api_key,
                "regions": "eu",
                "markets": "spreads",
                "bookmakers": "pinnacle",
                "oddsFormat": "decimal",
                "dateFormat": "iso",
                "eventIds": event_id  # Fetch only this specific event
            }

            self.logger.info(f"🔄 THE ODDS API (NPB): Fetching fresh odds for event {event_id}")

            data = await self._http_get_async(url, params=params)

            if not data or len(data) == 0:
                self.logger.warning(f"⚠️ No fresh odds data returned for event {event_id}")
                return None

            # Get the first (and only) event from response
            fresh_event = data[0]

            # Convert to API-Sports format for compatibility
            odds_data = self._format_odds_data(fresh_event)

            return odds_data

        except Exception as e:
            self.logger.error(f"❌ Error fetching odds for NPB game {game_id}: {e}")
            return None

    def _format_odds_data(self, event: Dict) -> Dict:
        """
        Convert The Odds API format to API-Sports format for compatibility
        Same as Soccer implementation
        """
        bookmakers = []

        for bm in event.get("bookmakers", []):
            if bm.get("key") != "pinnacle":
                continue

            bets = []

            for market in bm.get("markets", []):
                if market.get("key") != "spreads":
                    continue

                values = []
                home_team = event.get("home_team", "")
                away_team = event.get("away_team", "")

                for outcome in market.get("outcomes", []):
                    team_name = outcome.get("name", "")
                    point = outcome.get("point", 0)
                    price = outcome.get("price", 0)

                    # Determine if this is Home or Away
                    if team_name == home_team:
                        side = "Home"
                    elif team_name == away_team:
                        side = "Away"
                    else:
                        side = team_name

                    # Format as "Home +0.25" or "Away -0.25"
                    value_str = f"{side} {point:+.2f}".replace("+-", "-")

                    values.append({
                        "value": value_str,
                        "odd": str(price)
                    })

                if values:
                    bets.append({
                        "id": 4,  # Asian Handicap ID in API-Sports
                        "name": "Asian Handicap",
                        "values": values
                    })

            if bets:
                bookmakers.append({
                    "id": 4,  # Pinnacle ID in API-Sports
                    "name": "Pinnacle",
                    "bets": bets
                })

        result = {
            "fixture_id": event.get("id"),
            "bookmakers": bookmakers
        }

        self.logger.info(f"📤 THE ODDS API (NPB) _format_odds_data returning {len(bookmakers)} bookmakers")

        return result

    def _format_game_data(self, event: Dict) -> Dict:
        """
        Format The Odds API event data into our internal format

        The Odds API format:
        {
            "id": "uuid",
            "sport_key": "baseball_npb",
            "home_team": "Hanshin Tigers",
            "away_team": "Yokohama DeNA BayStars",
            "commence_time": "2025-10-15T09:00:00Z",
            "bookmakers": [...]
        }
        """
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        commence_time = event.get("commence_time", "")
        event_id = event.get("id", "")
        sport_key = event.get("sport_key", self.SPORT_KEY)

        # Parse commence_time
        try:
            game_datetime = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            date_str = game_datetime.strftime("%Y-%m-%d")
            time_str = game_datetime.strftime("%H:%M")
        except:
            date_str = ""
            time_str = ""

        # Format into our internal structure
        game = {
            "game_id": event_id,
            "event_id": event_id,
            "sport_key": sport_key,
            "home": home_team,
            "away": away_team,
            "date": date_str,
            "time": time_str,
            "commence_time": commence_time,
            "status": "scheduled",
            "_theodds_event": event,  # Store raw event for later odds retrieval
            "raw": event,  # Also store in raw field for compatibility
        }

        self.logger.debug(f"🏟️ NPB GAME: {home_team} vs {away_team} @ {date_str} {time_str}")

        return game

    def match_teams(self, parsed_game: Dict, api_games: List[Dict]) -> Optional[Dict]:
        """
        Match parsed game with API game data

        Args:
            parsed_game: パーサーからの試合データ
            api_games: APIから取得した試合データのリスト

        Returns:
            マッチした試合データ、見つからない場合はNone
        """
        parsed_home = parsed_game.get("team_a", "").strip()
        parsed_away = parsed_game.get("team_b", "").strip()

        self.logger.info(f"🔍 NPB MATCHING: '{parsed_home}' vs '{parsed_away}'")

        # Convert parsed team names (Japanese) to English using reverse_matcher
        home_english = self.reverse_matcher.get_english_name(parsed_home)
        away_english = self.reverse_matcher.get_english_name(parsed_away)

        self.logger.info(f"🔄 Home English: {home_english}")
        self.logger.info(f"🔄 Away English: {away_english}")

        if not home_english or not away_english:
            self.logger.warning(f"❌ NPB NO ENGLISH MAPPING: {parsed_home} -> {home_english}, {parsed_away} -> {away_english}")
            return None

        # Try to match with API games
        for game in api_games:
            api_home = game.get("home", "").strip().lower()
            api_away = game.get("away", "").strip().lower()

            self.logger.debug(f"  Comparing with API: {api_home} vs {api_away}")

            # Check if English names match API names
            home_match = home_english.lower() in api_home or api_home in home_english.lower()
            away_match = away_english.lower() in api_away or api_away in away_english.lower()

            if home_match and away_match:
                self.logger.info(f"✅ NPB MATCH FOUND: {api_home} vs {api_away}")
                return game

        self.logger.warning(f"❌ NPB NO MATCH: {parsed_home} vs {parsed_away}")
        return None

    def fetch_games(self, date: datetime, **kwargs) -> List[Dict]:
        """Synchronous wrapper for async fetch_games"""
        return asyncio.run(self.get_games_realtime(date, **kwargs))

    def fetch_odds(self, game_id: str, **kwargs) -> Optional[Dict]:
        """Synchronous wrapper for async fetch_odds"""
        return asyncio.run(self.get_odds_realtime(game_id, **kwargs))
