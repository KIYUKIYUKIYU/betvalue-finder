# -*- coding: utf-8 -*-
"""
GameID解決システム
競技別の試合ID取得機能を統合管理
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from enum import Enum

from .mlb import MLBGameManager
from .npb import NPBGameManager
from .soccer import SoccerGameManager


class SportType(Enum):
    """対応スポーツタイプ"""
    MLB = "mlb"
    NPB = "npb" 
    SOCCER = "soccer"
    
    @classmethod
    def from_string(cls, sport_str: str) -> 'SportType':
        """文字列からスポーツタイプを取得"""
        sport_lower = sport_str.lower()
        for sport in cls:
            if sport.value == sport_lower:
                return sport
        raise ValueError(f"Unsupported sport: {sport_str}")


class GameIDResolver:
    """競技横断的な試合ID解決システム"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._managers: Dict[SportType, Any] = {}
        self._initialize_managers()
    
    def _initialize_managers(self) -> None:
        """各競技のGameManagerを初期化"""
        self._managers = {
            SportType.MLB: MLBGameManager(self.api_key),
            SportType.NPB: NPBGameManager(self.api_key),
            SportType.SOCCER: SoccerGameManager(self.api_key),
        }
    
    def get_manager(self, sport: Union[str, SportType]) -> Any:
        """指定競技のGameManagerを取得"""
        if isinstance(sport, str):
            sport = SportType.from_string(sport)
        
        if sport not in self._managers:
            raise ValueError(f"Manager not found for sport: {sport}")
        
        return self._managers[sport]
    
    def resolve_game_id(
        self, 
        sport: Union[str, SportType],
        team_names: List[str],
        target_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        チーム名から試合IDを解決
        
        Args:
            sport: 競技名
            team_names: チーム名のリスト（2つ）
            target_date: 対象日付（None時は当日）
            use_cache: キャッシュ利用するか
            
        Returns:
            試合情報辞書 {"id": game_id, "home": home_team, "away": away_team} or None
        """
        if len(team_names) != 2:
            raise ValueError("team_names must contain exactly 2 teams")
        
        manager = self.get_manager(sport)
        
        # キャッシュから検索を試行
        if use_cache:
            cached_games = manager.load_latest_cache()
            if cached_games:
                match = manager.match_teams(team_names, cached_games)
                if match:
                    return match
        
        # キャッシュにない場合、APIから取得
        if target_date is None:
            target_date = datetime.now()
            
        print(f"🔍 Fetching {sport} games for {target_date.strftime('%Y-%m-%d')}...")
        games = manager.fetch_games(target_date)
        
        if not games:
            print(f"⚠️ No games found for {sport} on {target_date.strftime('%Y-%m-%d')}")
            return None
        
        # 新しく取得したゲームから検索
        match = manager.match_teams(team_names, games)
        if match:
            print(f"✅ Found game: {match['home']} vs {match['away']} (ID: {match['id']})")
            return match
        else:
            print(f"⚠️ No matching game found for teams: {team_names}")
            return None
    
    def fetch_odds_for_game(
        self,
        sport: Union[str, SportType], 
        game_id: str,
        bookmaker_ids: Optional[List[int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        指定試合のオッズデータを取得
        
        Args:
            sport: 競技名
            game_id: 試合ID
            bookmaker_ids: ブックメーカーID（None時はデフォルト）
            
        Returns:
            オッズデータ辞書 or None
        """
        manager = self.get_manager(sport)
        return manager.fetch_odds(game_id, bookmaker_ids)
    
    def resolve_and_fetch_odds(
        self,
        sport: Union[str, SportType],
        team_names: List[str],
        target_date: Optional[datetime] = None,
        bookmaker_ids: Optional[List[int]] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        チーム名から試合IDを解決してオッズデータを取得（ワンストップ処理）
        
        Args:
            sport: 競技名
            team_names: チーム名のリスト（2つ）
            target_date: 対象日付（None時は当日）
            bookmaker_ids: ブックメーカーID（None時はデフォルト）
            use_cache: キャッシュ利用するか
            
        Returns:
            オッズデータ辞書 or None
        """
        # 試合ID解決
        game_info = self.resolve_game_id(sport, team_names, target_date, use_cache)
        if not game_info:
            return None
        
        game_id = game_info["id"]
        if not game_id:
            print("⚠️ Game ID not found in resolved game info")
            return None
        
        # オッズ取得
        print(f"📊 Fetching odds for game ID: {game_id}...")
        odds_data = self.fetch_odds_for_game(sport, game_id, bookmaker_ids)
        
        if odds_data:
            # ゲーム情報を追加
            odds_data["game_info"] = game_info
            print(f"✅ Successfully fetched odds for {game_info['home']} vs {game_info['away']}")
        else:
            print(f"❌ Failed to fetch odds for game ID: {game_id}")
        
        return odds_data
    
    def get_available_sports(self) -> List[str]:
        """利用可能なスポーツリストを取得"""
        return [sport.value for sport in SportType]
    
    def get_manager_status(self) -> Dict[str, Dict[str, Any]]:
        """各マネージャーのステータス情報を取得"""
        status = {}
        for sport, manager in self._managers.items():
            try:
                latest_cache = manager.load_latest_cache()
                cache_count = len(latest_cache) if latest_cache else 0
                status[sport.value] = {
                    "manager_class": manager.__class__.__name__,
                    "cached_games": cache_count,
                    "cache_dir": manager.cache_dir,
                    "status": "ready"
                }
            except Exception as e:
                status[sport.value] = {
                    "manager_class": manager.__class__.__name__,
                    "error": str(e),
                    "status": "error"
                }
        return status


# 便利関数（後方互換性）
def create_game_id_resolver(api_key: str) -> GameIDResolver:
    """GameIDResolverインスタンスを作成"""
    return GameIDResolver(api_key)


def resolve_game_id_for_sport(
    api_key: str,
    sport: str,
    team_names: List[str],
    target_date: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """指定競技のチーム名から試合IDを解決（便利関数）"""
    resolver = GameIDResolver(api_key)
    return resolver.resolve_game_id(sport, team_names, target_date)