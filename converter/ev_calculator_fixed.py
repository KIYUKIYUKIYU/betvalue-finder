# -*- coding: utf-8 -*-
"""
converter/ev_calculator_fixed.py

README準拠の完全固定EV計算モジュール
絶対に変更しない不変コード

README Line 217-219:
EV% = (日本オッズ / フェアオッズ - 1) × 100
"""

def calculate_ev_readme_strict(jp_odds: float, fair_odds: float, rakeback: float = 0.015) -> dict:
    """
    README完全準拠のEV計算（不変版）
    
    Args:
        jp_odds: 日本側オッズ（通常1.60デフォルト）
        fair_odds: 公正オッズ（マージン除去済み）
        rakeback: レーキバック率（デフォルト0.015）
    
    Returns:
        {
            "ev_pct": EV%（レーキバックなし）,
            "ev_pct_rake": EV%（レーキバック込み）,
            "effective_jp_odds": 実効日本オッズ
        }
    """
    if not jp_odds or not fair_odds or fair_odds <= 0:
        return {
            "ev_pct": None,
            "ev_pct_rake": None, 
            "effective_jp_odds": None,
            "error": "Invalid odds values"
        }
    
    # レーキバックなしEV計算（README式）
    ev_pct = (jp_odds / fair_odds - 1) * 100
    
    # レーキバック込みEV計算（単純加算）
    effective_jp_odds = jp_odds + rakeback
    ev_pct_rake = (effective_jp_odds / fair_odds - 1) * 100
    
    return {
        "ev_pct": round(ev_pct, 2),
        "ev_pct_rake": round(ev_pct_rake, 2),
        "effective_jp_odds": round(effective_jp_odds, 6)
    }


def get_verdict(ev_pct_rake: float) -> str:
    """
    EV%からverdict判定（不変版）
    """
    if ev_pct_rake is None:
        return None
    
    if ev_pct_rake >= 5.0:
        return "clear_plus"
    elif ev_pct_rake >= 0.0:
        return "plus"
    elif ev_pct_rake >= -3.0:
        return "fair"
    else:
        return "minus"


# 検証用テストケース（不変データ）
def self_test():
    """自己検証テスト"""
    print("=== EV Calculator Fixed - Self Test ===")
    
    test_cases = [
        # (jp_odds, fair_odds, rakeback, expected_ev_rake)
        (1.60, 1.992, 0.015, -20.88),  # Everton case
        (1.60, 1.165, 0.015, 35.28),   # Union Berlin case (corrected)
    ]
    
    for jp_odds, fair_odds, rakeback, expected in test_cases:
        result = calculate_ev_readme_strict(jp_odds, fair_odds, rakeback)
        actual = result["ev_pct_rake"]
        match = abs(actual - expected) < 0.1 if actual is not None else False
        print(f"JP:{jp_odds}, Fair:{fair_odds} => EV:{actual}% {'✅' if match else '❌'}")
    
    print("Self test completed.")


if __name__ == "__main__":
    self_test()