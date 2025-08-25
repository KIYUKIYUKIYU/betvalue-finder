# app/main.py — /evaluate が lines_override 無し時に API-Football(Pinnacle=11) を自動参照
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime, timezone
import math, json, sqlite3, threading

from app.converter import jp_to_pinnacle
from app.af_client import get_pinnacle_lines_from_api_football

app = FastAPI(title="BetValue Finder API", version="0.3.0")

DB_PATH = "bet_snapshots.sqlite3"
_DB_LOCK = threading.Lock()

# ===== DB init =====
def init_db():
    with _DB_LOCK:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            fixture_id TEXT,
            league TEXT,
            side TEXT,
            jp_handicap TEXT,
            pinnacle_value REAL,
            fair_odds REAL,
            edge_pct REAL,
            verdict TEXT,
            jp_fullwin_odds REAL,
            lines_override_json TEXT,
            raw_request_json TEXT
        )
        """)
        con.commit()
        con.close()

init_db()

# ===== Models =====
class LineOdds(BaseModel):
    line: float = Field(..., description="ピナクルのスプレッド(例: -0.5, -1.0)")
    home_odds: float = Field(..., gt=1.0001)
    away_odds: float = Field(..., gt=1.0001)

class EvaluateRequest(BaseModel):
    fixture_id: str
    league: Literal["MLB", "NPB", "EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1", "NBA", "Other"] = "MLB"
    side: Literal["home", "away"]
    jp_handicap: str = Field(..., description="日本式ハンデ表記（'1.1','0/7','1半1' 等）")
    jp_fullwin_odds: Optional[float] = Field(1.90, description="丸勝ちの配当（地域差があれば上書き）")
    lines_override: Optional[List[LineOdds]] = Field(None, description="ピナクルのライン&オッズ（テスト/暫定）")

class EvaluateResponse(BaseModel):
    fixture_id: str
    league: str
    side: str
    jp_handicap: str
    pinnacle_value: float
    fair_odds: float
    edge_pct: float
    verdict: Literal["clear_plus", "slightly_plus", "fair", "minus"]
    captured_at: str

class MapRequest(BaseModel):
    jp_handicap: str
    side: Optional[Literal["home", "away"]] = "home"

class MapResponse(BaseModel):
    jp_handicap: str
    pinnacle_value: float
    target_line_for_home: float
    target_line_for_away: float

class IngestRequest(BaseModel):
    payload: dict

class IngestResponse(BaseModel):
    ok: bool
    stored_at: str

# ===== Helpers =====
def verdict_from_edge(edge_pct: float) -> Literal["clear_plus", "slightly_plus", "fair", "minus"]:
    if edge_pct > 5.0:
        return "clear_plus"
    if 0.0 <= edge_pct <= 5.0:
        return "slightly_plus"
    if -3.0 <= edge_pct < 0.0:
        return "fair"
    return "minus"

def remove_margin_pair(home_odds: float, away_odds: float) -> float:
    qh = 1.0 / home_odds
    qa = 1.0 / away_odds
    total = qh + qa
    if total <= 0:
        return 0.5
    return qh / total

def interp_prob(target_abs_line: float, lines: List[LineOdds]) -> float:
    if not lines:
        return 0.5
    pts = []
    for lo in lines:
        x = abs(lo.line)
        y = remove_margin_pair(lo.home_odds, lo.away_odds)
        pts.append((x, y))
    pts.sort(key=lambda t: t[0])

    for x, y in pts:
        if abs(x - target_abs_line) <= 1e-9:
            return y

    left = None
    right = None
    for i in range(len(pts) - 1):
        if pts[i][0] <= target_abs_line <= pts[i + 1][0]:
            left = pts[i]
            right = pts[i + 1]
            break
    if left and right:
        (x1, y1), (x2, y2) = left, right
        if abs(x1 - x2) <= 1e-12:
            return y1
        t = (target_abs_line - x1) / (x2 - x1)
        return y1 + t * (y2 - y1)

    if target_abs_line < pts[0][0]:
        (x1, y1), (x2, y2) = pts[0], pts[1] if len(pts) >= 2 else (pts[0], pts[0])
        if abs(x1 - x2) <= 1e-12:
            return y1
        slope = (y2 - y1) / (x2 - x1) if abs(x1 - x2) > 1e-12 else 0.0
        return y1 - slope * (x1 - target_abs_line)

    if target_abs_line > pts[-1][0]:
        (x1, y1), (x2, y2) = pts[-2] if len(pts) >= 2 else (pts[-1], pts[-1]), pts[-1]
        if abs(x1 - x2) <= 1e-12:
            return y2
        slope = (y2 - y1) / (x2 - x1)
        return y2 + slope * (target_abs_line - x2)

    return pts[-1][1]

def save_evaluation_row(req: EvaluateRequest, pv: float, fair_odds: float, edge_pct: float, verdict: str):
    with _DB_LOCK:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
            INSERT INTO evaluations
              (created_at, fixture_id, league, side, jp_handicap, pinnacle_value, fair_odds, edge_pct, verdict,
               jp_fullwin_odds, lines_override_json, raw_request_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            req.fixture_id, req.league, req.side, req.jp_handicap,
            float(round(pv, 2)),
            float(round(fair_odds, 6)),
            float(round(edge_pct, 6)),
            verdict,
            float(req.jp_fullwin_odds if req.jp_fullwin_odds and req.jp_fullwin_odds > 1.0 else 1.90),
            json.dumps([lo.model_dump() for lo in (req.lines_override or [])], ensure_ascii=False),
            json.dumps(req.model_dump(), ensure_ascii=False),
        ))
        con.commit()
        con.close()

# ===== Routes =====
@app.get("/")
def root():
    return {"status": "ok", "service": "betvalue-finder", "version": "0.3.0"}

@app.get("/health")
def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@app.post("/map", response_model=MapResponse)
def map_handicap(req: MapRequest):
    try:
        pv = jp_to_pinnacle(req.jp_handicap)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"jp_handicap が不正です: {e}")
    return MapResponse(
        jp_handicap=req.jp_handicap,
        pinnacle_value=round(pv, 2),
        target_line_for_home=round(-pv, 2),
        target_line_for_away=round(pv, 2)
    )

@app.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest):
    # 1) CSV唯一の正で変換
    try:
        pv = jp_to_pinnacle(req.jp_handicap)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"jp_handicap が不正です: {e}")

    # 2) ライン取得：優先順位
    #    a) lines_override（テスト手入力）
    #    b) API-Football (Pinnacle=11) 自動取得（サッカー系リーグのみ）
    #    c) データ無し → 0.5 フォールバック
    lines: Optional[List[LineOdds]] = None
    if req.lines_override and len(req.lines_override) >= 1:
        lines = req.lines_override
    else:
        SOCCER_LEAGUES = {"EPL", "LaLiga", "SerieA", "Bundesliga", "Ligue1"}
        if req.league in SOCCER_LEAGUES:
            fetched = get_pinnacle_lines_from_api_football(int(req.fixture_id))  # fixture_id は API-Football の数値ID前提
            if fetched:
                lines = [LineOdds(**d) for d in fetched]

    # 3) 公正オッズ推定
    if lines:
        p_home = float(interp_prob(abs(pv), lines))
    else:
        p_home = 0.5

    p_target = p_home if req.side == "home" else (1.0 - p_home)
    p_target = min(max(p_target, 1e-6), 1.0 - 1e-6)
    fair_odds = 1.0 / p_target

    # 4) エッジ & 判定
    offer = req.jp_fullwin_odds if req.jp_fullwin_odds and req.jp_fullwin_odds > 1.0 else 1.90
    edge_pct = (offer / fair_odds - 1.0) * 100.0
    verdict = verdict_from_edge(edge_pct)

    # 5) 保存（障害は飲み込み）
    try:
        save_evaluation_row(req, pv, fair_odds, edge_pct, verdict)
    except Exception:
        pass

    return EvaluateResponse(
        fixture_id=req.fixture_id,
        league=req.league,
        side=req.side,
        jp_handicap=req.jp_handicap,
        pinnacle_value=round(pv, 2),
        fair_odds=round(fair_odds, 4),
        edge_pct=round(edge_pct, 2),
        verdict=verdict,
        captured_at=datetime.now(timezone.utc).isoformat(),
    )

@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    with _DB_LOCK:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("""
        INSERT INTO evaluations
          (created_at, fixture_id, league, side, jp_handicap, pinnacle_value, fair_odds, edge_pct, verdict,
           jp_fullwin_odds, lines_override_json, raw_request_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            req.payload.get("fixture_id"),
            req.payload.get("league"),
            req.payload.get("side"),
            req.payload.get("jp_handicap"),
            None, None, None, None,
            None,
            None,
            json.dumps(req.payload, ensure_ascii=False),
        ))
        con.commit()
        con.close()
    return IngestResponse(ok=True, stored_at=datetime.now(timezone.utc).isoformat())
