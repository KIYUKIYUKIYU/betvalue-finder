# -*- coding: utf-8 -*-
"""
MarketStrategyFactory: マーケット戦略のファクトリー

責務:
- 設定に基づいて適切な戦略インスタンスを生成
- 環境変数からの設定読み込み
- フォールバック戦略の管理
"""

from enum import Enum
from typing import Optional
import logging
import os

from .market_strategy import MarketStrategy
from .simple_spreads_strategy import SimpleSpreadsStrategy
from .alternate_spreads_strategy import AlternateSpreadsStrategy


class MarketType(Enum):
    """マーケットタイプの列挙"""
    SIMPLE_SPREADS = "spreads"
    ALTERNATE_SPREADS = "alternate_spreads"

    @classmethod
    def from_string(cls, value: str) -> "MarketType":
        """
        文字列からMarketTypeを生成

        Args:
            value: マーケットタイプ文字列

        Returns:
            MarketType

        Raises:
            ValueError: 不正な値の場合
        """
        value_lower = value.lower().strip()
        for member in cls:
            if member.value == value_lower:
                return member
        raise ValueError(
            f"Invalid market type: {value}. "
            f"Valid options: {[m.value for m in cls]}"
        )


class MarketStrategyFactory:
    """マーケット戦略のファクトリー"""

    @staticmethod
    def create_strategy(
        market_type: Optional[MarketType] = None,
        logger: Optional[logging.Logger] = None
    ) -> MarketStrategy:
        """
        戦略インスタンスを生成

        Args:
            market_type: マーケットタイプ（Noneの場合は環境変数から読み込み）
            logger: ロガーインスタンス

        Returns:
            MarketStrategyインスタンス

        Raises:
            ValueError: 不正なマーケットタイプの場合
        """
        # 環境変数から設定を読み込み
        if market_type is None:
            market_type = MarketStrategyFactory._get_market_type_from_env()

        # ロガーの初期化
        if logger is None:
            logger = logging.getLogger(__name__)

        # 戦略の生成
        if market_type == MarketType.ALTERNATE_SPREADS:
            logger.info("🎯 Using AlternateSpreadsStrategy (multiple lines)")
            return AlternateSpreadsStrategy(logger)

        elif market_type == MarketType.SIMPLE_SPREADS:
            logger.info("🎯 Using SimpleSpreadsStrategy (single line)")
            return SimpleSpreadsStrategy(logger)

        else:
            raise ValueError(f"Unknown market type: {market_type}")

    @staticmethod
    def create_with_fallback(
        primary_type: MarketType,
        logger: Optional[logging.Logger] = None
    ) -> tuple[MarketStrategy, Optional[MarketStrategy]]:
        """
        プライマリ戦略とフォールバック戦略を生成

        Args:
            primary_type: プライマリマーケットタイプ
            logger: ロガーインスタンス

        Returns:
            (プライマリ戦略, フォールバック戦略) のタプル
        """
        if logger is None:
            logger = logging.getLogger(__name__)

        primary_strategy = MarketStrategyFactory.create_strategy(primary_type, logger)

        # フォールバック戦略の決定
        fallback_strategy = None
        if primary_type == MarketType.ALTERNATE_SPREADS:
            # alternate_spreads失敗時はspreadsにフォールバック
            if MarketStrategyFactory._is_fallback_enabled():
                fallback_strategy = SimpleSpreadsStrategy(logger)
                logger.info("🔄 Fallback enabled: alternate_spreads → spreads")

        return primary_strategy, fallback_strategy

    @staticmethod
    def _get_market_type_from_env() -> MarketType:
        """
        環境変数からマーケットタイプを取得

        環境変数:
            THEODDS_MARKET_TYPE: マーケットタイプ（デフォルト: alternate_spreads）

        Returns:
            MarketType
        """
        env_value = os.getenv("THEODDS_MARKET_TYPE", "alternate_spreads")

        try:
            return MarketType.from_string(env_value)
        except ValueError as e:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"⚠️ Invalid THEODDS_MARKET_TYPE: {env_value}. "
                f"Using default: alternate_spreads. Error: {e}"
            )
            return MarketType.ALTERNATE_SPREADS

    @staticmethod
    def _is_fallback_enabled() -> bool:
        """
        フォールバックが有効か確認

        環境変数:
            THEODDS_ENABLE_FALLBACK: true/false（デフォルト: true）

        Returns:
            True: フォールバック有効
            False: フォールバック無効
        """
        env_value = os.getenv("THEODDS_ENABLE_FALLBACK", "true").lower()
        return env_value in ["true", "1", "yes", "on"]

    @staticmethod
    def get_config_info() -> dict:
        """
        現在の設定情報を取得（デバッグ用）

        Returns:
            設定情報の辞書
        """
        market_type = MarketStrategyFactory._get_market_type_from_env()
        fallback_enabled = MarketStrategyFactory._is_fallback_enabled()

        return {
            "market_type": market_type.value,
            "fallback_enabled": fallback_enabled,
            "env_vars": {
                "THEODDS_MARKET_TYPE": os.getenv("THEODDS_MARKET_TYPE", "(not set)"),
                "THEODDS_ENABLE_FALLBACK": os.getenv("THEODDS_ENABLE_FALLBACK", "(not set)")
            }
        }
