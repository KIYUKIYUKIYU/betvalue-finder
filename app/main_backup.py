# app/main.py
# FastAPI エントリポイント - Pinnacle API連携版
# /map, /evaluate, /analyze_paste などのAPIを提供

from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple, Any
import os
import sys
import json
import requests
import datetime as dt
from collections import defaultdict
import math

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.converter import jp_to_pinnacle, pinnacle_to_jp, try_parse_jp
from converter.paste_parser import parse_paste_text
from converter.baseball_rules import BaseballEV, remove_margin_fair_probs, linear_interpolate

app = FastAPI(title="BetValue Finder API", version="0.3.0")

# CORS設定（開発用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 定数 ------------------------------------------------------------------

API_BASE = "https://v1.baseball.api-sports.io"
LEAGUE_ID = 1  # MLB
PINNACLE_ID = 4
BET365_ID = 2

# ハンデマーケット名のパターン
TARGET_MARKET_NAMES = {
    "asian handicap",
    "handicap",
    "spread",
    "spreads",
    "run line",
    "runline",
    "alternative run line",
    "alt run line",
    "run lines",
}

# verdict閾値
DEF_TH_CLEAR_PLUS = 5.0
DEF_TH_PLUS = 0.0
DEF_TH_FAIR = -3.0

# --- エラーコード定義 ------------------------------------------------------------------

ERROR_CODES = {
    "NO_GAMES": "試合データが見つかりません",
    "NO_FUTURE_GAMES": "今後の試合が見つかりません（すべて終了済み）",
    "NO_MATCHING_TEAM": "指定されたチームの試合が見つかりません",
    "NO_ODDS": "オッズデータが取得できません",
    "INVALID_LINE": "無効なハンデ指定です",
    "API_ERROR": "APIエラーが発生しました",
    "PAST_GAME": "すでに開始または終了した試合です",
}

# --- モデル ------------------------------------------------------------------

class MapRequest(BaseModel):
    jp: Optional[str] = None
    pinn: Optional[float] = None

class EvaluateRequest(BaseModel):
    jp: str
    prob: float  # 公正勝率（0〜1）
    payout: float = 1.90  # 日本式固定

class AnalyzePasteRequest(BaseModel):
    text: str  # 貼り付けテキスト
    sport: str = "mlb"  # 競技（mlb/soccer/nba）
    rakeback: float = 0.0  # レーキバック率（0〜0.03）
    jp_odds: float = 1.9  # 日本式オッズ
    date: Optional[str] = None  # YYYY-MM-DD形式

class GameEvaluation(BaseModel):
    # 基本情報
    team_a: str
    team_b: str
    team_a_jp: str
    team_b_jp: str
    fav_team: Optional[str]
    fav_team_jp: Optional[str]
    jp_line: Optional[str]
    pinnacle_line: Optional[float]
    # 判定結果
    fair_prob: Optional[float]
    fair_odds: Optional[float]
    ev_pct: Optional[float]
    ev_pct_rake: Optional[float]
    verdict: Optional[str]
    # 試合情報（拡張）
    game_id: Optional[int]
    game_datetime: Optional[str]
    home_team: Optional[str]
    away_team: Optional[str]
    time_until_game: Optional[str]  # "2時間30分後" など
    # エラー
    error: Optional[str]
    error_code: Optional[str]

# --- 静的ファイル配信 --------------------------------------------------------

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- ユーティリティ関数 ------------------------------------------------------

