# scripts/inspect_markets.py
# 目的:
#  手元の odds JSON をざっと検査して、
#   - どのブックメーカーが入っているか
#   - 各ブックの "bets"/"markets" の market名（例: Run Line / Runline / Spread ...）
#   - 各 market に values が入っているか（例サンプル）
#  を一覧化して出力する。
#
# 使い方:
#   python scripts\inspect_markets.py data\baseball_odds_YYYYMMDD.json --out scripts\output\market_inventory_YYYYMMDD.csv

from __future__ import annotations
import argparse, json, os, csv

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if isinstance(d, dict) and "response" in d:
        return d["response"]
    if isinstance(d, list):
        return d
    return []

def get(b: dict, *keys, default=None):
    cur = b
    for k in keys:
        if not isinstance(cur, dict): return default
        cur = cur.get(k, default)
    return cur

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path", help=r"data\baseball_odds_YYYYMMDD.json")
    ap.add_argument("--out", default=None, help=r"出力CSV (例: scripts\output\market_inventory_YYYYMMDD.csv)")
    args = ap.parse_args()

    events = load_json(args.json_path)
    if not events:
        print("[WARN] events が空です。JSONの中身（response配下）に試合が無い可能性があります。")
        return

    rows = []
    for ev in events:
        gid = get(ev, "game_id") or get(ev, "fixture", "id") or ev.get("id")
        home = get(ev, "teams", "home", "name") or ev.get("homeTeam") or "HOME"
        away = get(ev, "teams", "away", "name") or ev.get("awayTeam") or "AWAY"
        books = ev.get("bookmakers") or ev.get("odds") or []

        if not books:
            rows.append([gid, home, away, "", "", "", 0, "no bookmakers"])
            continue

        for bm in books:
            bname = (bm.get("name") or bm.get("bookmaker") or "").strip()
            bid = bm.get("id") or bm.get("bookmaker_id")
            markets = bm.get("bets") or bm.get("markets") or []
            if not markets:
                rows.append([gid, home, away, bname, bid, "", 0, "no markets"])
                continue

            for mk in markets:
                mname = (mk.get("name") or mk.get("label") or "").strip()
                values = mk.get("values") or mk.get("outcomes") or []
                vcount = len(values) if values else 0

                # サンプル1件だけ拾う（handicap/line, team & odd の有無チェック）
                sample = ""
                if values:
                    v0 = values[0]
                    cand = []
                    for k in ("handicap","value","line"):
                        if k in v0 and v0[k] is not None:
                            cand.append(f"{k}={v0[k]}")
                    if "odd_home" in v0 and "odd_away" in v0:
                        cand.append(f"odd_home={v0.get('odd_home')} odd_away={v0.get('odd_away')}")
                    if "home" in v0 and "away" in v0:
                        cand.append(f"home={v0.get('home')} away={v0.get('away')}")
                    if "team" in v0 and "odd" in v0:
                        cand.append(f"team={v0.get('team')} odd={v0.get('odd')}")
                    sample = " | ".join(cand)

                rows.append([gid, home, away, bname, bid, mname, vcount, sample])

    # 表示
    print("=== MARKET INVENTORY (bookmaker x market) ===")
    for r in rows[:80]:
        print(r)
    if len(rows) > 80:
        print(f"... ({len(rows)-80} more rows)")

    # CSV出力
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["game_id","home","away","bookmaker_name","bookmaker_id","market_name","values_count","sample"])
            w.writerows(rows)
        print(f"[OK] CSV saved: {args.out} (rows={len(rows)})")

if __name__ == "__main__":
    main()
