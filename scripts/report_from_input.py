# -*- coding: utf-8 -*-
"""
report_from_input.py (Phase 1: MLベースで標準/公正を一覧表示)
- 入力の対戦カードをAPI-SPORTSのfixturesに突き合わせ
- Pinnacle(4)のHome/Away(=ML)から標準/公正の勝率・オッズを算出
- 表形式で出力（HOME→AWAYの順を固定）
次版で：日本式ハンデ値での補間（0.05刻み）を追加予定
"""
import os
import sys
import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
import requests

API_BASE = "https://v1.baseball.api-sports.io"
BOOKMAKER_PINNACLE = 4

def jst_iso(dt_utc_str: str) -> str:
    # APIはUTC ISOを返す: "2025-08-21T23:15:00+00:00"
    try:
        dt = datetime.fromisoformat(dt_utc_str.replace("Z","+00:00"))
        jst = dt.astimezone(timezone(timedelta(hours=9)))
        return jst.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return dt_utc_str

def remove_margin_to_probs(odd_home: float, odd_away: float):
    # マージン除去（2項）
    qh = 1.0 / odd_home
    qa = 1.0 / odd_away
    total = qh + qa
    ph = qh / total
    pa = qa / total
    return ph, pa

def to_pct(x: float) -> str:
    return f"{x*100:.1f}%"

def fetch_json(path: str, params: dict, api_key: str):
    headers = {"x-apisports-key": api_key}
    url = f"{API_BASE}{path}?{urlencode(params)}"
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

