# converter/handicap_interpolator.py
"""
ハンディキャップラインの補間処理モジュール
- ライン0の計算
- 0.05刻みの細かい補間
- 全スポーツ対応（数値ベース）
"""

from typing import Dict, Tuple, Optional, List
import math


class HandicapInterpolator:
    """ハンディキャップラインの補間を行うクラス"""
    
    def __init__(self, precision: int = 4):
        """
        Args:
            precision: 小数点以下の精度（デフォルト4桁）
        """
        self.precision = precision
    
    def _round(self, value: float) -> float:
        """指定精度で丸める"""
        return round(value, self.precision)
    
    def calculate_line_zero(
        self,
        line_data: Dict[float, Tuple[float, float]]
    ) -> Optional[Tuple[float, float]]:
        """
        ライン0のオッズを計算。
        優先: 公正勝率（マージン除去）を±基準点間で線形補間→オッズへ。
        基準点は 0 を挟む最近の下側/上側ライン（例: -1.0 と +1.0）があればそれを使用。
        """
        if not line_data:
            return None

        keys = sorted(line_data.keys())
        # 0 を挟む最近のペアを探す
        lower = None
        upper = None
        for k in keys:
            if k <= 0:
                lower = k
            if k >= 0 and upper is None:
                upper = k
        if lower is None or upper is None:
            return None

        if lower == upper:
            # ちょうど0ラインが存在する
            return line_data[lower]

        # マージン除去して公正勝率を算出
        def fair_from_odds(odds_pair: Tuple[float, float]) -> Tuple[float, float]:
            ho, ao = odds_pair
            hp = 1.0 / ho
            ap = 1.0 / ao
            m = hp + ap
            return hp / m, ap / m

        home_fair_lower, _ = fair_from_odds(line_data[lower])
        home_fair_upper, _ = fair_from_odds(line_data[upper])

        # 線形補間（0点）
        if upper == lower:
            p_home_0 = home_fair_lower
        else:
            t = (0.0 - lower) / (upper - lower)
            p_home_0 = home_fair_lower + (home_fair_upper - home_fair_lower) * t

        # 公正勝率→オッズ（マージン=1.0想定）
        p_home_0 = max(1e-6, min(1 - 1e-6, p_home_0))
        p_away_0 = 1.0 - p_home_0
        return self._round(1.0 / p_home_0), self._round(1.0 / p_away_0)
    
    def linear_interpolate_odds(
        self,
        line_lower: float,
        odds_lower: Tuple[float, float],
        line_upper: float,
        odds_upper: Tuple[float, float],
        target_line: float
    ) -> Tuple[float, float]:
        """
        2つのライン間でオッズを線形補間（公正勝率ベース）
        
        Args:
            line_lower: 下側のライン値
            odds_lower: 下側のオッズ (home, away)
            line_upper: 上側のライン値
            odds_upper: 上側のオッズ (home, away)
            target_line: 補間したいライン値
        
        Returns:
            (home_odds, away_odds)
        """
        if line_upper == line_lower:
            return odds_lower
        
        # 補間比率を計算
        ratio = (target_line - line_lower) / (line_upper - line_lower)
        
        # マージン除去して公正勝率を算出
        def fair_from_odds(odds_pair) -> Tuple[float, float]:
            # 辞書形式とタプル形式の両方に対応
            if isinstance(odds_pair, dict):
                ho = float(odds_pair.get('home_odds', odds_pair.get('home', 0)))
                ao = float(odds_pair.get('away_odds', odds_pair.get('away', 0)))
            elif isinstance(odds_pair, (tuple, list)) and len(odds_pair) >= 2:
                ho, ao = float(odds_pair[0]), float(odds_pair[1])
            else:
                raise ValueError(f"Invalid odds format: {odds_pair}")
                
            hp = 1.0 / ho  # ブックメーカーの確率
            ap = 1.0 / ao
            m = hp + ap    # 総マージン
            return hp / m, ap / m  # 正規化された公正勝率
        
        home_fair_lower, away_fair_lower = fair_from_odds(odds_lower)
        home_fair_upper, away_fair_upper = fair_from_odds(odds_upper)
        
        # 公正勝率を線形補間
        home_fair = home_fair_lower + (home_fair_upper - home_fair_lower) * ratio
        away_fair = away_fair_lower + (away_fair_upper - away_fair_lower) * ratio
        
        # 正規化（合計=1.0を保証）
        total_fair = home_fair + away_fair
        if total_fair > 0:
            home_fair /= total_fair
            away_fair /= total_fair
        
        # 公正オッズに変換（マージン=0）
        home_odds = self._round(1.0 / home_fair) if home_fair > 1e-6 else 999.0
        away_odds = self._round(1.0 / away_fair) if away_fair > 1e-6 else 999.0
        
        return home_odds, away_odds
    
    def interpolate_fine_lines(
        self,
        line_data: Dict[float, Tuple[float, float]],
        step: float = 0.05,
        min_line: float = -4.0,
        max_line: float = 4.0
    ) -> Dict[float, Tuple[float, float]]:
        """
        0.05刻み（または指定刻み）でラインを補間
        
        Args:
            line_data: 既存のライン別オッズ {ライン値: (home_odds, away_odds)}
            step: 補間の刻み幅（デフォルト0.05）
            min_line: 補間範囲の最小値
            max_line: 補間範囲の最大値
        
        Returns:
            補間されたライン別オッズ
        """
        if not line_data:
            return {}
        
        result = dict(line_data)  # 既存データをコピー
        
        # ライン0が存在しない場合、計算を試みる
        if 0.0 not in result and 1.0 in line_data:
            zero_odds = self.calculate_line_zero(line_data)
            if zero_odds:
                result[0.0] = zero_odds
        
        # 利用可能なラインをソート
        available_lines = sorted(result.keys())
        if not available_lines:
            return result
        
        # 補間範囲を実データに合わせて調整
        actual_min = max(min_line, available_lines[0])
        actual_max = min(max_line, available_lines[-1])
        
        # 補間対象のライン値を生成（改良版：整数ベースで精度向上）
        target_lines = []
        
        # step の逆数を使って整数演算で精度を確保
        step_inv = int(round(1.0 / step))
        min_int = int(round(actual_min * step_inv))
        max_int = int(round(actual_max * step_inv))
        
        for i in range(min_int, max_int + 1):
            line_val = i / step_inv
            # 精度を考慮した丸め
            line_val = round(line_val, 2)
            
            if actual_min <= line_val <= actual_max:
                target_lines.append(line_val)
        
        # 各ターゲットラインに対して補間
        for target in target_lines:
            if target in result:
                continue  # 既存データはスキップ
            
            # 補間用の上下ラインを探す
            lower_line = None
            upper_line = None
            
            for line in available_lines:
                if line <= target:
                    lower_line = line
                if line >= target and upper_line is None:
                    upper_line = line
            
            # 補間可能な場合のみ処理
            if lower_line is not None and upper_line is not None:
                if lower_line == upper_line:
                    # 完全一致
                    result[target] = result[lower_line]
                else:
                    # 線形補間
                    interpolated = self.linear_interpolate_odds(
                        lower_line, result[lower_line],
                        upper_line, result[upper_line],
                        target
                    )
                    result[target] = interpolated
        
        return result
    
    def get_odds_for_line(
        self,
        line_data: Dict[float, Tuple[float, float]],
        target_line: float,
        allow_interpolation: bool = True
    ) -> Optional[Tuple[float, float]]:
        """
        指定ラインのオッズを取得（必要に応じて補間）
        
        Args:
            line_data: ライン別オッズ
            target_line: 取得したいライン
            allow_interpolation: 補間を許可するか
        
        Returns:
            (home_odds, away_odds) or None
        """
        # 完全一致チェック
        if target_line in line_data:
            return line_data[target_line]
        
        if not allow_interpolation:
            return None
        
        # ライン0の特別処理
        if target_line == 0.0:
            zero_odds = self.calculate_line_zero(line_data)
            if zero_odds:
                return zero_odds
        
        # 補間処理
        available_lines = sorted(line_data.keys())
        if not available_lines:
            return None
        
        # 範囲外チェック
        if target_line < available_lines[0] or target_line > available_lines[-1]:
            return None
        
        # 補間用の上下ラインを探す
        lower_line = None
        upper_line = None
        
        for line in available_lines:
            if line <= target_line:
                lower_line = line
            if line >= target_line and upper_line is None:
                upper_line = line
        
        if lower_line is None or upper_line is None:
            return None
        
        if lower_line == upper_line:
            return line_data[lower_line]
        
        # 線形補間
        return self.linear_interpolate_odds(
            lower_line, line_data[lower_line],
            upper_line, line_data[upper_line],
            target_line
        )
    
    def calculate_fair_probs_for_line(
        self,
        line_data: Dict[float, Tuple[float, float]],
        target_line: float,
        allow_interpolation: bool = True
    ) -> Optional[Tuple[float, float]]:
        """
        指定ラインの公正勝率を計算（マージン除去済み）
        
        Args:
            line_data: ライン別オッズ
            target_line: 計算したいライン
            allow_interpolation: 補間を許可するか
        
        Returns:
            (home_fair_prob, away_fair_prob) or None
        """
        odds = self.get_odds_for_line(line_data, target_line, allow_interpolation)
        if not odds:
            return None
        
        home_odds, away_odds = odds
        
        # 勝率に変換
        home_prob = 1.0 / home_odds
        away_prob = 1.0 / away_odds
        
        # マージン計算
        margin = home_prob + away_prob
        
        # 公正勝率（マージン除去）
        home_fair = self._round(home_prob / margin)
        away_fair = self._round(away_prob / margin)
        
        return home_fair, away_fair


