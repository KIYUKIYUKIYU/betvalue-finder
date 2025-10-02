"""
Game Manager モジュール
試合情報とオッズ管理の統合システム (Phase 2: リアルタイム対応)
"""

# 既存の同期管理クラス
from .base import GameManager
from .mlb import MLBGameManager
from .npb import NPBGameManager
from .soccer import SoccerGameManager

# Phase 2: リアルタイム管理クラス
from .realtime_game_manager import RealtimeGameManager, RealtimeConfig
from .realtime_mlb import RealtimeMLBGameManager
from .realtime_soccer import RealtimeSoccerGameManager

# TTL キャッシュ管理
from .ttl_cache_manager import TTLCacheManager, TTLConfig, DataType

# ゲームID解決
from .game_id_resolver import GameIDResolver, SportType, create_game_id_resolver, resolve_game_id_for_sport

__all__ = [
    # 従来の同期管理クラス
    "GameManager", 
    "MLBGameManager", 
    "NPBGameManager", 
    "SoccerGameManager",
    
    # Phase 2: リアルタイム管理クラス
    "RealtimeGameManager",
    "RealtimeMLBGameManager", 
    "RealtimeSoccerGameManager",
    "RealtimeConfig",
    
    # TTL キャッシュ
    "TTLCacheManager",
    "TTLConfig",
    "DataType",
    
    # ゲームID解決
    "GameIDResolver", 
    "SportType",
    "create_game_id_resolver",
    "resolve_game_id_for_sport"
]
