# -*- coding: utf-8 -*-
"""
MLBGameManager
MLB専用の試合管理機能
"""

import os
from datetime import datetime
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
        "マーリンズ": "Miami Marlins",
    }
    
    def __init__(self, api_key: str):
        super().__init__(api_key, cache_dir="data/mlb")
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
    
    def fetch_odds(self, game_id: str, bookmaker_ids: List[int] = None) -> Optional[Dict]:
        if bookmaker_ids is None:
            bookmaker_ids = [4, 2]  # Pinnacle, Bet365
            
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
                if int(bm.get("id", -1)) in bookmaker_ids:
                    filtered_bookmakers.append(bm)
            
            if not filtered_bookmakers:
                print(f"⚠️ No odds from specified bookmakers for game {game_id}")
                return None
            
            return {
                "game_id": game_id,
                "bookmakers": filtered_bookmakers,
                "fetch_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Failed to fetch odds for game {game_id}: {e}")
            return None

    def match_teams(self, teams: List[str]) -> Optional[Dict]:
        """チーム名から試合を検索"""
        from datetime import datetime
        import json
        import os
        
        # 今日の日付
        today = datetime.now().strftime("%Y%m%d")
        data_file = f"data/baseball_odds_{today}.json"
        
        # データファイルが存在しない場合はNone
        if not os.path.exists(data_file):
            return None
            
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # データ構造の判定
            if isinstance(data, list):
                games = data
            elif isinstance(data, dict) and 'response' in data:
                games = data['response']
            else:
                return None
            
            # 日本語名を英語名に変換
            team_a_jp = teams[0]
            team_b_jp = teams[1]
            team_a_en = self.TEAM_MAPPING.get(team_a_jp, team_a_jp)
            team_b_en = self.TEAM_MAPPING.get(team_b_jp, team_b_jp)
            
            # 試合を検索
            for game in games:
                if 'game' in game and 'teams' in game['game']:
                    home = game['game']['teams'].get('home', {}).get('name', '')
                    away = game['game']['teams'].get('away', {}).get('name', '')
                    game_id = game['game'].get('id')
                elif 'home' in game and 'away' in game:
                    home = game.get('home', {}).get('name', '')
                    away = game.get('away', {}).get('name', '')
                    game_id = game.get('id')
                else:
                    continue
                
                # チーム名でマッチング（部分一致も考慮）
                if (team_a_en in home and team_b_en in away) or \
                   (team_b_en in home and team_a_en in away) or \
                   (team_a_en in away and team_b_en in home) or \
                   (team_b_en in away and team_a_en in home):
                    return {
                        'id': game_id,
                        'home': home,
                        'away': away
                    }
                    
        except Exception as e:
            print(f"Error in match_teams: {e}")
            return None
        
        return None