def get_api_key() -> str:
    """API-SPORTSのAPIキーを取得"""
    key = os.environ.get("API_SPORTS_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=500, detail="API_SPORTS_KEY not configured")
    return key

def http_get(path: str, params: Dict[str, Any], key: str) -> requests.Response:
    """API-SPORTSへのHTTPリクエスト"""
    url = f"{API_BASE.rstrip('/')}/{path.lstrip('/')}"
    headers = {"x-apisports-key": key}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    return resp

def fetch_games(date_str: str, tz: str, season: int, key: str) -> List[Dict[str, Any]]:
    """指定日のMLB試合一覧を取得"""
    params = {
        "league": LEAGUE_ID,
        "season": season,
        "date": date_str,
        "timezone": tz,
    }
    r = http_get("games", params, key)
    r.raise_for_status()
    data = r.json()
    return data.get("response", [])

def fetch_odds_for_game(game_id: int, key: str) -> Optional[Dict[str, Any]]:
    """指定試合のオッズを取得"""
    params = {"game": game_id}
    r = http_get("odds", params, key)
    r.raise_for_status()
    j = r.json()
    resp = j.get("response", [])
    if not resp:
        return None
    return resp[0]

def norm_team_name(x: Any) -> str:
    """チーム名を正規化"""
    if isinstance(x, dict):
        x = x.get("name") or x.get("abbr") or x.get("team") or ""
    return str(x).strip().lower()

def parse_handicap_values(values: List[dict], home_name: str, away_name: str) -> Dict[float, Tuple[float, float]]:
    """
    values から {handicap: (odd_home, odd_away)} を組み立てる
    """
    by_h: Dict[float, Tuple[float, float]] = {}
    tmp: Dict[float, Dict[str, float]] = defaultdict(dict)
    
    home_norm = norm_team_name(home_name)
    away_norm = norm_team_name(away_name)
    
    for v in values or []:
        # ハンデ値の取得
        h_value = None
        if "handicap" in v and v["handicap"] is not None:
            try:
                h_value = abs(float(v["handicap"]))
            except:
                continue
        elif "value" in v and v["value"] is not None:
            # "Home -1.5" 形式のパース
            import re
            m = re.search(r'([+-]?\d+(?:\.\d+)?)', str(v["value"]))
            if m:
                try:
                    h_value = abs(float(m.group(1)))
                except:
                    continue
        
        if h_value is None:
            continue
        
        # オッズの取得
        if "odd" in v:
            # チーム判定
            team = v.get("team", "")
            if isinstance(team, dict):
                team = team.get("name", "")
            team_norm = norm_team_name(team)
            
            try:
                odd_val = float(v["odd"])
                if team_norm == home_norm or team_norm == "home":
                    tmp[h_value]["home"] = odd_val
                elif team_norm == away_norm or team_norm == "away":
                    tmp[h_value]["away"] = odd_val
            except:
                pass
    
    # ペアが揃ったものだけ採用
    for h, sides in tmp.items():
        if "home" in sides and "away" in sides:
            by_h[h] = (sides["home"], sides["away"])
    
    return by_h

def find_handicap_market(bets: List[dict]) -> Optional[dict]:
    """ハンデ系マーケットを探す"""
    for bet in bets or []:
        name = (bet.get("name") or "").lower()
        if any(market in name for market in TARGET_MARKET_NAMES):
            return bet
    return None

def parse_game_datetime(date_str: str) -> dt.datetime:
    """ISO形式の日時文字列をdatetimeオブジェクトに変換"""
    # "2025-08-22T02:10:00+09:00" 形式をパース
    try:
        # Python 3.7+ では fromisoformat が使える
        return dt.datetime.fromisoformat(date_str)
    except:
        # フォールバック
        import re
        # タイムゾーン部分を除去して簡易パース
        clean_date = re.sub(r'[+-]\d{2}:\d{2}', '', date_str)
    odds_data: Dict[str, Any],
    target_line: float,
    home_team: str,
    away_team: str
) -> Optional[Tuple[float, float]]:
    """
    指定ラインの公正勝率を取得（必要に応じて補間）
    Returns: (home_prob, away_prob) or None
    """
    bookmakers = odds_data.get("bookmakers", [])
    
    # Pinnacle優先で探す
    pinnacle_bm = None
    for bm in bookmakers:
        if bm.get("id") == PINNACLE_ID:
            pinnacle_bm = bm
            break
    
    if not pinnacle_bm:
        # Bet365をフォールバック
        for bm in bookmakers:
            if bm.get("id") == BET365_ID:
                pinnacle_bm = bm
                break
    
    if not pinnacle_bm:
        return None
    
    # ハンデマーケットを探す
    market = find_handicap_market(pinnacle_bm.get("bets", []))
    if not market:
        return None
    
    # values からライン別オッズを取得
    values = market.get("values", [])
    by_line = parse_handicap_values(values, home_team, away_team)
    
    if not by_line:
        return None
    
    # 完全一致するラインがあるか確認
    if target_line in by_line:
        odd_home, odd_away = by_line[target_line]
        return remove_margin_fair_probs(odd_home, odd_away)
    
    # 補間が必要な場合
    sorted_lines = sorted(by_line.keys())
    
    # 範囲外の場合
    if target_line < sorted_lines[0] or target_line > sorted_lines[-1]:
        return None
    
    # 補間用の2点を探す
    lower_line = None
    upper_line = None
    
    for line in sorted_lines:
        if line <= target_line:
            lower_line = line
        if line >= target_line and upper_line is None:
            upper_line = line
    
    if lower_line is None or upper_line is None:
        return None
    
    # 同じ値の場合
    if lower_line == upper_line:
        odd_home, odd_away = by_line[lower_line]
        return remove_margin_fair_probs(odd_home, odd_away)
    
    # 線形補間
    odd_home_lower, odd_away_lower = by_line[lower_line]
    odd_home_upper, odd_away_upper = by_line[upper_line]
    
    prob_home_lower, _ = remove_margin_fair_probs(odd_home_lower, odd_away_lower)
    prob_home_upper, _ = remove_margin_fair_probs(odd_home_upper, odd_away_upper)
    
    # homeの勝率を補間
    prob_home = linear_interpolate(
        lower_line, prob_home_lower,
        upper_line, prob_home_upper,
        target_line
    )
    
    return prob_home, 1.0 - prob_home

