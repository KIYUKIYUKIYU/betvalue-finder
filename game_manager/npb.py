# -*- coding: utf-8 -*-
"""
NPBGameManager
NPB専用の試合管理機能（メインシステム統合版）
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import GameManager


class NPBGameManager(GameManager):
    """NPB専用の試合管理クラス（メインシステム統合版）"""
    
    API_BASE = "https://v1.baseball.api-sports.io"
    LEAGUE_ID = 2  # NPB
    
    # BET HUNTERの既存チームマッピングと統合
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
    
    def __init__(self, api_key: str):
        super().__init__(api_key, cache_dir="data/npb")
        self.team_mapping = {}

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

        # デバッグ: 広島マッピング確認
        print(f"🔧 NPBGameManager initialized. 広島 maps to: {self.team_mapping.get('広島', 'NOT_FOUND')}")
        print(f"🔧 Total mappings: {len(self.team_mapping)}")
        print(f"🔧 Has match_teams method: {hasattr(self, 'match_teams')}")
        
    def match_teams(self, team_names: List[str], games: List[Dict] = None) -> Optional[Dict]:
        """NPB専用チーム名マッチング（双方向正規化）"""
        print(f"🔧 NPBGameManager.match_teams called with: {team_names}")
        print(f"🔧 games parameter: {len(games) if games else 'None'}")
        if games is None:
            print(f"🔧 Loading from cache...")
            games = self.load_latest_cache()
            if not games:
                print(f"🔧 No games from cache, returning None")
                return None
        print(f"🔧 Proceeding with {len(games)} games")

        # 入力チーム名を正規化
        normalized_input_names = set()
        for name in team_names:
            canonical_name = self.team_mapping.get(name, name)
            normalized_input_names.add(canonical_name)
            print(f"Matching NPB teams: {name} -> {canonical_name}")

        # ゲームデータ内の各試合をチェック
        for game in games:
            home_team = game.get("home", "")
            away_team = game.get("away", "")

            # ゲーム内チーム名も正規化
            home_canonical = self.team_mapping.get(home_team, home_team)
            away_canonical = self.team_mapping.get(away_team, away_team)
            game_teams = {home_canonical, away_canonical}

            # 正規化されたチーム名でマッチング
            if normalized_input_names.issubset(game_teams) or game_teams.issubset(normalized_input_names):
                print(f"✅ Found matching NPB game: {home_team} vs {away_team} (canonical: {home_canonical} vs {away_canonical})")
                return game

        print(f"⚠️ No matching NPB game found for {' vs '.join(normalized_input_names)}")
        return None

    def get_sport_name(self) -> str:
        return "NPB"
    
    def _get_canonical_en_name(self, team_name: str) -> str:
        """どんな名前のバリエーションからでも、ただ一つの英語の正式名称を返す"""
        normalized_name = team_name.lower().replace(" ", "").replace(".", "")
        for en_name, details in self.TEAM_MAPPING.items():
            normalized_en_name = en_name.lower().replace(" ", "").replace(".", "")
            if (normalized_name in normalized_en_name or
                normalized_en_name in normalized_name or
                team_name == details["jp_name"] or
                team_name in details["aliases"]):
                return en_name
        return team_name
    
    def _prepare_headers(self, headers: Dict) -> Dict:
        headers["x-apisports-key"] = self.api_key
        return headers
    
    def fetch_games(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        """指定日のNPB試合情報をAPIから取得"""
        date_str = date.strftime("%Y-%m-%d")
        season = date.year
        url = f"{self.API_BASE}/games"
        params = {
            "league": self.LEAGUE_ID, 
            "season": season, 
            "date": date_str,
            "timezone": timezone
        }
        
        try:
            response = self.http_get(url, params=params)
            data = response.json()
            
            remaining = response.headers.get("x-ratelimit-requests-remaining", "?")
            print(f"📊 API calls remaining: {remaining}")
            
            games = []
            for game_data in data.get("response", []):
                game_info = self._format_game_data(game_data)
                if game_info:
                    games.append(game_info)
            
            cache_data = {
                "sport": "npb",
                "fetch_date": date_str,
                "fetch_time": datetime.now().isoformat(),
                "timezone": timezone,
                "games": games
            }
            
            filename = f"games_{date_str.replace('-', '')}.json"
            self.save_cache(cache_data, filename)
            
            print(f"✅ Fetched {len(games)} NPB games for {date_str}")
            return games
            
        except Exception as e:
            print(f"❌ Failed to fetch NPB games: {e}")
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
            print(f"⚠️ Failed to format NPB game data: {e}")
            return None

    def fetch_odds(self, game_id: str, bookmaker_ids: List[int] = None, ttl_seconds: int = 120) -> Optional[Dict]:
        """指定試合のオッズをAPIから取得"""
        if bookmaker_ids is None:
            bookmaker_ids = [4]  # Pinnacle ONLY
            
        # TTLキャッシュ確認
        cache_path = os.path.join(self.cache_dir, f"odds_{game_id}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = __import__("json").load(f)
                ts = cached.get("fetch_time")
                if ts:
                    t = datetime.fromisoformat(ts)
                    if datetime.now() - t <= timedelta(seconds=ttl_seconds):
                        return cached
            except Exception:
                pass

        # NPB特有: まずfixture指定で試行、失敗したらseason+date方式
        url = f"{self.API_BASE}/odds"
        
        # パターン1: baseball APIでは'game'パラメータを使用
        from datetime import datetime
        current_season = datetime.now().year
        params = {
            "game": game_id,
            "season": current_season
        }
        
        try:
            response = self.http_get(url, params=params)
            data = response.json()
            
            odds_data = data.get("response", [])
            if odds_data:
                # game指定で成功
                odds_entry = odds_data[0]
                result = self._process_odds_data(odds_entry, game_id, bookmaker_ids)
                if result:
                    self._save_odds_cache(result, cache_path)
                    return result
                    
        except Exception as e:
            print(f"⚠️ Game-based NPB odds failed for {game_id}: {e}")
        
        # パターン2: season+league方式（NPB推奨、dateは除外）
        print(f"🔄 Trying season-only approach for NPB game {game_id}...")
        today = datetime.now()
        params = {
            "league": self.LEAGUE_ID,  # NPB = 2
            "season": today.year       # 2025 (dateは除外)
        }
        
        try:
            response = self.http_get(url, params=params)
            data = response.json()
            
            odds_data = data.get("response", [])
            print(f"📊 Found {len(odds_data)} NPB odds entries for season {params['season']}")
            
            # 指定game_idのオッズを検索 (NPBは"game"フィールドを使用)
            target_odds = None
            for odds_entry in odds_data:
                # NPB API では "game" フィールドに試合情報が格納される
                game_info = odds_entry.get("game", {})
                if str(game_info.get("id", "")) == str(game_id):
                    target_odds = odds_entry
                    print(f"🎯 Found matching game: {game_info.get('teams', {}).get('home', {}).get('name')} vs {game_info.get('teams', {}).get('away', {}).get('name')}")
                    break
                    
            if not target_odds:
                print(f"⚠️ No NPB odds found for game {game_id} in {len(odds_data)} entries")
                return None
                
            result = self._process_odds_data(target_odds, game_id, bookmaker_ids)
            if result:
                self._save_odds_cache(result, cache_path)
                print(f"✅ Successfully retrieved NPB odds for game {game_id}")
                return result
                
        except Exception as e:
            print(f"❌ Season-based NPB odds failed: {e}")
            return None
            
        return None
    
    def _process_odds_data(self, odds_entry: Dict, game_id: str, bookmaker_ids: List[int]) -> Optional[Dict]:
        """オッズデータを処理してフィルタリング"""
        filtered_bookmakers = []
        for bm in odds_entry.get("bookmakers", []):
            try:
                bid = int(bm.get("id", -1))
            except Exception:
                bid = -1
            if bid in bookmaker_ids:
                filtered_bookmakers.append(bm)
                
        # Pinnacleが無い場合はエラー（フォールバックなし）
        if not filtered_bookmakers:
            print(f"❌ ERROR: No Pinnacle odds available for NPB game {game_id}")
            return None
            
        if not filtered_bookmakers:
            return None
            
        return {
            "game_id": game_id,
            "bookmakers": filtered_bookmakers,
            "fetch_time": datetime.now().isoformat()
        }
    
    def _save_odds_cache(self, result: Dict, cache_path: str) -> None:
        """オッズキャッシュを保存"""
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                __import__("json").dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to save odds cache: {e}")

    def match_teams(self, teams: List[str], games: Optional[List[Dict]] = None) -> Optional[Dict]:
        """チーム名リストから該当する試合を特定"""
        # 照合対象のゲームリストを用意（複数日のキャッシュから検索）
        if games is None:
            games = self.load_all_recent_cache(days_back=7)
            if not games:
                # フォールバック：最新キャッシュのみ試す
                games = self.load_latest_cache()
                if not games:
                    print("⚠️ No cached NPB games available for team matching")
                    return None

        if len(teams) < 2:
            print("❌ Need at least 2 team names for matching")
            return None

        def norm(s: str) -> str:
            return (
                (s or "")
                .lower()
                .replace(".", "")
                .replace(" ", "")
                .replace("-", "")
            )

        input_a_canonical = self._get_canonical_en_name(teams[0])
        input_b_canonical = self._get_canonical_en_name(teams[1])

        print(f"Matching NPB teams: {teams[0]} -> {input_a_canonical}, {teams[1]} -> {input_b_canonical}")

        for game in games:
            game_home_canonical = self._get_canonical_en_name(game.get("home", ""))
            game_away_canonical = self._get_canonical_en_name(game.get("away", ""))

            if ((input_a_canonical == game_home_canonical and input_b_canonical == game_away_canonical) or 
                (input_a_canonical == game_away_canonical and input_b_canonical == game_home_canonical)):
                print(f"✅ Found matching NPB game: {game_home_canonical} vs {game_away_canonical}")
                return {"id": game.get("id"), "home": game.get("home"), "away": game.get("away")}
                
        print(f"⚠️ No matching NPB game found for {input_a_canonical} vs {input_b_canonical}")
        return None