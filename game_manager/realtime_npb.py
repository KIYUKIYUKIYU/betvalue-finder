# -*- coding: utf-8 -*-
"""
RealtimeNPBGameManager
リアルタイム対応NPB試合管理クラス
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .realtime_game_manager import RealtimeGameManager
from .ttl_cache_manager import TTLConfig
from .realtime_game_manager import RealtimeConfig
from converter.team_fuzzy_matcher import TeamFuzzyMatcher


class RealtimeNPBGameManager(RealtimeGameManager):
    """リアルタイム対応NPB試合管理クラス"""

    API_BASE = "https://v1.baseball.api-sports.io"
    LEAGUE_ID = 2  # NPB League ID

    # NPBチーム名マッピング（API実名ベース）
    TEAM_MAPPING = {
        "Yomiuri Giants": {"jp_name": "読売ジャイアンツ", "aliases": ["巨人", "ジャイアンツ", "G"]},
        "Tokyo Yakult Swallows": {"jp_name": "東京ヤクルトスワローズ", "aliases": ["ヤクルト", "スワローズ", "S"]},
        "Yakult Swallows": {"jp_name": "東京ヤクルトスワローズ", "aliases": ["ヤクルト", "スワローズ", "S"]},
        "Yokohama DeNA BayStars": {"jp_name": "横浜DeNAベイスターズ", "aliases": ["DeNA", "ベイスターズ", "横浜", "DB"]},
        "Yokohama BayStars": {"jp_name": "横浜DeNAベイスターズ", "aliases": ["DeNA", "ベイスターズ", "横浜", "DB"]},
        "Chunichi Dragons": {"jp_name": "中日ドラゴンズ", "aliases": ["中日", "ドラゴンズ", "D"]},
        "Hanshin Tigers": {"jp_name": "阪神タイガース", "aliases": ["阪神", "タイガース", "T"]},
        "Hiroshima Toyo Carp": {"jp_name": "広島東洋カープ", "aliases": ["広島", "カープ", "C"]},
        "Hiroshima Carp": {"jp_name": "広島東洋カープ", "aliases": ["広島", "カープ", "C"]},
        "Orix Buffaloes": {"jp_name": "オリックス・バファローズ", "aliases": ["オリックス", "バファローズ", "Bs"]},
        "Fukuoka SoftBank Hawks": {"jp_name": "福岡ソフトバンクホークス", "aliases": ["ソフトバンク", "ホークス", "ソフト", "SB", "H"]},
        "Fukuoka S. Hawks": {"jp_name": "福岡ソフトバンクホークス", "aliases": ["ソフトバンク", "ホークス", "ソフト", "SB", "H"]},
        "Saitama Seibu Lions": {"jp_name": "埼玉西武ライオンズ", "aliases": ["西武", "ライオンズ", "L"]},
        "Seibu Lions": {"jp_name": "埼玉西武ライオンズ", "aliases": ["西武", "ライオンズ", "L"]},
        "Tohoku Rakuten Golden Eagles": {"jp_name": "東北楽天ゴールデンイーグルス", "aliases": ["楽天", "イーグルス", "ゴールデンイーグルス", "E"]},
        "Rakuten Gold. Eagles": {"jp_name": "東北楽天ゴールデンイーグルス", "aliases": ["楽天", "イーグルス", "ゴールデンイーグルス", "E"]},
        "Chiba Lotte Marines": {"jp_name": "千葉ロッテマリーンズ", "aliases": ["ロッテ", "マリーンズ", "M"]},
        "Hokkaido Nippon-Ham Fighters": {"jp_name": "北海道日本ハムファイターズ", "aliases": ["日本ハム", "日ハム", "ファイターズ", "F"]},
        "Nippon Ham Fighters": {"jp_name": "北海道日本ハムファイターズ", "aliases": ["日本ハム", "日ハム", "ファイターズ", "F"]},
    }

    def __init__(
        self,
        api_key: str,
        cache_dir: str = "data/npb",
        enable_ttl_cache: bool = True,
        ttl_config: TTLConfig = None,
        realtime_config: RealtimeConfig = None,
        global_session = None
    ):
        # 統一インターフェース対応: キーワード引数で親クラスを呼び出し
        super().__init__(api_key=api_key, cache_dir=cache_dir)

        # APIの実際の名前形式に合わせたcanonical名を設定
        api_canonical_names = {
            "読売ジャイアンツ": "Yomiuri Giants",
            "東京ヤクルトスワローズ": "Yakult Swallows",
            "横浜DeNAベイスターズ": "Yokohama BayStars",
            "中日ドラゴンズ": "Chunichi Dragons",
            "阪神タイガース": "Hanshin Tigers",
            "広島東洋カープ": "Hiroshima Carp",  # API実名に合わせる
            "オリックス・バファローズ": "Orix Buffaloes",
            "福岡ソフトバンクホークス": "Fukuoka S. Hawks",  # API実名に合わせる
            "埼玉西武ライオンズ": "Seibu Lions",  # API実名に合わせる
            "東北楽天ゴールデンイーグルス": "Rakuten Gold. Eagles",  # API実名に合わせる
            "千葉ロッテマリーンズ": "Chiba Lotte Marines",
            "北海道日本ハムファイターズ": "Nippon Ham Fighters"  # API実名に合わせる
        }

        # team_mappingを構築: すべてをAPI実名に正規化
        for en_name, details in self.TEAM_MAPPING.items():
            jp_name = details["jp_name"]
            aliases = details["aliases"]
            api_canonical_name = api_canonical_names[jp_name]

            # 日本語→API実名
            self.team_mapping[jp_name] = api_canonical_name
            for alias in aliases:
                self.team_mapping[alias] = api_canonical_name

            # 英語バリアント→API実名
            self.team_mapping[en_name] = api_canonical_name

        self.logger.info(f"🏟️ RealtimeNPBGameManager initialized with {len(self.team_mapping)} team mappings")
        self.fuzzy_matcher = TeamFuzzyMatcher(threshold=0.6)

    def get_sport_name(self) -> str:
        return "NPB"

    def fetch_games(self, date: datetime, **kwargs) -> List[Dict]:
        """同期版ゲーム取得（RequestsベースでシンプルiD実装）"""
        date_str = date.strftime('%Y-%m-%d')
        url = f"{self.API_BASE}/games"

        params = {
            "league": self.LEAGUE_ID,
            "season": date.year,
            "date": date_str
        }

        try:
            import requests
            headers = self._prepare_headers({})
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            games_data = data.get("response", [])

            # ゲームデータをフォーマット
            formatted_games = []
            for raw_game in games_data:
                formatted_game = self._format_game_data(raw_game)
                if formatted_game:
                    formatted_games.append(formatted_game)

            self.logger.info(f"✅ Fetched {len(formatted_games)} NPB games for {date_str}")
            return formatted_games

        except Exception as e:
            self.logger.error(f"❌ Failed to fetch NPB games for {date_str}: {e}")
            return []

    def fetch_odds(self, game_id: str, bookmaker_ids: List[int] = None) -> Optional[Dict]:
        """同期版オッズ取得（NPB最適化版）"""
        if bookmaker_ids is None:
            bookmaker_ids = [4]  # Pinnacle のみ

        # NPB用の複数アプローチで試行
        result = self._try_fixture_based_odds(game_id, bookmaker_ids)
        if result:
            return result

        result = self._try_season_based_odds(game_id, bookmaker_ids)
        if result:
            return result

        self.logger.warning(f"⚠️ All NPB odds retrieval methods failed for game {game_id}")
        return None

    def _try_fixture_based_odds(self, game_id: str, bookmaker_ids: List[int]) -> Optional[Dict]:
        """ゲームベースでのオッズ取得（従来方式）"""
        url = f"{self.API_BASE}/odds"
        from datetime import datetime
        current_season = datetime.now().year
        params = {
            "game": game_id,
            "league": self.LEAGUE_ID,
            "season": current_season
        }

        try:
            import requests
            headers = self._prepare_headers({})
            self.logger.info(f"🔍 NPB odds: Trying game-based approach for {game_id}")

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            odds_data = data.get("response", [])

            self.logger.info(f"📊 NPB game-based response: {len(odds_data)} entries")

            if odds_data:
                odds_entry = odds_data[0]
                result = self._process_odds_data(odds_entry, game_id, bookmaker_ids)
                if result:
                    self.logger.info(f"✅ NPB game-based odds successful for {game_id}")
                    return result

        except Exception as e:
            self.logger.warning(f"⚠️ NPB game-based odds failed for {game_id}: {e}")

        return None

    def _try_season_based_odds(self, game_id: str, bookmaker_ids: List[int]) -> Optional[Dict]:
        """シーズンベースでのオッズ取得（NPB推奨方式）"""
        from datetime import datetime

        url = f"{self.API_BASE}/odds"
        current_year = datetime.now().year
        params = {
            "league": self.LEAGUE_ID,
            "season": current_year
        }

        try:
            import requests
            headers = self._prepare_headers({})
            self.logger.info(f"🔍 NPB odds: Trying season-based approach for {game_id}")

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            odds_data = data.get("response", [])

            self.logger.info(f"📊 NPB season-based response: {len(odds_data)} entries")

            # 指定game_idのオッズを検索
            target_odds = None
            for odds_entry in odds_data:
                fixture_data = odds_entry.get("fixture", {}) or odds_entry.get("game", {})
                entry_id = str(fixture_data.get("id", ""))

                if entry_id == str(game_id):
                    target_odds = odds_entry
                    break

            if target_odds:
                result = self._process_odds_data(target_odds, game_id, bookmaker_ids)
                if result:
                    self.logger.info(f"✅ NPB season-based odds successful for {game_id}")
                    return result
            else:
                self.logger.warning(f"⚠️ Game {game_id} not found in {len(odds_data)} NPB season entries")

        except Exception as e:
            self.logger.warning(f"⚠️ NPB season-based odds failed for {game_id}: {e}")

        return None

    def match_teams(self, teams: List[str], games: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        チーム名マッチング: 従来方式 + 組み合わせベース + ファジーマッチング
        """
        def norm(s: str) -> str:
            return (
                (s or "")
                .lower()
                .replace(".", "")
                .replace(" ", "")
                .replace("-", "")
                .replace("_", "")
            )

        if games is None:
            games = self.load_latest_cache()
            if not games:
                return None

        print(f"🔍 REALTIME NPB MATCH_TEAMS: 入力チーム名 {teams}")

        # 1. 従来方式（完全一致）を試行
        ta_jp, tb_jp = teams[0], teams[1]

        # 曖昧なチーム名の検出（ジャイアンツ、ライオンズ等）
        ambiguous_teams = {"ジャイアンツ", "giants", "ライオンズ", "lions", "ホークス", "hawks"}
        ta_is_ambiguous = ta_jp.lower() in ambiguous_teams
        tb_is_ambiguous = tb_jp.lower() in ambiguous_teams

        if ta_is_ambiguous or tb_is_ambiguous:
            print(f"🔍 REALTIME NPB AMBIGUOUS TEAM DETECTED: {ta_jp if ta_is_ambiguous else tb_jp}")
            # 組み合わせベースマッチングを優先
            combination_result = self._match_by_combination(teams, games)
            if combination_result:
                print(f"✅ REALTIME NPB COMBINATION SUCCESS: {combination_result.get('home')} vs {combination_result.get('away')}")
                return combination_result

        # 従来の辞書マッピング試行
        ta_en = self.team_mapping.get(ta_jp, ta_jp)
        tb_en = self.team_mapping.get(tb_jp, tb_jp)

        print(f"🔍 REALTIME NPB LEGACY: '{ta_jp}' → '{ta_en}', '{tb_jp}' → '{tb_en}'")

        a_candidates = {norm(ta_jp), norm(ta_en)}
        b_candidates = {norm(tb_jp), norm(tb_en)}

        for g in games:
            home = g.get("home") or g.get("raw", {}).get("teams", {}).get("home", {}).get("name", "")
            away = g.get("away") or g.get("raw", {}).get("teams", {}).get("away", {}).get("name", "")
            game_id = g.get("id") or g.get("raw", {}).get("id")

            nh = norm(home)
            na = norm(away)

            if (nh in a_candidates and na in b_candidates) or (nh in b_candidates and na in a_candidates):
                print(f"✅ REALTIME NPB LEGACY SUCCESS: {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

        # 2. 従来方式で見つからない場合、ファジーマッチングにフォールバック
        print(f"❌ REALTIME NPB LEGACY FAILED → Trying FUZZY MATCHING")
        fuzzy_result = self.fuzzy_matcher.match_teams_fuzzy(teams, games)
        if fuzzy_result:
            print(f"✅ REALTIME NPB FUZZY SUCCESS: {fuzzy_result.get('home')} vs {fuzzy_result.get('away')}")
            return fuzzy_result

        print(f"❌ REALTIME NPB FUZZY FAILED: No match found")
        return None

    def _match_by_combination(self, teams: List[str], games: List[Dict]) -> Optional[Dict]:
        """
        組み合わせベースのチームマッチング
        曖昧なチーム名（ジャイアンツ、ライオンズ等）を対戦相手との組み合わせで解決
        """
        ta_jp, tb_jp = teams[0], teams[1]

        # 各チームの候補リストを生成
        ta_candidates = self._get_team_candidates(ta_jp)
        tb_candidates = self._get_team_candidates(tb_jp)

        print(f"🔍 REALTIME NPB COMBINATION: {ta_jp} → {ta_candidates}")
        print(f"🔍 REALTIME NPB COMBINATION: {tb_jp} → {tb_candidates}")

        # 利用可能な試合との組み合わせマッチング
        for g in games:
            home = g.get("home") or g.get("raw", {}).get("teams", {}).get("home", {}).get("name", "")
            away = g.get("away") or g.get("raw", {}).get("teams", {}).get("away", {}).get("name", "")
            game_id = g.get("id") or g.get("raw", {}).get("id")

            # 正方向マッチング（A=home, B=away）
            if self._fuzzy_match_in_candidates(home, ta_candidates) and \
               self._fuzzy_match_in_candidates(away, tb_candidates):
                print(f"✅ REALTIME NPB COMBINATION MATCH (A→H, B→A): {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

            # 逆方向マッチング（A=away, B=home）
            if self._fuzzy_match_in_candidates(home, tb_candidates) and \
               self._fuzzy_match_in_candidates(away, ta_candidates):
                print(f"✅ REALTIME NPB COMBINATION MATCH (A→A, B→H): {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

        return None

    def _get_team_candidates(self, team_name: str) -> List[str]:
        """チーム名の候補リストを生成"""
        candidates = [team_name]

        # 曖昧なチームの場合、複数候補を追加
        if team_name.lower() in ["ジャイアンツ", "giants"]:
            candidates.extend(["Yomiuri Giants", "読売ジャイアンツ"])
        elif team_name.lower() in ["ライオンズ", "lions"]:
            candidates.extend(["Seibu Lions", "埼玉西武ライオンズ"])
        elif team_name.lower() in ["ホークス", "hawks"]:
            candidates.extend(["Fukuoka S. Hawks", "福岡ソフトバンクホークス"])

        # 基本的な辞書マッピングも追加
        try:
            mapped_name = self.team_mapping.get(team_name)
            if mapped_name and mapped_name != team_name:
                candidates.append(mapped_name)
        except:
            pass

        return candidates

    def _fuzzy_match_in_candidates(self, target: str, candidates: List[str]) -> bool:
        """ターゲットが候補リストにファジーマッチするかチェック"""
        for candidate in candidates:
            if self.fuzzy_matcher.calculate_similarity(target, candidate) >= 0.8:
                return True
        return False

    async def get_games_realtime(self, date: datetime, **kwargs) -> List[Dict]:
        """リアルタイム試合データ取得"""
        date_str = date.strftime('%Y-%m-%d')

        # TTLキャッシュキー
        cache_key = f"npb_games_{date_str}"

        # キャッシュチェック
        if self.ttl_cache:
            cached_games = self.ttl_cache.get(cache_key)
            if cached_games is not None:
                self.logger.info(f"🎯 NPB games cache hit for {date_str}")
                return cached_games

        # API呼び出し
        games = await self._fetch_games_async(date, **kwargs)

        # キャッシュに保存
        if games and self.ttl_cache:
            from .ttl_cache_manager import DataType
            self.ttl_cache.set(cache_key, games, DataType.GAME_DATA)
            self.logger.info(f"📊 Cached NPB games for {date_str}")

        return games or []

    async def fetch_games_async(self, date: datetime = None, **kwargs) -> List[Dict]:
        """外部アクセス用の公開ゲーム取得メソッド"""
        if date is None:
            date = datetime.now()
        return await self._fetch_games_async(date, **kwargs)

    async def _fetch_games_async(self, date: datetime, **kwargs) -> List[Dict]:
        """非同期ゲーム取得"""
        await self._ensure_session()

        date_str = date.strftime('%Y-%m-%d')
        url = f"{self.API_BASE}/games"

        params = {
            "league": self.LEAGUE_ID,
            "season": date.year,
            "date": date_str
        }

        try:
            async with self._semaphore:
                response = await self._session.get(url, params=params, headers=self._prepare_headers({}))
                await self._handle_rate_limit(response.headers)

                data = await response.json()
                games_data = data.get("response", [])

                # ゲームデータをフォーマット
                formatted_games = []
                for raw_game in games_data:
                    formatted_game = self._format_game_data(raw_game)
                    if formatted_game:
                        formatted_games.append(formatted_game)

                self.logger.info(f"✅ Fetched {len(formatted_games)} NPB games for {date_str}")
                return formatted_games

        except Exception as e:
            self.logger.error(f"❌ Failed to fetch NPB games for {date_str}: {e}")
            return []

    def _format_game_data(self, raw_game: Dict) -> Optional[Dict]:
        """APIからの生データを標準形式にフォーマット"""
        try:
            home_team_name = raw_game["teams"]["home"]["name"]
            away_team_name = raw_game["teams"]["away"]["name"]

            home_jp = self.TEAM_MAPPING.get(home_team_name, {}).get("jp_name", home_team_name)
            away_jp = self.TEAM_MAPPING.get(away_team_name, {}).get("jp_name", away_team_name)

            date_info = raw_game.get("date", "")
            time_info = raw_game.get("time", "")
            datetime_str = f"{date_info} {time_info}" if date_info and time_info else ""

            return {
                "id": raw_game["id"],
                "home": home_team_name,
                "away": away_team_name,
                "home_jp": home_jp,
                "away_jp": away_jp,
                "datetime": datetime_str,
                "league": "NPB",
                "status": raw_game["status"]["long"],
                "raw": raw_game,
            }
        except (KeyError, TypeError) as e:
            self.logger.warning(f"⚠️ Failed to format NPB game data: {e}")
            return None

    async def get_odds_realtime(
        self,
        game_id: str,
        bookmaker_ids: List[int] = None,
        force_refresh: bool = False,
        **kwargs
    ) -> Optional[Dict]:
        """リアルタイムオッズ取得"""
        self.logger.info(f"🌟 get_odds_realtime called for NPB game {game_id} with bookmaker_ids={bookmaker_ids}")

        if bookmaker_ids is None:
            bookmaker_ids = [4]  # Pinnacle のみ

        cache_key = f"npb_odds_{game_id}"

        # キャッシュチェック
        if not force_refresh and self.ttl_cache:
            cached_odds = self.ttl_cache.get(cache_key)
            if cached_odds is not None:
                self.logger.info(f"🎯 NPB odds cache hit for {game_id}")
                return cached_odds

        # API呼び出し
        self.logger.info(f"🔄 NPB calling _fetch_odds_async for game {game_id}")
        odds = await self._fetch_odds_async(game_id, bookmaker_ids, **kwargs)
        self.logger.info(f"🏁 NPB _fetch_odds_async result: {type(odds)} {bool(odds)}")

        # キャッシュに保存
        if odds and self.ttl_cache:
            from .ttl_cache_manager import DataType
            self.ttl_cache.set(cache_key, odds, DataType.ODDS_DATA)
            self.logger.info(f"📊 Cached NPB odds for {game_id}")

        return odds

    async def fetch_odds_async(self, game_id: str, bookmaker_ids: List[int] = None, **kwargs) -> Optional[Dict]:
        """外部アクセス用の公開メソッド"""
        self.logger.info(f"🚀 fetch_odds_async called for NPB game {game_id} with bookmaker_ids={bookmaker_ids}")
        result = await self._fetch_odds_async(game_id, bookmaker_ids, **kwargs)
        self.logger.info(f"🏁 fetch_odds_async result for NPB game {game_id}: {type(result)} {bool(result)}")
        return result

    async def _fetch_odds_async(self, game_id: str, bookmaker_ids: List[int] = None, **kwargs) -> Optional[Dict]:
        """非同期オッズ取得（NPB最適化版）"""
        await self._ensure_session()

        # ゲームベース試行
        self.logger.info(f"🎯 NPB async: Trying game-based odds for {game_id}")
        result = await self._try_fixture_based_odds_async(game_id, bookmaker_ids)
        if result:
            self.logger.info(f"✅ NPB async game-based odds successful for {game_id}")
            return result
        else:
            self.logger.warning(f"⚠️ NPB async game-based odds failed for {game_id}")

        # シーズンベース試行
        result = await self._try_season_based_odds_async(game_id, bookmaker_ids)
        if result:
            return result

        self.logger.warning(f"⚠️ All async NPB odds retrieval methods failed for game {game_id}")
        return None

    async def _try_fixture_based_odds_async(self, game_id: str, bookmaker_ids: List[int]) -> Optional[Dict]:
        """非同期ゲームベースオッズ取得"""
        url = f"{self.API_BASE}/odds"
        from datetime import datetime
        current_season = datetime.now().year
        params = {
            "game": game_id,
            "league": self.LEAGUE_ID,
            "season": current_season
        }

        try:
            async with self._semaphore:
                response = await self._session.get(url, params=params, headers=self._prepare_headers({}))
                await self._handle_rate_limit(response.headers)

                data = await response.json()
                odds_data = data.get("response", [])

                self.logger.info(f"📊 NPB async game-based response: {len(odds_data)} entries")

                if odds_data:
                    odds_entry = odds_data[0]
                    result = self._process_odds_data(odds_entry, game_id, bookmaker_ids)
                    if result:
                        self.logger.info(f"✅ NPB async game-based odds successful for {game_id}")
                        return result

        except Exception as e:
            self.logger.warning(f"⚠️ NPB async game-based odds failed for {game_id}: {e}")

        return None

    async def _try_season_based_odds_async(self, game_id: str, bookmaker_ids: List[int]) -> Optional[Dict]:
        """非同期シーズンベースオッズ取得"""
        from datetime import datetime

        url = f"{self.API_BASE}/odds"
        current_year = datetime.now().year
        params = {
            "league": self.LEAGUE_ID,
            "season": current_year
        }

        try:
            async with self._semaphore:
                response = await self._session.get(url, params=params, headers=self._prepare_headers({}))
                await self._handle_rate_limit(response.headers)

                data = await response.json()
                odds_data = data.get("response", [])

                self.logger.info(f"📊 NPB async season-based response: {len(odds_data)} entries")

                # 指定game_idのオッズを検索
                target_odds = None
                for odds_entry in odds_data:
                    fixture_data = odds_entry.get("fixture", {}) or odds_entry.get("game", {})
                    entry_id = str(fixture_data.get("id", ""))

                    if entry_id == str(game_id):
                        target_odds = odds_entry
                        break

                if target_odds:
                    result = self._process_odds_data(target_odds, game_id, bookmaker_ids)
                    if result:
                        self.logger.info(f"✅ NPB async season-based odds successful for {game_id}")
                        return result
                else:
                    self.logger.warning(f"⚠️ Game {game_id} not found in {len(odds_data)} NPB async season entries")

        except Exception as e:
            self.logger.warning(f"⚠️ NPB async season-based odds failed for {game_id}: {e}")

        return None

    def _process_odds_data(self, odds_entry: Dict, game_id: str, bookmaker_ids: List[int]) -> Optional[Dict]:
        """オッズデータ処理（NPB強化版）"""
        try:
            bookmakers = odds_entry.get("bookmakers", [])
            self.logger.info(f"🔍 NPB odds processing: {len(bookmakers)} bookmakers available")

            if not bookmakers:
                self.logger.warning(f"⚠️ No bookmakers found in NPB odds entry for {game_id}")
                return None

            # Pinnacle以外も含めた詳細ログ
            for bookmaker in bookmakers:
                bm_id = bookmaker.get("id", "unknown")
                bm_name = bookmaker.get("name", "unknown")
                self.logger.info(f"   Bookmaker: {bm_name} (ID: {bm_id})")

            # 指定されたブックメーカーを検索
            target_bookmaker = None
            for bookmaker in bookmakers:
                if bookmaker_ids and bookmaker.get("id") in bookmaker_ids:
                    target_bookmaker = bookmaker
                    self.logger.info(f"✅ Found target bookmaker: {bookmaker.get('name', 'unknown')} (ID: {bookmaker.get('id')})")
                    break

            if not target_bookmaker:
                available_ids = [bm.get("id") for bm in bookmakers]
                self.logger.warning(f"⚠️ Target bookmaker(s) {bookmaker_ids} not found. Available: {available_ids}")

                # フォールバック: 最初のブックメーカーを使用
                if bookmakers:
                    target_bookmaker = bookmakers[0]
                    self.logger.info(f"🔄 Using fallback bookmaker: {target_bookmaker.get('name', 'unknown')}")
                else:
                    return None

            # ハンディキャップオッズの確認
            bets = target_bookmaker.get("bets", [])

            # デバッグ: 利用可能なベットタイプを出力
            bet_types = [bet.get("name", "unknown") for bet in bets]
            self.logger.info(f"🔍 NPB available bet types for game {game_id}: {bet_types}")

            handicap_bet = None
            for bet in bets:
                bet_name = bet.get("name", "")
                if bet_name in ["Spread", "Handicap", "Asian Handicap"]:
                    handicap_bet = bet
                    self.logger.info(f"✅ Found handicap bet type: {bet_name}")
                    break

            if handicap_bet:
                values = handicap_bet.get("values", [])
                self.logger.info(f"📊 NPB handicap odds: {len(values)} lines available")
            else:
                self.logger.warning(f"⚠️ No handicap odds found for NPB game {game_id}")

            # レスポンス構築
            result = {
                "fixture": {"id": game_id},
                "bookmakers": [target_bookmaker]
            }

            # ゲーム情報も含める（可能な場合）
            if "fixture" in odds_entry:
                result["fixture"] = odds_entry["fixture"]
            elif "game" in odds_entry:
                result["fixture"] = odds_entry["game"]

            return result

        except Exception as e:
            self.logger.error(f"❌ Failed to process NPB odds data for {game_id}: {e}")
            import traceback
            self.logger.error(f"   Full traceback: {traceback.format_exc()}")

        return None


    def _prepare_headers(self, headers: Dict) -> Dict:
        """API リクエストヘッダー準備"""
        default_headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "v1.baseball.api-sports.io"
        }
        default_headers.update(headers)
        return default_headers

    async def _handle_rate_limit(self, response_headers):
        """レート制限処理"""
        remaining = response_headers.get("X-RateLimit-Remaining")
        if remaining:
            try:
                remaining_count = int(remaining)
                if remaining_count < 10:
                    self.logger.warning(f"⚠️ NPB API rate limit low: {remaining_count} remaining")
            except ValueError:
                pass

    # =============================================================================
    # プリゲーム機能拡張（インテリジェントプリゲームシステム互換性）
    # =============================================================================

    async def get_pregame_games_realtime(
        self,
        date: datetime,
        buffer_minutes: int = 30,
        **kwargs
    ) -> List[Dict]:
        """プリゲーム試合をリアルタイム取得"""
        all_games = await self.get_games_realtime(date, **kwargs)

        from .pregame_filter import PregameFilter
        pregame_games = PregameFilter.filter_pregame_games(all_games, buffer_minutes)

        if len(pregame_games) < len(all_games):
            excluded_count = len(all_games) - len(pregame_games)
            self.logger.info(f"🔍 NPB: {excluded_count} live/finished games excluded")
            self.logger.info(f"✅ {len(pregame_games)} pregame games available")

        return pregame_games

    async def get_pregame_npb_games_realtime(
        self,
        date: datetime,
        buffer_minutes: int = 30,
        **kwargs
    ) -> List[Dict]:
        """インテリジェントプリゲームシステム互換性のためのエイリアス"""
        return await self.get_pregame_games_realtime(date, buffer_minutes, **kwargs)