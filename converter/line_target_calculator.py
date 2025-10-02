# -*- coding: utf-8 -*-
"""
converter/line_target_calculator.py
フェイバリット/アンダードッグ向けのターゲットライン計算モジュール

フェイバリットとアンダードッグは対戦するライン値を使用する仕様に基づき、
適切なターゲットライン組み合わせを計算する。
"""

from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LineTargetCalculator:
    """
    フェイバリット/アンダードッグのターゲットライン計算クラス
    
    仕様:
    - フェイバリットとアンダードッグは対戦するライン値を使用
    - フェイバリット: 常にプラスライン（+1.5など）で低オッズ
    - アンダードッグ: 常にマイナスライン（-1.5など）で高オッズ
    """
    
    def __init__(self):
        """初期化"""
        pass
    
    def calculate_target_lines(
        self,
        fav_side: str,
        pinnacle_line: float
    ) -> Tuple[float, float]:
        """
        フェイバリット/アンダードッグのターゲットライン組み合わせを計算
        
        Args:
            fav_side: フェイバリット側 ("home" または "away")
            pinnacle_line: 日本式からの変換ライン値（例: 1.5）
            
        Returns:
            (fav_target_line, dog_target_line) のタプル
            
        例:
            fav_side="away", pinnacle_line=1.5
            → (fav_target_line=+1.5, dog_target_line=-1.5)
        """
        # 入力検証
        if fav_side not in ["home", "away"]:
            raise ValueError(f"Invalid fav_side: {fav_side}. Must be 'home' or 'away'.")
        
        if not isinstance(pinnacle_line, (int, float)):
            raise ValueError(f"Invalid pinnacle_line: {pinnacle_line}. Must be numeric.")
        
        # フェイバリットは常にプラスライン、アンダードッグは常にマイナスライン
        fav_target_line = +abs(pinnacle_line)  # 常に+1.5など
        dog_target_line = -abs(pinnacle_line)  # 常に-1.5など
        
        # デバッグログ
        logger.info(f"LineTargetCalculator: fav_side={fav_side}, pinnacle_line={pinnacle_line}")
        logger.info(f"LineTargetCalculator: fav_target_line={fav_target_line}, dog_target_line={dog_target_line}")
        
        return fav_target_line, dog_target_line
    
    def get_line_side_combination(
        self,
        fav_side: str,
        dog_side: str,
        pinnacle_line: float
    ) -> Dict[str, Any]:
        """
        完全な組み合わせ情報を取得
        
        Args:
            fav_side: フェイバリット側 ("home" または "away")
            dog_side: アンダードッグ側 ("home" または "away")  
            pinnacle_line: 日本式からの変換ライン値
            
        Returns:
            {
                "fav_target_line": float,
                "dog_target_line": float,
                "fav_side": str,
                "dog_side": str,
                "summary": str
            }
        """
        fav_target_line, dog_target_line = self.calculate_target_lines(fav_side, pinnacle_line)
        
        summary = (f"Fav({fav_side}): line={fav_target_line:+.1f}, "
                  f"Dog({dog_side}): line={dog_target_line:+.1f}")
        
        return {
            "fav_target_line": fav_target_line,
            "dog_target_line": dog_target_line,
            "fav_side": fav_side,
            "dog_side": dog_side,
            "summary": summary
        }


def calculate_target_lines(fav_side: str, pinnacle_line: float) -> Tuple[float, float]:
    """
    コンビニエンス関数: フェイバリット/アンダードッグのターゲットライン計算
    
    Args:
        fav_side: フェイバリット側 ("home" または "away")
        pinnacle_line: 日本式からの変換ライン値
        
    Returns:
        (fav_target_line, dog_target_line) のタプル
    """
    calculator = LineTargetCalculator()
    return calculator.calculate_target_lines(fav_side, pinnacle_line)