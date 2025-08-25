# scripts/dump_spreads_csv.py
# MLB: API-SPORTS(v1/baseball) のオッズJSONから
# "Asian Handicap/Run Line/Spread" 系市場を抽出 → マージン除去 → 0.05刻み補間 → CSV出力
#
# 出力: scripts/output/mlb_spreads_dump_YYYYMMDD.csv
#
# 使い方（必ずプロジェクト直下で実行）:
#   python scripts\dump_spreads_csv.py --sport mlb data\baseball_odds_YYYYMMDD.json --date YYYY-MM-DD

from __future__ import annotations
import argparse
import csv
import json
import math
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any

THIS_DIR = os.path.dirname(__file__)
OUTPUT_DIR = os.path.join(THIS_DIR, "output")

# 以前はID固定だったが、環境差吸収のため名称優先+ID併用
PINNACLE_PREFERRED_NAMES = {"pinnacle", "pinnacle sports"}
BET365_SECONDARY_NAMES = {"bet365", "bet 365"}
KNOWN_BOOK_IDS_PINNACLE = {4, 11}
KNOWN_BOOK_IDS_BET365 = {2, 8}

# 市場名のブレを広く許容（部分一致）
TARGET_MARKET_NAMES = {
    "asian handicap",
    "handicap",
    "spread",
    "spreads",
    "run line",
    "runline",
    "alternative run line",
    "alt run line",
    "run lines",
    "asian handicap first half",
    "asian handicap (1st inning)",
}

def ensure_dir(p: str) -> None:
    if not os.path.exists(p):
        os.makedirs(p, exist_ok=True)

def inv(x: float) -> float:
    return 1.0 / x if x > 0 else float("nan")

def margin_free_p(o_home: float, o_away: float) -> Tuple[float, float]:
    """ブックマージン除去 → 公正確率"""
    qh, qa = inv(o_home), inv(o_away)
    tot = qh + qa
    if tot <= 0 or not math.isfinite(tot):
        return float("nan"), float("nan")
    return qh / tot, qa / tot

def lin_interp(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    if abs(x2 - x1) < 1e-12:
        return y1
    t = (x - x1) / (x2 - x1)
    return y1 + t * (y2 - y1)

def norm_team_name(x: Any) -> str:
    """値オブジェクトの team/name などを正規化して比較用に小文字化"""
    if isinstance(x, dict):
        x = x.get("name") or x.get("abbr") or x.get("team") or ""
    return str(x).strip().lower()

def _parse_value_field(val: Any) -> Tuple[Optional[str], Optional[float]]:
    """
    'value' フィールドから (side, handicap) を抽出。
    受け入れ例:
      "Home -1" / "Away +1.5" / "home +0" / "away -0.5"
      "+1.5" / "-1" / "1.5" （サイド表記なし）
    戻り値: (side, h)  side は "home"/"away"/None, hは絶対値ではなく符号付き float
    """
    if val is None:
        return None, None
    s = str(val).strip()
    # 1) "Home -1.5" / "Away +1" 形式
    m = re.search(r'(?i)\b(home|away)\b\s*([+-]?\d+(?:\.\d+)?)', s)
    if m:
        side = m.group(1).lower()
        try:
            h = float(m.group(2))
            return side, h
        except Exception:
            return side, None
    # 2) "+1.5" / "-1" / "1.5" 単体
    m2 = re.search(r'([+-]?\d+(?:\.\d+)?)', s)
    if m2:
        try:
            h = float(m2.group(1))
            return None, h
        except Exception:
            return None, None
    return None, None

def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).replace(",", "").strip())
        except Exception:
            return None

