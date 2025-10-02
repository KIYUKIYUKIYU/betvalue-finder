# -*- coding: utf-8 -*-
"""
SportConfig - スポーツ別設定の統一管理
各スポーツのAPI設定、認証方式、エンドポイント情報を一元管理
"""

from dataclasses import dataclass
from typing import Dict, Optional, Type


@dataclass
class SportConfig:
    """スポーツ別設定クラス"""

    # 基本情報
    sport_name: str
    default_cache_dir: str

    # API設定
    api_base_url: str
    auth_header_name: str
    api_host_header: Optional[str] = None  # NPBのみ使用

    # エンドポイント設定
    games_endpoint: str = "/games"
    odds_endpoint: str = "/odds"

    # リーグID（Baseball系のみ）
    league_id: Optional[int] = None

    # チーム翻訳クラス（将来的に使用）
    team_translator_class: Optional[Type] = None

    def prepare_headers(self, api_key: str, base_headers: Optional[Dict] = None) -> Dict:
        """
        認証ヘッダーを準備

        Args:
            api_key: APIキー
            base_headers: 基本ヘッダー（オプション）

        Returns:
            完全な認証ヘッダー
        """
        headers = base_headers.copy() if base_headers else {}

        # 認証キーを設定
        headers[self.auth_header_name] = api_key

        # NPB用の追加ホストヘッダー
        if self.api_host_header:
            headers["X-RapidAPI-Host"] = self.api_host_header

        return headers


# ==========================================
# スポーツ別設定定義
# ==========================================

NPB_CONFIG = SportConfig(
    sport_name="NPB",
    default_cache_dir="data/npb",
    api_base_url="https://v1.baseball.api-sports.io",
    auth_header_name="X-RapidAPI-Key",
    api_host_header="v1.baseball.api-sports.io",
    games_endpoint="/games",
    odds_endpoint="/odds",
    league_id=2  # NPB League ID
)

MLB_CONFIG = SportConfig(
    sport_name="MLB",
    default_cache_dir="data/mlb",
    api_base_url="https://v1.baseball.api-sports.io",
    auth_header_name="x-apisports-key",
    games_endpoint="/games",
    odds_endpoint="/odds",
    league_id=1  # MLB League ID
)

SOCCER_CONFIG = SportConfig(
    sport_name="SOCCER",
    default_cache_dir="data/soccer",
    api_base_url="https://v3.football.api-sports.io",
    auth_header_name="x-apisports-key",
    games_endpoint="/fixtures",
    odds_endpoint="/odds",
    league_id=None  # Soccer uses league parameter in requests
)


# ==========================================
# 設定取得ヘルパー
# ==========================================

SPORT_CONFIGS = {
    "npb": NPB_CONFIG,
    "mlb": MLB_CONFIG,
    "soccer": SOCCER_CONFIG,
    "football": SOCCER_CONFIG,  # Alias
    "baseball": MLB_CONFIG,     # Alias
}


def get_sport_config(sport: str) -> SportConfig:
    """
    スポーツ名から設定を取得

    Args:
        sport: スポーツ名（大文字小文字区別なし）

    Returns:
        SportConfig

    Raises:
        ValueError: サポートされていないスポーツの場合
    """
    sport_key = sport.lower()

    if sport_key not in SPORT_CONFIGS:
        raise ValueError(
            f"Unsupported sport: {sport}. "
            f"Supported: {', '.join(SPORT_CONFIGS.keys())}"
        )

    return SPORT_CONFIGS[sport_key]