def decide_verdict(ev_rake_pct: float) -> str:
    """EV%からverdictを判定"""
    if ev_rake_pct >= DEF_TH_CLEAR_PLUS:
        return "clear_plus"
    if ev_rake_pct >= DEF_TH_PLUS:
        return "plus"
    if ev_rake_pct >= DEF_TH_FAIR:
        return "fair"
    return "minus"

# --- エンドポイント ----------------------------------------------------------

@app.get("/")
async def root():
    """ルート：index.htmlを返す"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"msg": "BetValue Finder API running."}

@app.post("/map")
async def map_endpoint(req: MapRequest):
    """日本式⇔ピナクル値の相互変換"""
    if req.jp:
        ok, pinn = try_parse_jp(req.jp)
        if not ok:
            return {"error": f"未対応の日本式表記: {req.jp}"}
        return {"jp": req.jp, "pinnacle": pinn}
    if req.pinn is not None:
        try:
            jp = pinnacle_to_jp(req.pinn)
            return {"pinnacle": req.pinn, "jp": jp}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "jp または pinn のどちらかを指定してください"}

@app.post("/evaluate")
async def evaluate_endpoint(req: EvaluateRequest):
    """単一の日本式ラインに対する期待値を計算"""
    ok, pinn = try_parse_jp(req.jp)
    if not ok:
        return {"error": f"未対応の日本式表記: {req.jp}"}

    p = req.prob
    ev = p * req.payout - 1.0
    edge_pct = ev * 100.0

    verdict = decide_verdict(edge_pct)

    return {
        "jp": req.jp,
        "pinnacle": pinn,
        "fair_prob": p,
        "fair_odds": round(1.0 / p, 3) if p > 0 else None,
        "jp_payout": req.payout,
        "edge_pct": round(edge_pct, 2),
        "verdict": verdict,
    }

@app.post("/analyze_paste", response_model=List[GameEvaluation])
async def analyze_paste_endpoint(req: AnalyzePasteRequest):
    """
    貼り付けテキストを解析してEV計算・判定を返す（拡張版）
    - 最も近い未来の試合を自動選択
    - 試合情報を含む詳細レスポンス
    - エラーコード対応
    """
    try:
        # APIキー確認
        api_key = get_api_key()
        
        # テキストをパース
        games = parse_paste_text(req.text, req.sport)
        
        if not games:
            raise HTTPException(
                status_code=400, 
                detail=ERROR_CODES["NO_GAMES"],
                headers={"X-Error-Code": "NO_GAMES"}
            )
        
        # 現在時刻（日本時間）
        current_jst = dt.datetime.utcnow() + dt.timedelta(hours=9)
        
        # 複数日のデータを取得（今日と明日）
        all_mlb_games = []
        dates_to_check = []
        
        # 今日
        today_str = current_jst.strftime("%Y-%m-%d")
        dates_to_check.append(today_str)
        
        # 明日
        tomorrow = current_jst + dt.timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")
        dates_to_check.append(tomorrow_str)
        
        # 各日付のデータを取得
        for date_str in dates_to_check:
            season = int(date_str[:4])
            print(f"Fetching games for {date_str}...")
            try:
                daily_games = fetch_games(date_str, "Asia/Tokyo", season, api_key)
                all_mlb_games.extend(daily_games)
            except Exception as e:
                print(f"Failed to fetch {date_str}: {e}")
                continue
        
        if not all_mlb_games:
            raise HTTPException(
                status_code=404,
                detail=ERROR_CODES["NO_GAMES"],
                headers={"X-Error-Code": "NO_GAMES"}
            )
        
        # EV計算オブジェクト
        ev_calc = BaseballEV(
            jp_fullwin_odds=req.jp_odds,
            rakeback_pct=req.rakeback
        )
        
        results = []
        
        for game in games:
            # 最も近い未来の試合を探す
            nearest_game = find_nearest_future_game(
                all_mlb_games,
                game["team_a"],
                game["team_b"],
                current_jst
            )
            
            if not nearest_game:
                # 試合が見つからない場合のエラー
                eval_result = GameEvaluation(
                    team_a=game["team_a"],
                    team_b=game["team_b"],
                    team_a_jp=game["team_a_jp"],
                    team_b_jp=game["team_b_jp"],
                    fav_team=None,
                    fav_team_jp=None,
                    jp_line=None,
                    pinnacle_line=None,
                    fair_prob=None,
                    fair_odds=None,
                    ev_pct=None,
                    ev_pct_rake=None,
                    verdict=None,
                    game_id=None,
                    game_datetime=None,
                    home_team=None,
                    away_team=None,
                    time_until_game=None,
                    error=ERROR_CODES["NO_FUTURE_GAMES"],
                    error_code="NO_FUTURE_GAMES"
                )
                results.append(eval_result)
                continue
            
            # 試合情報を取得
            game_data = nearest_game["game"]
            game_id = game_data.get("id")
            game_datetime = nearest_game["datetime"]
            home_team = nearest_game["home"]
            away_team = nearest_game["away"]
            time_until = format_time_until(game_datetime, current_jst)
            
            # フェイバリット側の判定
            if game["fav_side"] and game["fav_line_pinnacle"] is not None:
                fav_result = await process_side_with_game_info(
                    game, game_id, home_team, away_team, 
                    game_datetime, time_until, "fav", 
                    ev_calc, api_key
                )
                results.append(fav_result)
                
                # アンダードッグ側も判定
                underdog_result = await process_side_with_game_info(
                    game, game_id, home_team, away_team,
                    game_datetime, time_until, "underdog",
                    ev_calc, api_key
                )
                results.append(underdog_result)
            else:
                # ラインが指定されていない場合
                eval_result = GameEvaluation(
                    team_a=game["team_a"],
                    team_b=game["team_b"],
                    team_a_jp=game["team_a_jp"],
                    team_b_jp=game["team_b_jp"],
                    fav_team=None,
                    fav_team_jp=None,
                    jp_line=None,
                    pinnacle_line=None,
                    fair_prob=None,
                    fair_odds=None,
                    ev_pct=None,
                    ev_pct_rake=None,
                    verdict=None,
                    game_id=game_id,
                    game_datetime=game_datetime.isoformat(),
                    home_team=home_team,
                    away_team=away_team,
                    time_until_game=time_until,
                    error=ERROR_CODES["INVALID_LINE"],
                    error_code="INVALID_LINE"
                )
                results.append(eval_result)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"{ERROR_CODES['API_ERROR']}: {str(e)}",
            headers={"X-Error-Code": "API_ERROR"}
        )

async def process_side_with_game_info(
    game: Dict,
    game_id: int,
    home_team: str,
    away_team: str,
    game_datetime: dt.datetime,
    time_until: str,
    side: str,  # "fav" or "underdog"
    ev_calc: BaseballEV,
    api_key: str
) -> GameEvaluation:
    """
    片側の判定を処理（拡張版：試合情報付き）
    """
    # 基本情報の設定
    if side == "fav":
        if game["fav_side"] == "a":
            target_team = game["team_a"]
            target_team_jp = game["team_a_jp"]
            jp_line = game["line_a"]
            pinnacle_line = -abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
        else:
            target_team = game["team_b"]
            target_team_jp = game["team_b_jp"]
            jp_line = game["line_b"]
            pinnacle_line = -abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
    else:  # underdog
        if game["fav_side"] == "a":
            target_team = game["team_b"]
            target_team_jp = game["team_b_jp"]
            jp_line = f"+{game['line_a'].replace('-', '').replace('+', '')}" if game["line_a"] else None
            pinnacle_line = abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
        else:
            target_team = game["team_a"]
            target_team_jp = game["team_a_jp"]
            jp_line = f"+{game['line_b'].replace('-', '').replace('+', '')}" if game["line_b"] else None
            pinnacle_line = abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
    
    eval_result = GameEvaluation(
        team_a=game["team_a"],
        team_b=game["team_b"],
        team_a_jp=game["team_a_jp"],
        team_b_jp=game["team_b_jp"],
        fav_team=target_team,
        fav_team_jp=target_team_jp,
        jp_line=jp_line,
        pinnacle_line=pinnacle_line,
        # 試合情報
        game_id=game_id,
        game_datetime=game_datetime.isoformat(),
        home_team=home_team,
        away_team=away_team,
        time_until_game=time_until,
        # 初期値
        fair_prob=None,
        fair_odds=None,
        ev_pct=None,
        ev_pct_rake=None,
        verdict=None,
        error=None,
        error_code=None
    )
    
    if pinnacle_line is None:
        eval_result.error = ERROR_CODES["INVALID_LINE"]
        eval_result.error_code = "INVALID_LINE"
        return eval_result
    
    try:
        # オッズデータを取得
        odds_data = fetch_odds_for_game(game_id, api_key)
        if not odds_data:
            eval_result.error = ERROR_CODES["NO_ODDS"]
            eval_result.error_code = "NO_ODDS"
            return eval_result
        
        # ターゲットチームがホームかアウェイか判定
        target_is_home = target_team == home_team
        
        # 該当ラインの公正勝率を取得
        if target_is_home:
            home_line = pinnacle_line
        else:
            home_line = -pinnacle_line
        
        target_line_abs = abs(home_line)
        
        fair_probs = extract_fair_probs_for_line(
            odds_data,
            target_line_abs,
            home_team,
            away_team
        )
        
        if not fair_probs:
            eval_result.error = f"{ERROR_CODES['NO_ODDS']}: ライン {pinnacle_line}"
            eval_result.error_code = "NO_ODDS"
            return eval_result
        
        prob_home, prob_away = fair_probs
        
        # ターゲットチームの勝率
        if target_is_home:
            fair_prob = prob_home if home_line < 0 else prob_home
        else:
            fair_prob = prob_away if home_line > 0 else prob_away
        
        # EV計算
        ev_pct_plain = ev_calc.ev_pct_plain(fair_prob)
        ev_pct_rake = ev_calc.ev_pct_with_rakeback(fair_prob)
        
        # verdict判定
        verdict = decide_verdict(ev_pct_rake)
        
        eval_result.fair_prob = round(fair_prob, 3)
        eval_result.fair_odds = round(1.0 / fair_prob, 3) if fair_prob > 0 else None
        eval_result.ev_pct = round(ev_pct_plain, 2)
        eval_result.ev_pct_rake = round(ev_pct_rake, 2)
        eval_result.verdict = verdict
        
    except Exception as e:
        eval_result.error = f"{ERROR_CODES['API_ERROR']}: {str(e)}"
        eval_result.error_code = "API_ERROR"
    
    return eval_result

# 既存のprocess_side関数は削除または後方互換のために残す

# --- デバッグ用エンドポイント ------------------------------------------------

@app.get("/debug/test_api")
async def test_api():
    """API接続テスト"""
    try:
        api_key = get_api_key()
        tokyo_now = dt.datetime.utcnow() + dt.timedelta(hours=9)
        date_str = tokyo_now.strftime("%Y-%m-%d")
        season = int(date_str[:4])
        
        games = fetch_games(date_str, "Asia/Tokyo", season, api_key)
        
        return {
            "status": "success",
            "date": date_str,
            "games_count": len(games),
            "games": [
                {
                    "id": g.get("id"),
                    "home": g.get("teams", {}).get("home", {}).get("name"),
                    "away": g.get("teams", {}).get("away", {}).get("name")
                }
                for g in games[:5]  # 最初の5試合のみ
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}, '', date_str)
        return dt.datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S")

def find_nearest_future_game(
    all_games: List[Dict],
    team_a: str,
    team_b: str,
    current_time: dt.datetime
) -> Optional[Dict]:
    """
    指定チームの最も近い未来の試合を探す
    """
    matching_games = []
    
    for game in all_games:
        # チーム名確認
        teams = game.get("teams", {})
        home = teams.get("home", {}).get("name", "")
        away = teams.get("away", {}).get("name", "")
        
        # どちらかのチーム組み合わせに一致
        if {home, away} == {team_a, team_b}:
            # 試合時刻確認
            game_datetime_str = game.get("date")
            if not game_datetime_str:
                continue
                
            game_datetime = parse_game_datetime(game_datetime_str)
            
            # 未来の試合かチェック（status も確認）
            status = game.get("status", {}).get("short", "")
            if status in ["FT", "POST", "CANC"]:  # 終了・中止
                continue
                
            # 現在時刻より未来なら候補に追加
            if game_datetime > current_time:
                matching_games.append({
                    "game": game,
                    "datetime": game_datetime,
                    "home": home,
                    "away": away
                })
    
    # 最も近い試合を選択
    if matching_games:
        matching_games.sort(key=lambda x: x["datetime"])
        return matching_games[0]
    
    return None

def format_time_until(target: dt.datetime, current: dt.datetime) -> str:
    """試合開始までの時間を日本語でフォーマット"""
    delta = target - current
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 0:
        return "開始済み"
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours >= 24:
        days = hours // 24
        hours = hours % 24
        return f"{days}日{hours}時間後"
    elif hours > 0:
        return f"{hours}時間{minutes}分後"
    else:
        return f"{minutes}分後"

def extract_fair_probs_for_line(
    odds_data: Dict[str, Any],
    target_line: float,
    home_team: str,
    away_team: str
) -> Optional[Tuple[float, float]]:
    """
    指定ラインの公正勝率を取得（必要に応じて補間）
    Returns: (home_prob, away_prob) or None
    """
    bookmakers = odds_data.get("bookmakers", [])
    
    # Pinnacle優先で探す
    pinnacle_bm = None
    for bm in bookmakers:
        if bm.get("id") == PINNACLE_ID:
            pinnacle_bm = bm
            break
    
    if not pinnacle_bm:
        # Bet365をフォールバック
        for bm in bookmakers:
            if bm.get("id") == BET365_ID:
                pinnacle_bm = bm
                break
    
    if not pinnacle_bm:
        return None
    
    # ハンデマーケットを探す
    market = find_handicap_market(pinnacle_bm.get("bets", []))
    if not market:
        return None
    
    # values からライン別オッズを取得
    values = market.get("values", [])
    by_line = parse_handicap_values(values, home_team, away_team)
    
    if not by_line:
        return None
    
    # 完全一致するラインがあるか確認
    if target_line in by_line:
        odd_home, odd_away = by_line[target_line]
        return remove_margin_fair_probs(odd_home, odd_away)
    
    # 補間が必要な場合
    sorted_lines = sorted(by_line.keys())
    
    # 範囲外の場合
    if target_line < sorted_lines[0] or target_line > sorted_lines[-1]:
        return None
    
    # 補間用の2点を探す
    lower_line = None
    upper_line = None
    
    for line in sorted_lines:
        if line <= target_line:
            lower_line = line
        if line >= target_line and upper_line is None:
            upper_line = line
    
    if lower_line is None or upper_line is None:
        return None
    
    # 同じ値の場合
    if lower_line == upper_line:
        odd_home, odd_away = by_line[lower_line]
        return remove_margin_fair_probs(odd_home, odd_away)
    
    # 線形補間
    odd_home_lower, odd_away_lower = by_line[lower_line]
    odd_home_upper, odd_away_upper = by_line[upper_line]
    
    prob_home_lower, _ = remove_margin_fair_probs(odd_home_lower, odd_away_lower)
    prob_home_upper, _ = remove_margin_fair_probs(odd_home_upper, odd_away_upper)
    
    # homeの勝率を補間
    prob_home = linear_interpolate(
        lower_line, prob_home_lower,
        upper_line, prob_home_upper,
        target_line
    )
    
    return prob_home, 1.0 - prob_home

def decide_verdict(ev_rake_pct: float) -> str:
    """EV%からverdictを判定"""
    if ev_rake_pct >= DEF_TH_CLEAR_PLUS:
        return "clear_plus"
    if ev_rake_pct >= DEF_TH_PLUS:
        return "plus"
    if ev_rake_pct >= DEF_TH_FAIR:
        return "fair"
    return "minus"

# --- エンドポイント ----------------------------------------------------------

@app.get("/")
async def root():
    """ルート：index.htmlを返す"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"msg": "BetValue Finder API running."}

