# scripts/reply_matchups_report.py
# 目的:
#   ユーザーのテキスト入力（対戦カード＋日本式ハンデ）を読み取り、
#   MLB の Pinnacle AH(Asian Handicap) を基準に
#   「標準勝率/標準倍率（提示オッズ）」「公正勝率/公正倍率（マージン除去後）」を
#   フェイバ/アンダーの両側で表示する。
#
# 入力:
#   1) ユーザーのテキスト (UTF-8)。例:
#      [ＭＬＢ]
#      ツインズ
#      アスレチックス<0.1>
#      (空行)
#      ロイヤルズ<0.2>
#      レンジャーズ
#      ...
#   2) 当日の odds JSON: data/baseball_odds_YYYYMMDD.json
#   3) dumps CSV: scripts/output/mlb_spreads_dump_YYYYMMDD.csv
#
# 前提:
#   - dumps CSV には p_home_fair/p_away_fair（公正勝率）が入っている
#   - odds JSON から「標準オッズ（提示オッズ）」を引く
#   - 市場はフルゲームの「Asian Handicap」を優先（1st Inning/First Halfは除外）
#   - 「<> が付いた側 = マイナス側（負担）」とする（ユーザー合意済）
#
# 使い方 (cmd.exe):
#   python scripts\reply_matchups_report.py ^
#       --date 2025-08-22 ^
#       --user-text .\user_input.txt ^
#       --odds-json data\baseball_odds_20250822.json
#
# 出力:
#   コンソールにカードごとのレポートをテキストで表示
#
# 注意:
#   - チーム名の揺れは簡易正規化（小文字化・空白除去）で突合
#   - 標準オッズは「観測点(h=H)が JSON にある場合のみ」取得。無い場合は "—"
#   - 公正値は dumps CSV の h=H を使用。無いときは最も近い h を補間ベースで利用
#   - 日本式 <X> → Pinnacle H の対応は 0.05 刻み（0.1→0.05, 0.2→0.10, 1半→1.5 など）
#

from __future__ import annotations
import argparse
import csv
import json
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# -------------------------------
# 基本ユーティリティ
# -------------------------------

def norm_name(s: str) -> str:
    return re.sub(r"\s+", "", s or "").lower()

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_json_events(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict) and "response" in d:
        return d["response"]
    if isinstance(d, list):
        return d
    return []

