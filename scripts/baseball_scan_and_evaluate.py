# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import os
import sys
from typing import List

# =========================
# 重要: ModuleNotFoundError 対策
# プロジェクトルート (...\betvalue-finder) を sys.path に追加
# =========================
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# これで app.converter が確実に import 可能になる
from app.converter import jp_to_pinnacle  # 変換のみ使用

# 出力・閾値設定（README_PROJECT.md に従う）
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DUMP_PREFIX = "mlb_spreads_dump_"
JP_PAYOUT = 1.90

# verdict 閾値（※最終合意前の暫定値）
THRESH_CLEAR_PLUS = 0.05  # +5% 以上
THRESH_PLUS = 0.00        # 0% 以上
THRESH_FAIR = -0.03       # -3% 以上

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def read_dump(date: str) -> List[dict]:
    """
    scripts\\output\\mlb_spreads_dump_YYYYMMDD.csv を読む
    必須カラム: game_id, home, away, h, p_home_fair, p_away_fair
    """
    path = os.path.join(OUTPUT_DIR, f"{DUMP_PREFIX}{date.replace('-', '')}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(f"ダンプCSVが見つかりません: {path}")

    rows: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                r["h"] = float(r["h"])
                r["p_home_fair"] = float(r["p_home_fair"])
                r["p_away_fair"] = float(r["p_away_fair"])
                rows.append(r)
            except Exception:
                # 想定外の行はスキップ
                continue
    return rows

def nearest_prob(rows: List[dict], game_id, side: str, h_target: float):
    """同一 game_id 内で h_target に最も近い公正確率を返す"""
    candidates = [r for r in rows if str(r["game_id"]) == str(game_id)]
    if not candidates:
        return None
    best = min(candidates, key=lambda r: abs(r["h"] - h_target))
    return best["p_home_fair"] if side == "home" else best["p_away_fair"]

def ev_japanese_simple(p_win: float, stake: float = 1.0) -> float:
    """日本式 1.90 固定の単純EV（部分勝ち/負けの細則は別実装）"""
    return stake * (p_win * JP_PAYOUT - 1.0)

def verdict_from_edge(edge_pct: float) -> str:
    if edge_pct >= THRESH_CLEAR_PLUS * 100:
        return "clear_plus"
    if edge_pct >= THRESH_PLUS * 100:
        return "plus"
    if edge_pct >= THRESH_FAIR * 100:
        return "fair"
    return "minus"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help=r"data\baseball_odds_YYYYMMDD.json（存在確認のみ）")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    ensure_dir(OUTPUT_DIR)
    dump_rows = read_dump(args.date)

    if len(dump_rows) == 0:
        print("⚠ ダンプCSVの行数が 0 です。先に dump_spreads_csv.py の抽出条件を確認してください。")
        return

    # 既定の日本式候補セット（0, 0.25, 0.5, ... 3.0）
    default_lines = [round(x * 0.25, 10) for x in range(0, 13)]

    out_csv = os.path.join(OUTPUT_DIR, f"baseball_recommend_{args.date.replace('-', '')}.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["game_id","home","away","side","jp_line","pinn_value",
                    "fair_prob","fair_odds","jp_payout","edge_pct","verdict"])

        # game_id ごとにまとめる
        games = {}
        for r in dump_rows:
            games.setdefault(str(r["game_id"]), (r["home"], r["away"]))

        for gid, (home_name, away_name) in games.items():
            rows_g = [r for r in dump_rows if str(r["game_id"]) == gid]

            for jp in default_lines:
                # 日本式の表記文字列（1.0 は "1" として出す）
                jp_str = f"{jp:g}" if abs(jp - int(jp)) > 1e-9 else f"{int(jp)}"

                # 変換表に従い ピナクル値 へ
                try:
                    pinn = jp_to_pinnacle(jp_str)
                except Exception:
                    # 変換不可なものはスキップ
                    continue

                # ここでは home サイドのみ例示（必要に応じて away も評価可能）
                p = nearest_prob(rows_g, gid, "home", float(pinn))
                if not p or p <= 0:
                    continue

                fair_odds = 1.0 / p
                edge_pct = ev_japanese_simple(p) * 100.0  # %
                w.writerow([gid, home_name, away_name, "home", jp_str, f"{pinn:.2f}",
                            f"{p:.6f}", f"{fair_odds:.3f}", f"{JP_PAYOUT:.2f}",
                            f"{edge_pct:.2f}", verdict_from_edge(edge_pct)])

    print(f"✅ recommend: {out_csv}")

if __name__ == "__main__":
    main()
