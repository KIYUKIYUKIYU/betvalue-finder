# -*- coding: utf-8 -*-
"""
UnifiedGameManager - 統一GameManager基底クラス
全スポーツで一貫したインターフェースを提供し、設定ベースで動作を切り替え
"""

from typing import Dict, Optional
from .realtime_game_manager import RealtimeGameManager
from .sport_config import SportConfig


class UnifiedGameManager(RealtimeGameManager):
    """
    統一GameManager基底クラス

    全スポーツで統一されたインターフェースを提供。
    SportConfigによる設定駆動型アーキテクチャを採用。

    既存のRealtimeGameManagerを継承し、完全な後方互換性を保証。
    """

    def __init__(
        self,
        api_key: str,
        sport_config: SportConfig,
        cache_dir: Optional[str] = None,
        **kwargs
    ):
        """
        統一初期化メソッド

        Args:
            api_key: APIキー
            sport_config: スポーツ別設定
            cache_dir: キャッシュディレクトリ（Noneの場合は設定から取得）
            **kwargs: 追加パラメータ（RealtimeConfigなど）
        """
        # スポーツ設定を保存
        self.sport_config = sport_config

        # API基本URLを設定
        self.API_BASE = sport_config.api_base_url

        # リーグIDが存在する場合は設定（Baseball系）
        if sport_config.league_id is not None:
            self.LEAGUE_ID = sport_config.league_id

        # キャッシュディレクトリの決定
        if cache_dir is None:
            cache_dir = sport_config.default_cache_dir

        # 親クラス初期化（キーワード引数で統一）
        super().__init__(api_key=api_key, cache_dir=cache_dir, **kwargs)

    def _prepare_headers(self, headers: Dict) -> Dict:
        """
        API認証ヘッダーを準備（統一メソッド）

        Args:
            headers: 基本ヘッダー

        Returns:
            認証ヘッダーを含む完全なヘッダー
        """
        return self.sport_config.prepare_headers(self.api_key, headers)

    def get_sport_name(self) -> str:
        """
        スポーツ名を取得

        Returns:
            スポーツ名（例: "NPB", "MLB", "SOCCER"）
        """
        return self.sport_config.sport_name
