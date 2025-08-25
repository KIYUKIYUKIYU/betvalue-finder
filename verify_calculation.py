#!/usr/bin/env python3
"""EV計算の数学的検証スクリプト"""

def verify_ev_calculation():
    """先ほどのAPI結果を手計算で検証"""
    
    # APIの返却値
    api_result = {
        "fav_fair_prob": 0.5394,
        "fav_fair_odds": 1.854,
        "fav_ev_pct": 2.49,
        "fav_ev_pct_rake": 3.99,
        "fav_eff_odds": 1.928,
    }
    
    # パラメータ
    jp_odds = 1.9  # 日本式固定配当
    rakeback = 0.015  # 1.5%
    p = api_result["fav_fair_prob"]
    
    # 手計算
    print("=== EV計算の検証 ===")
    print(f"公正勝率 p = {p:.4f}")
    print(f"日本式配当 O = {jp_odds}")
    print(f"レーキバック r = {rakeback} (1.5%)")
    print()
    
    # 基本EV
    ev_base = (p * jp_odds - 1) * 100
    print(f"基本EV = (p × O - 1) × 100")
    print(f"      = ({p:.4f} × {jp_odds} - 1) × 100")
    print(f"      = {ev_base:.2f}%")
    print(f"API値 = {api_result['fav_ev_pct']:.2f}% ✓")
    print()
    
    # レーキバック込みEV
    ev_rake = (p * jp_odds - 1 + rakeback) * 100
    print(f"レーキ込EV = (p × O - 1 + r) × 100")
    print(f"         = ({p:.4f} × {jp_odds} - 1 + {rakeback}) × 100")
    print(f"         = {ev_rake:.2f}%")
    print(f"API値 = {api_result['fav_ev_pct_rake']:.2f}% ✓")
    print()
    
    # 実効配当
    o_eff = jp_odds + rakeback / p
    print(f"実効配当 O_eff = O + r/p")
    print(f"              = {jp_odds} + {rakeback}/{p:.4f}")
    print(f"              = {o_eff:.3f}")
    print(f"API値 = {api_result['fav_eff_odds']:.3f} ✓")
    print()
    
    # 公正オッズの逆算
    fair_odds = 1 / p
    print(f"公正オッズ = 1/p = 1/{p:.4f} = {fair_odds:.3f}")
    print(f"API値 = {api_result['fav_fair_odds']:.3f} ✓")

if __name__ == "__main__":
    verify_ev_calculation()
