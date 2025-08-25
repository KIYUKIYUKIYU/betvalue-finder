# scripts/fetch_fixtures.py
from __future__ import annotations
import os, sys, csv, json, time, math
import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests

API_BASE = os.environ.get("APISPORTS_BASE", "https://v1.baseball.api-sports.io")
API_KEY  = os.environ.get("APISPORTS_KEY")  # 必須

JST = ZoneInfo("Asia/Tokyo")

def jst_now():
    return datetime.now(JST)

def http_get(url: str, params: dict) -> dict:
    if not API_KEY:
        print("[ERROR] 環境変数 APISPORTS_KEY が設定されていません。")
        sys.exit(1)
    headers = {"x-apisports-key": API_KEY}
    for i in range(3):
        r = requests.get(url, headers=headers, params=params, timeout=20)
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                pass
        time.sleep(1.0 + i)
    print(f"[ERROR] API request failed: {url} {r.status_code} {r.text[:200]}")
    sys.exit(1)

def fetch_games_by_date(date_str: str, league: int|None, season: int|None) -> list[dict]:
    url = f"{API_BASE}/games"
    params = {"date": date_str, "timezone": "Asia/Tokyo"}
    if league: params["league"] = league
    if season: params["season"] = season
    js = http_get(url, params)
    if isinstance(js, dict) and "response" in js:
        return js["response"]
    if isinstance(js, list):
        return js
    return []

def to_dt_jst(iso: str|None) -> datetime|None:
    if not iso: return None
    try:
        # 例: "2025-08-22T02:10:00+09:00"
        return datetime.fromisoformat(iso).astimezone(JST)
    except Exception:
        return None

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="基準日 (YYYY-MM-DD, JST)")
    ap.add_argument("--days", type=int, default=2, help="取得する日数（基準日からN日、既定=2: 当日+翌日）")
    ap.add_argument("--league", type=int, default=1, help="リーグID（MLB想定: 1。必要に応じて変更）")
    ap.add_argument("--season", type=int, default=None, help="シーズン（未指定ならAPI側のデフォルト）")
    ap.add_argument("--outdir", default="data", help="保存先ディレクトリ（既定=data）")
    args = ap.parse_args()

    base_date = datetime.fromisoformat(args.date).replace(tzinfo=JST)
    dates = [(base_date + timedelta(days=i)).date().isoformat() for i in range(args.days)]

    all_games = []
    for d in dates:
        games = fetch_games_by_date(d, args.league, args.season)
        all_games.extend(games)

    # JSTで「未来（開始時刻 >= 今）」の試合だけ残す
    now = jst_now()
    future_games = []
    for g in all_games:
        fix = g.get("game") or g.get("fixture") or {}
        game_id = fix.get("id") or g.get("id")
        date_iso = fix.get("date") or g.get("date")
        dt = to_dt_jst(date_iso)
        status = (fix.get("status") or {}).get("long") or (g.get("status") or {}).get("long") or ""
        teams = g.get("teams") or {}
        home = (teams.get("home") or {}).get("name") or ""
        away = (teams.get("away") or {}).get("name") or ""

        if dt and dt >= now:
            future_games.append({
                "fixture_id": game_id,
                "commence_time_jst": dt.strftime("%Y-%m-%d %H:%M"),
                "commence_iso": date_iso,
                "status": status,
                "home_name_en": home,
                "away_name_en": away,
                "raw": g
            })

    ensure_dir(args.outdir)
    json_path = os.path.join(args.outdir, f"fixtures_{args.date.replace('-','')}.json")
    csv_path  = os.path.join(args.outdir, f"fixtures_{args.date.replace('-','')}.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"response": future_games}, f, ensure_ascii=False, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fixture_id","commence_time_jst","status","home_name_en","away_name_en"])
        for r in future_games:
            w.writerow([r["fixture_id"], r["commence_time_jst"], r["status"], r["home_name_en"], r["away_name_en"]])

    print(f"✅ saved: {json_path} (games: {len(future_games)})")
    print(f"✅ saved: {csv_path}")

if __name__ == "__main__":
    main()
