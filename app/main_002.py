# manual_calc.py として保存
from converter.baseball_rules import BaseballEV

# 手動で期待値計算
ev_calc = BaseballEV(jp_fullwin_odds=1.9, rakeback_pct=0.015)

# 主要な試合のラインと推定勝率
matches = [
    ("バルセロナ", "1半7", 0.72),  # 1.85倍 → 勝率72%程度
    ("アーセナル", "1.8", 0.68),    # 1.80倍 → 勝率68%程度
    ("Aマドリード", "1半3", 0.70),  # 1.55倍 → 勝率70%程度
    ("ナポリ", "0半7", 0.62),       # 0.85倍 → 勝率62%程度
    ("ACミラン", "1.4", 0.66),      # 1.40倍 → 勝率66%程度
]

print("=" * 60)
print("手動期待値計算（推定値）")
print("=" * 60)

recommendations = []

for team, line, prob in matches:
    ev_plain = ev_calc.ev_pct_plain(prob)
    ev_rake = ev_calc.ev_pct_with_rakeback(prob)
    
    if ev_rake > 0:
        recommendations.append({
            'team': team,
            'line': line,
            'prob': prob * 100,
            'ev': ev_rake
        })

# EV順でソート
recommendations.sort(key=lambda x: x['ev'], reverse=True)

print("\n【推奨ベット】")
print("-" * 60)
for i, rec in enumerate(recommendations, 1):
    print(f"{i:2}. {rec['team']:12} {rec['line']:6}")
    print(f"    推定勝率: {rec['prob']:.1f}%")
    print(f"    期待値: +{rec['ev']:.1f}%")
    print()