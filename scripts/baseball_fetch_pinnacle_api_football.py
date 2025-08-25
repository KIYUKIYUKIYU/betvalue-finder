from __future__ import annotations
import argparse, json, os, requests
from datetime import datetime, timezone

# API-Sports v3 /odds をそのまま使い、sport=4 (Baseball/MLB想定) で試す雛形
BASE_URL = os.getenv("API_FOOTBALL_BASE", "https://v3.football.api-sports.io")
API_KEY = os.getenv("API_SPORTS_KEY") or os.getenv("API_BASEBALL_KEY") or os.getenv("API_FOOTBALL_KEY")
BOOKMAKER_ID_PINNACLE = int(os.getenv("PINNACLE_BOOKMAKER_ID", "11"))

def fetch_odds(date_iso: str, league: str | None, tz: str = "Asia/Tokyo") -> list[dict]:
    if not API_KEY:
        raise SystemExit("環境変数 API_SPORTS_KEY / API_BASEBALL_KEY / API_FOOTBALL_KEY のいずれかを設定してください。")

    url = f"{BASE_URL}/odds"
    params = {
        "date": date_iso,
        "bookmaker": BOOKMAKER_ID_PINNACLE,
        "timezone": tz,
        "sport": "4",  # ← MLB想定（動かなければ実レス/ドキュに合わせて修正）
    }
    if league:
        params["league"] = league

    r = requests.get(url, headers={"x-apisports-key": API_KEY}, params=params, timeout=30)
    # デバッグ用にステータスと残りレート表示（ヘッダにあれば）
    print("HTTP", r.status_code, "| remaining:", r.headers.get("x-ratelimit-requests-remaining", "?"))
    r.raise_for_status()

    data = r.json()
    # 典型: {"response":[...], "results":N}。なければ丸ごと返す
    return data.get("response", data)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", type=str, default=datetime.now(timezone.utc).date().isoformat())
    ap.add_argument("--league", type=str, help="MLBのリーグID（任意）")
    ap.add_argument("--timezone", type=str, default="Asia/Tokyo")
    ap.add_argument("--peek", action="store_true", help="最初の1件のキーを覗く（デバッグ）")
    args = ap.parse_args()

    events = fetch_odds(args.date, args.league, args.timezone)

    # ざっくり中身を確認できるよう最初の1件の主要キーを表示
    if args.peek and events:
        first = events[0]
        print("[peek] top-level keys:", list(first.keys()))
        # bookmaker 構造も少し覗く
        bks = first.get("bookmakers") or []
        if bks:
            print("[peek] bookmaker keys:", list(bks[0].keys()))
            bets = bks[0].get("bets") or []
            if bets:
                print("[peek] market names sample:", [b.get("name") for b in bets[:5]])

    os.makedirs("../data", exist_ok=True)
    out = f"../data/baseball_odds_{args.date.replace('-', '')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved: {out} (events: {len(events)})")

if __name__ == "__main__":
    main()
