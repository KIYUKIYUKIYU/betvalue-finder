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
    odds_api_key = os.environ.get("ODDS_API_KEY", "test_api_key")
    # api_key と theodds_api_key の両方に同じキーを使用
    return BettingPipelineOrchestrator(api_key=odds_api_key, theodds_api_key=odds_api_key)

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
    league_jp: Optional[str] = None  # リーグ名 (日本語)
    league_en: Optional[str] = None  # リーグ名 (英語)
    sport_key: Optional[str] = None  # sport_key (内部用)

    # Team Info
    team_a_jp: Optional[str] = None  # チームA (日本語)
    team_b_jp: Optional[str] = None  # チームB (日本語)
    team_a_en: Optional[str] = None  # チームA (英語)
    team_b_en: Optional[str] = None  # チームB (英語)

    # Legacy fields (互換性のため残す)
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

@app.post("/analyze_paste", response_model=List[GameEvaluation])
async def analyze_paste_endpoint(req: AnalyzePasteRequest):
    api_key = os.environ.get("ODDS_API_KEY")
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
            # league_jp/league_en の取得
            league_jp = game.get("league")  # パーサー出力のleagueフィールド
            sport_key = game.get("sport_key", game.get("sport", ""))

            # sport_keyからleague_enを取得
            from converter.league_name_mapper import get_league_mapper
            mapper = get_league_mapper()
            _, league_en = mapper.get_league_names(sport_key)

            game_data = {
                # Game Info
                "game_date": game.get("game_date"),
                "sport": game.get("sport"),
                "league_jp": league_jp,
                "league_en": league_en,
                "sport_key": sport_key,

                # Team Info (新フィールド)
                "team_a_jp": game.get("home_team_jp"),  # homeをteam_aにマッピング
                "team_b_jp": game.get("away_team_jp"),  # awayをteam_bにマッピング
                "team_a_en": game.get("home_team_en"),
                "team_b_en": game.get("away_team_en"),

                # Legacy fields (互換性維持)
                "home_team_jp": game.get("home_team_jp"),
                "away_team_jp": game.get("away_team_jp"),

                # その他
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

@app.get("/debug/env")
async def debug_env():
    """環境変数デバッグ用エンドポイント（本番では削除）"""
    return {
        "ODDS_API_KEY": "設定済み" if os.environ.get("ODDS_API_KEY") else "未設定",
        "API_SPORTS_KEY": "設定済み" if os.environ.get("API_SPORTS_KEY") else "未設定",
        "DISCORD_WEBHOOK_URL": "設定済み" if os.environ.get("DISCORD_WEBHOOK_URL") else "未設定",
        "all_env_keys": [k for k in os.environ.keys() if not k.startswith("_")]
    }
