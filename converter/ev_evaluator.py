# -*- coding: utf-8 -*-
"""
converter/ev_evaluator.py
EV評価モジュール
公正勝率の計算とEV評価、verdict判定を行う
"""

from typing import Dict, List, Tuple, Optional, Any
import logging
from .baseball_rules import (
    BaseballEV, 
    remove_margin_fair_probs, 
    linear_interpolate,
    quantize_rakeback
)
from .handicap_interpolator import HandicapInterpolator, interpolate_odds_for_line

logger = logging.getLogger(__name__)


class EVEvaluator:
    """EV評価を行うクラス"""

    # verdict判定の既定しきい値（%）
    DEFAULT_THRESHOLDS = {
        "clear_plus": 5.0,   # +5% 以上
        "plus": 0.0,         # 0% 以上
        "fair": -3.0,        # -3% 以上
    }
    
    def __init__(
        self, 
        jp_odds: float = 1.9, 
        rakeback: float = 0.0,
        thresholds: Optional[Dict[str, float]] = None
    ):
        """
        初期化
        
        Args:
            jp_odds: 日本式の丸勝ち配当（既定1.9）
            rakeback: レーキバック率（0〜0.03、0.5%刻み）
            thresholds: verdict判定のしきい値
        """
        self.jp_odds = float(jp_odds)
        self.rakeback = quantize_rakeback(rakeback)
        
        # EV計算用のインスタンス
        self.ev_calc = BaseballEV(
            jp_fullwin_odds=self.jp_odds,
            rakeback_pct=self.rakeback
        )
        
        # 補間用のインスタンス
        self.interpolator = HandicapInterpolator()
        
        # しきい値設定
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        if thresholds:
            self.thresholds.update(thresholds)
    
    def evaluate_single_line(
        self, 
        odds_data: Dict[float, Tuple[float, float]], 
        target_line: float, 
        side: str = "home"
    ) -> Dict[str, Any]:
        """
        単一ラインのEV評価
        
        Args:
            odds_data: {ライン値: (home_odds, away_odds)} の辞書
            target_line: 評価したいライン値（ピナクル値）
            side: "home" または "away"
            
        Returns:
            {
                "line": ターゲットライン,
                "side": サイド,
                "fair_prob": 公正勝率,
                "fair_odds": 公正オッズ,
                "ev_pct": EV%（レーキなし）,
                "ev_pct_rake": EV%（レーキあり）,
                "eff_odds": 実効配当,
                "verdict": 判定
            }
        """
        # 🔍 EVEvaluatorデバッグログ（符号処理統一化）
        logger.info(f"🔍 EVEvaluator.evaluate_single_line - target_line: {target_line}, side: {side}")

        # 符号処理統一化チェック
        available_lines = sorted(odds_data.keys()) if odds_data else []
        positive_lines = [l for l in available_lines if l > 0]
        negative_lines = [l for l in available_lines if l < 0]

        logger.info(f"🔍 SIGN CHECK - Available positive lines: {positive_lines}")
        logger.info(f"🔍 SIGN CHECK - Available negative lines: {negative_lines}")
        logger.info(f"🔍 SIGN CHECK - Target line: {target_line} ({'positive' if target_line > 0 else 'negative' if target_line < 0 else 'zero'})")

        # フェイバリット/アンダードッグの符号期待値チェック
        if side == "home":
            if target_line > 0:
                logger.warning(f"🚨 SIGN WARNING - Home team with positive line ({target_line}) - Usually favorite should be negative")
        elif side == "away":
            if target_line < 0:
                logger.warning(f"🚨 SIGN WARNING - Away team with negative line ({target_line}) - Usually underdog should be positive")

        # 公正勝率を計算
        probs = self.interpolator.calculate_fair_probs_for_line(
            odds_data, 
            target_line, 
            allow_interpolation=True
        )
        
        if not probs:
            return {
                "line": target_line,
                "side": side,
                "fair_prob": None,
                "fair_odds": None,
                "ev_pct": None,
                "ev_pct_rake": None,
                "eff_odds": None,
                "verdict": None,
                "error": "Unable to calculate fair probability"
            }
        
        home_prob, away_prob = probs
        fair_prob = home_prob if side == "home" else away_prob
        
        # 公正オッズ
        fair_odds = 1.0 / fair_prob if fair_prob > 0 else None
        
        # デバッグ: 利用可能なオッズラインを確認
        available_lines = list(odds_data.keys()) if odds_data else []
        logger.info(f"Available lines: {available_lines}")
        
        # 実際のピナクルAPIオッズを取得
        actual_pinnacle_odds = None
        if target_line in odds_data:
            home_odds, away_odds = odds_data[target_line]
            actual_pinnacle_odds = home_odds if side == "home" else away_odds
            logger.info(f"Using actual Pinnacle odds: line {target_line}, {side} = {actual_pinnacle_odds}")
        else:
            logger.warning(f"Target line {target_line} not found in odds_data, using fallback calculation")
            logger.info(f"Trying interpolation for line {target_line}...")
        
        # 実際のオッズを取得（補間含む）
        if not actual_pinnacle_odds:
            # 直接存在しない場合は補間でオッズを取得
            interpolated_odds = interpolate_odds_for_line(odds_data, target_line)
            if interpolated_odds:
                home_odds, away_odds = interpolated_odds
                actual_pinnacle_odds = home_odds if side == "home" else away_odds
                logger.info(f"Using interpolated odds: line {target_line}, {side} = {actual_pinnacle_odds}")
        
        # EV計算（シンプルな確率ベース計算）
        ev_pct_plain = (fair_prob * self.jp_odds - 1.0) * 100
        effective_odds = self.jp_odds + self.rakeback
        ev_pct_rake = (fair_prob * effective_odds - 1.0) * 100
        logger.info(f"Calculated EV with Japanese fixed odds 1.9: plain={ev_pct_plain:.2f}%, rake={ev_pct_rake:.2f}%")
        
        # 実効配当（日本式固定配当にのみレーキバック適用）
        try:
            eff_odds = self.jp_odds + self.rakeback
        except (ZeroDivisionError, TypeError):
            eff_odds = None
        
        # verdict判定
        verdict = self.decide_verdict(ev_pct_rake)
        
        return {
            "line": target_line,
            "side": side,
            "fair_prob": round(fair_prob, 5) if fair_prob else None,
            "fair_odds": round(fair_odds, 3) if fair_odds else None,
            "raw_odds": round(actual_pinnacle_odds, 3) if actual_pinnacle_odds else None,  # 生オッズ追加
            "ev_pct": round(ev_pct_plain, 2),
            "ev_pct_rake": round(ev_pct_rake, 2),
            "eff_odds": round(eff_odds, 3) if eff_odds else None,
            "verdict": verdict
        }
    
    def evaluate_all_lines(
        self, 
        odds_data: Dict[float, Tuple[float, float]], 
        step: float = 0.25,
        min_line: float = -4.0,
        max_line: float = 4.0
    ) -> List[Dict[str, Any]]:
        """
        全ライン評価（0.25刻みなど）
        
        Args:
            odds_data: {ライン値: (home_odds, away_odds)} の辞書
            step: 評価するライン間隔（既定0.25）
            min_line: 最小ライン
            max_line: 最大ライン
            
        Returns:
            評価結果のリスト
        """
        results = []
        
        # 利用可能なラインの範囲を確認
        available_lines = sorted(odds_data.keys())
        if not available_lines:
            return results
        
        # 実際の範囲に調整
        actual_min = max(min_line, available_lines[0])
        actual_max = min(max_line, available_lines[-1])
        
        # 評価対象のライン値を生成
        current = actual_min
        target_lines = []
        while current <= actual_max:
            rounded = round(current / step) * step
            if actual_min <= rounded <= actual_max:
                target_lines.append(rounded)
            current += step
        
        # 各ラインを評価（Home/Away両方）
        for target_line in target_lines:
            # Home側の評価（アンダードッグ想定でプラスライン）
            home_target_line = abs(target_line)  # プラス値
            home_result = self.evaluate_single_line(odds_data, home_target_line, "home")
            if home_result.get("fair_prob"):
                results.append(home_result)
            
            # Away側の評価（フェイバリット想定でマイナスライン）
            away_target_line = -abs(target_line)  # マイナス値
            away_result = self.evaluate_single_line(odds_data, away_target_line, "away")
            if away_result.get("fair_prob"):
                results.append(away_result)
        
        # EV%でソート（降順）
        results.sort(key=lambda x: x.get("ev_pct_rake", -999), reverse=True)
        
        return results
    
    def find_best_lines(
        self, 
        odds_data: Dict[float, Tuple[float, float]], 
        top_n: int = 3,
        min_ev: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        最良のラインを見つける
        
        Args:
            odds_data: {ライン値: (home_odds, away_odds)} の辞書
            top_n: 上位N個を返す
            min_ev: 最小EV%（これ以上のもののみ返す）
            
        Returns:
            上位N個の評価結果
        """
        # 全ライン評価
        all_results = self.evaluate_all_lines(odds_data)
        
        # フィルタリング
        if min_ev is not None:
            filtered = [r for r in all_results if r.get("ev_pct_rake", -999) >= min_ev]
        else:
            filtered = all_results
        
        # 上位N個を返す
        return filtered[:top_n]
    
    def evaluate_simplified_line(
        self, 
        odds_data: Dict[float, Tuple[float, float]], 
        target_line: float, 
        side: str = "home"
    ) -> Dict[str, Any]:
        """
        簡略化されたライン評価（高精度版）
        """
        logger.info(f"🔍 EVEvaluator.evaluate_simplified_line (high-accuracy) - target_line: {target_line}, side: {side}")
        
        # 1. 生ピナクルオッズを直接取得（補間含む） - これは表示にのみ使用
        raw_odds = None
        if target_line in odds_data:
            home_odds, away_odds = odds_data[target_line]
            raw_odds = home_odds if side == "home" else away_odds
        else:
            from .handicap_interpolator import interpolate_odds_for_line
            interpolated_odds = interpolate_odds_for_line(odds_data, target_line)
            if interpolated_odds:
                home_odds, away_odds = interpolated_odds
                raw_odds = home_odds if side == "home" else away_odds

        # 2. 厳密な公正確率を計算 (fair_prob_for_team_at_line を使用)
        # この関数は従来の実装に合わせた座標系を使用
        # APIデータをそのまま使用してhome_lines/away_linesを作成
        home_lines = {line: odds[0] for line, odds in odds_data.items()}
        away_lines = {line: odds[1] for line, odds in odds_data.items()}

        logger.info(f"🔍 DEBUG fair_prob calculation for side={side}, target_line={target_line}")
        logger.info(f"  Available home_lines: {list(home_lines.keys())}")
        logger.info(f"  Available away_lines: {list(away_lines.keys())}")

        # fair_prob_for_team_at_line は home座標系のラインを期待する
        # オーケストレーターから渡される target_line は既にhome座標系になっている前提
        fair_prob = self.fair_prob_for_team_at_line(
            home_lines=home_lines,
            away_lines=away_lines,
            target_line_for_team=target_line,
            team_side=side
        )

        logger.info(f"  Calculated fair_prob: {fair_prob}")

        if fair_prob is None:
            logger.warning(f"❌ Could not calculate rigorous fair_prob for line {target_line}, side {side}")
            return {
                "line": target_line, "side": side, "raw_odds": raw_odds,
                "fair_odds": None, "ev_pct": None, "ev_pct_rake": None,
                "verdict": "Error", "error": "Could not calculate rigorous fair probability"
            }

        # 3. 厳密な公正確率から、公正オッズとEVを計算
        fair_odds = 1.0 / fair_prob if fair_prob > 0 else None
        
        ev_pct_plain = (fair_prob * self.jp_odds - 1.0) * 100
        
        effective_odds = self.jp_odds + self.rakeback
        ev_pct_rake = (fair_prob * effective_odds - 1.0) * 100
        
        verdict = self.decide_verdict(ev_pct_rake)
        
        return {
            "line": target_line,
            "side": side,
            "raw_odds": round(raw_odds, 3) if raw_odds else None,
            "fair_odds": round(fair_odds, 3) if fair_odds else None,
            "ev_pct": round(ev_pct_plain, 2),
            "ev_pct_rake": round(ev_pct_rake, 2),
            "verdict": verdict
        }

    def decide_verdict(self, ev_pct: float) -> str:
        """
        EV%からverdict（判定）を決定

        Args:
            ev_pct: EV%（レーキバック込み）

        Returns:
            "clear_plus", "plus", "fair", "minus" のいずれか
        """
        if ev_pct >= self.thresholds["clear_plus"]:
            return "clear_plus"
        elif ev_pct >= self.thresholds["plus"]:
            return "plus"
        elif ev_pct >= self.thresholds["fair"]:
            return "fair"
        else:
            return "minus"

    
    def fair_prob_for_team_at_line(
        self,
        home_lines: Dict[float, float],
        away_lines: Dict[float, float],
        target_line_for_team: float,
        team_side: str
    ) -> Optional[float]:
        """
        CSVデータから特定チーム・ラインの公正勝率を計算
        （mlb_from_paste_compare.pyのfair_prob_for_team_at_line関数の移植）
        
        Args:
            home_lines: Home側のライン別オッズ
            away_lines: Away側のライン別オッズ
            target_line_for_team: ターゲットライン
            team_side: "home" または "away"
            
        Returns:
            公正勝率 or None
        """
        # ペアが存在するラインを収集 - APIデータ構造に合わせて修正
        usable: Dict[float, Tuple[float, float]] = {}

        print(f"🔍 DEBUG fair_prob_for_team_at_line: target={target_line_for_team}, side={team_side}")
        print(f"  home_lines keys: {list(home_lines.keys())}")
        print(f"  away_lines keys: {list(away_lines.keys())}")

        # APIデータから直接ペアを作成（同じハンディキャップ値でペア）
        for line in home_lines.keys():
            if line in away_lines:
                home_odds = home_lines[line]
                away_odds = away_lines[line]
                # 現在の構造: 同じハンディキャップ値でHome/Awayオッズペア
                usable[line] = (home_odds, away_odds)
                print(f"    line {line}: home={home_odds}, away={away_odds}")

        print(f"  usable pairs: {len(usable)}")
        
        anchors = sorted(usable.keys())
        if not anchors:
            return None
        
        # 完全一致チェック
        for a in anchors:
            if abs(a - target_line_for_team) < 1e-9:
                odd_h, odd_a = usable[a]
                p_home, _ = remove_margin_fair_probs(odd_h, odd_a)
                return p_home if team_side == "home" else (1.0 - p_home)
        
        # 補間用の上下ラインを探す
        lower = max([a for a in anchors if a <= target_line_for_team], default=None)
        upper = min([a for a in anchors if a >= target_line_for_team], default=None)
        
        if lower is None or upper is None:
            return None
        
        # 生オッズを補間してからマージン除去
        home_odds_lower, away_odds_lower = usable[lower]
        home_odds_upper, away_odds_upper = usable[upper]

        # 生オッズを線形補間
        home_odds_interp = linear_interpolate(lower, home_odds_lower, upper, home_odds_upper, target_line_for_team)
        away_odds_interp = linear_interpolate(lower, away_odds_lower, upper, away_odds_upper, target_line_for_team)

        # 補間後の生オッズからマージン除去
        p_home_interp, _ = remove_margin_fair_probs(home_odds_interp, away_odds_interp)
        p_team = p_home_interp if team_side == "home" else (1.0 - p_home_interp)
        
        return p_team

    def evaluate_handicap(
        self,
        processed_odds: Dict[str, Any],
        game_info: Dict[str, Any],
        matched_game: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ハンディキャップEV評価（新メソッド）

        Args:
            processed_odds: 処理済みオッズデータ
            game_info: ゲーム情報
            matched_game: マッチしたゲーム情報

        Returns:
            評価結果
        """
        try:
            # スプレッドデータから評価
            spreads = processed_odds.get('spreads', {})
            if not spreads:
                return {
                    "error": "No spread data available",
                    "evaluation": None
                }

            # ターゲットラインとサイドを決定
            fav_line = game_info.get('fav_line_pinnacle', 0.0)
            fav_side = game_info.get('fav_side', 'home')

            # evaluate_single_lineを使用
            result = self.evaluate_single_line(
                odds_data=spreads,
                target_line=fav_line,
                side=fav_side
            )

            return {
                "evaluation": result,
                "game_info": game_info,
                "target_line": fav_line,
                "target_side": fav_side
            }

        except Exception as e:
            logger.error(f"Error in evaluate_handicap: {e}")
            return {
                "error": f"Evaluation failed: {str(e)}",
                "evaluation": None
            }

    def evaluate_from_csv_data(
        self,
        home_lines: Dict[float, float],
        away_lines: Dict[float, float],
        jp_label: str,
        fav_side: str
    ) -> Dict[str, Any]:
        """
        CSV形式のデータからEV評価
        （mlb_from_paste_compare.pyの処理の移植）
        
        Args:
            home_lines: Home側のライン別オッズ
            away_lines: Away側のライン別オッズ
            jp_label: 日本式ラベル
            fav_side: "home" または "away"
            
        Returns:
            評価結果
        """
        # 日本式ラベルをピナクル値に変換
        try:
            pinnacle_value = self.ev_calc.jp_label_to_pinnacle_value(jp_label)
        except Exception as e:
            return {
                "error": f"Failed to convert JP label: {jp_label}",
                "error_detail": str(e)
            }
        
        # home座標系でのターゲットライン
        target_line_for_home_axis = -pinnacle_value if fav_side == "home" else pinnacle_value
        
        # 公正勝率を計算
        fair_prob = self.fair_prob_for_team_at_line(
            home_lines=home_lines,
            away_lines=away_lines,
            target_line_for_team=target_line_for_home_axis,
            team_side=fav_side
        )
        
        if fair_prob is None:
            return {
                "jp_label": jp_label,
                "pinnacle_value": pinnacle_value,
                "fav_side": fav_side,
                "fair_prob": None,
                "error": "Unable to calculate fair probability"
            }
        
        # EV計算（シンプルな確率ベース計算）
        fair_odds = 1.0 / fair_prob
        ev_pct_plain = (fair_prob * self.jp_odds - 1.0) * 100
        effective_odds = self.jp_odds + self.rakeback
        ev_pct_rake = (fair_prob * effective_odds - 1.0) * 100
        
        # 実効配当
        try:
            eff_odds = self.jp_odds + self.rakeback
        except ZeroDivisionError:
            eff_odds = None
        
        # verdict判定
        verdict = self.decide_verdict(ev_pct_rake)
        
        return {
            "jp_label": jp_label,
            "pinnacle_value": round(pinnacle_value, 2),
            "fav_side": fav_side,
            "fair_prob": round(fair_prob, 5),
            "fair_odds": round(fair_odds, 3),
            "ev_pct": round(ev_pct_plain, 2),
            "ev_pct_rake": round(ev_pct_rake, 2),
            "eff_odds": round(eff_odds, 3) if eff_odds else None,
            "jp_odds": self.jp_odds,
            "rakeback": self.rakeback,
            "verdict": verdict
        }


# ヘルパー関数（既存コードとの互換性のため）
def evaluate_line(
    odds_data: Dict[float, Tuple[float, float]],
    target_line: float,
    jp_odds: float = 1.9,
    rakeback: float = 0.0,
    side: str = "home"
) -> Dict[str, Any]:
    """
    単一ラインを評価（互換性用ラッパー）
    
    Args:
        odds_data: ライン別オッズ
        target_line: ターゲットライン
        jp_odds: 日本式配当
        rakeback: レーキバック率
        side: サイド
        
    Returns:
        評価結果
    """
    evaluator = EVEvaluator(jp_odds=jp_odds, rakeback=rakeback)
    return evaluator.evaluate_single_line(odds_data, target_line, side)


def find_best_ev_lines(
    odds_data: Dict[float, Tuple[float, float]],
    jp_odds: float = 1.9,
    rakeback: float = 0.0,
    top_n: int = 3
) -> List[Dict[str, Any]]:
    """
    最良のEVラインを見つける（互換性用ラッパー）
    
    Args:
        odds_data: ライン別オッズ
        jp_odds: 日本式配当
        rakeback: レーキバック率
        top_n: 上位N個
        
    Returns:
        上位N個の評価結果
    """
    evaluator = EVEvaluator(jp_odds=jp_odds, rakeback=rakeback)
    return evaluator.find_best_lines(odds_data, top_n=top_n)