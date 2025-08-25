# scripts/make_comparison_from_odds.py
# -*- coding: utf-8 -*-
import argparse, json, math, re, sys
from pathlib import Path
from datetime import datetime  # 日本語日付フォーマット用

# 対象マーケット名の表記ゆらぎを吸収
HANDICAP_MARKET_NAMES = {
    "Asian Handicap", "Handicap", "Run Line", "Runline", "Spreads", "Spread"
}
ML_MARKET_NAMES = {"Home/Away", "Match Winner", "Moneyline", "Money Line"}

JAPAN_FIXED_ODDS = 1.9  # 日本式：丸勝ち時の配当固定（期待値はこれを用いる）

def load_json(path):
    p = Path(path)
    if not p.exists():
        sys.exit(f"[error] file not found: {path}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_conversion_table(project_root: Path):
    """
    変換表（ピナクル→日本式）を読み込む。
    pinn_to_jp: {pinn(float): jp_str}
    jp_to_pinn_norm: {jp_str_normalized: pinn(float)}
    """
    table_path = project_root / "## 1. 変換表（ピナクル → 日本式）.txt"
    if not table_path.exists():
        sys.exit("[error] 変換表ファイルが見つかりません: " + str(table_path))
    pinn_to_jp = {}
    with table_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "," not in line or line.startswith("#") or "ピナクル値" in line:
                continue
            try:
                pval_str, jp = line.split(",", 1)
                pval = float(pval_str)
                pinn_to_jp[round(pval, 2)] = jp.strip()
            except Exception:
                continue
    jp_to_pinn = {jp: p for p, jp in pinn_to_jp.items()}
    def norm(s: str) -> str:
        return s.replace(" ", "").replace("　", "")
    jp_to_pinn_norm = {norm(jp): p for jp, p in jp_to_pinn.items()}
    return pinn_to_jp, jp_to_pinn_norm

def jp_to_pinn_value(jp_str: str, jp_to_pinn_norm: dict) -> float:
    """
    日本式→ピナクル値（絶対値）。変換表にない純小数は 0.5 倍で近似。
    例) "0.1"→0.05, "1半"→1.50, "1半7"→1.85
    """
    key = jp_str.replace(" ", "").replace("　", "")
    if key in jp_to_pinn_norm:
        return float(jp_to_pinn_norm[key])
    try:
        val = float(key)
        return round(val * 0.5, 2)
    except ValueError:
        sys.exit(f"[error] 変換表に無い日本式表記です: {jp_str}")

def parse_games_for_fixture(games_json, fixture_id: int):
    resp = games_json.get("response") if isinstance(games_json, dict) else None
    if not resp:
        sys.exit("[error] games JSON に response がありません")
    for g in resp:
        if int(g.get("id")) == int(fixture_id):
            home = g.get("teams", {}).get("home", {}).get("name")
            away = g.get("teams", {}).get("away", {}).get("name")
            start_iso = g.get("date")       # 例: "2025-08-22T08:15:00+09:00"
            tz = g.get("timezone")          # 例: "Asia/Tokyo"
            return home, away, start_iso, tz
    sys.exit(f"[error] fixture_id={fixture_id} が /games に見つかりません")

def extract_pinnacle_bookmaker(odds_json):
    resp = odds_json.get("response") if isinstance(odds_json, dict) else None
    if not resp:
        sys.exit("[error] odds JSON に response がありません")
    for item in resp:  # 1試合想定
        for bm in item.get("bookmakers", []):
            if bm.get("id") == 4 or (bm.get("name") or "").lower() == "pinnacle":
                return bm
    sys.exit("[error] Pinnacle (id=4) のオッズが見つかりません")

def parse_handicap_grid(bookmaker_dict):
    """
    grid: { line(float, HOME基準): {"home": odd(float)|None, "away": odd(float)|None} }
    ml:   {"home": odd|None, "away": odd|None}
    """
    grid = {}
    ml = {"home": None, "away": None}
    bets = bookmaker_dict.get("bets", []) or []
    for bet in bets:
        name = bet.get("name", "")
        values = bet.get("values", []) or []
        if name in ML_MARKET_NAMES:
            for v in values:
                side = str(v.get("value", ""))
                odd = float(v.get("odd")) if v.get("odd") not in (None, "") else None
                if side.lower().startswith("home"):
                    ml["home"] = odd
                elif side.lower().startswith("away"):
                    ml["away"] = odd
        if name in HANDICAP_MARKET_NAMES:
            for v in values:
                val = str(v.get("value", ""))  # "Home -1.5" / "Away +1.5"
                m = re.search(r"(Home|Away)\s*([+-]?\d+(\.\d+)?)", val)
                if not m:
                    continue
                side = m.group(1)
                h = float(m.group(2))
                # HOME視点のラインに正規化
                home_line = h if side == "Home" else -h
                odd = float(v.get("odd")) if v.get("odd") not in (None, "") else None
                home_line = round(home_line, 2)
                grid.setdefault(home_line, {"home": None, "away": None})
                if side == "Home":
                    grid[home_line]["home"] = odd
                else:
                    grid[home_line]["away"] = odd
    # ML を 0.0 に補完（厳密にはML≠0.0ハンデだが参照用）
    grid.setdefault(0.0, {"home": ml["home"], "away": ml["away"]})
    if grid[0.0]["home"] is None: grid[0.0]["home"] = ml["home"]
    if grid[0.0]["away"] is None: grid[0.0]["away"] = ml["away"]
    return grid, ml

def normalized_probs(o_home: float, o_away: float):
    """標準勝率（提示オッズの正規化）"""
    if not o_home or not o_away:
        return None, None
    qh, qa = 1.0 / o_home, 1.0 / o_away
    s = qh + qa
    if s <= 0:
        return None, None
    return qh / s, qa / s

def interpolate(x, x1, y1, x2, y2):
    if x1 == x2:
        return y1
    t = (x - x1) / (x2 - x1)
    return y1 + t * (y2 - y1)

def fair_prob_at_line(grid, target_line):
    """
    ラインごとに標準勝率 p_home を作り、target_line で線形補間して返す。
    """
    xs = sorted(grid.keys())
    pairs = []
    for ln in xs:
        oH, oA = grid[ln].get("home"), grid[ln].get("away")
        pH, _ = normalized_probs(oH, oA)
        if pH is not None:
            pairs.append((ln, pH))
    if not pairs:
        return None
    # ぴったりヒット
    for ln, ph in pairs:
        if abs(ln - target_line) < 1e-9:
            return ph
    # 区間探索
    left = right = None
    for i in range(len(pairs) - 1):
        lnx, lny = pairs[i]
        rnx, rny = pairs[i + 1]
        if lnx <= target_line <= rnx:
            left, right = (lnx, lny), (rnx, rny)
            break
    if not left or not right:
        # 端の外：一番近い方
        nearest = min(pairs, key=lambda t: abs(t[0] - target_line))
        return nearest[1]
    return interpolate(target_line, left[0], left[1], right[0], right[1])

def fmt_pct(x):
    return f"{x*100:.1f}%" if x is not None else "N/A"

def fmt_odds(x):
    return f"{x:.3f}" if x is not None else "N/A"

def fmt_ev_pct(p):
    """日本式1.9倍での期待値％。p が None のときは N/A。"""
    if p is None:
        return "N/A"
    ev = (p * JAPAN_FIXED_ODDS - 1.0) * 100.0
    sign = "+" if ev >= 0 else ""
    return f"{sign}{ev:.1f}%"

def main():
    ap = argparse.ArgumentParser(description="Make comparison (標準/公正 + 日本式EV) for a fixture at specified JP line.")
    ap.add_argument("--games", required=True)
    ap.add_argument("--odds", required=True)
    ap.add_argument("--fixture", required=True, type=int)
    ap.add_argument("--jp_line", required=True, help="例: 0.1 / 1半 / 1半7 等")
    ap.add_argument("--fav_side", required=True, choices=["home", "away"], help="<> が付いている側")
    args = ap.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    pinn_to_jp, jp_to_pinn_norm = load_conversion_table(project_root)
    pinn_line_abs = jp_to_pinn_value(args.jp_line, jp_to_pinn_norm)

    games_json = load_json(args.games)
    odds_json  = load_json(args.odds)

    home, away, start_iso, tz = parse_games_for_fixture(games_json, args.fixture)

    # HOME基準ライン
    line_home = -pinn_line_abs if args.fav_side == "home" else +pinn_line_abs
    line_away = -line_home

    bm = extract_pinnacle_bookmaker(odds_json)
    grid, ml = parse_handicap_grid(bm)

    # 標準（提示）＆ 公正（補間）
    # HOME
    oH_std = oA_std = None
    pH_std = pA_std = None
    if line_home in grid and grid[line_home]["home"] and grid[line_home]["away"]:
        oH_std, oA_std = grid[line_home]["home"], grid[line_home]["away"]
        pH_std, pA_std = normalized_probs(oH_std, oA_std)
    pH_fair = fair_prob_at_line(grid, line_home)
    pA_fair = 1.0 - pH_fair if pH_fair is not None else None
    oH_fair = (1.0 / pH_fair) if pH_fair else None

    # AWAY
    oH_std2 = oA_std2 = None
    pH_std2 = pA_std2 = None
    if line_away in grid and grid[line_away]["home"] and grid[line_away]["away"]:
        oH_std2, oA_std2 = grid[line_away]["home"], grid[line_away]["away"]
        pH_std2, pA_std2 = normalized_probs(oH_std2, oA_std2)
    pH_fair2 = fair_prob_at_line(grid, line_away)
    oA_fair2 = (1.0 / (1.0 - pH_fair2)) if pH_fair2 is not None else None

    # 日本式注記
    jp_note_home = pinn_to_jp.get(abs(round(line_home, 2)))
    jp_note_away = pinn_to_jp.get(abs(round(line_away, 2)))

    # 日付（日本語・ゼロ埋め）
    try:
        dt = datetime.fromisoformat(start_iso)
        date_str = dt.strftime("%Y年%m月%d日 %H:%M")
    except Exception:
        date_str = start_iso

    # 出力
    print("=" * 60)
    print(f"{away} @ {home}")
    print(f"開始時刻: {date_str} (日本時間)")
    print("=" * 60)

    print(f"HOME: {home} （日本式: {'-' if line_home<0 else '+'}{jp_note_home or 'N/A'}）")
    if pH_std is not None:
        print(f"  標準勝率: {fmt_pct(pH_std)} / 公正勝率: {fmt_pct(pH_fair)} / 日本式EV: {fmt_ev_pct(pH_fair)}")
        print(f"  標準オッズ: {fmt_odds(oH_std)} / 公正オッズ: {fmt_odds(oH_fair)}")
    else:
        print(f"  標準勝率: N/A / 公正勝率: {fmt_pct(pH_fair)} / 日本式EV: {fmt_ev_pct(pH_fair)}")
        print(f"  標準オッズ: N/A / 公正オッズ: {fmt_odds(oH_fair)}")
    print()

    print(f"AWAY: {away} （日本式: {'-' if line_away<0 else '+'}{jp_note_away or 'N/A'}）")
    if pH_std2 is not None:
        print(f"  標準勝率: {fmt_pct(1.0 - pH_std2)} / 公正勝率: {fmt_pct(1.0 - (pH_fair2 or 0.0) if pH_fair2 is not None else None)} / 日本式EV: {fmt_ev_pct(1.0 - pH_fair2 if pH_fair2 is not None else None)}")
        print(f"  標準オッズ: {fmt_odds(oA_std2)} / 公正オッズ: {fmt_odds(oA_fair2)}")
    else:
        print(f"  標準勝率: N/A / 公正勝率: {fmt_pct(1.0 - (pH_fair2 or 0.0) if pH_fair2 is not None else None)} / 日本式EV: {fmt_ev_pct(1.0 - pH_fair2 if pH_fair2 is not None else None)}")
        print(f"  標準オッズ: N/A / 公正オッズ: {fmt_odds(oA_fair2)}")
    print()

if __name__ == "__main__":
    main()
