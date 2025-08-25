from __future__ import annotations
import argparse, json, os, requests
from datetime import datetime, timezone

BASE_URL = os.getenv("API_FOOTBALL_BASE", "https://v3.football.api-sports.io")
API_KEY = os.getenv("API_FOOTBALL_KEY")  # 環境変数で渡す
BOOKMAKER_ID_PINNACLE = int(os.getenv("PINNACLE_BOOKMAKER_ID", "11"))  # 既定11

def fetch_odds(date_iso: str, league: str | None) -> list[dict]:
    if not API_KEY:
        raise SystemExit("環境変数 API_FOOTBALL_KEY が未設定です。set API_FOOTBALL_KEY=YOUR_KEY")

    url = f"{BASE_URL}/odds"
    params = {"date": date_iso, "bookmaker": BOOKMAKER_ID_PINNACLE}
    if league:
        params["league"] = league

    r = requests.get(url, headers={"x-apisports-key": API_KEY}, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    # API-Football の標準フォーマットは { "response": [...] }
    return data.get("response", data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=str, default=datetime.now(timezone.utc).date().isoformat())
    ap.add_argument("--league", type=str, help="必要ならリーグID（例：EPL=39）")
    args = ap.parse_args()

    events = fetch_odds(args.date, args.league)
    os.makedirs("../data", exist_ok=True)
    out = f"../data/soccer_odds_{args.date.replace('-', '')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved: {out} (events: {len(events)})")

if __name__ == "__main__":
    main()