def parse_values(values: List[dict], home_name: str, away_name: str) -> Dict[float, Tuple[float, float]]:
    """
    values から {handicap(abs): (odd_home, odd_away)} を組み立てる。
    対応フォーマット:
      A) odd_home/odd_away を1レコードで併記
      B) home/away を1レコードで併記
      C) team + odd が別レコード（teamがチーム名 or "home"/"away"）
      D) value="Home -1" かつ odd=xxx（Home/Awayを別レコードで提供）
      E) value="+1.5" かつ odd_home/odd_away（稀）
    """
    by_h: Dict[float, Tuple[float, float]] = {}
    tmp: Dict[float, Dict[str, float]] = defaultdict(dict)

    home_norm = norm_team_name(home_name)
    away_norm = norm_team_name(away_name)

    for v in values or []:
        side_from_value: Optional[str] = None  # "home"/"away"
        h_signed: Optional[float] = None
        h_abs: Optional[float] = None

        # handicap/value/line のいずれかから h を抽出
        if "handicap" in v and v["handicap"] is not None:
            h_signed = _to_float(v["handicap"])
        elif "line" in v and v["line"] is not None:
            h_signed = _to_float(v["line"])
        elif "value" in v and v["value"] is not None:
            side_from_value, h_signed = _parse_value_field(v["value"])

        # サイド表記なしの "+1.5" 等は h_signed として取得済み、サイドは後で判断
        if h_signed is None:
            # 旧ロジックへのフォールバック：valueが "Home -1" 以外の雑な文字列のとき
            # ここではスキップ
            pass

        # odd の取り出し（どの形式でもこれは共通）
        odd_homeaway_pair = ("odd_home" in v and "odd_away" in v)
        has_homeaway_pair = ("home" in v and "away" in v)
        team_raw = v.get("team")
        odd_single = _to_float(v.get("odd"))

        # まず A/B: 1レコード併記パターン
        if odd_homeaway_pair and h_signed is not None:
            h_abs = abs(h_signed)
            oH = _to_float(v.get("odd_home"))
            oA = _to_float(v.get("odd_away"))
            if oH is not None and oA is not None:
                tmp[h_abs]["home"] = oH
                tmp[h_abs]["away"] = oA
            continue

        if has_homeaway_pair and h_signed is not None:
            h_abs = abs(h_signed)
            oH = _to_float(v.get("home"))
            oA = _to_float(v.get("away"))
            if oH is not None and oA is not None:
                tmp[h_abs]["home"] = oH
                tmp[h_abs]["away"] = oA
            continue

        # C/D: 別レコードで side+odd が来るパターン
        # team か value の side から home/away を判定する
        side: Optional[str] = None
        if team_raw is not None:
            tnorm = norm_team_name(team_raw)
            if tnorm in (home_norm, "home"):
                side = "home"
            elif tnorm in (away_norm, "away"):
                side = "away"
        if side is None and side_from_value is not None:
            side = side_from_value

        if side and odd_single is not None and h_signed is not None:
            h_abs = abs(h_signed)
            tmp[h_abs][side] = odd_single
            continue

        # それ以外は無視

    # 片側ずつ集まっている場合にペアが揃ったものだけ採用
    by_h = {h: (sides["home"], sides["away"])
            for h, sides in tmp.items()
            if "home" in sides and "away" in sides}

    return by_h

def pick_market(bets: List[dict]) -> Tuple[Optional[dict], Optional[str]]:
    """AH/Spread/Run Line 系市場を拾う（表記揺れを広く許容）"""
    for b in bets or []:
        name = (b.get("name") or b.get("label") or "").strip()
        low = name.lower()
        if any(key in low for key in TARGET_MARKET_NAMES):
            return b, name
    return None, None

def load_events(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict) and "response" in d:
        return d["response"]
    if isinstance(d, list):
        return d
    return []

def classify_bookmakers(bookmakers: List[dict]) -> Tuple[Optional[dict], Optional[dict], Optional[List[dict]]]:
    """名称優先 + 既知IDで Pinnacle / Bet365 を特定、残りは others"""
    if not bookmakers:
        return None, None, None

    def bm_name(bm: dict) -> str:
        return str(bm.get("name") or bm.get("bookmaker") or "").strip()

    def bm_id(bm: dict) -> int:
        try:
            return int(bm.get("id") or bm.get("bookmaker_id") or -1)
        except Exception:
            return -1

    pinn = None
    b365 = None

    # 名称
    for bm in bookmakers:
        name = bm_name(bm).lower()
        if name in PINNACLE_PREFERRED_NAMES:
            pinn = bm
        elif name in BET365_SECONDARY_NAMES:
            b365 = bm

    # ID
    if pinn is None:
        for bm in bookmakers:
            if bm_id(bm) in KNOWN_BOOK_IDS_PINNACLE:
                pinn = bm
                break
    if b365 is None:
        for bm in bookmakers:
            if bm_id(bm) in KNOWN_BOOK_IDS_BET365:
                b365 = bm
                break

    others = []
    for bm in bookmakers:
        if bm is pinn or bm is b365:
            continue
        others.append(bm)

    return pinn, b365, others

def rows_from_bm(bm: Optional[dict], home_name: str, away_name: str, label_fallback: str) -> List[Tuple[float, float, float, str, str]]:
    """指定ブックメーカーから (h, p_home, p_away, source, market_name) の行を抽出"""
    rows: List[Tuple[float, float, float, str, str]] = []
    if not bm:
        return rows
    bets = bm.get("bets") or bm.get("markets") or []
    market, market_name = pick_market(bets)
    if not market:
        return rows
    values = market.get("values") or market.get("outcomes") or []
    by_h = parse_values(values, home_name, away_name)
    for h, (odds_home, odds_away) in by_h.items():
        p_home, p_away = margin_free_p(odds_home, odds_away)
        if any(not math.isfinite(x) for x in (p_home, p_away)):
            continue
        source = str(bm.get("name") or bm.get("bookmaker") or label_fallback).strip().lower()
        rows.append((h, p_home, p_away, source, market_name or ""))
    return rows

