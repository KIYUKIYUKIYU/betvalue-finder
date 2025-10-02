# -*- coding: utf-8 -*-
from .realtime_game_manager import RealtimeGameManager
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from converter.comprehensive_team_translator import ComprehensiveTeamTranslator

class RealtimeSoccerGameManager(RealtimeGameManager):
    API_BASE = "https://v3.football.api-sports.io"

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, cache_dir="data/soccer", **kwargs)
        self.team_translator = ComprehensiveTeamTranslator()

    def get_sport_name(self) -> str:
        return "SOCCER"

    def _prepare_headers(self, headers: Dict) -> Dict:
        headers["x-apisports-key"] = self.api_key
        return headers

    async def _fetch_games_async(self, date: datetime, **kwargs) -> List[Dict]:
        params = {"date": date.strftime("%Y-%m-%d"), "timezone": "Asia/Tokyo"}
        if kwargs.get("league"):
            params["league"] = str(kwargs.get("league"))
        url = f"{self.API_BASE}/fixtures"
        data = await self._http_get_async(url, params=params)
        return [self._format_game_data(g) for g in data.get("response", []) if g]

    async def _fetch_odds_async(self, game_id: str, **kwargs) -> Optional[Dict]:
        try:
            params = {"fixture": game_id, "bookmaker": "4"} # Pinnacle Only
            url = f"{self.API_BASE}/odds"
            data = await self._http_get_async(url, params=params)
            res = data.get("response", [])
            return self._format_odds_data(res[0]) if res else None
        except Exception as e:
            self.logger.warning(f"⚠️ Soccer odds API failed for {game_id}: {e}")
            return None

    def match_teams(self, teams: List[str], games: List[Dict]) -> Optional[Dict]:
        """Enhanced team matching with special character normalization and city mappings"""
        team_a_name, team_b_name = teams[0], teams[1]
        if not team_a_name or not team_b_name:
            return None

        def normalize_team_name(s: str) -> str:
            """Enhanced normalization using ComprehensiveTeamTranslator"""
            if not s:
                return ""

            # First try comprehensive translation
            translated = self.team_translator.translate_if_needed(s)

            # Convert to lowercase
            result = translated.lower()

            # Normalize special characters (ü -> u, ä -> a, ö -> o, etc.)
            char_map = {
                'ü': 'u', 'ä': 'a', 'ö': 'o', 'ß': 'ss',
                'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
                'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
                'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
                'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
                'ú': 'u', 'ù': 'u', 'û': 'u', 'ç': 'c',
                'ñ': 'n'
            }

            for special_char, normal_char in char_map.items():
                result = result.replace(special_char, normal_char)

            # Remove common soccer team suffixes/prefixes
            soccer_suffixes = ['fc', 'cf', 'sc', 'ac', 'rc', 'cd', 'ud', 'sd', 'ad', 'sl']
            soccer_prefixes = ['rcd', 'real', 'club', 'cf', 'fc', 'sl']

            # Split into words
            words = result.split()
            filtered_words = []

            for word in words:
                # Remove dots, hyphens, underscores
                clean_word = word.replace('.', '').replace('-', '').replace('_', '')

                # Skip common suffixes and standalone prefixes
                if clean_word not in soccer_suffixes and clean_word not in soccer_prefixes:
                    filtered_words.append(clean_word)

            # Join back and remove any remaining spaces
            return ''.join(filtered_words)

        self.logger.info(f"🔍 REALTIME SOCCER MATCH_TEAMS: 入力チーム名 {teams}")

        # Normalize team names
        norm_a = normalize_team_name(team_a_name)
        norm_b = normalize_team_name(team_b_name)

        self.logger.info(f"🔍 REALTIME SOCCER NORMALIZED: '{team_a_name}' → '{norm_a}', '{team_b_name}' → '{norm_b}'")

        # Enhanced matching using ComprehensiveTeamTranslator
        def check_team_match(parsed_team, api_team):
            """Enhanced team matching using comprehensive translation"""
            norm_parsed = normalize_team_name(parsed_team)
            norm_api = normalize_team_name(api_team)

            self.logger.debug(f"   Comparing: '{parsed_team}' → '{norm_parsed}' vs '{api_team}' → '{norm_api}'")

            # 1. Exact match
            if norm_parsed == norm_api:
                self.logger.debug(f"   ✅ Exact match: {norm_parsed}")
                return True

            # 2. Check if either team contains the other (minimum 3 chars to avoid false positives)
            if len(norm_parsed) >= 3 and len(norm_api) >= 3:
                if norm_parsed in norm_api or norm_api in norm_parsed:
                    self.logger.debug(f"   ✅ Partial match: '{norm_parsed}' <-> '{norm_api}'")
                    return True

            # 3. Check without suffixes for better matching (e.g. "sittard" should match "fortuna sittard")
            if len(norm_parsed) >= 4 and len(norm_api) >= 4:
                # Split both names and check for word overlap
                parsed_words = norm_parsed.split() if ' ' in norm_parsed else [norm_parsed]
                api_words = norm_api.split() if ' ' in norm_api else [norm_api]

                for p_word in parsed_words:
                    if len(p_word) >= 4:  # Only check meaningful words
                        for a_word in api_words:
                            if len(a_word) >= 4 and (p_word in a_word or a_word in p_word):
                                self.logger.debug(f"   ✅ Word match: '{p_word}' <-> '{a_word}'")
                                return True

            return False

        # Try enhanced matching
        for game in games:
            home_name = game.get("home", "")
            away_name = game.get("away", "")

            # Check both orientations
            if ((check_team_match(team_a_name, home_name) and check_team_match(team_b_name, away_name)) or
                (check_team_match(team_a_name, away_name) and check_team_match(team_b_name, home_name))):
                self.logger.info(f"✅ REALTIME SOCCER SUCCESS: {team_a_name} vs {team_b_name} -> Game ID {game.get('id')}")
                self.logger.info(f"   Matched API: {home_name} vs {away_name}")
                return game

        self.logger.warning(f"❌ No match found for: {team_a_name} vs {team_b_name}")
        return None

    def _format_game_data(self, d: Dict) -> Optional[Dict]:
        try:
            return {"id": d["fixture"]["id"], "home": d["teams"]["home"]["name"], "away": d["teams"]["away"]["name"], "datetime": d["fixture"]["date"]}
        except (KeyError, TypeError): return None

    def _format_odds_data(self, d: Dict) -> Dict:
        return {"fixture_id": d.get("fixture", {}).get("id"), "bookmakers": d.get("bookmakers", [])}


    def fetch_games(self, date: datetime, **kwargs) -> List[Dict]:
        return asyncio.run(self.get_games_realtime(date, **kwargs))

    def fetch_odds(self, game_id: str, **kwargs) -> Optional[Dict]:
        return asyncio.run(self.get_odds_realtime(game_id, **kwargs))
