# -*- coding: utf-8 -*-
"""
TTLCacheManager
リアルタイムAPI呼び出し方式のためのTTL（Time To Live）キャッシュマネージャー
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib


class DataType(Enum):
    """キャッシュデータのタイプ"""
    GAME_DATA = "game_data"
    ODDS_DATA = "odds_data"
    LIVE_ODDS = "live_odds"
    ACTIVE_GAME = "active_game"


@dataclass
class CacheEntry:
    """キャッシュエントリー"""
    key: str
    data: Any
    data_type: DataType
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = None
    
    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """エントリーが期限切れかチェック"""
        return datetime.now() > self.expires_at
    
    def is_fresh(self, min_freshness_seconds: int = 60) -> bool:
        """データが新鮮かチェック（最低新鮮度秒数指定可能）"""
        return (datetime.now() - self.created_at).total_seconds() < min_freshness_seconds
    
    def access(self):
        """アクセス時の統計更新"""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class TTLConfig:
    """TTL設定"""
    game_data_ttl: int = 3600  # ゲームデータ: 1時間
    active_game_ttl: int = 1800  # アクティブゲーム: 30分
    odds_data_ttl: int = 300  # オッズデータ: 5分
    live_odds_ttl: int = 30  # ライブゲームオッズ: 30秒
    
    # 動的TTL計算用パラメータ
    pre_game_buffer_minutes: int = 60  # 試合開始前のバッファ時間
    live_game_refresh_seconds: int = 15  # ライブゲーム中の更新間隔
    close_to_start_ttl: int = 120  # 試合開始間近のTTL（2分）


class TTLCacheManager:
    """TTL対応キャッシュマネージャー"""
    
    def __init__(self, cache_dir: str = "cache", config: TTLConfig = None):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
            config: TTL設定
        """
        self.cache_dir = cache_dir
        self.config = config or TTLConfig()
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._cleanup_thread = None
        self._running = False
        
        # キャッシュディレクトリ作成
        os.makedirs(cache_dir, exist_ok=True)
        
        # 統計情報
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'cleanups': 0
        }
        
        # 自動クリーンアップ開始
        self.start_cleanup_thread()
    
    def _generate_cache_key(self, base_key: str, **kwargs) -> str:
        """キャッシュキーを生成"""
        if not kwargs:
            return base_key
        
        # kwargsをソートして一意なハッシュを生成
        sorted_kwargs = sorted(kwargs.items())
        kwargs_str = str(sorted_kwargs)
        hash_suffix = hashlib.md5(kwargs_str.encode()).hexdigest()[:8]
        return f"{base_key}_{hash_suffix}"
    
    def _calculate_dynamic_ttl(self, data_type: DataType, game_data: Dict = None) -> int:
        """
        動的TTL計算
        
        Args:
            data_type: データタイプ
            game_data: 試合データ（試合開始時刻等を含む）
        
        Returns:
            TTL秒数
        """
        # デフォルトTTL
        default_ttls = {
            DataType.GAME_DATA: self.config.game_data_ttl,
            DataType.ACTIVE_GAME: self.config.active_game_ttl,
            DataType.ODDS_DATA: self.config.odds_data_ttl,
            DataType.LIVE_ODDS: self.config.live_odds_ttl
        }
        
        base_ttl = default_ttls.get(data_type, 300)
        
        # 試合データが提供されていない場合はデフォルトTTLを返す
        if not game_data:
            return base_ttl
        
        # 試合開始時刻の取得を試行
        game_start_time = self._extract_game_start_time(game_data)
        if not game_start_time:
            return base_ttl
        
        now = datetime.now()
        time_to_start = (game_start_time - now).total_seconds()
        
        # 試合開始前の動的TTL調整
        if time_to_start > 0:
            # 試合開始間近（2時間以内）の場合、TTLを短くする
            if time_to_start <= 7200:  # 2時間
                if time_to_start <= 1800:  # 30分以内
                    return min(base_ttl, self.config.close_to_start_ttl)
                else:  # 30分-2時間
                    return min(base_ttl, 600)  # 10分
        
        # 試合中またはライブデータの場合
        elif time_to_start >= -10800:  # 試合開始から3時間以内（試合中と仮定）
            if data_type == DataType.LIVE_ODDS:
                return self.config.live_game_refresh_seconds
            elif data_type == DataType.ODDS_DATA:
                return min(base_ttl, 60)  # ライブ中のオッズは1分
        
        return base_ttl
    
    def _extract_game_start_time(self, game_data: Dict) -> Optional[datetime]:
        """
        試合データから開始時刻を抽出
        
        Args:
            game_data: 試合データ
            
        Returns:
            試合開始時刻またはNone
        """
        # 複数の形式に対応
        time_fields = ['datetime', 'start_time', 'game_time', 'scheduled_time', 'commence_time']
        date_fields = ['date', 'game_date']
        
        for field in time_fields:
            if field in game_data and game_data[field]:
                try:
                    if isinstance(game_data[field], str):
                        # ISO形式やその他の一般的な形式を試行
                        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                            try:
                                return datetime.strptime(game_data[field], fmt)
                            except ValueError:
                                continue
                    elif isinstance(game_data[field], datetime):
                        return game_data[field]
                except Exception:
                    continue
        
        # 日付フィールドがある場合の処理
        for field in date_fields:
            if field in game_data and game_data[field]:
                try:
                    if isinstance(game_data[field], str):
                        return datetime.strptime(game_data[field], '%Y-%m-%d')
                except Exception:
                    continue
        
        return None
    
    def set(self, key: str, data: Any, data_type: DataType = DataType.GAME_DATA, 
            custom_ttl: int = None, **kwargs) -> bool:
        """
        データをキャッシュに設定
        
        Args:
            key: キャッシュキー
            data: データ
            data_type: データタイプ
            custom_ttl: カスタムTTL（秒）
            **kwargs: 追加のキー生成パラメータ
            
        Returns:
            成功フラグ
        """
        try:
            with self._lock:
                full_key = self._generate_cache_key(key, **kwargs)
                
                # TTL計算（動的TTL適用）
                if custom_ttl:
                    ttl = custom_ttl
                else:
                    ttl = self._calculate_dynamic_ttl(data_type, data if isinstance(data, dict) else None)
                
                now = datetime.now()
                expires_at = now + timedelta(seconds=ttl)
                
                # キャッシュエントリー作成
                entry = CacheEntry(
                    key=full_key,
                    data=data,
                    data_type=data_type,
                    created_at=now,
                    expires_at=expires_at
                )
                
                self._cache[full_key] = entry
                
                # 永続化（オプション）
                self._persist_to_file(full_key, entry)
                
                return True
                
        except Exception as e:
            print(f"⚠️ TTLCache set error for key {key}: {e}")
            return False
    
    def get(self, key: str, default=None, **kwargs) -> Any:
        """
        キャッシュからデータを取得
        
        Args:
            key: キャッシュキー
            default: デフォルト値
            **kwargs: 追加のキー生成パラメータ
            
        Returns:
            キャッシュされたデータまたはデフォルト値
        """
        try:
            with self._lock:
                full_key = self._generate_cache_key(key, **kwargs)
                
                if full_key not in self._cache:
                    # ファイルからの復元を試行
                    if self._restore_from_file(full_key):
                        pass  # 復元成功、そのまま続行
                    else:
                        self.stats['misses'] += 1
                        return default
                
                entry = self._cache[full_key]
                
                # 期限切れチェック
                if entry.is_expired():
                    del self._cache[full_key]
                    self._remove_file(full_key)
                    self.stats['evictions'] += 1
                    self.stats['misses'] += 1
                    return default
                
                # アクセス記録
                entry.access()
                self.stats['hits'] += 1
                
                return entry.data
                
        except Exception as e:
            print(f"⚠️ TTLCache get error for key {key}: {e}")
            self.stats['misses'] += 1
            return default
    
    def has(self, key: str, **kwargs) -> bool:
        """
        キーの存在と有効性をチェック
        
        Args:
            key: キャッシュキー
            **kwargs: 追加のキー生成パラメータ
            
        Returns:
            存在し、有効かどうか
        """
        return self.get(key, None, **kwargs) is not None
    
    def delete(self, key: str, **kwargs) -> bool:
        """
        キャッシュからデータを削除
        
        Args:
            key: キャッシュキー
            **kwargs: 追加のキー生成パラメータ
            
        Returns:
            削除成功フラグ
        """
        try:
            with self._lock:
                full_key = self._generate_cache_key(key, **kwargs)
                
                if full_key in self._cache:
                    del self._cache[full_key]
                    self._remove_file(full_key)
                    return True
                    
                return False
                
        except Exception as e:
            print(f"⚠️ TTLCache delete error for key {key}: {e}")
            return False
    
    def clear(self):
        """キャッシュを全クリア"""
        with self._lock:
            self._cache.clear()
            # ファイルもクリア
            if os.path.exists(self.cache_dir):
                for file in os.listdir(self.cache_dir):
                    if file.endswith('.cache'):
                        os.remove(os.path.join(self.cache_dir, file))
    
    def cleanup_expired(self) -> int:
        """期限切れエントリーをクリーンアップ"""
        cleaned_count = 0
        
        try:
            with self._lock:
                expired_keys = []
                
                for key, entry in self._cache.items():
                    if entry.is_expired():
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._cache[key]
                    self._remove_file(key)
                    cleaned_count += 1
                
                self.stats['cleanups'] += 1
                self.stats['evictions'] += cleaned_count
                
        except Exception as e:
            print(f"⚠️ TTLCache cleanup error: {e}")
        
        return cleaned_count
    
    def start_cleanup_thread(self, interval_seconds: int = 300):
        """自動クリーンアップスレッドを開始（デフォルト5分間隔）"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return
        
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker, 
            args=(interval_seconds,),
            daemon=True
        )
        self._cleanup_thread.start()
    
    def stop_cleanup_thread(self):
        """自動クリーンアップスレッドを停止"""
        self._running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1)
    
    def _cleanup_worker(self, interval_seconds: int):
        """クリーンアップワーカー"""
        while self._running:
            try:
                cleaned = self.cleanup_expired()
                if cleaned > 0:
                    print(f"🧹 TTLCache cleaned {cleaned} expired entries")
                time.sleep(interval_seconds)
            except Exception as e:
                print(f"⚠️ TTLCache cleanup worker error: {e}")
                time.sleep(interval_seconds)
    
    def _persist_to_file(self, key: str, entry: CacheEntry):
        """エントリーをファイルに永続化"""
        try:
            filename = self._get_cache_filename(key)
            filepath = os.path.join(self.cache_dir, filename)
            
            # 辞書形式に変換（datetimeはISOフォーマットに）
            data = asdict(entry)
            data['created_at'] = entry.created_at.isoformat()
            data['expires_at'] = entry.expires_at.isoformat()
            data['last_accessed'] = entry.last_accessed.isoformat()
            data['data_type'] = entry.data_type.value
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ Failed to persist cache entry {key}: {e}")
    
    def _restore_from_file(self, key: str) -> bool:
        """ファイルからエントリーを復元"""
        try:
            filename = self._get_cache_filename(key)
            filepath = os.path.join(self.cache_dir, filename)
            
            if not os.path.exists(filepath):
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # データタイプとdatetimeを復元
            data['data_type'] = DataType(data['data_type'])
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
            
            entry = CacheEntry(**data)
            
            # 期限切れチェック
            if entry.is_expired():
                os.remove(filepath)
                return False
            
            self._cache[key] = entry
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to restore cache entry {key}: {e}")
            return False
    
    def _remove_file(self, key: str):
        """キャッシュファイルを削除"""
        try:
            filename = self._get_cache_filename(key)
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"⚠️ Failed to remove cache file {key}: {e}")
    
    def _get_cache_filename(self, key: str) -> str:
        """キャッシュファイル名を生成"""
        # ファイル名に使えない文字を置換
        safe_key = key.replace('/', '_').replace('\\', '_').replace(':', '_')
        return f"{safe_key}.cache"
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        with self._lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cache_size': len(self._cache),
                'hit_rate': f"{hit_rate:.1f}%",
                'total_hits': self.stats['hits'],
                'total_misses': self.stats['misses'],
                'total_evictions': self.stats['evictions'],
                'total_cleanups': self.stats['cleanups'],
                'memory_entries': len(self._cache)
            }
    
    def get_cache_info(self, key: str = None, **kwargs) -> Union[Dict, List[Dict]]:
        """キャッシュエントリー情報を取得"""
        with self._lock:
            if key:
                full_key = self._generate_cache_key(key, **kwargs)
                entry = self._cache.get(full_key)
                if entry:
                    return {
                        'key': entry.key,
                        'data_type': entry.data_type.value,
                        'created_at': entry.created_at.isoformat(),
                        'expires_at': entry.expires_at.isoformat(),
                        'access_count': entry.access_count,
                        'last_accessed': entry.last_accessed.isoformat(),
                        'is_expired': entry.is_expired(),
                        'ttl_remaining': max(0, (entry.expires_at - datetime.now()).total_seconds())
                    }
                return None
            else:
                # 全エントリーの情報を返す
                return [
                    {
                        'key': entry.key,
                        'data_type': entry.data_type.value,
                        'created_at': entry.created_at.isoformat(),
                        'expires_at': entry.expires_at.isoformat(),
                        'access_count': entry.access_count,
                        'is_expired': entry.is_expired(),
                        'ttl_remaining': max(0, (entry.expires_at - datetime.now()).total_seconds())
                    }
                    for entry in self._cache.values()
                ]
    
    def __enter__(self):
        """コンテキストマネージャーエントリー"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーイグジット"""
        self.stop_cleanup_thread()
    
    def __del__(self):
        """デストラクタ"""
        try:
            self.stop_cleanup_thread()
        except Exception:
            pass


# 使用例とヘルパー関数

def create_cache_manager(cache_dir: str = "cache", **config_kwargs) -> TTLCacheManager:
    """TTLCacheManagerの作成ヘルパー"""
    config = TTLConfig(**config_kwargs) if config_kwargs else TTLConfig()
    return TTLCacheManager(cache_dir=cache_dir, config=config)


def cache_with_ttl(cache_manager: TTLCacheManager, key_prefix: str, data_type: DataType):
    """デコレーター：関数の戻り値をTTLキャッシュする"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # 引数からキャッシュキーを生成
            cache_key = f"{key_prefix}_{func.__name__}"
            
            # キャッシュから取得試行
            cached_result = cache_manager.get(cache_key, args=args, kwargs=kwargs)
            if cached_result is not None:
                return cached_result
            
            # 関数実行
            result = func(*args, **kwargs)
            
            # 結果をキャッシュに保存
            cache_manager.set(cache_key, result, data_type, args=args, kwargs=kwargs)
            
            return result
        return wrapper
    return decorator