@app.post("/map")
async def map_endpoint(req: MapRequest):
    """日本式⇔ピナクル値の相互変換"""
    if req.jp:
        ok, pinn = try_parse_jp(req.jp)
        if not ok:
            return {"error": f"未対応の日本式表記: {req.jp}"}
        return {"jp": req.jp, "pinnacle": pinn}
    if req.pinn is not None:
        try:
            jp = pinnacle_to_jp(req.pinn)
            return {"pinnacle": req.pinn, "jp": jp}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "jp または pinn のどちらかを指定してください"}

@app.post("/evaluate")
async def evaluate_endpoint(req: EvaluateRequest):
    """単一の日本式ラインに対する期待値を計算"""
    ok, pinn = try_parse_jp(req.jp)
    if not ok:
        return {"error": f"未対応の日本式表記: {req.jp}"}

    p = req.prob
    ev = p * req.payout - 1.0
    edge_pct = ev * 100.0

    verdict = decide_verdict(edge_pct)

    return {
        "jp": req.jp,
        "pinnacle": pinn,
        "fair_prob": p,
        "fair_odds": round(1.0 / p, 3) if p > 0 else None,
        "jp_payout": req.payout,
        "edge_pct": round(edge_pct, 2),
        "verdict": verdict,
    }

@app.post("/analyze_paste", response_model=List[GameEvaluation])
async def analyze_paste_endpoint(req: AnalyzePasteRequest):
    """
    貼り付けテキストを解析してEV計算・判定を返す（両側判定対応版）
    """
    try:
        # APIキー確認
        api_key = get_api_key()
        
        # テキストをパース
        games = parse_paste_text(req.text, req.sport)
        
        if not games:
            raise HTTPException(status_code=400, detail="対戦カードが見つかりません")
        
        # 日付設定（MLB時差考慮 - 日本時間14:00を境界とする）
        tokyo_now = dt.datetime.utcnow() + dt.timedelta(hours=9)
        
        if req.date:
            # 手動で日付が指定された場合はそのまま使用
            primary_date = req.date
        else:
            # 自動判定：日本時間14:00を境界に
            # 14:00以降 → 今日のデータ（まだ試合がない可能性大）
            # 14:00以前 → 昨日のデータ（朝に見た試合）
            if tokyo_now.hour >= 14:
                # 14時以降は今日の日付
                primary_date = tokyo_now.strftime("%Y-%m-%d")
            else:
                # 14時前は昨日の日付（アメリカ時間）
                yesterday = tokyo_now - dt.timedelta(days=1)
                primary_date = yesterday.strftime("%Y-%m-%d")
        
        season = int(primary_date[:4])
        
        # まず primary_date で検索
        print(f"Fetching games for {primary_date} (primary)...")
        mlb_games = fetch_games(primary_date, "Asia/Tokyo", season, api_key)
        
        # データがない場合は前後の日付も試す
        if not mlb_games:
            # 前日を試す
            alt_date = dt.datetime.strptime(primary_date, "%Y-%m-%d") - dt.timedelta(days=1)
            alt_date_str = alt_date.strftime("%Y-%m-%d")
            print(f"No games found for {primary_date}, trying {alt_date_str}...")
            mlb_games = fetch_games(alt_date_str, "Asia/Tokyo", season, api_key)
            
            if mlb_games:
                primary_date = alt_date_str
                print(f"Found games for {alt_date_str}")
            else:
                # それでもなければ翌日を試す
                alt_date2 = dt.datetime.strptime(primary_date, "%Y-%m-%d") + dt.timedelta(days=1)
                alt_date_str2 = alt_date2.strftime("%Y-%m-%d")
                print(f"Still no games, trying {alt_date_str2}...")
                mlb_games = fetch_games(alt_date_str2, "Asia/Tokyo", season, api_key)
                
                if mlb_games:
                    primary_date = alt_date_str2
                    print(f"Found games for {alt_date_str2}")
        
        # 最終的に使用する日付
        date_str = primary_date
        
        if not mlb_games:
            # 詳細なエラーメッセージ
            if req.date:
                # 手動指定の場合
                raise HTTPException(
                    status_code=404, 
                    detail=f"{date_str}のMLB試合データが見つかりません。日付を確認してください。"
                )
            else:
                # 自動判定の場合
                raise HTTPException(
                    status_code=404, 
                    detail=f"MLBの試合データが見つかりません。試合がない日の可能性があります。"
                )
        
        # チーム名→試合IDのマッピング作成
        game_map = {}
        for g in mlb_games:
            teams = g.get("teams", {})
            home = teams.get("home", {}).get("name", "")
            away = teams.get("away", {}).get("name", "")
            game_id = g.get("id")
            if game_id and home and away:
                game_map[f"{home}:{away}"] = (game_id, home, away)
                game_map[f"{away}:{home}"] = (game_id, home, away)
        
        # EV計算オブジェクト
        ev_calc = BaseballEV(
            jp_fullwin_odds=req.jp_odds,
            rakeback_pct=req.rakeback
        )
        
        results = []
        
        for game in games:
            # 試合を特定
            key1 = f"{game['team_a']}:{game['team_b']}"
            key2 = f"{game['team_b']}:{game['team_a']}"
            
            game_info = game_map.get(key1) or game_map.get(key2)
            
            # フェイバリット側の判定
            if game["fav_side"] and game["fav_line_pinnacle"] is not None:
                fav_result = await process_side(
                    game, game_info, "fav", ev_calc, api_key, date_str
                )
                results.append(fav_result)
                
                # アンダードッグ側も判定（反対側）
                underdog_result = await process_side(
                    game, game_info, "underdog", ev_calc, api_key, date_str
                )
                results.append(underdog_result)
            else:
                # ラインが指定されていない場合
                eval_result = GameEvaluation(
                    team_a=game["team_a"],
                    team_b=game["team_b"],
                    team_a_jp=game["team_a_jp"],
                    team_b_jp=game["team_b_jp"],
                    fav_team=None,
                    fav_team_jp=None,
                    jp_line=None,
                    pinnacle_line=None,
                    fair_prob=None,
                    fair_odds=None,
                    ev_pct=None,
                    ev_pct_rake=None,
                    verdict=None,
                    error="日本式ラインが指定されていません"
                )
                results.append(eval_result)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_side(
    game: Dict,
    game_info: Optional[Tuple],
    side: str,  # "fav" or "underdog"
    ev_calc: BaseballEV,
    api_key: str,
    date_str: str
) -> GameEvaluation:
    """
    片側（フェイバリットまたはアンダードッグ）の判定を処理
    """
    # 基本情報の設定
    if side == "fav":
        if game["fav_side"] == "a":
            target_team = game["team_a"]
            target_team_jp = game["team_a_jp"]
            jp_line = game["line_a"]
            # フェイバリットはマイナスライン
            pinnacle_line = -abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
        else:
            target_team = game["team_b"]
            target_team_jp = game["team_b_jp"]
            jp_line = game["line_b"]
            pinnacle_line = -abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
    else:  # underdog
        if game["fav_side"] == "a":
            target_team = game["team_b"]
            target_team_jp = game["team_b_jp"]
            # アンダードッグは反対側なので、日本式表記も反転
            jp_line = f"+{game['line_a'].replace('-', '').replace('+', '')}" if game["line_a"] else None
            # アンダードッグはプラスライン
            pinnacle_line = abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
        else:
            target_team = game["team_a"]
            target_team_jp = game["team_a_jp"]
            jp_line = f"+{game['line_b'].replace('-', '').replace('+', '')}" if game["line_b"] else None
            pinnacle_line = abs(game["fav_line_pinnacle"]) if game["fav_line_pinnacle"] else None
    
    eval_result = GameEvaluation(
        team_a=game["team_a"],
        team_b=game["team_b"],
        team_a_jp=game["team_a_jp"],
        team_b_jp=game["team_b_jp"],
        fav_team=target_team,
        fav_team_jp=target_team_jp,
        jp_line=jp_line,
        pinnacle_line=pinnacle_line,
        fair_prob=None,
        fair_odds=None,
        ev_pct=None,
        ev_pct_rake=None,
        verdict=None,
        error=None
    )
    
    if not game_info:
        eval_result.error = f"{date_str}の試合データが見つかりません"
        return eval_result
    
    if pinnacle_line is None:
        eval_result.error = "ラインデータがありません"
        return eval_result
    
    try:
        game_id, home_team, away_team = game_info
        
        # オッズデータを取得
        odds_data = fetch_odds_for_game(game_id, api_key)
        if not odds_data:
            eval_result.error = "オッズデータが取得できません"
            return eval_result
        
        # ターゲットチームがホームかアウェイか判定
        target_is_home = target_team == home_team
        
        # 該当ラインの公正勝率を取得
        # ホーム視点のラインに変換
        if target_is_home:
            home_line = pinnacle_line
        else:
            home_line = -pinnacle_line
        
        target_line_abs = abs(home_line)
        
        fair_probs = extract_fair_probs_for_line(
            odds_data,
            target_line_abs,
            home_team,
            away_team
        )
        
        if not fair_probs:
            eval_result.error = f"ライン {pinnacle_line} のオッズが見つかりません"
            return eval_result
        
        prob_home, prob_away = fair_probs
        
        # ターゲットチームの勝率
        if target_is_home:
            # ホームチームで、home_lineがマイナスならフェイバリット
            if home_line < 0:
                fair_prob = prob_home
            else:
                fair_prob = prob_home
        else:
            # アウェイチームで、home_lineがプラスならアンダードッグ
            if home_line > 0:
                fair_prob = prob_away
            else:
                fair_prob = prob_away
        
        # EV計算
        ev_pct_plain = ev_calc.ev_pct_plain(fair_prob)
        ev_pct_rake = ev_calc.ev_pct_with_rakeback(fair_prob)
        
        # verdict判定
        verdict = decide_verdict(ev_pct_rake)
        
        eval_result.fair_prob = round(fair_prob, 3)
        eval_result.fair_odds = round(1.0 / fair_prob, 3) if fair_prob > 0 else None
        eval_result.ev_pct = round(ev_pct_plain, 2)
        eval_result.ev_pct_rake = round(ev_pct_rake, 2)
        eval_result.verdict = verdict
        
    except Exception as e:
        eval_result.error = f"計算エラー: {str(e)}"
    
    return eval_result

# --- デバッグ用エンドポイント ------------------------------------------------

@app.get("/debug/test_api")
async def test_api():
    """API接続テスト"""
    try:
        api_key = get_api_key()
        tokyo_now = dt.datetime.utcnow() + dt.timedelta(hours=9)
        date_str = tokyo_now.strftime("%Y-%m-%d")
        season = int(date_str[:4])
        
        games = fetch_games(date_str, "Asia/Tokyo", season, api_key)
        
        return {
            "status": "success",
            "date": date_str,
            "games_count": len(games),
            "games": [
                {
                    "id": g.get("id"),
                    "home": g.get("teams", {}).get("home", {}).get("name"),
                    "away": g.get("teams", {}).get("away", {}).get("name")
                }
                for g in games[:5]  # 最初の5試合のみ
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}