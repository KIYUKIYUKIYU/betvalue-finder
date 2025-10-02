# -*- coding: utf-8 -*-
"""
RealtimeMLBGameManager
リアルタイム対応のMLB専用試合管理クラス (Updated for global session support)
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .realtime_game_manager import RealtimeGameManager, RealtimeConfig
from .mlb import MLBGameManager
from .ttl_cache_manager import TTLConfig, DataType
from converter.team_fuzzy_matcher import TeamFuzzyMatcher


class RealtimeMLBGameManager(RealtimeGameManager):
    """リアルタイム対応MLB専用の試合管理クラス"""
    
    API_BASE = "https://v1.baseball.api-sports.io"
    LEAGUE_ID = 1  # MLB
    
    # MLBGameManagerと同じチーム名マッピング
    TEAM_MAPPING = {
        "ヤンキース": "New York Yankees",
        "レッドソックス": "Boston Red Sox",
        "メッツ": "New York Mets",
        "ドジャース": "Los Angeles Dodgers",
        "ジャイアンツ": "San Francisco Giants",
        "エンゼルス": "Los Angeles Angels",
        "マリナーズ": "Seattle Mariners",
        "レンジャーズ": "Texas Rangers",
        "アストロズ": "Houston Astros",
        "アスレチックス": "Athletics",
        "レイズ": "Tampa Bay Rays",
        "ブルージェイズ": "Toronto Blue Jays",
        "オリオールズ": "Baltimore Orioles",
        "タイガース": "Detroit Tigers",
        "ホワイトソックス": "Chicago White Sox",
        "ツインズ": "Minnesota Twins",
        "ガーディアンズ": "Cleveland Guardians",
        "ロイヤルズ": "Kansas City Royals",
        "パドレス": "San Diego Padres",
        "フィリーズ": "Philadelphia Phillies",
        "ブレーブス": "Atlanta Braves",
        "ブリュワーズ": "Milwaukee Brewers",
        "カージナルス": "St.Louis Cardinals",
        "カブス": "Chicago Cubs",
        "パイレーツ": "Pittsburgh Pirates",
        "レッズ": "Cincinnati Reds",
        "ダイヤモンドバックス": "Arizona Diamondbacks",
        "ロッキーズ": "Colorado Rockies",
        "ナショナルズ": "Washington Nationals",
        # 略称対応
        "Wソックス": "Chicago White Sox",
        "Rソックス": "Boston Red Sox",
        "Dバックス": "Arizona Diamondbacks",
        "マーリンズ": "Miami Marlins",
    }
    
    def __init__(
        self,
        api_key: str,
        cache_dir: str = "data/mlb",
        enable_ttl_cache: bool = True,
        ttl_config: TTLConfig = None,
        realtime_config: RealtimeConfig = None,
        global_session: Optional[aiohttp.ClientSession] = None,
        enable_retries: bool = True
    ):
        # 統一インターフェース対応: キーワード引数で親クラスを呼び出し
        super().__init__(api_key=api_key, cache_dir=cache_dir)
        self.team_mapping = self.TEAM_MAPPING
        self.fuzzy_matcher = TeamFuzzyMatcher(threshold=0.6)
        self.enable_retries = enable_retries
        
        # MLB専用のリアルタイム設定
        if realtime_config is None:
            self.realtime_config = RealtimeConfig(
                max_concurrent_requests=5,  # MLBは控えめに
                request_timeout=20,
                rate_limit_delay=0.2,  # 少し長めの間隔
                enable_request_logging=True
            )
    
    def get_sport_name(self) -> str:
        return "MLB"
    
    def _prepare_headers(self, headers: Dict) -> Dict:
        headers["x-apisports-key"] = self.api_key
        return headers
    
    # =============================================================================
    # リアルタイム API 実装
    # =============================================================================
    
    async def _fetch_games_async(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        """
        非同期でMLB試合データを取得
        
        Args:
            date: 対象日付
            timezone: タイムゾーン
            **kwargs: 追加パラメータ
        
        Returns:
            試合データリスト
        """
        date_str = date.strftime("%Y-%m-%d")
        season = date.year
        
        url = f"{self.API_BASE}/games"
        params = {
            "league": self.LEAGUE_ID,
            "season": season,
            "date": date_str,
            "timezone": timezone,
        }
        
        # 追加パラメータを統合
        params.update(kwargs)
        
        try:
            # JSONデータを直接取得
            data = await self._http_get_async(url, params=params)
            
            # API制限情報表示（簡易版）
            self.logger.info(f"📊 MLB API request completed")
            
            games = []
            for game_data in data.get("response", []):
                game_info = self._format_game_data(game_data)
                if game_info:
                    games.append(game_info)
            
            # キャッシュファイルも保存（従来互換性のため）
            if games:
                await self._save_cache_async(date_str, timezone, games)
            
            self.logger.info(f"✅ Fetched {len(games)} MLB games for {date_str} (realtime)")
            return games
            
        except Exception as e:
            self.logger.error(f"❌ Failed to fetch MLB games: {e}")
            raise e
    
    async def _fetch_odds_async(
        self,
        game_id: str,
        bookmaker_ids: List[int] = None,
        **kwargs
    ) -> Optional[Dict]:
        """
        非同期でMLBオッズデータを取得（再試行メカニズム付き）

        Args:
            game_id: ゲームID
            bookmaker_ids: ブックメーカーIDリスト
            **kwargs: 追加パラメータ

        Returns:
            オッズデータまたはNone
        """
        if bookmaker_ids is None:
            bookmaker_ids = [4]  # Pinnacle PREFERRED

        url = f"{self.API_BASE}/odds"

        # 再試行設定
        retry_intervals = [0, 30, 90]  # 即座、30秒後、90秒後
        enable_retries = kwargs.pop('enable_retries', self.enable_retries)  # インスタンス設定を使用

        for attempt, delay in enumerate(retry_intervals):
            if attempt > 0 and not enable_retries:
                break  # 再試行が無効化されている場合は1回のみ

            if delay > 0:
                self.logger.info(f"⏰ Waiting {delay}s before retry {attempt+1} for game {game_id}")
                await asyncio.sleep(delay)

            try:
                # First try with specified bookmakers
                params = {
                    "game": game_id,
                    "bookmaker": ",".join(map(str, bookmaker_ids)),
                }
                params.update(kwargs)

                # JSONデータを直接取得
                data = await self._http_get_async(url, params=params)
                self.logger.info(f"📊 MLB Odds API request completed (attempt {attempt+1})")

                # レスポンス処理
                response_data = data.get("response", [])
                if not response_data:
                    self.logger.warning(f"⚠️ No odds data found for game {game_id} with preferred bookmaker (attempt {attempt+1})")

                    # Fallback: Try with all bookmakers
                    self.logger.info(f"🔄 Falling back to all bookmakers for game {game_id} (attempt {attempt+1})")
                    fallback_params = {
                        "game": game_id,
                    }
                    fallback_params.update(kwargs)

                    fallback_data = await self._http_get_async(url, params=fallback_params)
                    response_data = fallback_data.get("response", [])

                    if not response_data:
                        if attempt == len(retry_intervals) - 1:  # 最後の試行
                            self.logger.warning(f"⚠️ No odds data found for game {game_id} from any bookmaker after all retries")
                            return None
                        else:
                            self.logger.warning(f"⚠️ No odds data found for game {game_id} from any bookmaker (attempt {attempt+1}), will retry")
                            break  # このループを抜けて次のリトライへ
                    else:
                        self.logger.info(f"✅ Found fallback odds from {len(response_data)} sources (attempt {attempt+1})")
                else:
                    self.logger.info(f"✅ Found preferred odds from {len(response_data)} sources (attempt {attempt+1})")

                # 最初のオッズデータを返す
                odds_data = response_data[0]

                # フォーマット処理
                formatted_odds = self._format_odds_data(odds_data)

                self.logger.info(f"✅ Fetched odds for MLB game {game_id} (realtime, attempt {attempt+1})")
                return formatted_odds

            except Exception as e:
                if attempt == len(retry_intervals) - 1:  # 最後の試行
                    self.logger.error(f"❌ Failed to fetch MLB odds for {game_id} after all retries: {e}")
                    return None
                else:
                    self.logger.warning(f"⚠️ Failed to fetch MLB odds for {game_id} (attempt {attempt+1}): {e}, will retry")
                    # 次の試行へ（forループが適切にdelayを処理）

        return None

    # =============================================================================
    # 組み合わせベースチームマッチング (曖昧なチーム名対応)
    # =============================================================================

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

        print(f"🔍 REALTIME MLB MATCH_TEAMS: 入力チーム名 {teams}")

        # 1. 従来方式（完全一致）を試行
        ta_jp, tb_jp = teams[0], teams[1]

        # 曖昧なチーム名の検出（ジャイアンツ等）
        ambiguous_teams = {"ジャイアンツ", "giants"}
        ta_is_ambiguous = ta_jp.lower() in ambiguous_teams
        tb_is_ambiguous = tb_jp.lower() in ambiguous_teams

        if ta_is_ambiguous or tb_is_ambiguous:
            print(f"🔍 REALTIME MLB AMBIGUOUS TEAM DETECTED: {ta_jp if ta_is_ambiguous else tb_jp}")
            # 組み合わせベースマッチングを優先
            combination_result = self._match_by_combination(teams, games)
            if combination_result:
                print(f"✅ REALTIME MLB COMBINATION SUCCESS: {combination_result.get('home')} vs {combination_result.get('away')}")
                return combination_result

        # 従来の辞書マッピング試行
        ta_en = self.team_mapping.get(ta_jp, ta_jp)
        tb_en = self.team_mapping.get(tb_jp, tb_jp)

        print(f"🔍 REALTIME MLB LEGACY: '{ta_jp}' → '{ta_en}', '{tb_jp}' → '{tb_en}'")

        a_candidates = {norm(ta_jp), norm(ta_en)}
        b_candidates = {norm(tb_jp), norm(tb_en)}

        for g in games:
            home = g.get("home") or g.get("raw", {}).get("teams", {}).get("home", {}).get("name", "")
            away = g.get("away") or g.get("raw", {}).get("teams", {}).get("away", {}).get("name", "")
            game_id = g.get("id") or g.get("raw", {}).get("id")

            nh = norm(home)
            na = norm(away)

            if (nh in a_candidates and na in b_candidates) or (nh in b_candidates and na in a_candidates):
                print(f"✅ REALTIME MLB LEGACY SUCCESS: {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

        # 2. 従来方式で見つからない場合、ファジーマッチングにフォールバック
        print(f"❌ REALTIME MLB LEGACY FAILED → Trying FUZZY MATCHING")
        fuzzy_result = self.fuzzy_matcher.match_teams_fuzzy(teams, games)
        if fuzzy_result:
            print(f"✅ REALTIME MLB FUZZY SUCCESS: {fuzzy_result.get('home')} vs {fuzzy_result.get('away')}")
            return fuzzy_result

        print(f"❌ REALTIME MLB FUZZY FAILED: No match found")
        return None

    def _match_by_combination(self, teams: List[str], games: List[Dict]) -> Optional[Dict]:
        """
        組み合わせベースのチームマッチング
        曖昧なチーム名（ジャイアンツ等）を対戦相手との組み合わせで解決
        """
        ta_jp, tb_jp = teams[0], teams[1]

        # 各チームの候補リストを生成
        ta_candidates = self._get_team_candidates(ta_jp)
        tb_candidates = self._get_team_candidates(tb_jp)

        print(f"🔍 REALTIME MLB COMBINATION: {ta_jp} → {ta_candidates}")
        print(f"🔍 REALTIME MLB COMBINATION: {tb_jp} → {tb_candidates}")

        # 利用可能な試合との組み合わせマッチング
        for g in games:
            home = g.get("home") or g.get("raw", {}).get("teams", {}).get("home", {}).get("name", "")
            away = g.get("away") or g.get("raw", {}).get("teams", {}).get("away", {}).get("name", "")
            game_id = g.get("id") or g.get("raw", {}).get("id")

            # 正方向マッチング（A=home, B=away）
            if self._fuzzy_match_in_candidates(home, ta_candidates) and \
               self._fuzzy_match_in_candidates(away, tb_candidates):
                print(f"✅ REALTIME MLB COMBINATION MATCH (A→H, B→A): {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

            # 逆方向マッチング（A=away, B=home）
            if self._fuzzy_match_in_candidates(home, tb_candidates) and \
               self._fuzzy_match_in_candidates(away, ta_candidates):
                print(f"✅ REALTIME MLB COMBINATION MATCH (A→A, B→H): {home} vs {away}")
                return {"id": game_id, "home": home, "away": away}

        return None

    def _get_team_candidates(self, team_name: str) -> List[str]:
        """チーム名の候補リストを生成"""
        candidates = [team_name]

        # 曖昧なチームの場合、複数候補を追加
        if team_name.lower() in ["ジャイアンツ", "giants"]:
            candidates.extend(["San Francisco Giants", "New York Giants"])

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
    
    # =============================================================================
    # MLB専用メソッド
    # =============================================================================
    
    async def get_today_games_realtime(self, timezone: str = "Asia/Tokyo") -> List[Dict]:
        """今日のMLB試合をリアルタイム取得"""
        today = datetime.now()
        return await self.get_games_realtime(today, timezone=timezone)
    
    async def get_live_games_realtime(self, date: Optional[datetime] = None) -> List[Dict]:
        """ライブ中のMLB試合をリアルタイム取得"""
        if date is None:
            date = datetime.now()
        
        all_games = await self.get_games_realtime(date)
        
        # ライブゲームのみフィルタ
        live_games = []
        for game in all_games:
            if self._is_game_live(game):
                live_games.append(game)
        
        self.logger.info(f"🔴 Found {len(live_games)} live MLB games")
        return live_games
    
    async def get_upcoming_games_realtime(
        self, 
        hours_ahead: int = 24, 
        timezone: str = "Asia/Tokyo"
    ) -> List[Dict]:
        """今後指定時間内のMLB試合をリアルタイム取得"""
        now = datetime.now()
        end_date = now + timedelta(hours=hours_ahead)
        
        # 日付範囲内のデータを取得
        dates = []
        current_date = now.date()
        while current_date <= end_date.date():
            dates.append(datetime.combine(current_date, datetime.min.time()))
            current_date += timedelta(days=1)
        
        # 並行取得
        games_by_date = await self.get_multiple_games_realtime(dates, timezone=timezone)
        
        # 全ゲームを統合してソート
        all_games = []
        for games in games_by_date.values():
            all_games.extend(games)
        
        # 時刻でソート
        upcoming_games = []
        for game in all_games:
            game_time = self._extract_game_time(game)
            if game_time and now <= game_time <= end_date:
                upcoming_games.append(game)
        
        # ソート
        upcoming_games.sort(key=lambda g: self._extract_game_time(g) or datetime.max)
        
        self.logger.info(f"⏰ Found {len(upcoming_games)} upcoming MLB games in next {hours_ahead}h")
        return upcoming_games
    
    async def get_team_games_realtime(
        self, 
        team_name: str, 
        days_range: int = 7
    ) -> List[Dict]:
        """特定チームの試合をリアルタイム取得（複数日）"""
        now = datetime.now()
        
        # 日付範囲生成
        dates = []
        for i in range(-days_range//2, days_range//2 + 1):
            dates.append(now + timedelta(days=i))
        
        # 並行取得
        games_by_date = await self.get_multiple_games_realtime(dates)
        
        # チーム名正規化
        normalized_team = self.team_mapping.get(team_name, team_name)
        
        # チーム試合を検索
        team_games = []
        for games in games_by_date.values():
            for game in games:
                if (game.get("home") == normalized_team or 
                    game.get("away") == normalized_team or
                    game.get("home_jp") == team_name or
                    game.get("away_jp") == team_name):
                    team_games.append(game)
        
        # 時刻でソート
        team_games.sort(key=lambda g: self._extract_game_time(g) or datetime.max)
        
        self.logger.info(f"🏟️ Found {len(team_games)} games for team '{team_name}' in {days_range} days")
        return team_games
    
    # =============================================================================
    # ユーティリティメソッド
    # =============================================================================
    
    def _format_game_data(self, raw_game: Dict) -> Optional[Dict]:
        """ゲームデータフォーマット（既存のMLBGameManagerと同じ）"""
        try:
            game_id = raw_game.get("id")
            teams = raw_game.get("teams", {})
            home_team = teams.get("home", {}).get("name", "")
            away_team = teams.get("away", {}).get("name", "")
            
            # 日本語チーム名検索
            home_jp = None
            away_jp = None
            for jp_name, en_name in self.TEAM_MAPPING.items():
                if en_name == home_team:
                    home_jp = jp_name
                if en_name == away_team:
                    away_jp = jp_name
            
            # 日時情報
            date_info = raw_game.get("date", "")
            time_info = raw_game.get("time", "")
            datetime_str = f"{date_info} {time_info}" if date_info and time_info else ""
            
            return {
                "id": game_id,
                "home": home_team,
                "away": away_team,
                "home_jp": home_jp,
                "away_jp": away_jp,
                "datetime": datetime_str,
                "league": "MLB",
                "status": raw_game.get("status", {}).get("long", ""),
                "raw": raw_game,
                "realtime": True,  # リアルタイム取得フラグ
                "fetched_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"⚠️ Failed to format MLB game data: {e}")
            return None
    
    def _format_odds_data(self, odds_data: Dict) -> Dict:
        """オッズデータフォーマット"""
        try:
            formatted = {
                "game_id": odds_data.get("game", {}).get("id"),
                "league": "MLB",
                "bookmakers": odds_data.get("bookmakers", []),
                "raw": odds_data,
                "realtime": True,  # リアルタイム取得フラグ
                "fetched_at": datetime.now().isoformat()
            }
            
            # ゲーム情報も含める
            game_info = odds_data.get("game", {})
            if game_info:
                formatted["game"] = self._format_game_data(game_info)
            
            return formatted
            
        except Exception as e:
            self.logger.error(f"⚠️ Failed to format MLB odds data: {e}")
            return odds_data
    
    def _is_game_live(self, game: Dict) -> bool:
        """ゲームがライブ中かチェック"""
        status = game.get("status", "").lower()
        raw_game = game.get("raw", {})
        
        # ステータス文字列チェック
        live_keywords = [
            "in play", "live", "active", "started", 
            "1st inning", "2nd inning", "3rd inning", "4th inning",
            "5th inning", "6th inning", "7th inning", "8th inning", 
            "9th inning", "extra innings", "bottom", "top"
        ]
        
        if any(keyword in status for keyword in live_keywords):
            return True
        
        # 詳細ステータスチェック
        if isinstance(raw_game.get("status"), dict):
            status_long = raw_game["status"].get("long", "").lower()
            status_short = raw_game["status"].get("short", "").lower()
            
            if any(keyword in status_long or keyword in status_short for keyword in live_keywords):
                return True
        
        return False
    
    async def _save_cache_async(self, date_str: str, timezone: str, games: List[Dict]):
        """非同期キャッシュ保存"""
        cache_data = {
            "sport": "mlb",
            "fetch_date": date_str,
            "fetch_time": datetime.now().isoformat(),
            "timezone": timezone,
            "games": games,
            "realtime": True
        }
        
        filename = f"games_{date_str.replace('-', '')}.json"
        filepath = f"{self.cache_dir}/{filename}"
        
        try:
            # 非同期ファイル書き込み（簡易版）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def write_file():
                import os
                os.makedirs(self.cache_dir, exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                return filepath
            
            saved_path = await loop.run_in_executor(None, write_file)
            self.logger.info(f"💾 Cached to {saved_path}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save cache file: {e}")
    
    # =============================================================================
    # 後方互換性メソッド（既存のMLBGameManagerと同じインターフェース）
    # =============================================================================
    
    def fetch_games_sync(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        """同期版ゲーム取得の実装"""
        try:
            # まず現在のループを試す
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # ループが実行中の場合は新しいスレッドで新しいループを作成
                    import concurrent.futures
                    import threading

                    def run_in_new_loop():
                        # 新しいスレッドで新しいイベントループを作成
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(self._fetch_games_async(date, timezone=timezone, **kwargs))
                        finally:
                            new_loop.close()

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_new_loop)
                        return future.result()
                else:
                    # ループが実行中でない場合は直接実行
                    return loop.run_until_complete(self._fetch_games_async(date, timezone=timezone, **kwargs))
            except RuntimeError:
                # イベントループが存在しない場合は新しく作成
                return asyncio.run(self._fetch_games_async(date, timezone=timezone, **kwargs))
        except Exception as e:
            self.logger.error(f"❌ MLB fetch_games_sync error: {str(e)}")
            return []

    def fetch_games(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        """同期版ゲーム取得（後方互換性）"""
        return self.fetch_games_sync(date, timezone=timezone, **kwargs)
    
    def fetch_odds(self, game_id: str, bookmaker_ids: List[int] = None, **kwargs) -> Optional[Dict]:
        """同期版オッズ取得（後方互換性）"""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.get_odds_realtime(game_id, bookmaker_ids, **kwargs))
        except RuntimeError as e:
            # 既存のイベントループがある場合はタスクとして実行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.get_odds_realtime(game_id, bookmaker_ids, **kwargs))
                return future.result()

    async def get_odds_realtime(self, game_id: str, bookmaker_ids: List[int] = None, **kwargs) -> Optional[Dict]:
        """
        リアルタイムオッズ取得（再試行メカニズム付き）

        Args:
            game_id: ゲームID
            bookmaker_ids: ブックメーカーIDリスト
            enable_retries: 再試行を有効にするか (デフォルト: True)
            **kwargs: 追加パラメータ

        Returns:
            オッズデータまたはNone
        """
        return await self._fetch_odds_async(game_id, bookmaker_ids, **kwargs)
    
    # =============================================================================
    # プリゲーム機能拡張
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
            self.logger.info(f"🔍 MLB: {excluded_count} live/finished games excluded")
            self.logger.info(f"✅ {len(pregame_games)} pregame games available")
        
        return pregame_games

    async def get_pregame_mlb_games_realtime(
        self,
        date: datetime,
        buffer_minutes: int = 30,
        **kwargs
    ) -> List[Dict]:
        """インテリジェントプリゲームシステム互換性のためのエイリアス"""
        return await self.get_pregame_games_realtime(date, buffer_minutes, **kwargs)

    async def match_pregame_teams_realtime(
        self, 
        team_names: List[str], 
        date: Optional[datetime] = None,
        buffer_minutes: int = 30, 
        **kwargs
    ) -> Optional[Dict]:
        """チーム名からプリゲーム試合をリアルタイム検索"""
        if date is None:
            date = datetime.now()
        
        pregame_games = await self.get_pregame_games_realtime(date, buffer_minutes, **kwargs)
        return self.match_teams(team_names, pregame_games)