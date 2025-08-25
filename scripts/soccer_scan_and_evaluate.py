from __future__ import annotations
import argparse, csv, json, os, requests
from typing import Any, Dict, List, Tuple
from datetime import datetime

API_URL = os.getenv("BETFINDER_API_URL", "http://127.0.0.1:8001")

# 市場名の候補（リーグにより揺れる）
PREF_ML_MARKET_KEYS = {"Match Winner", "1X2 (2-way)", "Home/Away", "Winner (2-way)", "Moneyline (2-way)"}
PREF_AH_MARKET_KEYS = {"Asian Handicap", "Handicap"}

JP_LIST = ["0.1","0.2","0.3","0.4","0.5","1","1半"]  # 代表セット

def load_events(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def find_market(bookmaker: Dict[str, Any], names: set[str]) -> Dict[str, Any] | None:
    for bet in bookmaker.get("bets", []):
        if bet.get("name") in names:
            return bet
    return None

def extract_ml_and_spreads(ev: Dict[str, Any]) -> Tuple[Dict[str, float], List[Dict[str, float]], str, str, str]:
    """戻り値: (ml(home/away), spreads(raw), league_label, home_name, away_name)"""
    fixture = ev.get("fixture", {})
    league = ev.get("league", {})
    home = fixture.get("teams", {}).get("home", {}).get("name") or ev.get("teams", {}).get("home", {}).get("name")
    away = fixture.get("teams", {}).get("away", {}).get("name") or ev.get("teams", {}).get("away", {}).get("name")
    league_label = league.get("name", "League")

    bookmakers = ev.get("bookmakers") or []
    if not bookmakers:
        raise ValueError("no bookmakers in record")
    bk = bookmakers[0]  # Pinnacleのみの取得想定

    # --- ML（2-way） ---
    ml_market = find_market(bk, PREF_ML_MARKET_KEYS)
    if not ml_market:
        raise ValueError("no 2-way ML market")

    prices: Dict[str, float] = {}
    for o in ml_market.get("values", ml_market.get("outcomes", [])):
        name = (o.get("name") or o.get("value") or "").lower()
        try:
            odd = float(o.get("odd") or o.get("price"))
        except Exception:
            continue
        prices[name] = odd

    def pick(p: dict, home_name: str, away_name: str) -> Tuple[float, float]:
        if "home" in p and "away" in p:
            return float(p["home"]), float(p["away"])
        # チーム名ヒューリスティック
        for k, v in list(p.items()):
            kl = k.lower()
            if home_name and home_name.lower() in kl:
                p["home"] = v
            if away_name and away_name.lower() in kl:
                p["away"] = v
        if "home" in p and "away" in p:
            return float(p["home"]), float(p["away"])
        raise ValueError("cannot parse ML outcomes")

    home_ml, away_ml = pick(prices, home or "home", away or "away")

    # --- AH（アジアン） ---
    spreads_raw: List[Dict[str, float]] = []
    ah_market = find_market(bk, PREF_AH_MARKET_KEYS)
    if ah_market:
        for v in ah_market.get("values", []):
            hcp = v.get("handicap") or v.get("point") or v.get("value")
            if hcp is None:
                continue
            try:
                point = float(hcp)
            except Exception:
                continue
            # home/away を取得
            try:
                ho = float(v["home"])
                ao = float(v["away"])
            except Exception:
                ho = float(v.get("Home") or v.get("team") or 0)
                ao = float(v.get("Away") or v.get("opponent") or 0)
            if ho > 0 and ao > 0:
                spreads_raw.append({"point": point, "home": ho, "away": ao})

    ml = {"home": home_ml, "away": away_ml}
    return ml, spreads_raw, league_label, (home or "Home"), (away or "Away")

def post_evaluate(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{API_URL}/evaluate", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json", type=str, help="data/soccer_odds_YYYYMMDD.json")
    ap.add_argument("--date", type=str, help="YYYY-MM-DD（CSV名に使用）")
    args = ap.parse_args()

    events = load_events(args.input_json)
    os.makedirs("output", exist_ok=True)
    date_str = args.date or datetime.now().date().isoformat()
    out_csv = f"output/soccer_recommend_{date_str.replace('-', '')}.csv"

    rows: List[List[Any]] = [["league","home","away","fav_team","dog_team","jp","fair_odds","edge_pct","verdict"]]

    for ev in events:
        try:
            ml_raw, ah_raw, league_name, home, away = extract_ml_and_spreads(ev)
            fav_side = "home" if ml_raw["home"] <= ml_raw["away"] else "away"
            fav_team = home if fav_side == "home" else away
            dog_team = away if fav_side == "home" else home

            ml = {
                "team": float(ml_raw[fav_side]),
                "opponent": float(ml_raw["away" if fav_side == "home" else "home"]),
            }

            # favorite視点の [-X] に揃える
            spreads = []
            for r in ah_raw:
                p = float(r["point"])
                ho = float(r["home"]); ao = float(r["away"])
                if fav_side == "home":
                    if p < 0:
                        spreads.append({"point": p, "team": ho, "opponent": ao})
                else:
                    if p > 0:
                        spreads.append({"point": -p, "team": ao, "opponent": ho})

            for jp in JP_LIST:
                payload = {
                    "sport": "soccer",
                    "league": league_name,
                    "team": fav_team,
                    "opponent": dog_team,
                    "jp_handicap": jp,
                    "lines": {"ml": ml, "spreads": spreads},
                }
                try:
                    res = post_evaluate(payload)
                    rows.append([
                        league_name, home, away, fav_team, dog_team, jp,
                        res.get("fair_odds"), res.get("edge_pct"), res.get("verdict")
                    ])
                except Exception:
                    continue
        except Exception:
            continue

    # edge降順
    def edge_key(r: List[Any]) -> float:
        try:
            return float(r[7])
        except Exception:
            return -9999.0

    rows_sorted = [rows[0]] + sorted(rows[1:], key=edge_key, reverse=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows_sorted)

    print(f"✅ Saved: {out_csv} (rows: {len(rows_sorted)-1})")

if __name__ == "__main__":
    main()
