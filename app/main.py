# app/main.py
# BetValue Finder API - MLB/サッカー対応版
# 日本式ハンデからピナクルオッズを取得して期待値を計算

from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Tuple, Any
import os
import sys
import json
import requests
import datetime as dt
from collections import defaultdict
import re
import logging

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.converter import jp_to_pinnacle, pinnacle_to_jp, try_parse_jp

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="BetValue Finder API", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル配信
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- 定数 ---
MLB_API_BASE = "https://v1.baseball.api-sports.io"
SOCCER_API_BASE = "https://v3.football.api-sports.io"
MLB_LEAGUE_ID = 1
SOCCER_LEAGUES = {
    39: "Premier League",
    140: "La Liga", 
    78: "Bundesliga",
    135: "Serie A",
    61: "Ligue 1",
}

PINNACLE_ID = 4
BET365_ID = 2

# --- モデル ---
class MapRequest(BaseModel):
    jp: Optional[str] = None
    pinn: Optional[float] = None

class AnalyzePasteRequest(BaseModel):
    text: str
    sport: str = "auto"  # auto/mlb/soccer
    rakeback: float = 0.015
    jp_odds: float = 1.9
    date: Optional[str] = None

class GameEvaluation(BaseModel):
    team_a: str
    team_b: str
    team_a_jp: str
    team_b_jp: str
    fav_team: Optional[str] = None
    fav_team_jp: Optional[str] = None
    jp_line: Optional[str] = None
    pinnacle_line: Optional[float] = None
    fair_prob: Optional[float] = None
    fair_odds: Optional[float] = None
    ev_pct: Optional[float] = None
    ev_pct_rake: Optional[float] = None
    verdict: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