def normalize_team_name(s: str) -> str:
    # 大文字小文字/スペース/ピリオド等を緩く吸収
    s = s.strip().lower()
    s = re.sub(r"[\.\-]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s

def parse_user_input(path: str):
    """
    入力例：
    [ＭＬＢ]

    ツインズ
    アスレチックス<0.1>

    ロイヤルズ<0.2>
    レンジャーズ
    ...
    """
    text = open(path, "r", encoding="utf-8").read()
    # ブロックごとに「行の非空×2」を拾う（<0.x>はあってもなくてもOK）
    # 1行目=上段、2行目=下段。下段に<0.x>が付くことが多いので残しておく（今は未使用）
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # ラベル行（[ＭＬＢ]等）は除外
    lines = [ln for ln in lines if not ln.startswith("[") and not ln.startswith("【")]

    pairs = []
    i = 0
    while i < len(lines)-1:
        top = lines[i]
        bottom = lines[i+1]
        pairs.append((top, bottom))
        i += 2
    return pairs

def pick_fixture_for_pair(pair, fixtures):
    """
    pair: (line1, line2)
    fixtures: API /games の response配列
    マッチ方針：
      - fixtureの (away_name @ home_name) と照合
      - 行順はユーザー入力の順のまま（上段=ホーム/アウェイの断定はしない）
      - 英名/略称に寄せるため、normalizeして部分一致も許容
    """
    p1, p2 = pair
    # 角カッコ内の日本式表記を除去（名前側だけ取り出す）
    team1 = re.sub(r"<.*?>", "", p1).strip()
    team2 = re.sub(r"<.*?>", "", p2).strip()

    n1 = normalize_team_name(team1)
    n2 = normalize_team_name(team2)

    candidates = []
    for fx in fixtures:
        home = fx["teams"]["home"]["name"]
        away = fx["teams"]["away"]["name"]
        nh = normalize_team_name(home)
        na = normalize_team_name(away)

        # 2方向（team1 vs team2 / team2 vs team1）の緩い一致
        ok12 = (n1 in nh or nh in n1 or n1 in na or na in n1) and \
               (n2 in nh or nh in n2 or n2 in na or na in n2)
        if not ok12:
            continue
        # 未来試合（Not Started/Scheduled）
        st = fx.get("status", {}).get("long") or fx.get("status", {}).get("short")
        if isinstance(st, str) and st.lower().startswith(("not started","scheduled","ns")):
            candidates.append(fx)

    # 単純に最初の候補を採用（※曖昧ケースは将来スコア）
    return candidates[0] if candidates else None

def extract_ml_from_pinnacle(odds_json: dict):
    """
    Pinnacleの bookmakers -> bets の中から "Home/Away" を探す
    戻り値: (odd_home, odd_away) or None
    """
    resp = odds_json.get("response", [])
    if not resp:
        return None
    bk_list = resp[0].get("bookmakers", [])
    bk = next((b for b in bk_list if b.get("id")==BOOKMAKER_PINNACLE), None)
    if not bk:
        return None
    bets = bk.get("bets", [])
    ml = next((b for b in bets if (b.get("name") in ("Home/Away","Money Line","Money Line (Including OT)"))), None)
    if not ml:
        # 一部ブックで "Match Winner" をML相当として扱うこともあるが、Pinnacleは基本 "Home/Away"
        ml = next((b for b in bets if b.get("name")=="Match Winner"), None)
    if not ml:
        return None
    vals = ml.get("values", [])
    v_home = next((v for v in vals if v.get("value")=="Home"), None)
    v_away = next((v for v in vals if v.get("value")=="Away"), None)
    if not (v_home and v_away):
        return None
    try:
        oh = float(v_home["odd"])
        oa = float(v_away["odd"])
        return oh, oa
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="例: 2025-08-22 (JST基準で未開始狙い)")
    ap.add_argument("--league", type=int, default=1, help="MLBは1")
    ap.add_argument("--season", type=int, default=2025)
    ap.add_argument("--timezone", default="Asia/Tokyo")
    ap.add_argument("--input", required=True, help="ユーザー入力テキスト")
    args = ap.parse_args()

    api_key = os.environ.get("APISPORTS_KEY")
    if not api_key:
        print("ERROR: 環境変数 APISPORTS_KEY が未設定です。")
        sys.exit(1)

    # 1) 当日fixturesを取得
    games = fetch_json(
        "/games",
        {
            "date": args.date,
            "league": args.league,
            "season": args.season,
            "timezone": args.timezone
        },
        api_key
    )
    fixtures = games.get("response", [])

    # 2) 入力のペアを読む
    pairs = parse_user_input(args.input)

    print("="*60)
    print(f"[ＭＬＢ] @ {args.date}")
    print("="*60)

    if not fixtures:
        print("※ 当日のfixturesが0件です。date/season/league/timezoneをご確認ください。")
        return

    for top, bottom in pairs:
        # 対応fixture探索
        fx = pick_fixture_for_pair((top, bottom), fixtures)

        # 見出し
        print()
        if fx:
            away = fx["teams"]["away"]["name"]
            home = fx["teams"]["home"]["name"]
            start_jst = jst_iso(fx["date"])
            print("="*60)
            print(f"{away} @ {home}")
            print(f"開始時刻(JST): {start_jst}")
            print("="*60)
        else:
            # fixtureが見つからない場合でも見出しだけ出す（ユーザーに気づきを与える）
            print("="*60)
            print(f"{re.sub(r'<.*?>','', bottom)} @ {re.sub(r'<.*?>','', top)}")
            print(f"開始時刻(JST): {args.date}")
            print("="*60)
            print("※ 該当カードを当日のfixturesから見つけられませんでした（未来試合のみ対象）。")
            continue

        # 3) 試合オッズ（Pinnacle）を取得 → MLを抜く
        odds = fetch_json(
            "/odds",
            {"game": fx["id"], "bookmaker": BOOKMAKER_PINNACLE},
            api_key
        )
        ml = extract_ml_from_pinnacle(odds)
        if not ml:
            print("※ Pinnacle(4)のHome/Away(=ML)が見つかりませんでした。")
            continue

        odd_home, odd_away = ml
        # 標準勝率（逆数の正規化ではなく“提示値の逆数”をそのまま％表示すると誤解を招くので、公正と区別表示）
        # 第1版：標準勝率は 1/odds を単独で％にした参考値として出す（ラベルに“参考”表記）
        std_home = 1.0 / odd_home
        std_away = 1.0 / odd_away

        # 公正（マージン除去）
        fair_home, fair_away = remove_margin_to_probs(odd_home, odd_away)

        # 公正オッズ
        fair_odd_home = 1.0 / fair_home if fair_home > 0 else None
        fair_odd_away = 1.0 / fair_away if fair_away > 0 else None

        # 表示（HOME → AWAY の順）
        # ユーザーの脳内モデルに合わせ、％を先に、倍率を後ろに
        print("サイド\t\t標準勝率(参考)\t公正勝率\t標準オッズ\t公正オッズ")
        print(f"[HOME]\t\t{to_pct(std_home)}\t{to_pct(fair_home)}\t{odd_home:.2f}\t\t{fair_odd_home:.2f}")
        print(f"[AWAY]\t\t{to_pct(std_away)}\t{to_pct(fair_away)}\t{odd_away:.2f}\t\t{fair_odd_away:.2f}")

        # 付記：次版で日本式ポイント補間を入れる旨を小さく案内
        # （出力は簡潔に保つ）
