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


class GameManager(ABC):
    """試合管理の基底クラス"""
    
    def __init__(self, api_key: str, cache_dir: str = "data"):
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.team_mapping = {}
        
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
    
    def load_cache(self, filename: str) -> Optional[Dict]:
        filepath = os.path.join(self.cache_dir, filename)
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def load_latest_cache(self) -> Optional[List[Dict]]:
        cache_files = []
        if os.path.exists(self.cache_dir):
            for file in os.listdir(self.cache_dir):
                if file.startswith("games_") and file.endswith(".json"):
                    cache_files.append(file)
                    
        if not cache_files:
            return None
            
        latest_file = sorted(cache_files)[-1]
        data = self.load_cache(latest_file)
        
        if data and "games" in data:
            return data["games"]
        return data
    
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
