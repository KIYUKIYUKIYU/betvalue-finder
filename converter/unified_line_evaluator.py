# -*- coding: utf-8 -*-
"""
converter/unified_line_evaluator.py
統一ライン評価モジュール

APIの表記法に関係なく、正しい同一ライン上での
Home/Away両チームのオッズを適切に評価する。

重要な理解:
- legacy_data[-1.5] = (Home -1.5, Away +1.5) の同一ライン対戦
- legacy_data[+1.5] = (Home +1.5, Away -1.5) の同一ライン対戦
"""

from typing import Dict, Tuple, Optional, Any
import logging
from .handicap_interpolator import HandicapInterpolator

logger = logging.getLogger(__name__)


class UnifiedLineEvaluator:
    """
    統一ライン評価クラス

    同一ライン上でのHome/Away両チームのオッズを正しく評価し、
    1.9倍固定に最も近いオプションを選択する。
    """

    def __init__(self, target_odds: float = 1.9):
        """
        Args:
            target_odds: 目標オッズ（日本式固定倍率、デフォルト1.9）
        """
        self.target_odds = target_odds
        self.interpolator = HandicapInterpolator()

    def evaluate_optimal_line(
        self,
        line_data: Dict[float, Tuple[float, float]],
        pinnacle_line: float,
        fav_side: str,
        dog_side: str
    ) -> Dict[str, Any]:
        """
        最適なライン評価を実行

        Args:
            line_data: {ライン値: (home_odds, away_odds)} の辞書
            pinnacle_line: ピナクル値（例: 1.3）
            fav_side: フェイバリット側 ("home" または "away")
            dog_side: アンダードッグ側 ("home" または "away")

        Returns:
            最適化された評価結果
        """
        # 負のライン（フェイバリット不利、アンダードッグ有利）で評価
        target_line = -abs(pinnacle_line)

        logger.info(f"🎯 UNIFIED EVALUATION - target_line: {target_line}")
        logger.info(f"🎯 UNIFIED EVALUATION - fav_side: {fav_side}, dog_side: {dog_side}")

        # 同一ライン上でのHome/Awayオッズを取得
        home_odds = self._get_odds_for_team(line_data, target_line, "home")
        away_odds = self._get_odds_for_team(line_data, target_line, "away")

        if home_odds is None or away_odds is None:
            return {
                "error": f"Unable to calculate odds for line {target_line}",
                "target_line": target_line
            }

        logger.info(f"🎯 UNIFIED EVALUATION - home_odds: {home_odds}, away_odds: {away_odds}")

        # フェイバリット/アンダードッグのオッズを特定
        fav_odds = home_odds if fav_side == "home" else away_odds
        dog_odds = away_odds if fav_side == "home" else home_odds

        # 1.9倍に最も近いオプションを選択
        fav_distance = abs(fav_odds - self.target_odds)
        dog_distance = abs(dog_odds - self.target_odds)

        if dog_distance < fav_distance:
            # アンダードッグが最適
            optimal_side = dog_side
            optimal_odds = dog_odds
            optimal_role = "underdog"
        else:
            # フェイバリットが最適
            optimal_side = fav_side
            optimal_odds = fav_odds
            optimal_role = "favorite"

        logger.info(f"🎯 UNIFIED EVALUATION - optimal: {optimal_side} ({optimal_role}) = {optimal_odds}")
        logger.info(f"🎯 UNIFIED EVALUATION - distances: fav={fav_distance:.3f}, dog={dog_distance:.3f}")

        return {
            "target_line": target_line,
            "home_odds": home_odds,
            "away_odds": away_odds,
            "fav_odds": fav_odds,
            "dog_odds": dog_odds,
            "optimal_side": optimal_side,
            "optimal_odds": optimal_odds,
            "optimal_role": optimal_role,
            "fav_distance": fav_distance,
            "dog_distance": dog_distance,
            "target_odds": self.target_odds
        }

    def _get_odds_for_team(
        self,
        line_data: Dict[float, Tuple[float, float]],
        target_line: float,
        team_side: str
    ) -> Optional[float]:
        """
        指定チーム・ラインのオッズを取得（補間含む）

        Args:
            line_data: ライン別オッズ辞書
            target_line: ターゲットライン
            team_side: "home" または "away"

        Returns:
            オッズ値 or None
        """
        # 完全一致チェック
        if target_line in line_data:
            home_odds, away_odds = line_data[target_line]
            return home_odds if team_side == "home" else away_odds

        # 補間でオッズを取得
        interpolated_odds = self.interpolator.get_odds_for_line(
            line_data,
            target_line,
            allow_interpolation=True
        )

        if interpolated_odds:
            home_odds, away_odds = interpolated_odds
            return home_odds if team_side == "home" else away_odds

        return None

    def calculate_ev_for_optimal(
        self,
        optimal_result: Dict[str, Any],
        jp_odds: float = 1.9,
        rakeback: float = 0.0
    ) -> Dict[str, Any]:
        """
        最適化結果のEV計算

        Args:
            optimal_result: evaluate_optimal_line()の結果
            jp_odds: 日本式配当
            rakeback: レーキバック率

        Returns:
            EV計算結果を含む拡張された結果
        """
        if "error" in optimal_result:
            return optimal_result

        optimal_odds = optimal_result["optimal_odds"]

        # 公正勝率の計算（マージン除去）
        home_odds = optimal_result["home_odds"]
        away_odds = optimal_result["away_odds"]

        home_prob = 1.0 / home_odds
        away_prob = 1.0 / away_odds
        margin = home_prob + away_prob

        # マージン除去
        home_fair = home_prob / margin
        away_fair = away_prob / margin

        # 最適側の公正勝率
        optimal_side = optimal_result["optimal_side"]
        fair_prob = home_fair if optimal_side == "home" else away_fair

        # EV計算
        ev_pct_plain = (fair_prob * jp_odds - 1.0) * 100
        effective_odds = jp_odds + rakeback
        ev_pct_rake = (fair_prob * effective_odds - 1.0) * 100

        # verdict判定
        if ev_pct_rake >= 5.0:
            verdict = "clear_plus"
        elif ev_pct_rake >= 0.0:
            verdict = "plus"
        elif ev_pct_rake >= -3.0:
            verdict = "fair"
        else:
            verdict = "minus"

        # 結果をマージ
        result = optimal_result.copy()
        result.update({
            "fair_prob": round(fair_prob, 5),
            "fair_odds": round(1.0 / fair_prob, 3),
            "ev_pct": round(ev_pct_plain, 2),
            "ev_pct_rake": round(ev_pct_rake, 2),
            "eff_odds": round(effective_odds, 3),
            "verdict": verdict,
            "jp_odds": jp_odds,
            "rakeback": rakeback
        })

        return result


