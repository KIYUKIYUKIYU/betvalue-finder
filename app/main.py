# -*- coding: utf-8 -*-
"""
app/main.py
BetValue Finder API - MLB/サッカー対応版
モジュール化されたオッズ処理とEV評価を使用
"""

from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import sys
import json
import datetime as dt
import re
import logging

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 既存のconverterモジュール
from app.converter import jp_to_pinnacle, pinnacle_to_jp, try_parse_jp

# 新しいモジュール
from converter.odds_processor import OddsProcessor
from converter.ev_evaluator import EVEvaluator
from game_manager.mlb import MLBGameManager

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="BetValue Finder API", version="2.0.0")

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
    eff_odds: Optional[float] = None
    verdict: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

class EvaluateOddsRequest(BaseModel):
    game_id: str
    jp_line: str
    side: str = "home"  # home/away
    rakeback: float = 0.0
    jp_odds: float = 1.9

class BestLinesRequest(BaseModel):
    game_id: str
    top_n: int = 3
    min_ev: Optional[float] = None
    rakeback: float = 0.0
    jp_odds: float = 1.9

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
                    current_game["jp_line"] = current_game["line_a"]
            elif "line_b" in current_game:
                ok, pinn = try_parse_jp(current_game["line_b"])
                if ok:
                    current_game["fav_line_pinnacle"] = pinn
                    current_game["jp_line"] = current_game["line_b"]
                    
            games.append(current_game)
            current_game = {}
    
    return games

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
            <h1>BetValue Finder API v2.0</h1>
            <p>API is running with modularized odds processing and EV evaluation.</p>
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
    """貼り付けテキストを解析してEV計算（GameManager統合版）"""
    try:
        # APIキー取得
        api_key = get_api_key()
        
        # テキストをパース
        games = parse_paste_text(req.text, req.sport)
        
        if not games:
            raise HTTPException(status_code=400, detail="試合データが見つかりません")
        
        # GameManagerとモジュール初期化
        mlb_manager = MLBGameManager(api_key)
        odds_processor = OddsProcessor()
        ev_evaluator = EVEvaluator(jp_odds=req.jp_odds, rakeback=req.rakeback)
        
        results = []
        
        for game in games:
            # 基本的な評価結果を作成
            eval_result = GameEvaluation(
                team_a=game["team_a"],
                team_b=game["team_b"],
                team_a_jp=game.get("team_a_jp", game["team_a"]),
                team_b_jp=game.get("team_b_jp", game["team_b"])
            )
            
            # 試合を検索
            matched_game = mlb_manager.match_teams([game["team_a"], game["team_b"]])
            
            if not matched_game:
                eval_result.error = "試合が見つかりません"
                eval_result.error_code = "GAME_NOT_FOUND"
                results.append(eval_result)
                continue
            
            # フェイバリット側の処理
            if game.get("fav_side") and game.get("fav_line_pinnacle"):
                if game["fav_side"] == "a":
                    eval_result.fav_team = game["team_a"]
                    eval_result.fav_team_jp = game["team_a_jp"]
                    eval_result.jp_line = game.get("jp_line")
                    side = "home" if matched_game["home"] == eval_result.fav_team else "away"
                else:
                    eval_result.fav_team = game["team_b"]
                    eval_result.fav_team_jp = game["team_b_jp"]
                    eval_result.jp_line = game.get("jp_line")
                    side = "home" if matched_game["home"] == eval_result.fav_team else "away"
                
                eval_result.pinnacle_line = game["fav_line_pinnacle"]
                
                # オッズを取得
                odds_data = mlb_manager.fetch_odds(matched_game["id"])
                
                if not odds_data:
                    eval_result.error = "オッズが取得できません"
                    eval_result.error_code = "NO_ODDS"
                    results.append(eval_result)
                    continue
                
                # オッズを処理
                line_data = odds_processor.prepare_line_data(odds_data)
                
                if not line_data:
                    eval_result.error = "ハンデオッズが見つかりません"
                    eval_result.error_code = "NO_HANDICAP_ODDS"
                    results.append(eval_result)
                    continue
                
                # EV評価
                evaluation = ev_evaluator.evaluate_single_line(
                    line_data,
                    eval_result.pinnacle_line,
                    side
                )
                
                # 結果を設定
                eval_result.fair_prob = evaluation.get("fair_prob")
                eval_result.fair_odds = evaluation.get("fair_odds")
                eval_result.ev_pct = evaluation.get("ev_pct")
                eval_result.ev_pct_rake = evaluation.get("ev_pct_rake")
                eval_result.eff_odds = evaluation.get("eff_odds")
                eval_result.verdict = evaluation.get("verdict")
                
                if evaluation.get("error"):
                    eval_result.error = evaluation["error"]
                    eval_result.error_code = "EVALUATION_ERROR"
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

@app.post("/evaluate_odds")
async def evaluate_odds_endpoint(req: EvaluateOddsRequest):
    """特定ゲーム・ラインのEV評価"""
    try:
        api_key = get_api_key()
        
        # GameManagerとモジュール初期化
        mlb_manager = MLBGameManager(api_key)
        odds_processor = OddsProcessor()
        ev_evaluator = EVEvaluator(jp_odds=req.jp_odds, rakeback=req.rakeback)
        
        # オッズ取得
        odds_data = mlb_manager.fetch_odds(req.game_id)
        
        if not odds_data:
            raise HTTPException(status_code=404, detail="Odds not found for this game")
        
        # オッズを処理
        line_data = odds_processor.prepare_line_data(odds_data)
        
        if not line_data:
            raise HTTPException(status_code=404, detail="No handicap odds available")
        
        # 日本式をピナクル値に変換
        ok, pinnacle_value = try_parse_jp(req.jp_line)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Invalid JP line: {req.jp_line}")
        
        # EV評価
        result = ev_evaluator.evaluate_single_line(
            line_data,
            pinnacle_value,
            req.side
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in evaluate_odds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find_best_lines")
async def find_best_lines_endpoint(req: BestLinesRequest):
    """特定ゲームの最良ラインを検索"""
    try:
        api_key = get_api_key()
        
        # GameManagerとモジュール初期化
        mlb_manager = MLBGameManager(api_key)
        odds_processor = OddsProcessor()
        ev_evaluator = EVEvaluator(jp_odds=req.jp_odds, rakeback=req.rakeback)
        
        # オッズ取得
        odds_data = mlb_manager.fetch_odds(req.game_id)
        
        if not odds_data:
            raise HTTPException(status_code=404, detail="Odds not found for this game")
        
        # オッズを処理
        line_data = odds_processor.prepare_line_data(odds_data)
        
        if not line_data:
            raise HTTPException(status_code=404, detail="No handicap odds available")
        
        # 最良ラインを検索
        best_lines = ev_evaluator.find_best_lines(
            line_data,
            top_n=req.top_n,
            min_ev=req.min_ev
        )
        
        return best_lines
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in find_best_lines: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "modules": {
            "odds_processor": "OK",
            "ev_evaluator": "OK",
            "game_manager": "OK"
        },
        "timestamp": dt.datetime.utcnow().isoformat()
    }

# メイン実行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)