# ヘルパー関数（既存コードとの互換性のため）
def interpolate_handicap_lines(
    line_data: Dict[float, Tuple[float, float]],
    step: float = 0.05
) -> Dict[float, Tuple[float, float]]:
    """
    ハンディキャップラインを補間する（互換性用ラッパー）
    
    Args:
        line_data: ライン別オッズ
        step: 補間の刻み幅
    
    Returns:
        補間されたライン別オッズ
    """
    interpolator = HandicapInterpolator()
    return interpolator.interpolate_fine_lines(line_data, step)


def get_fair_prob_for_line(
    line_data: Dict[float, Tuple[float, float]],
    target_line: float
) -> Optional[Tuple[float, float]]:
    """
    指定ラインの公正勝率を取得（互換性用ラッパー）
    
    Args:
        line_data: ライン別オッズ
        target_line: 取得したいライン
    
    Returns:
        (home_fair_prob, away_fair_prob) or None
    """
    interpolator = HandicapInterpolator()
    return interpolator.calculate_fair_probs_for_line(line_data, target_line)


def interpolate_odds_for_line(
    line_data: Dict[float, Tuple[float, float]],
    target_line: float
) -> Optional[Tuple[float, float]]:
    """
    指定されたラインのオッズを補間計算する（モジュールレベル関数）
    正しい公正勝率ベース補間を使用

    Args:
        line_data: {ライン値: (home_odds, away_odds)} の辞書
        target_line: 計算したいライン値

    Returns:
        (home_odds, away_odds) のタプル、または None
    """
    interpolator = HandicapInterpolator()
    return interpolator.get_odds_for_line(line_data, target_line, allow_interpolation=True)