# ヘルパー関数
def evaluate_unified_line(
    line_data: Dict[float, Tuple[float, float]],
    pinnacle_line: float,
    fav_side: str,
    dog_side: str,
    jp_odds: float = 1.9,
    rakeback: float = 0.0
) -> Dict[str, Any]:
    """
    統一ライン評価の簡易インターフェース

    Args:
        line_data: ライン別オッズ辞書
        pinnacle_line: ピナクル値
        fav_side: フェイバリット側
        dog_side: アンダードッグ側
        jp_odds: 日本式配当
        rakeback: レーキバック率

    Returns:
        統一評価結果
    """
    evaluator = UnifiedLineEvaluator()
    optimal_result = evaluator.evaluate_optimal_line(
        line_data, pinnacle_line, fav_side, dog_side
    )
    return evaluator.calculate_ev_for_optimal(optimal_result, jp_odds, rakeback)


if __name__ == "__main__":
    # テスト実行
    test_data = {
        -1.5: (1.98, 1.92),  # (Home -1.5, Away +1.5)
        -1.0: (1.64, 2.37),  # (Home -1.0, Away +1.0)
        +1.5: (1.27, 3.79)   # (Home +1.5, Away -1.5)
    }

    result = evaluate_unified_line(
        line_data=test_data,
        pinnacle_line=1.3,
        fav_side="home",
        dog_side="away"
    )

    print("=== 統一ライン評価テスト ===")
    for key, value in result.items():
        print(f"{key}: {value}")