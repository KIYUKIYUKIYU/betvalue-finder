# -*- coding: utf-8 -*-
"""
MLB odds fetcher for API-SPORTS (Baseball v1)
- Primary: Pinnacle (bookmaker id = 4)
- If --allow-fallback: per-game fallback to priority bookmakers when Pinnacle is absent
- Saves a single JSON merged file under ../data/baseball_odds_YYYYMMDD.json

Usage (cmd.exe):
  set API_SPORTS_KEY=<YOUR KEY>
  python baseball_fetch_pinnacle_api_sports.py --timezone Asia/Tokyo --peek
  python baseball_fetch_pinnacle_api_sports.py --date 2025-08-22 --timezone Asia/Tokyo --allow-fallback

Notes:
- API base: https://v1.baseball.api-sports.io
- Endpoints used: /games, /odds
- Market naming: Asian Handicap (id=2) for spreads (Run Line equivalent)
"""

import argparse
import datetime as dt
import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = "https://v1.baseball.api-sports.io"
BOOKMAKER_PINNACLE = 4
# Fallback priority when --allow-fallback (only if Pinnacle absent for that game)
FALLBACK_PRIORITY = [2, 19, 22, 9, 1]  # Bet365, Betway, WilliamHill, 10Bet, 1xBet

SESSION = requests.Session()


def log(msg: str) -> None:
    print(msg, flush=True)


def req(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.environ.get("API_SPORTS_KEY", "").strip()
    if not api_key:
        log("ERROR: Environment variable API_SPORTS_KEY is not set.")
        sys.exit(1)
    headers = {"x-apisports-key": api_key}
    url = f"{API_BASE}{path}"
    resp = SESSION.get(url, headers=headers, params=params, timeout=30)
    remaining = resp.headers.get("x-ratelimit-requests-remaining")
    try:
        data = resp.json()
    except Exception:
        log(f"HTTP {resp.status_code} | failed to parse JSON")
        log(resp.text[:2000])
        sys.exit(1)
    if resp.status_code != 200:
        log(f"HTTP {resp.status_code} | {path} | remaining: {remaining}")
        log(json.dumps(data, ensure_ascii=False)[:2000])
        sys.exit(1)
    return {"http_status": resp.status_code, "remaining": remaining, "data": data}


def parse_date_arg(date_str: Optional[str], tz: str) -> str:
    if date_str:
        return date_str
    # default: today in timezone tz
    # API expects YYYY-MM-DD; we approximate by using local date (cmd runs in JST commonly)
    # The API also accepts timezone on /games to align day buckets.
    today = dt.datetime.now().date()
    return today.strftime("%Y-%m-%d")


def get_games_for_date(target_date: str, tz: str) -> List[Dict[str, Any]]:
    params = {
        "league": 1,         # MLB
        "season": _season_from_date(target_date),
        "date": target_date,
        "timezone": tz,
    }
    r = req("/games", params)
    data = r["data"]
    if data.get("errors"):
        log(f"WARNING /games errors: {data['errors']}")
    games = data.get("response", []) or []
    return games


def _season_from_date(date_str: str) -> int:
    # MLB season year equals the calendar year of the date
    return int(date_str[:4])


def fetch_odds_for_game(game_id: int, allow_fallback: bool) -> Optional[Dict[str, Any]]:
    """
    Returns the odds payload for a single game.
    Priority:
      1) Try bookmaker=4 (Pinnacle). If present, keep only that bookmaker in the record.
      2) If missing and allow_fallback: fetch all bookmakers and pick first present
         from FALLBACK_PRIORITY; keep only that bookmaker in the record.
      3) If none present: return None (skip this game).
    """
    # 1) Try Pinnacle only
    p1 = {"game": game_id, "bookmaker": BOOKMAKER_PINNACLE}
    r1 = req("/odds", p1)["data"]
    if r1.get("response"):
        rec = r1["response"][0]
        # Keep only Pinnacle bookmaker block
        rec["bookmakers"] = [bk for bk in rec.get("bookmakers", []) if bk.get("id") == BOOKMAKER_PINNACLE]
        rec["source_bookmaker"] = BOOKMAKER_PINNACLE
        return rec

    if not allow_fallback:
        return None

    # 2) Fallback: fetch all, then select a single bookmaker from priority list
    p2 = {"game": game_id}
    r2 = req("/odds", p2)["data"]
    if not r2.get("response"):
        return None
    rec = r2["response"][0]
    bks: List[Dict[str, Any]] = rec.get("bookmakers", []) or []

    # Prefer Pinnacle if happens to exist (rare but just in case)
    for bk in bks:
        if bk.get("id") == BOOKMAKER_PINNACLE:
            rec["bookmakers"] = [bk]
            rec["source_bookmaker"] = BOOKMAKER_PINNACLE
            return rec

    # Choose first available from fallback priority
    for cand in FALLBACK_PRIORITY:
        for bk in bks:
            if bk.get("id") == cand:
                rec["bookmakers"] = [bk]
                rec["source_bookmaker"] = cand
                return rec

    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch MLB odds (API-SPORTS v1, Pinnacle-first).")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in local)")
    ap.add_argument("--timezone", default="Asia/Tokyo", help="IANA tz for /games day bucket (default: Asia/Tokyo)")
    ap.add_argument("--peek", action="store_true", help="Print market names found per game.")
    ap.add_argument("--allow-fallback", action="store_true", help="Allow per-game bookmaker fallback when Pinnacle absent (default: OFF).")
    args = ap.parse_args()

    target_date = parse_date_arg(args.date, args.timezone)
    season = _season_from_date(target_date)

    # Step 1: list games
    games = get_games_for_date(target_date, args.timezone)
    game_ids = [int(g["id"]) for g in games]
    log(f"Games {target_date} (season {season}) JST={args.timezone}: {len(game_ids)} found")

    merged: List[Dict[str, Any]] = []
    total_requests = 0

    for gid in game_ids:
        rec = fetch_odds_for_game(gid, allow_fallback=args.allow_fallback)
        total_requests += 1
        if not rec:
            log(f"  - game {gid}: odds not available (Pinnacle first; fallback={'ON' if args.allow_fallback else 'OFF'})")
            continue

        # optional peek
        if args.peek:
            bks = rec.get("bookmakers", [])
            if bks:
                bk = bks[0]
                bk_name = bk.get("name")
                markets = [b.get("name") for b in bk.get("bets", []) if "name" in b]
                log(f"  - game {gid}: bookmaker={bk_name} | markets={', '.join(markets[:8])}{'...' if len(markets)>8 else ''}")

        merged.append(rec)

    # Compose a compact envelope (compatible with existing dump script expectations)
    envelope = {
        "get": "odds",
        "parameters": {"league": "1", "season": str(season), "date": target_date},
        "results": len(merged),
        "response": merged
    }

    os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)
    out_name = f"baseball_odds_{target_date.replace('-', '')}.json"
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", out_name)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(envelope, f, ensure_ascii=False)

    # Approximate remaining; show last request's header if available by one more call (cheap ping)
    ping = req("/leagues", {"search": "MLB"})
    remaining = ping.get("remaining")
    log(f"HTTP 200 | remaining: {remaining}")
    log(f"✅ Saved: ../data/{out_name} (events: {len(merged)})")


if __name__ == "__main__":
    main()
