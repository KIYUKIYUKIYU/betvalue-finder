# app/find_fixture_with_pinnacle.py
import os, json, sys
from datetime import datetime, timedelta
import requests

API = "https://v3.football.api-sports.io"
HEAD = {"x-apisports-key": os.getenv("API_FOOTBALL_KEY", "")}
TZ = "Asia/Tokyo"
LEAGUES = [39, 140, 135, 78, 61]  # EPL, LaLiga, SerieA, Bundesliga, Ligue1

def jprint(obj): print(json.dumps(obj, ensure_ascii=False, indent=2))

def get(url, params):
    r = requests.get(url, headers=HEAD, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def list_fixtures(dt_str, league):
    return get(f"{API}/fixtures", {"date": dt_str, "league": league, "season": 2025, "timezone": TZ}).get("response", [])

def get_bm11_lines(fix_id: int):
    data = get(f"{API}/odds", {"fixture": fix_id, "bookmaker": 11})
    out = []
    for res in data.get("response", []):
        for bm in res.get("bookmakers", []):
            if str(bm.get("id")) != "11": continue
            for bet in bm.get("bets", []):
                name = (bet.get("name") or "").lower()
                if not any(k in name for k in ["handicap", "asian handicap", "ah", "line"]):
                    continue
                # value例: "Home (-1.0)" / "Away (+1.0)"
                rec = {}
                for v in bet.get("values", []):
                    val = (v.get("value") or "").lower()
                    odd = v.get("odd")
                    if "home" in val and "(" in val:
                        try:
                            rec.setdefault("home", {})[val] = float(str(odd).replace(",", "."))
                        except: pass
                    if "away" in val and "(" in val:
                        try:
                            rec.setdefault("away", {})[val] = float(str(odd).replace(",", "."))
                        except: pass
                if rec:
                    out.append(rec)
    return out

def main():
    if not HEAD["x-apisports-key"]:
        print("ERROR: API_FOOTBALL_KEY is not set", file=sys.stderr)
        sys.exit(1)

    today = datetime.now().date()
    dates = [(today + timedelta(days=i)).isoformat() for i in range(0, 4)]  # 今日〜+3日

    for dt in dates:
        for lg in LEAGUES:
            fx = list_fixtures(dt, lg)
            if not fx: 
                continue
            for f in fx:
                fid = f["fixture"]["id"]
                teams = f["teams"]["home"]["name"] + " vs " + f["teams"]["away"]["name"]
                lines = get_bm11_lines(fid)
                if not lines:
                    continue
                # ここまで来たら「BM11でハンデ有り」
                print("FOUND")
                print("date:", dt, "league:", lg, "fixture_id:", fid, "teams:", teams)
                # 簡易サマリ表示
                sample = lines[0]
                jprint({"fixture_id": fid, "sample_bm11": sample})
                return
    print("NO_FIXTURE_WITH_PINNACLE_HANDICAP_FOUND")

if __name__ == "__main__":
    main()
