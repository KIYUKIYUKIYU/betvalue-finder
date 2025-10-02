# app/af_client.py
# API-Football から Pinnacle(11) のハンディキャップラインを取得して
# {line, home_odds, away_odds} の配列で返すユーティリティ
import os
import re
import requests
from typing import List, Dict, Optional

API_BASE = "https://v3.football.api-sports.io"

# 例: "Home (-1.0)" / "Away (+1.0)" / "Home (-1)" などから符号付き数値だけ抜く
_NUM_RE = re.compile(r"[-+]?(\d+(?:\.\d+)?)")

def _extract_signed_number(s: str) -> Optional[float]:
    if s is None:
        return None
    # 括弧内優先で探す
    m = re.search(r"\(([-+]?\d+(?:\.\d+)?)\)", s)
    if m:
        try:
            return float(m.group(1))
        except:
            return None
    # それ以外も一応
    m2 = _NUM_RE.search(s)
    if m2:
        try:
            return float(m2.group(0))
        except:
            return None
    return None

def get_pinnacle_lines_from_api_football(fixture_id: int, timeout: float = 8.0) -> List[Dict]:
    """
    API-Football の /odds エンドポイントから Pinnacle(bookmaker=11) の
    アジアンハンディキャップ相当のラインを抽出。
    戻り値: [{"line": 0.5, "home_odds": 1.95, "away_odds": 1.95}, ...]
    """
    api_key = os.getenv("API_SPORTS_KEY")
    if not api_key:
        return []

    headers = {"x-apisports-key": api_key}
    params = {"fixture": int(fixture_id), "bookmaker": 11}
    url = f"{API_BASE}/odds"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

    # データ構造: data["response"] -> [ { "bookmakers":[{ "id":11, "bets":[{ "name": "...", "values":[{"value":"Home (-1.0)","odd":"2.10"}, ...]} ] } ] } ]
    response = data.get("response") or []
    lines_map = {}  # abs(line) -> {"home_odds": float, "away_odds": float}

    for item in response:
        bookmakers = item.get("bookmakers") or []
        for bm in bookmakers:
            if bm.get("id") != 11 and str(bm.get("id")) != "11":
                continue
            bets = bm.get("bets") or []
            for bet in bets:
                name = (bet.get("name") or "").lower()
                # ハンディキャップ系だけ対象（名称の揺れを許容）
                if not any(k in name for k in ["handicap", "asian handicap", "ah", "line"]):
                    continue
                values = bet.get("values") or []
                for v in values:
                    label = v.get("value") or ""
                    odd_str = (v.get("odd") or "").replace(",", ".")
                    try:
                        odd = float(odd_str)
                    except:
                        continue

                    # Home or Away？
                    is_home = "home" in label.lower()
                    is_away = "away" in label.lower()

                    # 符号付きラインを抽出
                    signed = _extract_signed_number(label)
                    if signed is None:
                        continue
                    absline = abs(float(signed))

                    rec = lines_map.setdefault(absline, {})
                    if is_home:
                        rec["home_odds"] = odd
                    elif is_away:
                        rec["away_odds"] = odd
                    else:
                        # "Team1 (-1.0)" 等のケースはラベルで判定が必要だが、
                        # 一意に決められない場合はスキップ
                        continue

    # home/away 両方揃ったもののみ返す
    results: List[Dict] = []
    for absline, rec in sorted(lines_map.items()):
        if "home_odds" in rec and "away_odds" in rec:
            results.append({
                "line": float(-absline),  # APIではHome(-X)が一般的 → homeのlineは負で表す（evaluate側はabsを参照）
                "home_odds": float(rec["home_odds"]),
                "away_odds": float(rec["away_odds"]),
            })
    return results
