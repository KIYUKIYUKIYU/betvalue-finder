# -*- coding: utf-8 -*-
"""
GameManager基底クラス
全スポーツ共通の試合管理機能を定義
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from .pregame_filter import PregameFilter
from .ttl_cache_manager import TTLCacheManager, DataType, TTLConfig


class GameManager(ABC):
    """試合管理の基底クラス"""
    
    def __init__(self, api_key: str, cache_dir: str = "data", enable_ttl_cache: bool = True, ttl_config: TTLConfig = None):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.team_mapping = {}
        
        # TTLキャッシュマネージャーの初期化
        self.enable_ttl_cache = enable_ttl_cache
        if enable_ttl_cache:
            ttl_cache_dir = os.path.join(cache_dir, "ttl_cache")
            self.ttl_cache = TTLCacheManager(cache_dir=ttl_cache_dir, config=ttl_config)
        else:
            self.ttl_cache = None
        
    @abstractmethod
    def fetch_games(self, date: datetime, **kwargs) -> List[Dict]:
        pass
    
    @abstractmethod
    def fetch_odds(self, game_id: str, bookmaker_ids: List[int] = None) -> Optional[Dict]:
        pass
    
    def match_teams(self, team_names: List[str], games: List[Dict] = None) -> Optional[Dict]:
        if games is None:
            games = self.load_latest_cache()
            if not games:
                return None

        normalized_names = set()
        for name in team_names:
            if name in self.team_mapping:
                normalized_names.add(self.team_mapping[name])
            else:
                normalized_names.add(name)
                
        for game in games:
            game_teams = {game.get("home"), game.get("away")}
            if normalized_names.issubset(game_teams) or game_teams.issubset(normalized_names):
                return game
                
        return None
    
    def save_cache(self, data: Dict, filename: str = None) -> str:
        if filename is None:
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"games_{date_str}.json"
            
        filepath = os.path.join(self.cache_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Saved: {filepath}")
        return filepath
    
    def load_cache(self, filename: str, use_ttl: bool = None) -> Optional[Dict]:
        """
        キャッシュからデータを読み込み（TTL対応）
        
        Args:
            filename: ファイル名
            use_ttl: TTLキャッシュを使用するか（None=自動判定）
            
        Returns:
            キャッシュデータまたはNone
        """
        # TTL使用判定
        if use_ttl is None:
            use_ttl = self.enable_ttl_cache
        
        # TTLキャッシュから取得を試行
        if use_ttl and self.ttl_cache:
            cached_data = self.ttl_cache.get(f"file_{filename}")
            if cached_data is not None:
                print(f"✅ TTL cache hit for {filename}")
                return cached_data
        
        # 従来のファイル読み込み
        filepath = os.path.join(self.cache_dir, filename)
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # TTLキャッシュに保存
            if use_ttl and self.ttl_cache and data:
                self.ttl_cache.set(f"file_{filename}", data, DataType.GAME_DATA)
                print(f"📁 Cached {filename} to TTL cache")
            
            return data
            
        except Exception as e:
            print(f"⚠️ Failed to load cache file {filename}: {e}")
            return None
    
    def load_latest_cache(self) -> Optional[List[Dict]]:
        cache_files = []
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                if file.startswith("games_") and file.endswith(".json"):
                    cache_files.append(file)

        if not cache_files:
            return None

        # 逆順（最新から古い順）でファイルを確認し、ゲームデータがあるファイルを探す
        for filename in sorted(cache_files, reverse=True):
            data = self.load_cache(filename)
            if data and "games" in data and data["games"]:
                print(f"✅ Using cache file {filename} with {len(data['games'])} games")
                return data["games"]
            elif data and isinstance(data, list) and data:
                print(f"✅ Using cache file {filename} with {len(data)} games (direct list)")
                return data

        print("⚠️ No cache files with game data found")
        return None
    
    def load_all_recent_cache(self, days_back: int = 7) -> List[Dict]:
        """複数日のキャッシュファイルから試合データを読み込み"""
        all_games = []
        cache_files = []
        
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                if file.startswith("games_") and file.endswith(".json"):
                    cache_files.append(file)
        
        if not cache_files:
            return []
        
        # 最新からdays_back日分のファイルを取得
        recent_files = sorted(cache_files)[-days_back:]
        
        for filename in recent_files:
            try:
                data = self.load_cache(filename)
                if data and "games" in data:
                    all_games.extend(data["games"])
            except Exception as e:
                print(f"⚠️ Failed to load cache file {filename}: {e}")
                continue
        
        return all_games
    
    def http_get(self, url: str, headers: Dict = None, params: Dict = None) -> requests.Response:
        if headers is None:
            headers = {}
            
        headers = self._prepare_headers(headers)
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            raise
    
    def _prepare_headers(self, headers: Dict) -> Dict:
        return headers
    
    @abstractmethod
    def get_sport_name(self) -> str:
        pass
    
    def fetch_pregame_games(self, date: datetime, buffer_minutes: int = 30, **kwargs) -> List[Dict]:
        """プリゲーム（試合開始前）の試合のみを取得"""
        all_games = self.fetch_games(date, **kwargs)
        pregame_games = PregameFilter.filter_pregame_games(all_games, buffer_minutes)
        
        if len(pregame_games) < len(all_games):
            excluded_count = len(all_games) - len(pregame_games)
            print(f"🔍 {self.get_sport_name()}: {excluded_count} live/finished games excluded")
            print(f"✅ {len(pregame_games)} pregame games available")
        
        return pregame_games
    
    def match_pregame_teams(self, team_names: List[str], date: Optional[datetime] = None, 
                           buffer_minutes: int = 30, **kwargs) -> Optional[Dict]:
        """チーム名から当日のプリゲーム試合を検索"""
        if date:
            games = self.fetch_pregame_games(date, buffer_minutes, **kwargs)
        else:
            # キャッシュから取得してフィルタ
            all_games = self.load_latest_cache()
            if not all_games:
                return None
            games = PregameFilter.filter_pregame_games(all_games, buffer_minutes)
        
        return self.match_teams(team_names, games)
    
    def debug_game_statuses(self, games: List[Dict]) -> None:
        """ゲームステータスのデバッグ情報を表示"""
        print(f"\n=== {self.get_sport_name()} Game Status Debug ===")
        for i, game in enumerate(games[:5]):  # 最初の5試合のみ
            status_info = PregameFilter.get_game_status_info(game)
            teams = f"{game.get('away', 'N/A')} @ {game.get('home', 'N/A')}"
            print(f"Game {i+1}: {teams}")
            print(f"  Status: {status_info['main_status']} | Raw: {status_info['raw_long']}")
            print(f"  DateTime: {status_info['datetime']}")
            print(f"  Pregame: Status={status_info['is_pregame_status']}, Time={status_info['is_pregame_datetime']}")
            print()
    
    # TTLキャッシュ統合メソッド
    
    def cache_games(self, games: List[Dict], date: datetime = None, cache_key_suffix: str = "") -> bool:
        """
        試合データをTTLキャッシュに保存
        
        Args:
            games: 試合データのリスト
            date: 対象日付
            cache_key_suffix: キャッシュキーの接尾辞
        
        Returns:
            成功フラグ
        """
        if not self.ttl_cache:
            return False
            
        try:
            date_str = date.strftime("%Y-%m-%d") if date else datetime.now().strftime("%Y-%m-%d")
            cache_key = f"games_{date_str}_{self.get_sport_name().lower()}{cache_key_suffix}"
            
            # ゲームデータを分類してキャッシュ
            active_games = []
            regular_games = []
            
            for game in games:
                if self._is_active_game(game):
                    active_games.append(game)
                else:
                    regular_games.append(game)
            
            # アクティブゲームは短いTTL、通常ゲームは長いTTL
            if active_games:
                self.ttl_cache.set(f"{cache_key}_active", active_games, DataType.ACTIVE_GAME)
            
            if regular_games:
                self.ttl_cache.set(f"{cache_key}_regular", regular_games, DataType.GAME_DATA)
            
            # 全体もキャッシュ
            self.ttl_cache.set(cache_key, games, DataType.GAME_DATA)
            
            print(f"🏆 Cached {len(games)} games ({len(active_games)} active, {len(regular_games)} regular)")
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to cache games: {e}")
            return False
    
    def get_cached_games(self, date: datetime = None, cache_key_suffix: str = "", include_active: bool = True) -> Optional[List[Dict]]:
        """
        TTLキャッシュから試合データを取得
        
        Args:
            date: 対象日付
            cache_key_suffix: キャッシュキーの接尾辞
            include_active: アクティブゲームを含めるか
        
        Returns:
            試合データのリストまたはNone
        """
        if not self.ttl_cache:
            return None
            
        try:
            date_str = date.strftime("%Y-%m-%d") if date else datetime.now().strftime("%Y-%m-%d")
            cache_key = f"games_{date_str}_{self.get_sport_name().lower()}{cache_key_suffix}"
            
            # 全体キャッシュから取得を試行
            games = self.ttl_cache.get(cache_key)
            if games is not None:
                return games
            
            # 分離されたキャッシュから統合して取得
            regular_games = self.ttl_cache.get(f"{cache_key}_regular", [])
            active_games = self.ttl_cache.get(f"{cache_key}_active", []) if include_active else []
            
            if regular_games or active_games:
                combined_games = regular_games + active_games
                print(f"🔄 Reconstructed {len(combined_games)} games from split cache")
                return combined_games
            
            return None
            
        except Exception as e:
            print(f"⚠️ Failed to get cached games: {e}")
            return None
    
    def cache_odds(self, game_id: str, odds_data: Dict, is_live: bool = False) -> bool:
        """
        オッズデータをTTLキャッシュに保存
        
        Args:
            game_id: ゲームID
            odds_data: オッズデータ
            is_live: ライブオッズかどうか
        
        Returns:
            成功フラグ
        """
        if not self.ttl_cache:
            return False
            
        try:
            cache_key = f"odds_{game_id}_{self.get_sport_name().lower()}"
            data_type = DataType.LIVE_ODDS if is_live else DataType.ODDS_DATA
            
            # 試合データを含む場合は動的TTLを活用
            game_data = odds_data.get('game') or odds_data.get('fixture')
            
            self.ttl_cache.set(cache_key, odds_data, data_type)
            
            ttl_info = "live" if is_live else "regular"
            print(f"📊 Cached {ttl_info} odds for game {game_id}")
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to cache odds for game {game_id}: {e}")
            return False
    
    def get_cached_odds(self, game_id: str) -> Optional[Dict]:
        """
        TTLキャッシュからオッズデータを取得
        
        Args:
            game_id: ゲームID
        
        Returns:
            オッズデータまたはNone
        """
        if not self.ttl_cache:
            return None
            
        cache_key = f"odds_{game_id}_{self.get_sport_name().lower()}"
        return self.ttl_cache.get(cache_key)
    
    def _is_active_game(self, game: Dict) -> bool:
        """
        ゲームがアクティブ（開始間近またはライブ）かを判定
        
        Args:
            game: ゲームデータ
        
        Returns:
            アクティブかどうか
        """
        try:
            # ステータスでの判定
            status = game.get('status', {})
            if isinstance(status, dict):
                status_long = status.get('long', '').lower()
                status_short = status.get('short', '').lower()
                
                # ライブまたは進行中のステータス
                live_keywords = ['live', 'in play', 'active', 'started', '1st half', '2nd half', 'halftime']
                if any(keyword in status_long for keyword in live_keywords):
                    return True
                if any(keyword in status_short for keyword in live_keywords):
                    return True
            
            # 時刻での判定（開始2時間以内）
            game_time = self._extract_game_time(game)
            if game_time:
                time_diff = (game_time - datetime.now()).total_seconds()
                # 開始2時間前から開始3時間後まで
                return -10800 <= time_diff <= 7200
            
            return False
            
        except Exception:
            return False
    
    def _extract_game_time(self, game: Dict) -> Optional[datetime]:
        """ゲームデータから開始時刻を抽出（ttl_cache_manager.pyの同等機能）"""
        time_fields = ['datetime', 'start_time', 'game_time', 'scheduled_time', 'commence_time']
        date_fields = ['date', 'game_date']
        
        for field in time_fields:
            if field in game and game[field]:
                try:
                    if isinstance(game[field], str):
                        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                            try:
                                return datetime.strptime(game[field], fmt)
                            except ValueError:
                                continue
                    elif isinstance(game[field], datetime):
                        return game[field]
                except Exception:
                    continue
        
        for field in date_fields:
            if field in game and game[field]:
                try:
                    if isinstance(game[field], str):
                        return datetime.strptime(game[field], '%Y-%m-%d')
                except Exception:
                    continue
        
        return None
    
    def get_ttl_cache_stats(self) -> Dict:
        """TTLキャッシュの統計情報を取得"""
        if not self.ttl_cache:
            return {"ttl_cache_enabled": False}
        
        stats = self.ttl_cache.get_stats()
        stats["ttl_cache_enabled"] = True
        return stats
    
    def clear_ttl_cache(self) -> bool:
        """TTLキャッシュをクリア"""
        if not self.ttl_cache:
            return False
        
        try:
            self.ttl_cache.clear()
            print("🧹 TTL cache cleared")
            return True
        except Exception as e:
            print(f"⚠️ Failed to clear TTL cache: {e}")
            return False