# --- ユーティリティ ---
def get_api_key() -> str:
    """APIキーを取得"""
    key = os.environ.get("API_SPORTS_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=500, detail="API_SPORTS_KEY not configured")
    return key

def detect_sport(text: str) -> str:
    """テキストから競技を自動判定"""
    # サッカーのキーワード
    soccer_keywords = [
        "パレス", "フォレスト", "シティ", "ユナイテッド", "チェルシー", 
        "リバプール", "アーセナル", "バルセロナ", "レアル", "バイエルン",
        "ユベントス", "ミラン", "パリ", "0/3", "0/5", "0/7"
    ]
    
    # MLBのキーワード
    mlb_keywords = [
        "ヤンキース", "レッドソックス", "ドジャース", "ジャイアンツ",
        "カブス", "メッツ", "エンゼルス", "アストロズ", "ブレーブス"
    ]
    
    text_lower = text.lower()
    
    # キーワードチェック
    for keyword in soccer_keywords:
        if keyword.lower() in text_lower:
            return "soccer"
    
    for keyword in mlb_keywords:
        if keyword.lower() in text_lower:
            return "mlb"
    
    # デフォルトはMLB
    return "mlb"

def parse_paste_text(text: str, sport: str = "auto") -> List[Dict]:
    """貼り付けテキストをパース"""
    if sport == "auto":
        sport = detect_sport(text)
        logging.info(f"Auto-detected sport: {sport}")
    
    games = []
    lines = text.strip().split('\n')
    
    current_game = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # <>でハンデが指定されている場合
        if '<' in line and '>' in line:
            match = re.search(r'(.+?)<(.+?)>', line)
            if match:
                team = match.group(1).strip()
                handicap = match.group(2).strip()
                
                if not current_game:
                    current_game = {
                        "team_a": team,
                        "team_a_jp": team,
                        "line_a": handicap,
                        "fav_side": "a"
                    }
                else:
                    current_game["team_b"] = team
                    current_game["team_b_jp"] = team
                    current_game["line_b"] = handicap
                    current_game["fav_side"] = "b"
        else:
            # ハンデなしのチーム
            if not current_game:
                current_game = {
                    "team_a": line,
                    "team_a_jp": line
                }
            else:
                current_game["team_b"] = line
                current_game["team_b_jp"] = line
                
        # ペアが揃ったらゲームとして登録
        if current_game and "team_b" in current_game:
            # ハンデをピナクル値に変換
            if "line_a" in current_game:
                ok, pinn = try_parse_jp(current_game["line_a"])
                if ok:
                    current_game["fav_line_pinnacle"] = pinn
            elif "line_b" in current_game:
                ok, pinn = try_parse_jp(current_game["line_b"])
                if ok:
                    current_game["fav_line_pinnacle"] = pinn
                    
            games.append(current_game)
            current_game = {}
    
    return games

def calculate_ev(fair_prob: float, jp_odds: float, rakeback: float = 0.0) -> float:
    """期待値を計算"""
    ev = fair_prob * jp_odds - 1.0 + rakeback
    return ev * 100.0

def decide_verdict(ev_pct: float) -> str:
    """判定を決定"""
    if ev_pct >= 5.0:
        return "clear_plus"
    elif ev_pct >= 0.0:
        return "plus"
    elif ev_pct >= -3.0:
        return "fair"
    else:
        return "minus"

# --- エンドポイント ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """ルート：index.htmlを返す"""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    # index.htmlがない場合は簡単なメッセージ
    return HTMLResponse(content="""
    <html>
        <head><title>BetValue Finder</title></head>
        <body>
            <h1>BetValue Finder API</h1>
            <p>API is running. Please ensure index.html exists in /app/static/</p>
            <p><a href="/docs">API Documentation</a></p>
        </body>
    </html>
    """)

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

@app.post("/analyze_paste", response_model=List[GameEvaluation])
async def analyze_paste_endpoint(req: AnalyzePasteRequest):
    """貼り付けテキストを解析してEV計算"""
    try:
        # テキストをパース
        games = parse_paste_text(req.text, req.sport)
        
        if not games:
            raise HTTPException(status_code=400, detail="試合データが見つかりません")
        
        results = []
        
        for game in games:
            # 基本的な評価結果を作成
            eval_result = GameEvaluation(
                team_a=game["team_a"],
                team_b=game["team_b"],
                team_a_jp=game.get("team_a_jp", game["team_a"]),
                team_b_jp=game.get("team_b_jp", game["team_b"])
            )
            
            # フェイバリット側の処理
            if game.get("fav_side") and game.get("fav_line_pinnacle"):
                if game["fav_side"] == "a":
                    eval_result.fav_team = game["team_a"]
                    eval_result.fav_team_jp = game["team_a_jp"]
                    eval_result.jp_line = game.get("line_a")
                else:
                    eval_result.fav_team = game["team_b"]
                    eval_result.fav_team_jp = game["team_b_jp"]
                    eval_result.jp_line = game.get("line_b")
                
                eval_result.pinnacle_line = game["fav_line_pinnacle"]
                
                # ここで本来はAPIからオッズを取得して計算するが、
                # 簡単のため仮の値を設定
                # TODO: 実際のAPI接続とオッズ取得を実装
                
                # 仮の公正勝率（50-60%の間でランダム）
                import random
                fair_prob = 0.5 + random.random() * 0.1
                eval_result.fair_prob = round(fair_prob, 3)
                eval_result.fair_odds = round(1.0 / fair_prob, 3) if fair_prob > 0 else None
                
                # EV計算
                ev_plain = calculate_ev(fair_prob, req.jp_odds, 0)
                ev_rake = calculate_ev(fair_prob, req.jp_odds, req.rakeback)
                
                eval_result.ev_pct = round(ev_plain, 2)
                eval_result.ev_pct_rake = round(ev_rake, 2)
                eval_result.verdict = decide_verdict(ev_rake)
            else:
                eval_result.error = "ハンデが指定されていません"
                eval_result.error_code = "NO_HANDICAP"
            
            results.append(eval_result)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in analyze_paste: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "timestamp": dt.datetime.utcnow().isoformat()}

# メイン実行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
