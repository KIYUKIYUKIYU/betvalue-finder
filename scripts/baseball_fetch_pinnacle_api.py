# -*- coding: utf-8 -*-
"""
MLB odds fetcher via API-SPORTS Baseball v1
- Policy:
  - Pinnacle(id=4) only by default
  - If --allow-fallback is set, use Bet365(id=2) ONLY when Pinnacle is missing for a game
- Markets are NOT filtered here; we store whatever the bookmaker returns
- Output JSON (list shape) compatible with downstream dump scripts

Usage (cmd.exe):
  set API_SPORTS_KEY=<YOUR_KEY>
  python baseball_fetch_pinnacle_api.py --date YYYY-MM-DD --timezone Asia/Tokyo [--allow-fallback] [--peek]
"""

import argparse
import datetime as dt
import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests

API_BASE = "https://v1.baseball.api-sports.io"
LEAGUE_ID = 1  # MLB

def env_api_key() -> str:
    key = os.environ.get("API_SPORTS_KEY", "").strip()
    if not key:
        print("ERROR: environment variable API_SPORTS_KEY is not set.", file=sys.stderr)
        sys.exit(1)
    return key

def http_get(path: str, params: Dict[str, Any], key: str) -> requests.Response:
    url = f"{API_BASE.rstrip('/')}/{path.lstrip('/')}"
    headers = {"x-apisports-key": key}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    return resp

def fetch_games(date_str: str, tz: str, season: int, key: str) -> List[Dict[str, Any]]:
    params = {
        "league": LEAGUE_ID,
        "season": season,
        "date": date_str,
        "timezone": tz,
    }
    r = http_get("games", params, key)
    try:
        remaining = r.headers.get("x-ratelimit-requests-remaining") or r.headers.get("x-ratelimit-remaining")
        print(f"HTTP {r.status_code} | remaining: {remaining if remaining is not None else '?'}")
    except Exception:
        print(f"HTTP {r.status_code}")
    r.raise_for_status()
    data = r.json()
    return data.get("response", [])

def fetch_odds_for_game(game_id: int, key: str) -> Optional[Dict[str, Any]]:
    # We do NOT filter bookmaker at the server side; we need all to decide fallback locally
    params = {"game": game_id}
    r = http_get("odds", params, key)
    r.raise_for_status()
    j = r.json()
    resp = j.get("response", [])
    if not resp:
        return None
    # API returns a single record for the game
    return resp[0]

def select_bookmaker(entry: Dict[str, Any], primary_id: int, fallback_id: Optional[int], allow_fallback: bool) -> Optional[Dict[str, Any]]:
    bks = entry.get("bookmakers", []) or []
    picked = None
    for bk in bks:
        if int(bk.get("id", -1)) == int(primary_id):
            picked = bk
            break
    if picked:
        return picked
    if allow_fallback and fallback_id is not None:
        for bk in bks:
            if int(bk.get("id", -1)) == int(fallback_id):
                return bk
    return None

def build_output_record(source: Dict[str, Any], picked_bk: Dict[str, Any]) -> Dict[str, Any]:
    # Keep shapes similar to API-Sports odds records; only include the chosen bookmaker
    return {
        "league": source.get("league", {}),
        "country": source.get("country", {}),
        "game": source.get("game", {}),
        "bookmakers": [
            {
                "id": picked_bk.get("id"),
                "name": picked_bk.get("name"),
                "bets": picked_bk.get("bets", []) or []
            }
        ]
    }

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Fetch MLB odds (Pinnacle by default, optional Bet365 fallback).")
    ap.add_argument("--date", required=False, help="YYYY-MM-DD (Tokyo date recommended)")
    ap.add_argument("--timezone", default="Asia/Tokyo")
    ap.add_argument("--bookmaker-id", type=int, default=4, help="Primary bookmaker id (default: 4 = Pinnacle)")
    ap.add_argument("--fallback-bookmaker-id", type=int, default=2, help="Fallback bookmaker id when --allow-fallback (default: 2 = Bet365)")
    ap.add_argument("--allow-fallback", action="store_true", help="Allow fallback to Bet365 when Pinnacle is missing for a game")
    ap.add_argument("--peek", action="store_true", help="Print markets list seen in the saved file")
    return ap.parse_args()

def main():
    args = parse_args()
    key = env_api_key()

    # Resolve date (default: today's Tokyo date if not provided)
    if args.date:
        date_str = args.date
    else:
        # naive "today" in Asia/Tokyo by offset; acceptable for our use since caller usually passes --date
        tokyo_now = dt.datetime.utcnow() + dt.timedelta(hours=9)
        date_str = tokyo_now.strftime("%Y-%m-%d")

    # Season is just the year part
    try:
        season = int(date_str[:4])
    except Exception:
        print("ERROR: --date must be in format YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    # 1) list games of the day (Tokyo)
    games = fetch_games(date_str, args.timezone, season, key)
    game_ids = [g.get("id") for g in games if isinstance(g.get("id"), int)]
    if not game_ids:
        out_path = os.path.join("..", "data", f"baseball_odds_{date_str.replace('-', '')}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)
        print(f"✅ Saved: {out_path} (events: 0)")
        return

    # 2) fetch odds for each game, select bookmaker
    saved_records: List[Dict[str, Any]] = []
    for gid in game_ids:
        try:
            odds_entry = fetch_odds_for_game(gid, key)
        except Exception as e:
            print(f"warn: game {gid} odds fetch failed: {e}")
            continue
        if not odds_entry:
            continue
        picked = select_bookmaker(
            odds_entry,
            primary_id=args.bookmaker_id,
            fallback_id=args.fallback_bookmaker_id,
            allow_fallback=args.allow_fallback
        )
        if picked is None:
            # No Pinnacle; and no fallback or fallback missing => skip
            continue
        saved_records.append(build_output_record(odds_entry, picked))

    # 3) save
    os.makedirs(os.path.join("..", "data"), exist_ok=True)
    out_path = os.path.join("..", "data", f"baseball_odds_{date_str.replace('-', '')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(saved_records, f, ensure_ascii=False)
    print(f"✅ Saved: {out_path} (events: {len(saved_records)})")

    # 4) optional peek: list unique market names
    if args.peek:
        markets = set()
        bms = set()
        for rec in saved_records:
            for bk in rec.get("bookmakers", []) or []:
                bms.add(f"{bk.get('id')}:{bk.get('name')}")
                for bet in bk.get("bets", []) or []:
                    name = (bet.get("name") or "").strip()
                    if name:
                        markets.add(name)
        if saved_records:
            print("bookmakers:", ", ".join(sorted(bms)))
            print("markets:", ", ".join(sorted(markets)))
        else:
            print("bookmakers: (none)")
            print("markets: (none)")

if __name__ == "__main__":
    main()
