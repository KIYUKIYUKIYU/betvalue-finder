# -*- coding: utf-8 -*-
"""
貼り付け方式で日本式EV%を算出。レーキバック（turnover, 0〜3%, 0.5%刻み）対応。
実効配当 O_eff = O + r/p を表示。
NEW: verdict(判定)の既定しきい値を固定実装（CLIで上書き可）。
"""

import os
import sys
import re
import csv
import argparse
from typing import Dict, Tuple, List, Optional
from converter.baseball_rules import (
    BaseballEV, remove_margin_fair_probs, linear_interpolate
)

# 日本語→英語チーム名（必要に応じて拡張）
JP2EN = {
    "ヤンキース": "New York Yankees",
    "レッドソックス": "Boston Red Sox",
    "メッツ": "New York Mets",
    "ドジャース": "Los Angeles Dodgers",
    "ジャイアンツ": "San Francisco Giants",
    "エンゼルス": "Los Angeles Angels",
    "マリナーズ": "Seattle Mariners",
    "レンジャーズ": "Texas Rangers",
    "アストロズ": "Houston Astros",
    "アスレチックス": "Oakland Athletics",
    "レイズ": "Tampa Bay Rays",
    "ブルージェイズ": "Toronto Blue Jays",
    "オリオールズ": "Baltimore Orioles",
    "タイガース": "Detroit Tigers",
    "ホワイトソックス": "Chicago White Sox",
    "ツインズ": "Minnesota Twins",
    "ガーディアンズ": "Cleveland Guardians",
    "ロイヤルズ": "Kansas City Royals",
    "パドレス": "San Diego Padres",
    "フィリーズ": "Philadelphia Phillies",
    "ブレーブス": "Atlanta Braves",
    "ブリュワーズ": "Milwaukee Brewers",
    "カージナルス": "St. Louis Cardinals",
    "カブス": "Chicago Cubs",
    "パイレーツ": "Pittsburgh Pirates",
    "レッズ": "Cincinnati Reds",
    "ダイヤモンドバックス": "Arizona Diamondbacks",
    "ロッキーズ": "Colorado Rockies",
    "ナショナルズ": "Washington Nationals",
    "マーリンズ": "Miami Marlins",
}

LINE_RE = re.compile(r"^\s*(?P<name>[^<>\r\n]+?)(?:<(?P<jp>[^>]+)>)?\s*$")

# 既定しきい値（%）
DEF_TH_CLEAR_PLUS = 5.0
DEF_TH_PLUS = 0.0
DEF_TH_FAIR = -3.0


def parse_paste_lines(path: str) -> List[Tuple[str, Optional[str]]]:
    pairs: List[Tuple[str, Optional[str]]] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            m = LINE_RE.match(raw)
            if not m:
                continue
            name = m.group("name").strip()
            jp = m.group("jp")
            jp = jp.strip() if jp else None
            pairs.append((name, jp))
    return pairs


def chunk_games(pairs: List[Tuple[str, Optional[str]]]) -> List[Tuple[Tuple[str, Optional[str]], Tuple[str, Optional[str]]]]:
    out = []
    for i in range(0, len(pairs) - 1, 2):
        out.append((pairs[i], pairs[i + 1]))
    return out