# テスト用のサンプルデータと実行例
if __name__ == "__main__":
    # サンプルデータ（Pinnacleから取得したような形式）
    sample_data = {
        1.0: (1.85, 1.95),   # ライン+1.0
        1.5: (1.75, 2.05),   # ライン+1.5
        2.0: (1.65, 2.20),   # ライン+2.0
        2.5: (1.55, 2.35),   # ライン+2.5
    }
    
    interpolator = HandicapInterpolator()
    
    # ライン0を計算
    print("=== ライン0の計算 ===")
    zero_odds = interpolator.calculate_line_zero(sample_data)
    if zero_odds:
        print(f"ライン0: Home {zero_odds[0]:.3f}, Away {zero_odds[1]:.3f}")
    
    # 0.05刻みで補間
    print("\n=== 0.05刻み補間 ===")
    interpolated = interpolator.interpolate_fine_lines(sample_data, step=0.05)
    
    # 主要なラインを表示
    for line in [0.0, 0.5, 1.0, 1.05, 1.1, 1.5, 2.0]:
        if line in interpolated:
            odds = interpolated[line]
            print(f"ライン{line:+.2f}: Home {odds[0]:.3f}, Away {odds[1]:.3f}")
    
    # 特定ラインの公正勝率を計算
    print("\n=== 公正勝率計算 ===")
    for target in [0.05, 1.25, 1.85]:
        probs = interpolator.calculate_fair_probs_for_line(sample_data, target)
        if probs:
            print(f"ライン{target:+.2f}: Home {probs[0]:.1%}, Away {probs[1]:.1%}")
