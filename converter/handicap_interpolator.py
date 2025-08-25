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
        ライン0のオッズを計算（±1.0のペアから中間値として算出）
        
        Args:
            line_data: {ライン値: (home_odds, away_odds)}
        
        Returns:
            (home_odds, away_odds) or None
        """
        # ±1.0のペアが存在するか確認
        if 1.0 not in line_data:
            return None
        
        # ±1.0のオッズを取得
        odds_plus_1 = line_data[1.0]  # ライン+1.0
        
        # 対称性を仮定：ライン0は±1.0の中間
        # ホーム側のライン-1.0とアウェイ側のライン+1.0から推定
        
        # 単純な方法：オッズの幾何平均を使用
        # より精密には勝率ベースで計算すべきだが、まずはシンプルに
        
        # ±1.0から勝率を計算して平均を取る方法
        home_odds_plus1, away_odds_plus1 = odds_plus_1
        
        # 勝率に変換（マージン込み）
        home_prob_plus1 = 1.0 / home_odds_plus1
        away_prob_plus1 = 1.0 / away_odds_plus1
        
        # ライン0での推定勝率（簡易的に中間を取る）
        # 注：これは簡易実装。より正確には対数オッズ空間での補間が望ましい
        margin = home_prob_plus1 + away_prob_plus1
        
        # ライン0での勝率配分を推定
        # +1.0でホームが有利なので、0では中間的な値に
        home_prob_0 = (home_prob_plus1 + away_prob_plus1) / 2
        away_prob_0 = (away_prob_plus1 + home_prob_plus1) / 2
        
        # マージンを維持したまま正規化
        total = home_prob_0 + away_prob_0
        home_prob_0 = home_prob_0 * margin / total
        away_prob_0 = away_prob_0 * margin / total
        
        # オッズに変換
        home_odds_0 = self._round(1.0 / home_prob_0)
        away_odds_0 = self._round(1.0 / away_prob_0)
        
        return home_odds_0, away_odds_0
    
    def linear_interpolate_odds(
        self,
        line_lower: float,
        odds_lower: Tuple[float, float],
        line_upper: float,
        odds_upper: Tuple[float, float],
        target_line: float
    ) -> Tuple[float, float]:
        """
        2つのライン間でオッズを線形補間
        
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
        
        # 勝率ベースで補間（オッズの逆数）
        home_prob_lower = 1.0 / odds_lower[0]
        away_prob_lower = 1.0 / odds_lower[1]
        home_prob_upper = 1.0 / odds_upper[0]
        away_prob_upper = 1.0 / odds_upper[1]
        
        # 線形補間
        home_prob = home_prob_lower + (home_prob_upper - home_prob_lower) * ratio
        away_prob = away_prob_lower + (away_prob_upper - away_prob_lower) * ratio
        
        # オッズに変換
        home_odds = self._round(1.0 / home_prob)
        away_odds = self._round(1.0 / away_prob)
        
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
        
        # 補間対象のライン値を生成
        target_lines = []
        current = actual_min
        while current <= actual_max:
            # 丸め誤差を考慮
            rounded = round(current / step) * step
            if actual_min <= rounded <= actual_max:
                target_lines.append(rounded)
            current += step
        
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