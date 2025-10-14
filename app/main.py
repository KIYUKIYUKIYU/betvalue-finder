# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import logging
import asyncio

# ロギングシステムの初期化
from app.logging_system import log_manager
from app.middleware.logging_middleware import setup_logging_middleware
from app.pipeline_orchestrator import BettingPipelineOrchestrator
from app.api.logging_endpoints import router as logging_router

app = FastAPI(title="BetValue Finder API", version="4.0.0")

# CORS設定 - Cloudflareからのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では具体的なドメインを指定することを推奨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ログミドルウェアの設定
setup_logging_middleware(app)

# ログAPI エンドポイントの追加
app.include_router(logging_router)

# 静的ファイルの設定（存在する場合のみ）
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Pipeline Orchestrator の初期化（API keyは実行時に設定）
def get_pipeline():
    # ODDS_API_KEY を優先、なければ API_SPORTS_KEY（後方互換性）
    api_key = os.environ.get("ODDS_API_KEY") or os.environ.get("API_SPORTS_KEY", "test_api_key")
    return BettingPipelineOrchestrator(api_key=api_key)

class AnalyzePasteRequest(BaseModel):
    paste_text: str  # Changed from 'text' to 'paste_text' to match frontend
    sport_hint: Optional[str] = "mixed"
    jp_odds: Optional[float] = 1.9
    rakeback: Optional[float] = 0.0

class TeamOdds(BaseModel):
    raw_pinnacle_odds: Optional[float] = None
    fair_odds: Optional[float] = None
    ev_percentage: Optional[float] = None
    verdict: Optional[str] = None

class GameEvaluation(BaseModel):
    # Game Info
    game_date: Optional[str] = None
    sport: Optional[str] = None
    home_team_jp: Optional[str] = None
    away_team_jp: Optional[str] = None
    
    # Match Info
    match_confidence: Optional[float] = None
    
    # Line Info
    jp_line: Optional[str] = None
    pinnacle_line: Optional[float] = None
    fav_team: Optional[str] = None

    # Team-specific results
    home_team_odds: TeamOdds
    away_team_odds: TeamOdds

    # Metadata
    error: Optional[str] = None
    processing_time: Optional[float] = None

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = os.path.join("app", "static", "index.html")
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>BetValue Finder API v4.0</h1><p>Complete pipeline integration with enhanced parsing, team mapping, game matching, odds fetching, and EV calculation.</p><a href='/docs'>API Docs</a>")

@app.get("/debug/upcoming-matches")
async def get_upcoming_matches(sport: str = "soccer_epl", limit: int = 5):
    """今後予定されている試合を取得（テスト用）"""
    import requests
    from datetime import datetime

    api_key = os.environ.get("ODDS_API_KEY") or os.environ.get("API_SPORTS_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="ODDS_API_KEY not configured")

    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
        params = {
            'apiKey': api_key,
            'regions': 'eu',
            'markets': 'h2h'
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        games = response.json()

        results = []
        for game in games[:limit]:
            commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            results.append({
                "home_team": game['home_team'],
                "away_team": game['away_team'],
                "commence_time": commence_time.isoformat(),
                "sport_key": game['sport_key']
            })

        return {
            "total_matches": len(games),
            "showing": len(results),
            "matches": results
        }
    except Exception as e:
        log_manager.log_error("Failed to fetch upcoming matches", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch matches: {str(e)}")

@app.post("/analyze_paste", response_model=List[GameEvaluation])
async def analyze_paste_endpoint(req: AnalyzePasteRequest):
    # ODDS_API_KEY を使用（Railway環境変数と一致）
    api_key = os.environ.get("ODDS_API_KEY") or os.environ.get("API_SPORTS_KEY")
    if not api_key:
        log_manager.log_error("API configuration error", Exception("ODDS_API_KEY not configured"))
        raise HTTPException(status_code=500, detail="ODDS_API_KEY not configured")

    try:
        log_manager.main_logger.info(f"📝 Analyze request received: text length {len(req.paste_text)}")

        # Validate input
        if not req.paste_text or not req.paste_text.strip():
            raise HTTPException(
                status_code=400,
                detail="試合データが入力されていません。テキストを貼り付けてください。"
            )

        # Initialize pipeline with API key
        pipeline = get_pipeline()

        # Execute complete pipeline with timeout
        pipeline_result = await asyncio.wait_for(
            pipeline.execute_pipeline(
                customer_text=req.paste_text,
                sport_hint=req.sport_hint or "mixed",  # Use provided sport hint or auto-detect
                jp_odds=req.jp_odds,
                rakeback=req.rakeback
            ),
            timeout=60.0  # 60 second timeout
        )

        # Convert pipeline results to API response format
        results = []
        final_games = getattr(pipeline_result, 'games_processed', [])
        for game in final_games:
            # The 'game' dict now has the new structure from the orchestrator
            game_data = {
                "game_date": game.get("game_date"),
                "sport": game.get("sport"),
                "home_team_jp": game.get("home_team_jp"),
                "away_team_jp": game.get("away_team_jp"),
                "match_confidence": game.get("match_confidence"),
                "jp_line": game.get("jp_line"),
                "pinnacle_line": game.get("pinnacle_line"),
                "fav_team": game.get("fav_team"),
                "home_team_odds": game.get("home_team_odds"),
                "away_team_odds": game.get("away_team_odds"),
                "error": game.get("error"),
                "processing_time": pipeline_result.total_time,
            }
            results.append(GameEvaluation(**game_data))

        total_time = getattr(pipeline_result, 'total_time', 0.0)
        stages_completed = getattr(pipeline_result, 'stages_completed', [])
        log_manager.main_logger.info(f"✅ Pipeline processed {len(results)} games in {total_time:.2f}s "
                    f"with {len(stages_completed)}/6 stages successful")

        return results

    except asyncio.TimeoutError:
        log_manager.log_error("Pipeline timeout", Exception("Pipeline execution exceeded 60 seconds"))
        raise HTTPException(status_code=408, detail="Request timeout: Analysis took too long")
    except ValueError as ve:
        # ユーザー入力エラー（チーム名認識失敗など）
        log_manager.main_logger.warning(f"⚠️ User input error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        # Re-raise HTTP exceptions (like 400 for empty input)
        raise
    except Exception as e:
        log_manager.log_error("Pipeline execution failed in API endpoint", e)
        error_detail = f"Analysis failed: {str(e)[:200]}..."  # Truncate long error messages
        raise HTTPException(status_code=500, detail=error_detail)
