from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from .base import GameManager
from converter.soccer_team_names import normalize_soccer_team
from converter.team_fuzzy_matcher import TeamFuzzyMatcher

class SoccerGameManager(GameManager):
    API_BASE = "https://v3.football.api-sports.io"
    
    # ヨーロッパサッカーパック（主要1部リーグ全網羅）
    EUROPEAN_LEAGUES = [
        39,   # Premier League (England)
        140,  # La Liga (Spain) 
        78,   # Bundesliga (Germany)
        135,  # Serie A (Italy)
        61,   # Ligue 1 (France)
        94,   # Primeira Liga (Portugal)
        144,  # Jupiler Pro League (Belgium)
        88,   # Eredivisie (Netherlands)
        203,  # Super Lig (Turkey)
        197,  # Greek Super League
        218,  # Swiss Super League
        179,  # Austrian Bundesliga
        113,  # Eliteserien (Norway)
        116,  # Danish Superliga
        119,  # Allsvenskan (Sweden)
        244,  # Czech First League
        106,  # Polish Ekstraklasa
        345,  # Ukrainian Premier League
        327,  # Russian Premier League
        317,  # Croatian First League
    ]
    
    # Jリーグ専用パック（地名重複対応のため分離）
    J_LEAGUE = [
        98,   # J1 League
        99,   # J2 League
        100,  # J3 League
    ]
    
    # 国際大会
    INTERNATIONAL = [
        1,    # World Cup
        4,    # UEFA Nations League
        5,    # UEFA Euro Championship
        9,    # Copa America
        10,   # World Cup Qualification Europe
        11,   # World Cup Qualification South America
        2,    # UEFA Champions League
        961,  # UEFA Europa League
        848,  # UEFA Europa Conference League
    ]
    
    # 全リーグ統合（デフォルト）
    LEAGUES_DEFAULT = EUROPEAN_LEAGUES + J_LEAGUE + INTERNATIONAL

    def __init__(self, api_key: str):
        super().__init__(api_key, cache_dir="data/soccer")
        self.fuzzy_matcher = TeamFuzzyMatcher(threshold=0.6)
    
    def fetch_european_games(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        """ヨーロッパサッカーパック専用"""
        return self.fetch_games(date, timezone=timezone, leagues=self.EUROPEAN_LEAGUES, **kwargs)
    
    def fetch_jleague_games(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        """Jリーグ専用パック"""
        return self.fetch_games(date, timezone=timezone, leagues=self.J_LEAGUE, **kwargs)
    
    def fetch_international_games(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        """国際大会"""
        return self.fetch_games(date, timezone=timezone, leagues=self.INTERNATIONAL, **kwargs)
    
    # プリゲーム専用メソッド
    def fetch_pregame_european_games(self, date: datetime, timezone: str = "Asia/Tokyo", buffer_minutes: int = 30, **kwargs) -> List[Dict]:
        """ヨーロッパサッカーパック（プリゲームのみ）"""
        games = self.fetch_european_games(date, timezone=timezone, **kwargs)
        from .pregame_filter import PregameFilter
        return PregameFilter.filter_pregame_games(games, buffer_minutes)
    
    def fetch_pregame_jleague_games(self, date: datetime, timezone: str = "Asia/Tokyo", buffer_minutes: int = 30, **kwargs) -> List[Dict]:
        """Jリーグ（プリゲームのみ）"""
        games = self.fetch_jleague_games(date, timezone=timezone, **kwargs)
        from .pregame_filter import PregameFilter
        return PregameFilter.filter_pregame_games(games, buffer_minutes)

    def get_sport_name(self) -> str:
        return "SOCCER"

    def _prepare_headers(self, headers: Dict) -> Dict:
        headers["x-apisports-key"] = self.api_key
        return headers

    def fetch_games(
        self,
        date: datetime,
        timezone: str = "Asia/Tokyo",
        leagues: Optional[List[int]] = None,
        **kwargs,
    ) -> List[Dict]:
        if leagues is None:
            leagues = self.LEAGUES_DEFAULT

        date_str = date.strftime("%Y-%m-%d")
        url = f"{self.API_BASE}/fixtures"
        params = {"date": date_str, "timezone": timezone}
        try:
            response = self.http_get(url, params=params)
            data = response.json()
            fixtures = data.get("response", [])
            games: List[Dict] = []
            for fx in fixtures:
                g = self._format_fixture(fx)
                if not g:
                    continue
                if leagues and g.get("league_id") not in leagues:
                    continue
                games.append(g)
            cache_data = {
                "sport": "soccer",
                "fetch_date": date_str,
                "fetch_time": datetime.now().isoformat(),
                "timezone": timezone,
                "games": games,
            }
            filename = f"games_{date_str.replace('-', '')}.json"
            self.save_cache(cache_data, filename)
            print(f"✅ Fetched {len(games)} SOCCER games for {date_str}")
            return games
        except Exception as e:
            print(f"❌ Failed to fetch soccer fixtures: {e}")
            return []

    def _format_fixture(self, fx: Dict) -> Optional[Dict]:
        try:
            fixture = fx.get("fixture", {})
            teams = fx.get("teams", {})
            league = fx.get("league", {})
            game_id = fixture.get("id")
            home_team = teams.get("home", {}).get("name", "")
            away_team = teams.get("away", {}).get("name", "")
            home_jp = normalize_soccer_team(home_team, to_english=False)
            away_jp = normalize_soccer_team(away_team, to_english=False)
            datetime_str = fixture.get("date") or ""
            return {
                "id": game_id,
                "home": home_team,
                "away": away_team,
                "home_jp": home_jp,
                "away_jp": away_jp,
                "datetime": datetime_str,
                "league": league.get("name", ""),
                "league_id": league.get("id"),
                "status": fixture.get("status", {}).get("long", ""),
                "raw": fx,
            }
        except Exception as e:
            print(f"⚠️ Failed to format soccer fixture: {e}")
            return None

    def fetch_odds(
        self,
        game_id: str,
        bookmaker_ids: Optional[List[int]] = None,
        ttl_seconds: int = 120,
    ) -> Optional[Dict]:
        if bookmaker_ids is None:
            bookmaker_ids = [11]  # Pinnacle (API-Football)
        cache_path = os.path.join(self.cache_dir, f"odds_{game_id}.json")
        if os.path.exists(cache_path):
            try:
                import json as _json
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = _json.load(f)
                ts = cached.get("fetch_time")
                if ts:
                    t = datetime.fromisoformat(ts)
                    if datetime.now() - t <= timedelta(seconds=ttl_seconds):
                        return cached
            except Exception:
                pass
        url = f"{self.API_BASE}/odds"
        params = {"fixture": game_id}
        try:
            response = self.http_get(url, params=params)
            data = response.json()
            entries = data.get("response", [])
            if not entries:
                print(f"⚠️ No soccer odds for fixture {game_id}")
                return None
            entry = entries[0]
            filtered = []
            for bm in entry.get("bookmakers", []):
                try:
                    bid = int(bm.get("id", -1))
                except Exception:
                    bid = -1
                if bid in bookmaker_ids:
                    filtered.append(bm)
            if not filtered:
                filtered = entry.get("bookmakers", [])
            result = {
                "game_id": game_id,
                "bookmakers": filtered,
                "fetch_time": datetime.now().isoformat(),
            }
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                import json as _json
                with open(cache_path, "w", encoding="utf-8") as f:
                    _json.dump(result, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return result
        except Exception as e:
            print(f"❌ Failed to fetch soccer odds for fixture {game_id}: {e}")
            return None

    def match_teams(self, teams: List[str], games: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        チーム名マッチング: 従来方式 + ファジーマッチング フォールバック
        """
        def norm(s: str) -> str:
            """Enhanced normalization for soccer team names"""
            if not s:
                return ""

            # Convert to lowercase
            result = s.lower()

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

            # City name mappings for soccer teams
            city_map = {
                'münchen': 'munich',
                'munchen': 'munich',
            }

            for city, english_city in city_map.items():
                result = result.replace(city, english_city)

            # Remove common soccer team suffixes/prefixes
            soccer_suffixes = ['fc', 'cf', 'sc', 'ac', 'rc', 'cd', 'ud', 'sd', 'ad']
            soccer_prefixes = ['rcd', 'real', 'club', 'cf', 'fc']

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

        if games is None:
            games = self.load_latest_cache()
            if not games:
                return None

        print(f"🔍 MATCH_TEAMS: 入力チーム名 {teams}")
        print(f"🔍 SOCCER GAME MANAGER: match_teams method called!")

        # Debug: show first few API games for context
        print(f"🔍 Available API games: {len(games)} total")
        if games:
            for i, game in enumerate(games[:3]):
                home = game.get('home', 'N/A')
                away = game.get('away', 'N/A')
                print(f"  Sample {i+1}: {home} vs {away}")

        # 1. 従来方式（完全一致）を試行
        ta_jp, tb_jp = teams[0], teams[1]

        # 曖昧なチーム名の検出（マンチェスター等）
        ambiguous_teams = {"マンチェスター", "manchester"}
        ta_is_ambiguous = ta_jp.lower() in ambiguous_teams
        tb_is_ambiguous = tb_jp.lower() in ambiguous_teams

        if ta_is_ambiguous or tb_is_ambiguous:
            print(f"🔍 AMBIGUOUS TEAM DETECTED: {ta_jp if ta_is_ambiguous else tb_jp}")
            # 組み合わせベースマッチングを優先
            combination_result = self._match_by_combination(teams, games)
            if combination_result:
                print(f"✅ COMBINATION SUCCESS: {combination_result.get('home')} vs {combination_result.get('away')}")
                return combination_result

        ta_en = normalize_soccer_team(ta_jp, to_english=True)
        tb_en = normalize_soccer_team(tb_jp, to_english=True)

        print(f"🔍 LEGACY: '{ta_jp}' → '{ta_en}', '{tb_jp}' → '{tb_en}'")
        print(f"🔍 NORMALIZED: '{norm(ta_jp)}' & '{norm(ta_en)}' vs '{norm(tb_jp)}' & '{norm(tb_en)}'")

        a_candidates = {norm(ta_jp), norm(ta_en)}
        b_candidates = {norm(tb_jp), norm(tb_en)}

        for g in games:
            home = g.get("home") or g.get("raw", {}).get("teams", {}).get("home", {}).get("name", "")
            away = g.get("away") or g.get("raw", {}).get("teams", {}).get("away", {}).get("name", "")
            game_id = g.get("id") or g.get("raw", {}).get("fixture", {}).get("id")

            nh = norm(home)
            na = norm(away)
            nhj = norm(g.get("home_jp") or "")
            naj = norm(g.get("away_jp") or "")

            # Debug first few games
            if g == games[0]:
                print(f"🔍 SAMPLE MATCH: '{home}' → '{nh}' vs '{away}' → '{na}'")
                print(f"🔍 SAMPLE CANDIDATES A: {a_candidates}")
                print(f"🔍 SAMPLE CANDIDATES B: {b_candidates}")

            if (nh in a_candidates and na in b_candidates) or (nh in b_candidates and na in a_candidates):
                print(f"✅ LEGACY SUCCESS: {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}
            if (nhj in a_candidates and naj in b_candidates) or (nhj in b_candidates and naj in a_candidates):
                print(f"✅ LEGACY SUCCESS (JP): {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

        # 2. 従来方式で見つからない場合、ファジーマッチングにフォールバック
        print(f"❌ LEGACY FAILED → Trying FUZZY MATCHING")
        fuzzy_result = self.fuzzy_matcher.match_teams_fuzzy(teams, games)
        if fuzzy_result:
            print(f"✅ FUZZY SUCCESS: {fuzzy_result.get('home')} vs {fuzzy_result.get('away')}")
            return fuzzy_result

        print(f"❌ FUZZY FAILED: No match found")
        return None

    def _match_by_combination(self, teams: List[str], games: List[Dict]) -> Optional[Dict]:
        """
        組み合わせベースのチームマッチング
        曖昧なチーム名（マンチェスター等）を対戦相手との組み合わせで解決
        """
        ta_jp, tb_jp = teams[0], teams[1]

        # 各チームの候補リストを生成
        ta_candidates = self._get_team_candidates(ta_jp)
        tb_candidates = self._get_team_candidates(tb_jp)

        print(f"🔍 COMBINATION: {ta_jp} → {ta_candidates}")
        print(f"🔍 COMBINATION: {tb_jp} → {tb_candidates}")

        # 利用可能な試合との組み合わせマッチング
        for g in games:
            home = g.get("home") or g.get("raw", {}).get("teams", {}).get("home", {}).get("name", "")
            away = g.get("away") or g.get("raw", {}).get("teams", {}).get("away", {}).get("name", "")
            game_id = g.get("id") or g.get("raw", {}).get("fixture", {}).get("id")

            # 正方向マッチング（A=home, B=away）
            if self._fuzzy_match_in_candidates(home, ta_candidates) and \
               self._fuzzy_match_in_candidates(away, tb_candidates):
                print(f"✅ COMBINATION MATCH (A→H, B→A): {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

            # 逆方向マッチング（A=away, B=home）
            if self._fuzzy_match_in_candidates(home, tb_candidates) and \
               self._fuzzy_match_in_candidates(away, ta_candidates):
                print(f"✅ COMBINATION MATCH (A→A, B→H): {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

        return None

    def _get_team_candidates(self, team_name: str) -> List[str]:
        """チーム名の候補リストを生成"""
        candidates = [team_name]

        # 曖昧なチームの場合、複数候補を追加
        if team_name.lower() in ["マンチェスター", "manchester"]:
            candidates.extend(["Manchester City", "Manchester United"])

        # 基本的な英語変換も追加
        try:
            en_name = normalize_soccer_team(team_name, to_english=True)
            if en_name and en_name != team_name:
                candidates.append(en_name)
        except:
            pass

        return candidates

    def _fuzzy_match_in_candidates(self, target: str, candidates: List[str]) -> bool:
        """ターゲットが候補リストにファジーマッチするかチェック"""
        for candidate in candidates:
            if self.fuzzy_matcher.calculate_similarity(target, candidate) >= 0.8:
                return True
        return False