def load_dump_csv(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            # 型を少し整える
            try:
                row["h"] = float(row["h"])
                row["p_home_fair"] = float(row["p_home_fair"])
                row["p_away_fair"] = float(row["p_away_fair"])
            except Exception:
                pass
            rows.append(row)
    return rows

def to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        try:
            return float(str(x).replace(",", "").strip())
        except Exception:
            return None

def pct(x: float, nd=1) -> str:
    if x is None or not math.isfinite(x):
        return "—"
    return f"{x*100:.{nd}f}%"

def odds_fmt(x: float, nd=4) -> str:
    if x is None or not math.isfinite(x) or x <= 0:
        return "—"
    return f"{x:.{nd}f}"

# -------------------------------
# 日本式 <X> → Pinnacle H の変換
#  - 0.1→0.05, 0.2→0.10, 0.3→0.15, ...
#  - 「半」= +0.5 の意味（例: 1半→1.5, 1半1→1.1? など表記バリエは本変換では
#     最小限: [数字][半] のみ対応。必要に応じて拡張）
# -------------------------------

def jp_to_pinnacle_h(jp: str) -> Optional[float]:
    """
    日本式 "<...>" 内の値を Pinnacle の H（絶対値, 0.05 刻み）へ
    例:
      "0.1" -> 0.05
      "0.2" -> 0.10
      "1.0" -> 1.00
      "1半"  -> 1.5
      "3.0" -> 3.0
    """
    s = jp.strip()
    # 「半」を含む (例: "1半" → 1.5)
    if "半" in s:
        # 数字部のみ拾う
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", s)
        base = float(m.group(1)) if m else 0.0
        return round(base + 0.5, 2)

    # 純数値（0.1, 0.2, 1.0, 3.0 など）
    try:
        x = float(s)
    except Exception:
        return None

    # 0.1 刻み → 0.05 刻みに合わせる（0.1→0.05, 0.2→0.10 ...）
    # ただし整数などはそのまま
    if abs(x - round(x)) < 1e-9:
        return float(f"{x:.2f}")
    # 小数第1位（0.1/0.2/0.3/...）→ x/2
    return float(f"{(x/2):.2f}")

# -------------------------------
# ユーザー入力をパースして、[ (teamA, teamB, jp_handicap_str_on_A_or_B) ] の配列に
#   - 直前/直後の2行で1カードとみなす
#   - 「<...>」が付いている側が“マイナス側（負担）”
# -------------------------------

def parse_user_cards(user_text: str) -> List[Tuple[str, str, Optional[Tuple[str, str]]]]:
    """
    戻り値: [(team_top, team_bottom, handicap_tuple), ...]
    handicap_tuple は (side, jp_value_str) で side in {"top","bottom"}
    無い場合は None
    """
    lines = [l.strip() for l in user_text.splitlines()]
    # 雑見出しや空行をスキップしつつ2行ごとに組む
    teams: List[str] = []
    for l in lines:
        if not l or l.startswith("["):
            continue
        teams.append(l)

    cards: List[Tuple[str, str, Optional[Tuple[str, str]]]] = []
    i = 0
    while i < len(teams):
        if i+1 >= len(teams):
            break
        top = teams[i]
        bottom = teams[i+1]
        i += 2

        # <...> を検出
        m_top = re.search(r"<([^>]+)>", top)
        m_bot = re.search(r"<([^>]+)>", bottom)
        hc: Optional[Tuple[str, str]] = None
        if m_top and not m_bot:
            hc = ("top", m_top.group(1))
            top = re.sub(r"<[^>]+>", "", top).strip()
        elif m_bot and not m_top:
            hc = ("bottom", m_bot.group(1))
            bottom = re.sub(r"<[^>]+>", "", bottom).strip()
        elif m_top and m_bot:
            # 両方にあるケースは今は bottom を優先（必要あれば設計で決める）
            hc = ("bottom", m_bot.group(1))
            bottom = re.sub(r"<[^>]+>", "", bottom).strip()

        cards.append((top, bottom, hc))
    return cards

# -------------------------------
# JSON から フルゲーム Asian Handicap の「標準オッズ」を取得
#   - h=H の観測点があれば、home/away の raw odds を返す
#   - 名称に "1st" "First Half" 等が入る市場は除外
#   - values の value="Home -1" / "Away +1.5" / team+odd などの形式に対応
# -------------------------------

MARKET_BLACKLIST_KEYWORDS = ("1st inning", "first half", "(1st inning)")

def pick_fullgame_ah_market(bookmakers: List[dict]) -> Optional[dict]:
    # Pinnacle を優先
    def bm_name(bm: dict) -> str:
        return (bm.get("name") or bm.get("bookmaker") or "").strip().lower()

    pinn = None
    for bm in bookmakers or []:
        if bm_name(bm) in ("pinnacle", "pinnacle sports"):
            pinn = bm
            break
    cand = [pinn] if pinn else bookmakers or []
    for bm in cand:
        markets = bm.get("bets") or bm.get("markets") or []
        for mk in markets:
            name = (mk.get("name") or mk.get("label") or "").strip().lower()
            if "asian handicap" in name and not any(k in name for k in MARKET_BLACKLIST_KEYWORDS):
                return mk
    return None

def parse_market_values_for_raw_odds(market: dict, home_name: str, away_name: str) -> Dict[float, Tuple[Optional[float], Optional[float]]]:
    """
    観測値のみ（補間なし）の raw odds を h → (odd_home, odd_away) で返す
    h は絶対値（0.05, 0.10, 1.50 など）
    """
    values = market.get("values") or market.get("outcomes") or []
    home_norm = norm_name(home_name)
    away_norm = norm_name(away_name)

    out: Dict[float, Tuple[Optional[float], Optional[float]]] = {}

    for v in values:
        # h 抽出
        h = None
        # 1) handicap/line
        for hk in ("handicap", "line", "value"):
            if hk in v and v[hk] is not None:
                # value は "Home -1" 形式もある
                if hk == "value":
                    m = re.search(r'(?i)\b(home|away)\b\s*([+-]?\d+(?:\.\d+)?)', str(v["value"]))
                    if m:
                        try:
                            h = abs(float(m.group(2)))
                        except Exception:
                            h = None
                    else:
                        # "+1.5" のような単体
                        m2 = re.search(r'([+-]?\d+(?:\.\d+)?)', str(v["value"]))
                        if m2:
                            h = abs(float(m2.group(1)))
                else:
                    h = abs(to_float(v[hk]) or 0.0)
                break
        if h is None:
            continue

        # odds 抽出
        oH, oA = None, None
        if "odd_home" in v and "odd_away" in v:
            oH = to_float(v.get("odd_home"))
            oA = to_float(v.get("odd_away"))
        elif "home" in v and "away" in v:
            oH = to_float(v.get("home"))
            oA = to_float(v.get("away"))
        else:
            # team+odd が別行
            t = (v.get("team") or "").strip()
            o = to_float(v.get("odd"))
            if t and o is not None:
                tn = norm_name(t)
                # 片側ずつ集めるため、先に既存を参照
                oH_existing, oA_existing = out.get(h, (None, None))
                if tn in (home_norm, "home"):
                    oH = o if oH is None else oH
                    oA = oA_existing
                elif tn in (away_norm, "away"):
                    oA = o if oA is None else oA
                    oH = oH_existing
        # 更新
        curH, curA = out.get(h, (None, None))
        if oH is None:
            oH = curH
        if oA is None:
            oA = curA
        out[h] = (oH, oA)

    # 片側欠けているものは残してもOK（表示側で "—" にする）
    return out

# -------------------------------
# dumps CSV（公正勝率）から h=H を探す
#   - 完全一致が無ければ最近傍（|h-H|最小）を使う
# -------------------------------

def pick_fair_probs(dump_rows: List[Dict[str, Any]], game_id: Any, H: float) -> Optional[Tuple[float, float, float]]:
    """
    戻り値: (h_used, p_home_fair, p_away_fair) or None
    """
    cand = [r for r in dump_rows if str(r.get("game_id")) == str(game_id)]
    if not cand:
        return None
    # 最も近い h
    best = None
    best_d = 1e9
    for r in cand:
        try:
            h = float(r["h"])
            d = abs(h - H)
            if d < best_d:
                best_d = d
                best = r
        except Exception:
            continue
    if not best:
        return None
    return float(best["h"]), float(best["p_home_fair"]), float(best["p_away_fair"])

# -------------------------------
# メイン処理
# -------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYY-MM-DD（CSV/JSONの日付）」")
    ap.add_argument("--user-text", required=True, help="ユーザー入力テキストファイル（UTF-8）")
    ap.add_argument("--odds-json", required=True, help=r"odds JSON（例: data\baseball_odds_YYYYMMDD.json）")
    ap.add_argument("--dump-csv", default=None, help=r"dumps CSV（省略時は scripts\output\mlb_spreads_dump_YYYYMMDD.csv）")
    args = ap.parse_args()

    date_dash = args.date
    date_compact = date_dash.replace("-", "")
    dump_csv = args.dump_csv or os.path.join("scripts", "output", f"mlb_spreads_dump_{date_compact}.csv")

    user_text = read_text(args.user_text)
    cards = parse_user_cards(user_text)
    events = load_json_events(args.odds_json)
    dump_rows = load_dump_csv(dump_csv)

    # events を (norm_home, norm_away) キーで引けるように整形
    idx = []
    for ev in events:
        teams = ev.get("teams") or {}
        home = (teams.get("home", {}) or {}).get("name") or ev.get("homeTeam") or "HOME"
        away = (teams.get("away", {}) or {}).get("name") or ev.get("awayTeam") or "AWAY"
        idx.append((norm_name(home), norm_name(away), ev))

    # カードごとに処理
    for (top, bottom, hc) in cards:
        top_raw, bottom_raw = top, bottom
        top_n, bot_n = norm_name(top), norm_name(bottom)

        # マッチする試合（home,awayのどちらが top/bottom でもOK）
        match_ev = None
        home_first = True
        for (h_n, a_n, ev) in idx:
            if (top_n == h_n and bot_n == a_n) or (top_n == a_n and bot_n == h_n):
                match_ev = ev
                home_first = (top_n == h_n)  # Trueなら top=HOME
                break

        # 見出し
        if match_ev:
            teams = match_ev.get("teams") or {}
            home = (teams.get("home", {}) or {}).get("name") or "HOME"
            away = (teams.get("away", {}) or {}).get("name") or "AWAY"
            title = f"{away} @ {home}"
        else:
            title = f"{bottom_raw} @ {top_raw}"

        print("="*60)
        print(title)
        print(f"対象日: {date_dash} (JST)")
        print("="*60)

        if not match_ev:
            print("試合が見つかりませんでした。チーム名/日付をご確認ください。")
            print()
            continue

        # H を決める（<> が付いた側 = マイナス側）
        H = None
        minus_side = None  # "home" or "away"
        if hc:
            side_tag, jp_val = hc  # side_tag in {"top","bottom"}
            H = jp_to_pinnacle_h(jp_val)
            if H is None:
                print(f"ハンデの解釈に失敗しました: <{jp_val}>")
                print()
                continue
            # どちらがマイナス側か
            #   top が HOME なら side_tag=="top" → HOMEがマイナス
            #   top が AWAY なら side_tag=="top" → AWAYがマイナス
            minus_side = "home" if (home_first and side_tag=="top") or ((not home_first) and side_tag=="bottom") else "away"
        else:
            print("ハンデ表記 <...> が見つからなかったため、基準ラインが決められません。")
            print()
            continue

        # 標準オッズ（観測点）取得
        bookmakers = match_ev.get("bookmakers") or match_ev.get("odds") or []
        mk = pick_fullgame_ah_market(bookmakers)
        raw_home, raw_away = None, None
        if mk:
            raw_map = parse_market_values_for_raw_odds(mk,
                                                       (match_ev.get("teams") or {}).get("home", {}).get("name") or "HOME",
                                                       (match_ev.get("teams") or {}).get("away", {}).get("name") or "AWAY")
            if H in raw_map:
                raw_home, raw_away = raw_map[H]

        # 公正（CSVから）
        game_id = match_ev.get("game_id") or (match_ev.get("fixture") or {}).get("id") or match_ev.get("id")
        picked = pick_fair_probs(dump_rows, game_id, H)
        if not picked:
            print("公正勝率が見つかりませんでした（CSV未整備または日付違い）。")
            print()
            continue
        h_used, pH_fair, pA_fair = picked

        # 表示対象の2側（マイナス側 / プラス側）
        # minus_side が "home" なら home が負担、away が受け取り
        sides = [("minus", minus_side), ("plus", "away" if minus_side=="home" else "home")]

        # 標準勝率/倍率は観測点がある場合のみ（raw_odds から）
        def std_odds_to_prob(o: Optional[float]) -> Optional[float]:
            if o is None or o <= 1e-9:
                return None
            return 1.0 / o

        # 出力
        for label, side in sides:
            # ラベル文字列
            jp_sign = "-" if label=="minus" else "+"
            # どの列を使うか（公正）
            if side == "home":
                p_fair = pH_fair
                o_std = raw_home  # 観測点あれば
            else:
                p_fair = pA_fair
                o_std = raw_away

            # 公正倍率
            o_fair = (1.0 / p_fair) if p_fair and p_fair > 0 else None
            # 標準勝率（観測点がある時だけ）
            p_std = std_odds_to_prob(o_std) if o_std and o_std > 0 else None

            # サイド名（HOME/AWAY）
            hv = "HOME" if side=="home" else "AWAY"
            # チーム名（読みやすく）
            teams = match_ev.get("teams") or {}
            team_name = (teams.get(side, {}) or {}).get("name") or hv

            # 見出し行
            print(f"{team_name} <{jp_sign}{(H*2):.1f if H<1 else H:.1f if H%1==0 else H}>  （H={H:.2f})")
            # ↑ 表示上の <±X> は “日本式X = H×2（小数1位）” をベースに簡易表示
            #   例: H=0.05 → 0.1, H=1.50 → 3.0 ではなく 1半 等の完全表記は簡易化
            #   （将来：変換表から日本式表記を厳密生成へ）

            print(f"  標準勝率: {pct(p_std, 1)}    標準倍率: {odds_fmt(o_std, 4)}")
            print(f"  公正勝率: {pct(p_fair, 1)}    公正倍率: {odds_fmt(o_fair, 4)}")
            print()

    # 最後に軽い注意
    print("※ 標準は観測点(h=H)に raw オッズがある場合のみ計算。無い場合は “—”。")
    print("※ 公正は dumps CSV を使用（観測点が無ければ最近傍を利用）。")
    print("※ フルゲームの Asian Handicap のみを対象にしています。")
    print()
    print("完了。")
    

if __name__ == "__main__":
    main()