def load_dump_csv(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_row_for_match(rows: List[Dict[str, str]], en_a: str, en_b: str) -> Optional[Dict[str, str]]:
    for r in rows:
        h = r.get("home_team", "").strip()
        a = r.get("away_team", "").strip()
        if {h, a} == {en_a, en_b}:
            return r
    return None


def collect_line_odds(row: Dict[str, str]) -> Tuple[Dict[float, float], Dict[float, float]]:
    """
    行から Home/ Away のライン別オッズを抽出。
    戻り値：
      home_lines[line_value] = odd（H_...）
      away_lines[line_value] = odd（A_...）
    """
    home_lines: Dict[float, float] = {}
    away_lines: Dict[float, float] = {}
    for k, v in row.items():
        if not v:
            continue
        if k.startswith("H_") or k.startswith("A_"):
            try:
                odd = float(v)
            except ValueError:
                continue
            sign_val = k.split("_", 1)[1].replace("+", "")
            try:
                line_val = float(sign_val)
            except ValueError:
                continue
            if k.startswith("H_"):
                home_lines[line_val] = odd
            else:
                away_lines[line_val] = odd
    return home_lines, away_lines


def fair_prob_for_team_at_line(
    home_lines: Dict[float, float],
    away_lines: Dict[float, float],
    target_line_for_team: float,
    team_side: str,  # "home" or "away"
) -> Optional[float]:
    """
    指定チームの target_line における公正勝率を、既存ラインのペア H_l と A_-l から
    マージン除去→線形補間で推定。
    """
    usable: Dict[float, Tuple[float, float]] = {}
    for l, odd_home in home_lines.items():
        odd_away = away_lines.get(-l)
        if odd_away is not None:
            usable[l] = (odd_home, odd_away)

    anchors = sorted(usable.keys())
    if not anchors:
        return None

    if any(abs(a - target_line_for_team) < 1e-9 for a in anchors):
        key = [a for a in anchors if abs(a - target_line_for_team) < 1e-9][0]
        odd_h, odd_a = usable[key]
        p_home, _ = remove_margin_fair_probs(odd_h, odd_a)
        return p_home if team_side == "home" else (1.0 - p_home)

    lower = max([a for a in anchors if a <= target_line_for_team], default=None)
    upper = min([a for a in anchors if a >= target_line_for_team], default=None)
    if lower is None or upper is None:
        return None

    p_home_lower, _ = remove_margin_fair_probs(usable[lower][0], usable[lower][1])
    p_home_upper, _ = remove_margin_fair_probs(usable[upper][0], usable[upper][1])
    p_team_lower = p_home_lower if team_side == "home" else (1.0 - p_home_lower)
    p_team_upper = p_home_upper if team_side == "home" else (1.0 - p_home_upper)

    p_team = linear_interpolate(lower, p_team_lower, upper, p_team_upper, target_line_for_team)
    return p_team


def decide_verdict(ev_rake_pct: float, th_clear_plus: float, th_plus: float, th_fair: float) -> str:
    if ev_rake_pct >= th_clear_plus:
        return "clear_plus"
    if ev_rake_pct >= th_plus:
        return "plus"
    if ev_rake_pct >= th_fair:
        return "fair"
    return "minus"


def main():
    ap = argparse.ArgumentParser(description="MLB 日本式ハンデ（貼り付け比較）— turnover rakeback + 実効配当 + verdict/CSV")
    ap.add_argument("input_path", help="input\\paste_YYYYMMDD.txt")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD（ダンプCSVの日付と一致）")
    ap.add_argument("--season", default="2025")
    ap.add_argument("--league", default="1")
    ap.add_argument("--timezone", default="Asia/Tokyo")
    ap.add_argument("--csv", help="scripts\\output\\mlb_spreads_dump_YYYYMMDD.csv の明示パス")
    ap.add_argument("--jp_odds", type=float, default=1.9, help="日本式丸勝ちの配当（既定1.9）")
    ap.add_argument("--rakeback", type=float, default=0.0, help="レーキバック率（0〜0.03, 例: 0.015）")
    # verdict thresholds（CLI未指定なら既定値を使用）
    ap.add_argument("--th-clear-plus", type=float, help="clear_plus の下限（%） [既定: 5.0]")
    ap.add_argument("--th-plus", type=float, help="plus の下限（%） [既定: 0.0]")
    ap.add_argument("--th-fair", type=float, help="fair の下限（%） [既定: -3.0]")
    # CSV export
    ap.add_argument("--export", help="結果CSVの出力パス（例：scripts\\output\\compare_YYYYMMDD.csv）")
    args = ap.parse_args()

    # しきい値（CLI指定があれば上書き）
    th_clear_plus = args.th_clear_plus if args.th_clear_plus is not None else DEF_TH_CLEAR_PLUS
    th_plus = args.th_plus if args.th_plus is not None else DEF_TH_PLUS
    th_fair = args.th_fair if args.th_fair is not None else DEF_TH_FAIR

    # CSVの場所
    if args.csv:
        csv_path = args.csv
    else:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        csv_path = os.path.join(root, "scripts", "output", f"mlb_spreads_dump_{args.date.replace('-', '')}.csv")

    if not os.path.exists(csv_path):
        print(f"[error] スプレッドCSVが見つかりません: {csv_path}")
        print("       先に次のコマンドで生成してください：")
        print("       python scripts\\dump_spreads_csv.py --sport mlb data\\baseball_odds_YYYYMMDD.json --date YYYY-MM-DD")
        sys.exit(0)

    rows = load_dump_csv(csv_path)
    if not rows:
        print("[error] スプレッドCSVにデータがありません。")
        sys.exit(0)

    pairs = parse_paste_lines(args.input_path)
    games = chunk_games(pairs)
    if not games:
        print("[error] 入力の対戦が見つかりません（2行1組）。")
        sys.exit(0)

    ev = BaseballEV(
        jp_fullwin_odds=args.jp_odds,
        rakeback_pct=args.rakeback,   # 既定は 0.0（=0%）。内部で0.5%刻みに丸め。
    )

    # CSV用バッファ
    csv_rows: List[Dict[str, str]] = []

    for (name_a, jp_a), (name_b, jp_b) in games:
        en_a = JP2EN.get(name_a, name_a)
        en_b = JP2EN.get(name_b, name_b)

        row = find_row_for_match(rows, en_a, en_b)
        print("============================================================")
        if not row:
            print(f"{name_a} vs {name_b}")
            print("対象試合のオッズ行が見つかりません（チーム名不一致の可能性）。英語表記での照合を検討してください。")
            continue

        home_lines, away_lines = collect_line_odds(row)
        game_dt = row.get("game_datetime", "").strip()
        home_team = row.get("home_team", "").strip()
        away_team = row.get("away_team", "").strip()

        # <> が付いた側＝評価対象
        if jp_a:
            fav_name = en_a
            fav_jp = jp_a
            fav_side = "home" if fav_name == home_team else "away"
            oth_name = home_team if fav_side == "away" else away_team
        elif jp_b:
            fav_name = en_b
            fav_jp = jp_b
            fav_side = "home" if fav_name == home_team else "away"
            oth_name = home_team if fav_side == "away" else away_team
        else:
            print(f"{away_team} @ {home_team}")
            print("この対戦では日本式ラインが指定されていないためスキップしました。")
            continue

        try:
            pv = ev.jp_label_to_pinnacle_value(fav_jp)
        except Exception as e:
            print(f"{away_team} @ {home_team}")
            print(f"日本式ラベルの変換に失敗: {fav_jp} | {e}")
            continue

        # home座標系ではフェイバ側は -pv を見る
        target_line_for_home_axis = -pv
        p_team = fair_prob_for_team_at_line(
            home_lines=home_lines,
            away_lines=away_lines,
            target_line_for_team=target_line_for_home_axis,
            team_side=fav_side,
        )

        print(f"{away_team} @ {home_team}")
        if game_dt:
            print(f"開始時刻: {game_dt} (表示タイムゾーンはCSV準拠)")
        jp_side_label = f"{fav_name}（日本式: {fav_jp}）"
        if fav_side == "home":
            print(f"HOME: {jp_side_label}")
            print(f"AWAY: {oth_name}")
        else:
            print(f"HOME: {home_team}")
            print(f"AWAY: {jp_side_label}")

        if p_team is None:
            print("標準勝率: N/A / 公正勝率: N/A / 日本式EV: N/A / 日本式EV(レーキ後): N/A")
            print("※ 該当ラインのペアオッズ（H_l & A_-l）が不足しているため推定不可。")
            continue

        fair_odds = 1.0 / p_team
        ev_pct_plain = ev.ev_pct_plain(p_team)
        ev_pct_rake = ev.ev_pct_with_rakeback(p_team)

        # 実効配当（レーキ相当オッズ）：O_eff = O + r/p
        try:
            eff_odds = ev.jp_fullwin_odds + (ev.rakeback_pct / p_team)
        except ZeroDivisionError:
            eff_odds = float("inf")

        # verdict
        verdict = decide_verdict(ev_pct_rake, th_clear_plus, th_plus, th_fair)

        # 画面出力
        print(f"標準勝率: N/A / 公正勝率: {p_team*100:.1f}% / 日本式EV: {ev_pct_plain:+.1f}% / 日本式EV(レーキ後): {ev_pct_rake:+.1f}%")
        print(f"標準オッズ: N/A / 公正オッズ: {fair_odds:.3f}")
        print(f"[rakeback(turnover)] {ev.rakeback_pct:.3f}  / 日本式(実効配当): O={ev.jp_fullwin_odds:.3f} → O_eff={eff_odds:.3f}  / verdict: {verdict}")

        # CSV行
        csv_rows.append({
            "game_datetime": game_dt,
            "home_team": home_team,
            "away_team": away_team,
            "fav_side": fav_side,
            "fav_team": fav_name,
            "jp_label": fav_jp,
            "pin_value": f"{pv:.2f}",
            "fair_prob": f"{p_team:.5f}",
            "fair_odds": f"{fair_odds:.3f}",
            "ev_pct_plain": f"{ev_pct_plain:.2f}",
            "rakeback": f"{ev.rakeback_pct:.3f}",
            "jp_odds": f"{ev.jp_fullwin_odds:.3f}",
            "eff_odds": f"{eff_odds:.3f}",
            "ev_pct_rake": f"{ev_pct_rake:.2f}",
            "verdict": verdict,
            "th_clear_plus": f"{th_clear_plus:.2f}",
            "th_plus": f"{th_plus:.2f}",
            "th_fair": f"{th_fair:.2f}",
        })

    # CSV保存
    if args.export and csv_rows:
        export_path = args.export
        os.makedirs(os.path.dirname(export_path), exist_ok=True)
        with open(export_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"[exported] {export_path}")


if __name__ == "__main__":
    main()