def extract_game_rows(event: dict) -> List[Tuple[float, float, float, str, str]]:
    """各試合の (h, p_home, p_away, source, market_name) を返す"""
    teams = event.get("teams") or {}
    home_name = (teams.get("home", {}) or {}).get("name") or event.get("homeTeam") or "HOME"
    away_name = (teams.get("away", {}) or {}).get("name") or event.get("awayTeam") or "AWAY"

    bookmakers = event.get("bookmakers") or event.get("odds") or []
    pinn, b365, others = classify_bookmakers(bookmakers)

    rows = rows_from_bm(pinn, home_name, away_name, "pinnacle")
    if not rows:
        rows = rows_from_bm(b365, home_name, away_name, "bet365")
    if not rows and others:
        for bm in others:
            rows = rows_from_bm(bm, home_name, away_name, "other")
            if rows:
                break
    return rows

def interpolate_rows(rows: List[Tuple[float, float, float, str, str]]) -> List[Tuple[float, float, float, str, str]]:
    """h の昇順で 0.05 刻みに補間（端部外挿なし）"""
    if not rows:
        return []
    rows = sorted(rows, key=lambda x: x[0])
    hs = [r[0] for r in rows]
    pH = [r[1] for r in rows]
    pA = [r[2] for r in rows]
    src = rows[0][3]
    mkt = rows[0][4]

    def round05(x: float) -> float:
        return round(round(x / 0.05) * 0.05, 10)

    h_min, h_max = hs[0], hs[-1]
    H: List[float] = []
    cur = math.ceil(h_min / 0.05) * 0.05
    cur = round05(cur)
    while cur <= h_max + 1e-9:
        H.append(round05(cur))
        cur += 0.05

    out: List[Tuple[float, float, float, str, str]] = []
    for x in H:
        # 既存点
        hit = [r for r in rows if abs(r[0] - x) < 1e-9]
        if hit:
            ph, pa = hit[0][1], hit[0][2]
            out.append((x, ph, pa, "observed:" + src, mkt))
            continue
        # 区間内なら線形補間
        left = None
        right = None
        for i in range(len(hs) - 1):
            if hs[i] <= x <= hs[i + 1]:
                left = i
                right = i + 1
                break
        if left is None:
            continue
        ph = lin_interp(hs[left], pH[left], hs[right], pH[right], x)
        pa = lin_interp(hs[left], pA[left], hs[right], pA[right], x)
        out.append((x, ph, pa, "interp:" + src, mkt))
    return out

def load_events(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict) and "response" in d:
        return d["response"]
    if isinstance(d, list):
        return d
    return []

def load_game_id(ev: dict) -> Any:
    return ev.get("game_id") or (ev.get("fixture") or {}).get("id") or ev.get("id")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", required=True, choices=["mlb", "baseball"], help="スポーツ種別")
    ap.add_argument("json_path", help=r"data\baseball_odds_YYYYMMDD.json")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD（出力ファイル名に使用）")
    args = ap.parse_args()

    ensure_dir(OUTPUT_DIR)

    events = load_events(args.json_path)
    all_rows = []  # (game_id, home, away, h, p_home, p_away, source, market_name)

    for ev in events:
        game_id = load_game_id(ev)
        teams = ev.get("teams") or {}
        home_name = (teams.get("home", {}) or {}).get("name") or ev.get("homeTeam") or "HOME"
        away_name = (teams.get("away", {}) or {}).get("name") or ev.get("awayTeam") or "AWAY"

        rows = extract_game_rows(ev)
        rows = interpolate_rows(rows)

        for (h, ph, pa, src, mkt) in rows:
            if any(not math.isfinite(x) for x in (ph, pa)):
                continue
            all_rows.append((game_id, home_name, away_name, h, ph, pa, src, mkt))

    out_csv = os.path.join(OUTPUT_DIR, f"mlb_spreads_dump_{args.date.replace('-','')}.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["game_id", "home", "away", "h", "p_home_fair", "p_away_fair", "source", "market_name"])
        for row in all_rows:
            w.writerow(row)

    print(f"✅ dumped: {out_csv} (rows: {len(all_rows)})")

if __name__ == "__main__":
    main()
