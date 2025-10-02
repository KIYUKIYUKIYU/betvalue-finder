# -*- coding: utf-8 -*-
"""
PregameFilter
プリゲーム（試合開始前）のゲームのみを対象とするフィルタリングクラス
"""

from datetime import datetime
from typing import Dict, List, Optional


class PregameFilter:
    """プリゲーム専用フィルタリングクラス"""
    
    # 試合開始前を示すステータス
    PREGAME_STATUSES = {
        # MLB/NPB
        "Not Started", "Scheduled", "Postponed", "Delayed", "Pre-Game",
        # Soccer
        "Not Started", "TBD", "NS", "PST", 
        # 共通
        "SCHEDULED", "PREGAME", "PRE_GAME"
    }
    
    # 開始済み/終了済みを示すステータス（除外対象）
    EXCLUDE_STATUSES = {
        # 試合中
        "In Progress", "1st Period", "2nd Period", "3rd Period", "4th Period",
        "1H", "2H", "HT", "Break", "Live", "LIVE",
        # 終了済み
        "Finished", "Final", "Game Finished", "Match Finished", 
        "FT", "AET", "PEN", "COMPLETE", "COMPLETED",
        # 中止
        "Cancelled", "Abandoned", "CANCELLED", "ABANDONED"
    }
    
    @classmethod
    def is_pregame_status(cls, status: str) -> bool:
        """ステータスがプリゲーム（試合開始前）かを判定"""
        if not status:
            return False
            
        status_clean = status.strip()
        
        # プリゲームステータスの場合
        if status_clean in cls.PREGAME_STATUSES:
            return True
            
        # 除外ステータスの場合
        if status_clean in cls.EXCLUDE_STATUSES:
            return False
            
        # 不明なステータスは保守的にプリゲーム扱い
        return True
    
    @classmethod
    def is_pregame_datetime(cls, game_datetime: str, buffer_minutes: int = 30) -> bool:
        """
        試合時刻がプリゲーム（現在時刻より十分先）かを判定
        buffer_minutes: 試合開始前の最低余裕時間（分）
        """
        if not game_datetime:
            return False
            
        try:
            # ISO形式の日時をパース
            game_dt = datetime.fromisoformat(game_datetime.replace('Z', '+00:00'))
            now = datetime.now(game_dt.tzinfo) if game_dt.tzinfo else datetime.now()
            
            # 試合開始まで十分な時間があるか
            time_diff = (game_dt - now).total_seconds() / 60  # 分単位
            return time_diff >= buffer_minutes
            
        except Exception:
            # 日時パース失敗時は保守的にTrue
            return True
    
    @classmethod
    def filter_pregame_games(cls, games: List[Dict], buffer_minutes: int = 30) -> List[Dict]:
        """ゲームリストからプリゲームの試合のみをフィルタ"""
        pregame_games = []
        
        for game in games:
            # ステータスチェック
            status = game.get("status") or game.get("raw", {}).get("status", {}).get("long", "")
            if not cls.is_pregame_status(status):
                continue
                
            # 日時チェック
            datetime_str = game.get("datetime") or game.get("raw", {}).get("fixture", {}).get("date", "")
            if not cls.is_pregame_datetime(datetime_str, buffer_minutes):
                continue
                
            pregame_games.append(game)
            
        return pregame_games
    
    @classmethod
    def get_game_status_info(cls, game: Dict) -> Dict[str, str]:
        """ゲームのステータス情報を取得（デバッグ用）"""
        status = game.get("status", "")
        raw_status = game.get("raw", {}).get("status", {})
        raw_long = raw_status.get("long", "") if raw_status else ""
        raw_short = raw_status.get("short", "") if raw_status else ""
        datetime_str = game.get("datetime", "")
        
        return {
            "main_status": status,
            "raw_long": raw_long,
            "raw_short": raw_short,
            "datetime": datetime_str,
            "is_pregame_status": cls.is_pregame_status(status) or cls.is_pregame_status(raw_long),
            "is_pregame_datetime": cls.is_pregame_datetime(datetime_str)
        }