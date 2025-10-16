# -*- coding: utf-8 -*-
"""
The Odds API integration for soccer odds
Provides fresh Pinnacle odds data (60-second updates for featured markets)
"""
from .realtime_game_manager import RealtimeGameManager
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from converter.comprehensive_team_translator import ComprehensiveTeamTranslator


class RealtimeTheOddsSoccerGameManager(RealtimeGameManager):
    """The Odds API implementation for soccer"""

    API_BASE = "https://api.the-odds-api.com/v4"

    # Sport key mapping: league_id → sport_key
    LEAGUE_MAPPING = {
        # Top 5 European Leagues
        "39": "soccer_epl",  # Premier League
        "140": "soccer_spain_la_liga",  # La Liga
        "78": "soccer_germany_bundesliga",  # Bundesliga
        "135": "soccer_italy_serie_a",  # Serie A
        "61": "soccer_france_ligue_one",  # Ligue 1

        # Other Major Leagues
        "2": "soccer_uefa_champs_league",  # Champions League
        "3": "soccer_uefa_europa_league",  # Europa League
        "253": "soccer_usa_mls",  # MLS
        "144": "soccer_belgium_first_div",  # Belgium First Division
        "88": "soccer_netherlands_eredivisie",  # Eredivisie
        "94": "soccer_portugal_primeira_liga",  # Primeira Liga
    }

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, cache_dir="data/theodds_soccer", **kwargs)
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
        return "THEODDS_SOCCER"

    def _prepare_headers(self, headers: Dict) -> Dict:
        """The Odds API doesn't use headers for authentication"""
        return headers

    async def _fetch_games_async(self, date: datetime, **kwargs) -> List[Dict]:
        """
        Fetch games from The Odds API
        Note: The Odds API returns games + odds in a single call
        """
        league_id = kwargs.get("league")

        # If no league specified, fetch all major leagues
        if not league_id or league_id == "None":
            self.logger.info("🌍 No league specified - fetching all major leagues")
            sport_keys = list(self.LEAGUE_MAPPING.values())
        else:
            # Map API-Sports league ID to The Odds API sport_key
            sport_key = self.LEAGUE_MAPPING.get(str(league_id))
            if not sport_key:
                self.logger.warning(f"⚠️ League ID {league_id} not supported in The Odds API")
                return []
            sport_keys = [sport_key]

        params = {
            "apiKey": self.api_key,
            "regions": "eu",  # European bookmakers
            "markets": "spreads",  # Asian Handicap only
            "bookmakers": "pinnacle",  # Pinnacle only
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }

        # Fetch games from all sport_keys
        all_games = []

        for sport_key in sport_keys:
            url = f"{self.API_BASE}/sports/{sport_key}/odds"

            try:
                self.logger.info(f"🔍 THE ODDS API: Fetching {sport_key}")
                self.logger.info(f"🔍 THE ODDS API URL: {url}")
                self.logger.info(f"🔍 THE ODDS API PARAMS: {params}")

                data = await self._http_get_async(url, params=params)

                self.logger.info(f"🔍 THE ODDS API RESPONSE TYPE: {type(data)}")
                self.logger.info(f"🔍 THE ODDS API RESPONSE LENGTH: {len(data) if isinstance(data, list) else 'N/A (not a list)'}")

                # DEBUG: Log raw API response for first event
                if data and len(data) > 0:
                    import json
                    sample_event = data[0]
                    self.logger.info(f"🔍 DEBUG RAW API EVENT: {json.dumps(sample_event, indent=2, ensure_ascii=False)}")

                # Cache events for later odds retrieval
                for event in data:
                    event_id = event.get("id")
                    if event_id:
                        self._events_cache[event_id] = event

                games = [self._format_game_data(event) for event in data if event]

                self.logger.info(f"🔍 THE ODDS API: {sport_key} → {len(games)} games")

                all_games.extend(games)

                # Log remaining requests
                if hasattr(self, '_last_response_headers'):
                    remaining = self._last_response_headers.get('x-requests-remaining')
                    if remaining:
                        self.logger.info(f"📊 The Odds API requests remaining: {remaining}")

            except Exception as e:
                self.logger.error(f"❌ The Odds API fetch failed for {sport_key}: {e}")
                continue

        self.logger.info(f"🌍 THE ODDS API TOTAL: {len(all_games)} games from {len(sport_keys)} leagues")
        return all_games

    async def _fetch_odds_async(self, game_id: str, **kwargs) -> Optional[Dict]:
        """
        Fetch fresh odds for a specific game in real-time using strategy pattern
        Makes a new API call every time to get the latest odds
        """
        self.logger.info(f"🎯 THE ODDS API _fetch_odds_async called for game_id={game_id}")
        try:
            # Extract event_id from the kwargs if available
            event_id = kwargs.get("event_id", game_id)
            self.logger.info(f"🎯 THE ODDS API event_id={event_id}")

            # Try to get event from kwargs first (passed from match_teams)
            theodds_event = kwargs.get("_theodds_event")

            if not theodds_event:
                # Fallback to cache
                theodds_event = self._events_cache.get(event_id)

            if not theodds_event:
                self.logger.warning(f"⚠️ No event metadata for {event_id}")
                return None

            sport_key = theodds_event.get("sport_key")

            # NEW: Use strategy pattern to fetch odds
            await self._ensure_session()

            # Try primary strategy
            odds_data = await self.market_strategy.fetch_odds(
                session=self._session,
                api_key=self.api_key,
                sport_key=sport_key,
                event_id=event_id,
                regions="eu",
                bookmakers="pinnacle"
            )

            # If primary strategy failed and fallback is available, try fallback
            if not odds_data and self.fallback_strategy:
                self.logger.info(f"🔄 PRIMARY strategy failed, trying FALLBACK strategy")
                odds_data = await self.fallback_strategy.fetch_odds(
                    session=self._session,
                    api_key=self.api_key,
                    sport_key=sport_key,
                    event_id=event_id,
                    regions="eu",
                    bookmakers="pinnacle"
                )

            if odds_data:
                # Count outcomes for logging
                outcome_count = self._count_outcomes(odds_data)
                self.logger.info(f"✅ Odds retrieved: {outcome_count} outcome(s)")

            return odds_data

        except Exception as e:
            self.logger.warning(f"⚠️ The Odds API odds fetch failed for {game_id}: {e}")
            return None

    def _normalize_team_name(self, team_name: str) -> str:
        """
        英語チーム名を正規化 (English team name normalization)

        Normalization rules:
        - Lowercase
        - Remove spaces, dots, hyphens, underscores
        - Remove soccer prefixes/suffixes: FC, CF, SC, AC, RC, CD, UD, SD, AD, SL, AFC, RCD
        """
        if not team_name:
            return ""

        # Lowercase
        normalized = team_name.lower().strip()

        # Remove special characters
        normalized = normalized.replace(' ', '').replace('.', '').replace('-', '').replace('_', '').replace('&', '')

        # Remove soccer prefixes/suffixes
        soccer_affixes = ['fc', 'cf', 'sc', 'ac', 'rc', 'cd', 'ud', 'sd', 'ad', 'sl', 'afc', 'rcd']
        for affix in soccer_affixes:
            if normalized.startswith(affix):
                normalized = normalized[len(affix):]
            if normalized.endswith(affix):
                normalized = normalized[:-len(affix)]

        return normalized.strip()

    def _match_normalized_english(self, teams: List[str], games: List[Dict]) -> Optional[Dict]:
        """
        英語チーム名の正規化マッチング (Normalized English team name matching)

        Strategy:
        1. Exact match after normalization
        2. Partial match (one contains the other, min 5 chars)

        Args:
            teams: User input team names (English) from STAGE1
            games: API games with English team names

        Returns:
            Matched API game object (unchanged) or None
        """
        team_a_name, team_b_name = teams[0], teams[1]

        # Normalize user input
        team_a_norm = self._normalize_team_name(team_a_name)
        team_b_norm = self._normalize_team_name(team_b_name)

        self.logger.info(f"🔤 NORMALIZED ENGLISH MATCH: {team_a_name} → {team_a_norm}, {team_b_name} → {team_b_norm}")

        for game in games:
            home_name = game.get("home_team", "")
            away_name = game.get("away_team", "")

            if not home_name or not away_name:
                continue

            # Normalize API team names
            home_norm = self._normalize_team_name(home_name)
            away_norm = self._normalize_team_name(away_name)

            # Helper: check if two normalized names match (exact or partial)
            def names_match(norm_a: str, norm_b: str) -> bool:
                if not norm_a or not norm_b:
                    return False

                # Exact match
                if norm_a == norm_b:
                    return True

                # Partial match (min 3 chars, one contains the other)
                if len(norm_a) >= 3 and len(norm_b) >= 3:
                    if norm_a in norm_b or norm_b in norm_a:
                        return True

                # Fuzzy match for typos (1-2 char difference, min 6 chars)
                if len(norm_a) >= 6 and len(norm_b) >= 6:
                    # Simple Levenshtein distance check (allow 1-2 char difference)
                    from difflib import SequenceMatcher
                    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
                    if ratio >= 0.85:  # 85% similarity
                        return True

                return False

            # Check both directions: (home=A and away=B) or (home=B and away=A)
            match_found = False

            if names_match(home_norm, team_a_norm) and names_match(away_norm, team_b_norm):
                match_found = True
            elif names_match(home_norm, team_b_norm) and names_match(away_norm, team_a_norm):
                match_found = True

            if match_found:
                match_datetime = game.get('datetime', '')
                self.logger.info(f"✅ THE ODDS API SUCCESS (NORMALIZED): {team_a_name} vs {team_b_name} -> Game ID {game.get('id')}")
                self.logger.info(f"   Matched API: {home_name} vs {away_name}")
                self.logger.info(f"   Normalized: {home_norm} vs {away_norm}")
                self.logger.info(f"   Match Date/Time: {match_datetime}")

                return game  # Return unchanged API game object

        return None

    def match_teams(self, teams: List[str], games: List[Dict]) -> Optional[Dict]:
        """
        マルチレイヤーマッチング: 英語正規化 → 逆引き日本語フォールバック
        Multi-layer matching: Normalized English → Reverse Japanese fallback

        契約不変 (Contract unchanged):
        - Input: teams (List[str]), games (List[Dict])
        - Output: Optional[Dict] - unchanged API game object
        """
        team_a_name, team_b_name = teams[0], teams[1]
        if not team_a_name or not team_b_name:
            return None

        self.logger.info(f"🔍 THE ODDS API MATCH_TEAMS: Input teams {teams}")
        self.logger.info(f"🔍 Searching through {len(games)} available games")

        # Layer 1: 英語正規化マッチング (優先)
        matched = self._match_normalized_english(teams, games)
        if matched:
            return matched

        # Layer 2: 逆引きマッチング (フォールバック)
        self.logger.info(f"🔄 Falling back to REVERSE MATCHER (Japanese-based matching)")

        user_teams = [team_a_name, team_b_name]

        for game in games:
            home_name = game.get("home_team", "")
            away_name = game.get("away_team", "")

            if not home_name or not away_name:
                continue

            # 逆引きマッチャーを使ってマッチング
            # home と team_a OR team_b がマッチし、away と残りのチームがマッチするか確認
            home_matches_a = self.reverse_matcher.match(home_name, [team_a_name])
            home_matches_b = self.reverse_matcher.match(home_name, [team_b_name])
            away_matches_a = self.reverse_matcher.match(away_name, [team_a_name])
            away_matches_b = self.reverse_matcher.match(away_name, [team_b_name])

            # 両方向でチェック: (home=A and away=B) or (home=B and away=A)
            match_found = False
            if (home_matches_a and away_matches_b) or (home_matches_b and away_matches_a):
                match_found = True

            if match_found:
                match_datetime = game.get('datetime', '')
                self.logger.info(f"✅ THE ODDS API SUCCESS (REVERSE): {team_a_name} vs {team_b_name} -> Game ID {game.get('id')}")
                self.logger.info(f"   Matched API: {home_name} vs {away_name}")
                self.logger.info(f"   Match Date/Time: {match_datetime}")

                # デバッグ: 日本語候補を表示
                home_candidates = self.reverse_matcher.get_japanese_candidates(home_name)
                away_candidates = self.reverse_matcher.get_japanese_candidates(away_name)
                self.logger.info(f"   Home candidates: {list(home_candidates)[:3]}")
                self.logger.info(f"   Away candidates: {list(away_candidates)[:3]}")

                return game

        self.logger.warning(f"❌ No match found for: {team_a_name} vs {team_b_name}")
        self.logger.warning(f"   Normalized search terms: '{team_a_norm}' vs '{team_b_norm}'")
        self.logger.warning(f"   Total games searched: {len(games)}")

        # デバッグ: 最初の5試合を表示
        self.logger.warning(f"   First 5 API games:")
        for i, game in enumerate(games[:5], 1):
            home = game.get('home_team', 'N/A')
            away = game.get('away_team', 'N/A')
            home_norm = self._normalize_team_name(home)
            away_norm = self._normalize_team_name(away)
            self.logger.warning(f"     {i}. {home} vs {away}")
            self.logger.warning(f"        Normalized: {home_norm} vs {away_norm}")

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
                "status": "Not Started",  # The Odds API doesn't provide status
                "_theodds_event": event  # Store complete event for odds retrieval
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
