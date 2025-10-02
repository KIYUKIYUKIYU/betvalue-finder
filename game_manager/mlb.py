# -*- coding: utf-8 -*-
"""
MLBGameManager
MLB専用の試合管理機能
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import GameManager


class MLBGameManager(GameManager):
    """MLB専用の試合管理クラス"""
    
    API_BASE = "https://v1.baseball.api-sports.io"
    LEAGUE_ID = 1  # MLB
    
    # 日本語→英語チーム名マッピング
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
    
    def __init__(self, api_key: str, cache_dir: str = "data/mlb", enable_ttl_cache: bool = True, ttl_config=None):
        super().__init__(api_key, cache_dir=cache_dir, enable_ttl_cache=enable_ttl_cache, ttl_config=ttl_config)
        self.team_mapping = self.TEAM_MAPPING
        
    def get_sport_name(self) -> str:
        return "MLB"
    
    def _prepare_headers(self, headers: Dict) -> Dict:
        headers["x-apisports-key"] = self.api_key
        return headers
    
    def fetch_games(self, date: datetime, timezone: str = "Asia/Tokyo", **kwargs) -> List[Dict]:
        date_str = date.strftime("%Y-%m-%d")
        season = date.year
        
        url = f"{self.API_BASE}/games"
        params = {
            "league": self.LEAGUE_ID,
            "season": season,
            "date": date_str,
            "timezone": timezone,
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
                "sport": "mlb",
                "fetch_date": date_str,
                "fetch_time": datetime.now().isoformat(),
                "timezone": timezone,
                "games": games
            }
            
            filename = f"games_{date_str.replace('-', '')}.json"
            self.save_cache(cache_data, filename)
            
            print(f"✅ Fetched {len(games)} MLB games for {date_str}")
            return games
            
        except Exception as e:
            print(f"❌ Failed to fetch games: {e}")
            return []
    
    def _format_game_data(self, raw_game: Dict) -> Optional[Dict]:
        try:
            game_id = raw_game.get("id")
            teams = raw_game.get("teams", {})
            home_team = teams.get("home", {}).get("name", "")
            away_team = teams.get("away", {}).get("name", "")
            
            home_jp = None
            away_jp = None
            for jp_name, en_name in self.TEAM_MAPPING.items():
                if en_name == home_team:
                    home_jp = jp_name
                if en_name == away_team:
                    away_jp = jp_name
            
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
                "raw": raw_game
            }
            
        except Exception as e:
            print(f"⚠️ Failed to format game data: {e}")
            return None
    
    def fetch_odds(self, game_id: str, bookmaker_ids: List[int] = None, ttl_seconds: int = 120) -> Optional[Dict]:
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

        url = f"{self.API_BASE}/odds"
        params = {"game": game_id}
        
        try:
            response = self.http_get(url, params=params)
            data = response.json()
            
            odds_data = data.get("response", [])
            if not odds_data:
                print(f"⚠️ No odds found for game {game_id}")
                return None
            
            odds_entry = odds_data[0]
            
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
                print(f"❌ ERROR: No Pinnacle odds available for game {game_id}")
                return None
            
            result = {
                "game_id": game_id,
                "bookmakers": filtered_bookmakers,
                "fetch_time": datetime.now().isoformat()
            }
            # キャッシュ保存
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                with open(cache_path, "w", encoding="utf-8") as f:
                    __import__("json").dump(result, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return result
            
        except Exception as e:
            print(f"❌ Failed to fetch odds for game {game_id}: {e}")
            return None

    def match_teams(self, teams: List[str], games: Optional[List[Dict]] = None) -> Optional[Dict]:
        """チーム名から当日の試合をキャッシュ経由で検索（正規化つき）
        gamesが与えられた場合はそれを優先して照合する。
        """
        def norm(s: str) -> str:
            return (
                (s or "")
                .lower()
                .replace(".", "")
                .replace(" ", "")
                .replace("-", "")
            )

        # 照合対象のゲームリストを用意（複数日のキャッシュから検索）
        if games is None:
            games = self.load_all_recent_cache(days_back=7)
            if not games:
                # フォールバック：最新キャッシュのみ試す
                games = self.load_latest_cache()
                if not games:
                    return None

        # 日本語→英語へ正規化
        team_a_jp = teams[0]
        team_b_jp = teams[1]
        team_a_en = self.TEAM_MAPPING.get(team_a_jp, team_a_jp)
        team_b_en = self.TEAM_MAPPING.get(team_b_jp, team_b_jp)

        a = norm(team_a_en)
        b = norm(team_b_en)

        for g in games:
            home = g.get("home") or g.get("raw", {}).get("teams", {}).get("home", {}).get("name", "")
            away = g.get("away") or g.get("raw", {}).get("teams", {}).get("away", {}).get("name", "")
            game_id = g.get("id") or g.get("raw", {}).get("id")

            nh = norm(home)
            na = norm(away)

            if (a == nh and b == na) or (a == na and b == nh):
                return {"id": game_id, "home": home, "away": away}

            # 日本語名でも突き合わせ（home_jp/away_jp）
            home_jp = g.get("home_jp") or ""
            away_jp = g.get("away_jp") or ""
            nhj = norm(home_jp)
            naj = norm(away_jp)
            aj = norm(self.TEAM_MAPPING.get(team_a_jp, team_a_jp))  # 既に英訳済みだが念のため
            bj = norm(self.TEAM_MAPPING.get(team_b_jp, team_b_jp))
            # 直接日本語比較（記号・空白無視）
            ta_j = norm(team_a_jp)
            tb_j = norm(team_b_jp)
            if (ta_j == nhj and tb_j == naj) or (ta_j == naj and tb_j == nhj):
                return {"id": game_id, "home": home, "away": away}

        return None
