# -*- coding: utf-8 -*-
"""
Mock Japanese Bookmaker API
日本ブックメーカーAPIのモック実装

Phase 1の一環として、日本ブックメーカーの論理的に一貫したラインとオッズを生成
"""

import random
from typing import Dict, Optional, Tuple
from decimal import Decimal


class MockJapaneseBookmaker:
    """
    日本ブックメーカーのモック実装

    現実的なライン調整とオッズ生成を行い、
    Pinnacleラインとは異なる値を提供する
    """

    def __init__(self):
        # 日本ブックメーカーの特徴：
        # - Pinnacleより保守的なライン設定
        # - 若干高いマージン
        self.margin_adjustment = 0.05  # 5%のマージン調整

    def generate_jp_line_and_odds(self,
                                 parsed_handicap: str,
                                 home_team: str,
                                 away_team: str) -> Dict[str, any]:
        """
        日本ブックメーカーのラインとオッズを生成

        Args:
            parsed_handicap: パーサーからのハンディキャップ値 (例: "1.5")
            home_team: ホームチーム名
            away_team: アウェーチーム名

        Returns:
            日本ブックメーカーの市場データ
        """

        try:
            base_line = float(parsed_handicap)
        except (ValueError, TypeError):
            base_line = 0.0

        # 日本ブックメーカーの特徴的調整
        jp_line_adjustment = self._calculate_jp_adjustment(home_team, away_team, base_line)
        jp_line = base_line + jp_line_adjustment

        # 日本市場向けのオッズ生成
        jp_odds = self._generate_jp_odds(jp_line, home_team, away_team)

        return {
            'jp_line': jp_line,
            'jp_odds': jp_odds,
            'jp_line_opposite': -jp_line,
            'jp_odds_opposite': self._calculate_opposite_odds(jp_odds),
            'bookmaker': 'JP_Mock',
            'currency': 'JPY',
            'last_updated': 'mock_timestamp'
        }

    def _calculate_jp_adjustment(self, home_team: str, away_team: str, base_line: float) -> float:
        """
        日本ブックメーカー特有のライン調整を計算

        実際の日本ブックメーカーの傾向：
        - 人気チームに有利なライン調整
        - 地域チームに微調整
        - 保守的なライン設定
        """

        adjustment = 0.0

        # NPBチームの人気度調整
        popular_teams = ['巨人', '阪神', 'ソフトバンク', '西武']
        if home_team in popular_teams:
            adjustment += 0.25  # 人気チームのホーム有利
        if away_team in popular_teams:
            adjustment -= 0.25  # 人気チームのアウェー不利

        # 地域性調整（関東vs関西など）
        kanto_teams = ['西武', '巨人', 'ヤクルト', '横浜', 'ロッテ']
        kansai_teams = ['阪神', 'オリックス']

        if home_team in kanto_teams and away_team in kansai_teams:
            adjustment += 0.1  # 関東ホーム有利
        elif home_team in kansai_teams and away_team in kanto_teams:
            adjustment -= 0.1  # 関西アウェー対応

        # ランダム市場変動要素（±0.1）
        market_variation = (random.random() - 0.5) * 0.2
        adjustment += market_variation

        return round(adjustment, 1)

    def _generate_jp_odds(self, jp_line: float, home_team: str, away_team: str) -> float:
        """
        日本市場向けのオッズを生成

        日本ブックメーカーの特徴：
        - 1.80-2.10の範囲が一般的
        - Pinnacleより若干マージンが高い
        """

        # ベースオッズ計算（ライン難易度に基づく）
        line_difficulty = abs(jp_line)

        if line_difficulty <= 0.5:
            base_odds = 1.90  # 互角に近い
        elif line_difficulty <= 1.0:
            base_odds = 1.85  # やや有利
        elif line_difficulty <= 1.5:
            base_odds = 1.82  # 有利
        else:
            base_odds = 1.78  # 大幅有利

        # 日本市場の微調整
        team_adjustment = 0.0
        if home_team in ['巨人', '阪神']:
            team_adjustment += 0.02  # 人気チーム補正
        if away_team in ['ソフトバンク', '西武']:
            team_adjustment -= 0.02  # 強豪アウェー補正

        # 市場変動
        market_variance = (random.random() - 0.5) * 0.08  # ±4%の変動

        final_odds = base_odds + team_adjustment + market_variance

        # 現実的な範囲に制限
        final_odds = max(1.70, min(2.20, final_odds))

        return round(final_odds, 2)

    def _calculate_opposite_odds(self, jp_odds: float) -> float:
        """
        対戦相手のオッズを計算

        総確率が100%を超えるようにマージンを設定
        """

        # 確率変換
        prob_main = 1.0 / jp_odds

        # 日本ブックメーカーのマージン（通常5-8%）
        total_margin = 1.05 + (random.random() * 0.03)  # 5-8%のマージン

        prob_opposite = total_margin - prob_main
        prob_opposite = max(0.45, min(0.58, prob_opposite))  # 現実的な範囲

        opposite_odds = 1.0 / prob_opposite

        return round(opposite_odds, 2)

    def get_market_summary(self, game_data: Dict) -> Dict:
        """
        市場概要を取得（デバッグ用）
        """

        jp_data = self.generate_jp_line_and_odds(
            game_data.get('handicap', '0'),
            game_data.get('team_a', ''),
            game_data.get('team_b', '')
        )

        return {
            'japanese_bookmaker': jp_data,
            'data_consistency': {
                'jp_line_type': type(jp_data['jp_line']).__name__,
                'jp_odds_range': f"{jp_data['jp_odds']:.2f}",
                'market_margin': f"{((1/jp_data['jp_odds']) + (1/jp_data['jp_odds_opposite'])) - 1:.3f}",
                'line_difference_expected': 'YES' if jp_data['jp_line'] != float(game_data.get('handicap', 0)) else 'NO'
            }
        }


# 使用例とテスト用のヘルパー関数
def test_mock_bookmaker():
    """モックブックメーカーのテスト"""

    mock_jp = MockJapaneseBookmaker()

    # 西武 vs ロッテのテストケース
    test_game = {
        'handicap': '1.5',
        'team_a': '西武',
        'team_b': 'ロッテ'
    }

    jp_data = mock_jp.generate_jp_line_and_odds(
        test_game['handicap'],
        test_game['team_a'],
        test_game['team_b']
    )

    print("🏟️ Mock Japanese Bookmaker Test")
    print("=" * 40)
    print(f"Original Handicap: {test_game['handicap']}")
    print(f"JP Line: {jp_data['jp_line']}")
    print(f"JP Odds: {jp_data['jp_odds']}")
    print(f"Market Margin: {((1/jp_data['jp_odds']) + (1/jp_data['jp_odds_opposite'])) - 1:.3f}")
    print(f"Line Difference: {'✅' if jp_data['jp_line'] != float(test_game['handicap']) else '❌'}")

    return jp_data


if __name__ == "__main__":
    test_mock_bookmaker()