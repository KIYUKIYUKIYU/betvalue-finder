# -*- coding: utf-8 -*-
"""
Intelligent Pregame Selection System
多次元コンテキスト分析による自動意図判定・最適ゲーム選択システム
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging


@dataclass
class ContextProfile:
    """統合コンテキストプロファイル"""
    temporal_context: Dict = None
    linguistic_context: Dict = None
    behavioral_context: Dict = None
    situational_context: Dict = None
    intent_confidence: float = 0.0
    primary_intent: str = "unknown"

    def __post_init__(self):
        if self.temporal_context is None:
            self.temporal_context = {}
        if self.linguistic_context is None:
            self.linguistic_context = {}
        if self.behavioral_context is None:
            self.behavioral_context = {}
        if self.situational_context is None:
            self.situational_context = {}


@dataclass
class GameSelection:
    """ゲーム選択結果"""
    primary_games: List[Dict]
    secondary_games: List[Dict] = None
    display_mode: str = "default"
    explanation: str = ""
    recommendations: List[str] = None
    confidence_score: float = 0.0

    def __post_init__(self):
        if self.secondary_games is None:
            self.secondary_games = []
        if self.recommendations is None:
            self.recommendations = []


class SportTimePatterns:
    """競技別時間パターン定義"""

    PATTERNS = {
        "npb": {
            "research_windows": [
                (9, 12, "morning_research", 0.8),
                (12, 15, "lunch_analysis", 0.7),
                (15, 17, "pre_betting_prep", 0.6)
            ],
            "betting_windows": [
                (16, 18, "betting_prime", 0.9),
                (17, 19, "last_chance", 0.8)
            ],
            "handicap_lead_time": 1.5,  # 1.5時間前送付
            "typical_start_times": [14, 18],  # 14:00 or 18:00
            "consecutive_game_gap": 20  # 連戦最小間隔(時間)
        },
        "mlb": {
            "research_windows": [
                (6, 10, "morning_prep", 0.8),
                (10, 19, "day_analysis", 0.9)
            ],
            "betting_windows": [
                (20, 23, "handicap_prime", 0.95),
                (0, 6, "game_time", 0.7)
            ],
            "handicap_send_time": (20, 22),  # 20-22時送付
            "timezone_offset": -13,  # アメリカ東部時間差
            "consecutive_game_gap": 18
        },
        "soccer": {
            "research_windows": [
                (10, 17, "day_analysis", 0.8)
            ],
            "betting_windows": [
                (17, 23, "evening_prime", 0.9),
                (0, 5, "late_night", 0.7)
            ],
            "handicap_lead_time": 1.5,
            "weekend_extension": True,  # 週末は時間範囲拡張
            "consecutive_game_gap": 48  # サッカーは連戦少ない
        },
        "nba": {  # NBA対応準備
            "research_windows": [
                (8, 12, "morning_prep", 0.8),
                (12, 18, "afternoon_analysis", 0.9)
            ],
            "betting_windows": [
                (18, 22, "handicap_prime", 0.95),
                (22, 2, "game_time", 0.8)
            ],
            "handicap_lead_time": 2.0,  # 2時間前送付
            "timezone_consideration": True,
            "consecutive_game_gap": 24
        }
    }


class TemporalAnalyzer:
    """時間的文脈分析器"""

    def __init__(self):
        self.sport_patterns = SportTimePatterns.PATTERNS
        self.logger = logging.getLogger(__name__)

    def analyze(self, request_data: Dict) -> Dict:
        """時間的文脈の詳細分析"""

        now = datetime.now()
        sport = request_data.get("sport", "").lower()

        context = {
            "current_hour": now.hour,
            "day_of_week": now.weekday(),
            "is_weekend": now.weekday() >= 5,
            "sport": sport
        }

        # 競技別パターンマッチング
        if sport in self.sport_patterns:
            patterns = self.sport_patterns[sport]
            context.update(self._analyze_sport_patterns(now, patterns))
            context.update(self._analyze_handicap_timing(now, sport, patterns))

        return context

    def _analyze_sport_patterns(self, now: datetime, patterns: Dict) -> Dict:
        """競技パターン分析"""

        result = {
            "window_matches": [],
            "dominant_context": "unknown",
            "confidence": 0.0
        }

        current_hour = now.hour

        # 各時間窓での分析
        for window_type in ["research_windows", "betting_windows"]:
            if window_type in patterns:
                for start, end, name, confidence in patterns[window_type]:
                    if start <= current_hour < end:
                        result["window_matches"].append({
                            "type": window_type.replace("_windows", ""),
                            "name": name,
                            "confidence": confidence
                        })

        # 支配的コンテキスト決定
        if result["window_matches"]:
            best_match = max(result["window_matches"], key=lambda x: x["confidence"])
            result["dominant_context"] = best_match["type"]
            result["confidence"] = best_match["confidence"]

        return result

    def _analyze_handicap_timing(self, now: datetime, sport: str, patterns: Dict) -> Dict:
        """ハンデ送付タイミング分析"""

        result = {"handicap_analysis": {}}

        if sport == "npb":
            lead_time = patterns.get("handicap_lead_time", 1.5)
            result["handicap_analysis"] = {
                "is_handicap_active": self._is_npb_handicap_active(now, lead_time),
                "next_opportunity": self._get_next_npb_opportunity(now),
                "urgency_level": self._calculate_urgency(now, sport)
            }

        elif sport == "mlb":
            send_start, send_end = patterns.get("handicap_send_time", (20, 22))
            result["handicap_analysis"] = {
                "is_handicap_window": send_start <= now.hour <= send_end,
                "next_window": self._get_next_mlb_window(now, send_start),
                "timezone_impact": self._analyze_timezone_impact(now)
            }

        elif sport == "soccer":
            lead_time = patterns.get("handicap_lead_time", 1.5)
            result["handicap_analysis"] = {
                "is_active_period": now.hour >= 17 or now.hour <= 5,
                "weekend_boost": patterns.get("weekend_extension", False) and now.weekday() >= 5
            }

        elif sport == "nba":
            result["handicap_analysis"] = {
                "is_season_active": self._is_nba_season(now),
                "game_day_probability": self._calculate_nba_game_probability(now)
            }

        return result

    def _is_npb_handicap_active(self, now: datetime, lead_time: float) -> bool:
        """NPBハンデ送付アクティブ判定"""
        # NPB試合時間 (14:00, 18:00) - lead_time = 送付時間
        potential_times = [14 - lead_time, 18 - lead_time]
        current_hour = now.hour + (now.minute / 60.0)

        for target_time in potential_times:
            if abs(current_hour - target_time) <= 0.5:  # 30分の余裕
                return True
        return False

    def _calculate_urgency(self, now: datetime, sport: str) -> float:
        """緊急度計算"""
        if sport == "npb":
            # 16-18時は最高緊急度
            if 16 <= now.hour <= 18:
                return 0.9
            elif 15 <= now.hour <= 19:
                return 0.6
        elif sport == "mlb":
            # 20-22時は最高緊急度
            if 20 <= now.hour <= 22:
                return 0.95

        return 0.3

    def _is_nba_season(self, now: datetime) -> bool:
        """NBA シーズン中判定"""
        # NBA season: 10月-4月
        month = now.month
        return month >= 10 or month <= 4

    def _get_next_mlb_window(self, now: datetime, start_hour: int) -> Dict:
        """次のMLBハンデ送付窓計算"""
        if now.hour < start_hour:
            # 今日の送付時間前
            next_time = now.replace(hour=start_hour, minute=0, second=0)
        else:
            # 明日の送付時間
            next_time = (now + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0)

        return {
            "next_window_start": next_time,
            "hours_until": (next_time - now).total_seconds() / 3600
        }

    def _analyze_timezone_impact(self, now: datetime) -> Dict:
        """タイムゾーンの影響分析"""
        return {
            "local_hour": now.hour,
            "is_jst": True,  # 常にJST環境と仮定
            "impact_level": "normal",
            "timezone_offset": "+09:00"
        }


class LinguisticAnalyzer:
    """言語的文脈分析器"""

    def __init__(self):
        self.intent_keywords = {
            "research_strong": {
                "keywords": ["分析", "研究", "調査", "検討", "比較", "データ", "統計"],
                "weight": 0.9
            },
            "research_mild": {
                "keywords": ["確認", "チェック", "見る", "調べる", "情報", "状況"],
                "weight": 0.6
            },
            "betting_strong": {
                "keywords": ["ベット", "賭け", "勝負", "狙い", "勝てる", "投資"],
                "weight": 0.95
            },
            "betting_mild": {
                "keywords": ["検討", "考える", "どう", "迷う", "様子見"],
                "weight": 0.7
            },
            "urgency_indicators": {
                "keywords": ["今すぐ", "急いで", "すぐに", "至急", "今夜", "直ぐ"],
                "weight": 0.8
            },
            "future_indicators": {
                "keywords": ["明日", "来週", "後で", "将来", "準備", "予定"],
                "weight": 0.6
            }
        }

        # 競技特有表現
        self.sport_expressions = {
            "npb": {
                "team_focus": ["広島", "阪神", "巨人", "ヤクルト", "中日", "DeNA"],
                "game_focus": ["ナイター", "デイゲーム", "連戦", "日本シリーズ"],
                "betting_focus": ["ハンデ", "オッズ", "EV", "期待値"]
            },
            "mlb": {
                "team_focus": ["ドジャース", "ヤンキース", "レッドソックス", "エンゼルス"],
                "time_focus": ["深夜", "朝", "時差", "アメリカ", "現地時間"],
                "betting_focus": ["メジャー", "大谷", "投手戦", "ワールドシリーズ"]
            },
            "soccer": {
                "team_focus": ["バルセロナ", "レアル", "マンU", "チェルシー", "バイエルン"],
                "league_focus": ["プレミア", "リーガ", "セリエA", "ブンデス", "CL"],
                "betting_focus": ["欧州", "国内", "カップ戦", "リーグ戦"]
            },
            "nba": {  # NBA準備
                "team_focus": ["レイカーズ", "ウォリアーズ", "セルティックス", "ヒート"],
                "player_focus": ["レブロン", "カリー", "KD", "八村"],
                "betting_focus": ["NBA", "プレイオフ", "レギュラーシーズン"]
            }
        }

    def analyze(self, request_data: Dict) -> Dict:
        """言語的文脈分析"""

        text = request_data.get("text", "")
        sport = request_data.get("sport", "").lower()

        context = {
            "intent_scores": self._calculate_intent_scores(text),
            "sport_specificity": self._analyze_sport_expressions(text, sport),
            "urgency_level": self._analyze_urgency(text),
            "formality_level": self._analyze_formality(text),
            "confidence_indicators": self._analyze_confidence_indicators(text)
        }

        return context

    def _calculate_intent_scores(self, text: str) -> Dict[str, float]:
        """意図スコア計算"""

        scores = {}
        text_lower = text.lower()

        for intent_type, config in self.intent_keywords.items():
            score = 0.0
            matches = 0

            for keyword in config["keywords"]:
                if keyword in text_lower:
                    score += config["weight"]
                    matches += 1

            # 正規化 (最大1.0)
            if matches > 0:
                score = min(score / matches, 1.0)

            scores[intent_type] = score

        return scores

    def _analyze_sport_expressions(self, text: str, sport: str) -> Dict:
        """競技特有表現分析"""

        if sport not in self.sport_expressions:
            return {"focus_score": 0.0, "categories": {}}

        expressions = self.sport_expressions[sport]
        analysis = {"categories": {}, "focus_score": 0.0}

        total_possible = 0
        total_matches = 0

        for category, keywords in expressions.items():
            matches = [kw for kw in keywords if kw in text]
            analysis["categories"][category] = {
                "matches": matches,
                "score": len(matches) / len(keywords) if keywords else 0
            }
            total_possible += len(keywords)
            total_matches += len(matches)

        analysis["focus_score"] = total_matches / total_possible if total_possible > 0 else 0

        return analysis

    def _analyze_urgency(self, text: str) -> float:
        """緊急度分析"""
        urgency_patterns = [
            r"[！]{2,}",  # 複数感嘆符
            r"急[いぎ]",   # 急ぎ、急いで
            r"今すぐ|直ぐ|すぐに",
            r"[至緊]急"
        ]

        urgency_score = 0.0
        for pattern in urgency_patterns:
            if re.search(pattern, text):
                urgency_score += 0.3

        return min(urgency_score, 1.0)

    def _analyze_formality(self, text: str) -> float:
        """文体の丁寧度分析"""
        formal_patterns = [
            r"です。|ます。|である。",
            r"について|に関して",
            r"検討|分析|調査"
        ]

        casual_patterns = [
            r"[！？。]{2,}",
            r"[wW]+|[笑爆草]",
            r"やばい|すげー|マジ"
        ]

        formal_score = sum(1 for p in formal_patterns if re.search(p, text))
        casual_score = sum(1 for p in casual_patterns if re.search(p, text))

        if formal_score + casual_score == 0:
            return 0.5  # 中性

        return formal_score / (formal_score + casual_score)

    def _analyze_confidence_indicators(self, text: str) -> Dict:
        """確信度指標分析"""

        confidence_patterns = {
            "high": r"確実|間違いなく|絶対|必ず",
            "medium": r"たぶん|多分|おそらく|思う",
            "low": r"かも|かな|よくわからない|迷"
        }

        results = {}
        for level, pattern in confidence_patterns.items():
            results[level] = bool(re.search(pattern, text))

        return results


class IntegratedDecisionEngine:
    """統合意思決定エンジン"""

    def __init__(self):
        self.dimension_weights = {
            "temporal": 0.35,
            "linguistic": 0.30,
            "behavioral": 0.20,
            "situational": 0.15
        }

        self.logger = logging.getLogger(__name__)

    def make_decision(self, context_profile: ContextProfile, sport: str) -> str:
        """統合判断による意図決定"""

        # 時間的文脈の重み
        temporal_score = self._calculate_temporal_score(context_profile.temporal_context)

        # 言語的文脈の重み
        linguistic_score = self._calculate_linguistic_score(context_profile.linguistic_context)

        # 統合スコア計算
        research_score = (
            temporal_score.get("research", 0) * self.dimension_weights["temporal"] +
            linguistic_score.get("research", 0) * self.dimension_weights["linguistic"]
        )

        betting_score = (
            temporal_score.get("betting", 0) * self.dimension_weights["temporal"] +
            linguistic_score.get("betting", 0) * self.dimension_weights["linguistic"]
        )

        urgency_score = linguistic_score.get("urgency", 0)

        # 意図判定
        if betting_score > 0.7 and urgency_score > 0.5:
            return "betting_urgent"
        elif betting_score > 0.6:
            return "betting_focused"
        elif research_score > 0.7:
            return "research_focused"
        elif research_score > betting_score:
            return "research_mild"
        else:
            return "adaptive_hybrid"

    def _calculate_temporal_score(self, temporal_context: Dict) -> Dict:
        """時間的コンテキストスコア計算"""

        scores = {"research": 0.0, "betting": 0.0}

        dominant_context = temporal_context.get("dominant_context", "unknown")
        confidence = temporal_context.get("confidence", 0.0)

        if dominant_context == "research":
            scores["research"] = confidence
        elif dominant_context == "betting":
            scores["betting"] = confidence

        # ハンデ送付タイミング補正
        handicap_analysis = temporal_context.get("handicap_analysis", {})
        if handicap_analysis.get("is_handicap_active", False):
            scores["betting"] += 0.3

        return scores

    def _calculate_linguistic_score(self, linguistic_context: Dict) -> Dict:
        """言語的コンテキストスコア計算"""

        intent_scores = linguistic_context.get("intent_scores", {})

        research_score = max(
            intent_scores.get("research_strong", 0),
            intent_scores.get("research_mild", 0) * 0.7
        )

        betting_score = max(
            intent_scores.get("betting_strong", 0),
            intent_scores.get("betting_mild", 0) * 0.7
        )

        urgency_score = intent_scores.get("urgency_indicators", 0)

        return {
            "research": research_score,
            "betting": betting_score,
            "urgency": urgency_score
        }


class IntelligentPregameSystem:
    """統合インテリジェントプリゲームシステム"""

    def __init__(self, game_manager=None, api_key=None):
        self.temporal_analyzer = TemporalAnalyzer()
        self.linguistic_analyzer = LinguisticAnalyzer()
        self.decision_engine = IntegratedDecisionEngine()
        self.logger = logging.getLogger(__name__)
        self.game_manager = game_manager
        self.api_key = api_key

    async def select_optimal_games_with_auto_fetch(self, request_data: Dict) -> GameSelection:
        """最適ゲーム選択のメイン処理（自動取得版）"""

        try:
            # 1. 多次元コンテキスト分析
            context_profile = self._analyze_context(request_data)

            # 2. 統合意思決定
            intent = self.decision_engine.make_decision(context_profile, request_data.get("sport", ""))

            # 3. 智能的未来試合自動取得
            future_games = await self._auto_fetch_future_games(request_data)

            self.logger.info(f"🧠 Auto-fetched {len(future_games)} future games for intelligent analysis")

            # 4. 意図に応じたゲーム選択
            game_selection = self._select_games_by_intent(intent, request_data, future_games, context_profile)

            self.logger.info(f"Intelligent selection: {intent} -> {len(game_selection.primary_games)} primary games")

            return game_selection

        except Exception as e:
            self.logger.error(f"Intelligent selection with auto-fetch failed: {e}")
            # フォールバック: 空のゲーム選択
            return GameSelection(
                primary_games=[],
                display_mode="fallback",
                explanation="🤖 インテリジェント分析に失敗しました。再度お試しください。",
                confidence_score=0.0
            )

    def select_optimal_games(self, request_data: Dict, available_games: List[Dict]) -> GameSelection:
        """最適ゲーム選択のメイン処理（従来版・下位互換）"""

        try:
            # 1. 多次元コンテキスト分析
            context_profile = self._analyze_context(request_data)

            # 2. 統合意思決定
            intent = self.decision_engine.make_decision(context_profile, request_data.get("sport", ""))

            # 3. 意図に応じたゲーム選択
            game_selection = self._select_games_by_intent(intent, request_data, available_games, context_profile)

            self.logger.info(f"Intelligent selection: {intent} -> {len(game_selection.primary_games)} primary games")

            return game_selection

        except Exception as e:
            self.logger.error(f"Intelligent selection failed: {e}")
            # フォールバック: 全ゲーム返却
            return GameSelection(
                primary_games=available_games,
                display_mode="fallback",
                explanation="自動判定に失敗したため、全試合を表示しています",
                confidence_score=0.0
            )

    def _analyze_context(self, request_data: Dict) -> ContextProfile:
        """統合コンテキスト分析"""

        temporal_context = self.temporal_analyzer.analyze(request_data)
        linguistic_context = self.linguistic_analyzer.analyze(request_data)

        return ContextProfile(
            temporal_context=temporal_context,
            linguistic_context=linguistic_context,
            behavioral_context={},  # 将来拡張
            situational_context={}  # 将来拡張
        )

    def _select_games_by_intent(self, intent: str, request_data: Dict, available_games: List[Dict], context: ContextProfile) -> GameSelection:
        """意図別ゲーム選択"""

        sport = request_data.get("sport", "").lower()

        if intent == "betting_urgent":
            return self._create_betting_urgent_selection(sport, available_games, context)
        elif intent == "betting_focused":
            return self._create_betting_focused_selection(sport, available_games, context)
        elif intent == "research_focused":
            return self._create_research_focused_selection(sport, available_games, context)
        elif intent == "research_mild":
            return self._create_research_mild_selection(sport, available_games, context)
        else:
            return self._create_adaptive_hybrid_selection(sport, available_games, context)

    def _create_betting_urgent_selection(self, sport: str, games: List[Dict], context: ContextProfile) -> GameSelection:
        """緊急ベット向け選択"""

        bettable_games = self._filter_immediately_bettable(sport, games)

        return GameSelection(
            primary_games=bettable_games,
            secondary_games=[],
            display_mode="betting_urgent",
            explanation="🚨 今すぐベット可能な試合のみを表示",
            recommendations=[
                "ハンデ送付タイミングに基づき、即座にベット可能な試合です",
                "オッズの変動が予想されるため、お早めにご検討ください"
            ],
            confidence_score=0.9
        )

    def _create_betting_focused_selection(self, sport: str, games: List[Dict], context: ContextProfile) -> GameSelection:
        """ベット重視選択"""

        bettable_games = self._filter_immediately_bettable(sport, games)
        near_future_games = self._filter_near_future_games(sport, games, bettable_games)

        return GameSelection(
            primary_games=bettable_games,
            secondary_games=near_future_games,
            display_mode="betting_focused",
            explanation="🎯 ベット可能な試合を優先表示",
            recommendations=[
                "現在ベット可能な試合を上部に表示",
                "下部には近日ベット可能になる試合も表示"
            ],
            confidence_score=0.8
        )

    def _create_research_focused_selection(self, sport: str, games: List[Dict], context: ContextProfile) -> GameSelection:
        """研究重視選択"""

        return GameSelection(
            primary_games=games,
            secondary_games=[],
            display_mode="research_focused",
            explanation="📊 研究・分析用に全試合を表示",
            recommendations=[
                "すべての試合データを分析対象として表示",
                "統計分析やトレンド研究にご活用ください"
            ],
            confidence_score=0.8
        )

    def _create_adaptive_hybrid_selection(self, sport: str, games: List[Dict], context: ContextProfile) -> GameSelection:
        """適応的ハイブリッド選択"""

        bettable_games = self._filter_immediately_bettable(sport, games)

        if len(bettable_games) > 0:
            return GameSelection(
                primary_games=bettable_games,
                secondary_games=[g for g in games if g not in bettable_games],
                display_mode="hybrid",
                explanation="⚡ ベット可能試合と分析用試合を分けて表示",
                recommendations=[
                    "上部: 今すぐベット可能",
                    "下部: 研究・将来ベット用"
                ],
                confidence_score=0.6
            )
        else:
            return GameSelection(
                primary_games=games,
                display_mode="research_fallback",
                explanation="📈 現在ベット可能な試合がないため、分析用として全試合を表示",
                confidence_score=0.5
            )

    def _filter_immediately_bettable(self, sport: str, games: List[Dict]) -> List[Dict]:
        """即座にベット可能な試合フィルタ"""

        now = datetime.now()
        patterns = SportTimePatterns.PATTERNS.get(sport, {})
        lead_time = patterns.get("handicap_lead_time", 1.5)

        bettable_games = []

        for game in games:
            # ステータスチェック
            status = game.get("status", "")
            if status != "Not Started":
                continue

            # 時間チェック
            game_datetime = game.get("datetime", "")
            if self._is_within_betting_window(game_datetime, now, sport, lead_time):
                bettable_games.append(game)

        return bettable_games

    def _filter_near_future_games(self, sport: str, all_games: List[Dict], exclude_games: List[Dict]) -> List[Dict]:
        """近未来ベット対象試合フィルタ"""

        exclude_ids = {g.get("id") for g in exclude_games}

        return [
            game for game in all_games
            if (game.get("id") not in exclude_ids and
                game.get("status") == "Not Started")
        ]

    def _is_within_betting_window(self, game_datetime: str, now: datetime, sport: str, lead_time: float) -> bool:
        """ベット窓内判定"""

        if not game_datetime:
            return False

        try:
            # ゲーム開始時刻のパース
            if "T" in game_datetime:
                game_dt_str = game_datetime.split(" ")[0]  # "2025-09-18T18:00:00+09:00 18:00" -> "2025-09-18T18:00:00+09:00"
                game_dt = datetime.fromisoformat(game_dt_str.replace('Z', '+00:00'))
            else:
                return True  # パース失敗時は安全側

            # 現在時刻との比較
            time_until_game = (game_dt - now).total_seconds() / 3600  # 時間単位

            # ベット窓判定
            if sport == "npb":
                # NPB: 1.5時間前から送付、試合開始30分前まで受付
                return lead_time <= time_until_game <= 4.0
            elif sport == "mlb":
                # MLB: ハンデ送付後から試合開始1時間前まで
                return 1.0 <= time_until_game <= 12.0
            elif sport == "soccer":
                # Soccer: 1.5時間前から送付、30分前まで受付
                return 0.5 <= time_until_game <= 3.0
            elif sport == "nba":
                # NBA: 2時間前から送付、1時間前まで受付
                return 1.0 <= time_until_game <= 4.0

            return True

        except Exception:
            return True  # パース失敗時は安全側でTrue

    def _create_research_mild_selection(self, sport: str, games: List[Dict], context: ContextProfile) -> GameSelection:
        """軽度研究向け選択"""

        return GameSelection(
            primary_games=games,
            display_mode="research_mild",
            explanation="📋 情報確認用に全試合を表示",
            recommendations=["試合情報の確認・軽い分析用として表示"],
            confidence_score=0.6
        )

    async def _auto_fetch_future_games(self, request_data: Dict) -> List[Dict]:
        """智能的未来試合自動取得"""

        sport = request_data.get("sport", "").lower()
        now = datetime.now()

        # 時間コンテキストに基づく日付範囲決定
        temporal_context = self.temporal_analyzer.analyze(request_data)
        date_range = self._determine_optimal_date_range(sport, temporal_context, now)

        all_future_games = []

        # 分析モードフラグを取得
        analysis_mode = request_data.get("analysis_mode", False)

        # ゲームマネージャーが設定されている場合は使用
        if self.game_manager:
            all_future_games = await self._fetch_via_game_manager(sport, date_range, analysis_mode)

        # APIキーが設定されている場合は直接API呼び出し
        elif self.api_key:
            all_future_games = await self._fetch_via_direct_api(sport, date_range)

        # デフォルト: 最小限の未来試合検索
        else:
            all_future_games = await self._fetch_minimal_future_games(sport, date_range)

        # プリゲームフィルタリング（"Not Started"のみ）
        future_games = self._filter_future_games_only(all_future_games)

        self.logger.info(f"🎯 Auto-fetched {len(future_games)} future games from {len(all_future_games)} total")

        return future_games

    def _determine_optimal_date_range(self, sport: str, temporal_context: Dict, now: datetime) -> List[datetime]:
        """最適な日付範囲決定"""

        urgency_level = temporal_context.get("handicap_analysis", {}).get("urgency_level", 0.3)

        # 緊急度に基づく検索範囲
        if urgency_level > 0.8:
            # 高緊急度: 今日・明日のみ
            date_range = [now, now + timedelta(days=1)]
        elif urgency_level > 0.5:
            # 中緊急度: 今日から3日間
            date_range = [now + timedelta(days=i) for i in range(3)]
        else:
            # 低緊急度: 今日から7日間
            date_range = [now + timedelta(days=i) for i in range(7)]

        # スポーツ別調整
        if sport == "soccer":
            # サッカー: Champions League等は週中開催が多い
            date_range.extend([now + timedelta(days=i) for i in range(3, 5)])
        elif sport == "mlb":
            # MLB: 時差考慮で翌日まで延長
            date_range.append(now + timedelta(days=1))

        return list(set(date_range))  # 重複除去

    async def _fetch_via_game_manager(self, sport: str, date_range: List[datetime], analysis_mode: bool = False) -> List[Dict]:
        """ゲームマネージャー経由での取得（オッズ込み完全データ）

        Args:
            sport: 競技名
            date_range: 検索日付範囲
            analysis_mode: Trueの場合、分析専用高速モード（オッズ取得を遅延）
        """

        all_games = []

        try:
            for target_date in date_range:
                # 1. 試合データを取得
                games_without_odds = []

                if sport == "soccer":
                    # Champions League等の国際大会を優先取得
                    games = await self.game_manager.get_international_games_realtime(target_date)
                    games_without_odds.extend(games)

                    # ヨーロッパリーグも取得（国内リーグ含む）
                    european_games = await self.game_manager.get_pregame_european_games_realtime(target_date)
                    games_without_odds.extend(european_games)

                    # 全リーグ取得（包括的アプローチ）
                    all_games = await self.game_manager.get_pregame_games_realtime(target_date)
                    games_without_odds.extend(all_games)

                elif sport == "mlb":
                    games = await self.game_manager.get_pregame_mlb_games_realtime(target_date)
                    games_without_odds.extend(games)

                elif sport == "npb":
                    games = await self.game_manager.get_pregame_npb_games_realtime(target_date)
                    games_without_odds.extend(games)

                # 2. 各試合のオッズを取得して完全なデータを作成
                if analysis_mode:
                    # 分析モード: 常にオッズ取得を遅延（超高速）
                    complete_games = await self._enrich_games_with_odds(games_without_odds, limit_odds_fetch=True)
                    self.logger.info(f"🚄 Analysis mode: skipped odds fetch for {len(games_without_odds)} games")
                else:
                    # 通常モード: 従来通りオッズ取得を遅延
                    complete_games = await self._enrich_games_with_odds(games_without_odds, limit_odds_fetch=True)
                all_games.extend(complete_games)

        except Exception as e:
            self.logger.warning(f"Game manager fetch failed: {e}")

        return all_games

    async def _enrich_games_with_odds(self, games: List[Dict], limit_odds_fetch: bool = False) -> List[Dict]:
        """試合データにオッズを追加して完全なデータにする

        Args:
            games: 試合データリスト
            limit_odds_fetch: Trueの場合、オッズ取得を制限してパフォーマンスを向上
        """

        enriched_games = []

        for game in games:
            game_id = game.get("id")

            # ゲームデータをコピー
            complete_game = game.copy()

            # 既にbookmakersがある場合はそのまま
            if complete_game.get("bookmakers"):
                enriched_games.append(complete_game)
                continue

            # limit_odds_fetchが有効な場合、オッズ取得をスキップしてプレースホルダーを設定
            if limit_odds_fetch:
                complete_game["bookmakers"] = []  # プレースホルダー
                complete_game["odds_fetch_deferred"] = True  # 後でオッズ取得可能フラグ
                enriched_games.append(complete_game)
                continue

            # オッズを取得
            if game_id and self.game_manager:
                try:
                    odds_data = await self.game_manager.get_odds_realtime(game_id)
                    if odds_data:
                        bookmakers = odds_data.get("bookmakers", [])
                        complete_game["bookmakers"] = bookmakers
                        self.logger.info(f"✅ Enriched game {game_id} with {len(bookmakers)} bookmakers")
                    else:
                        complete_game["bookmakers"] = []
                        self.logger.warning(f"⚠️ No odds found for game {game_id}")

                except Exception as e:
                    self.logger.warning(f"❌ Failed to fetch odds for game {game_id}: {e}")
                    complete_game["bookmakers"] = []
            else:
                complete_game["bookmakers"] = []

            enriched_games.append(complete_game)

        return enriched_games

    async def fetch_odds_for_game(self, game: Dict) -> Dict:
        """特定の試合のオッズをオンデマンドで取得する

        Args:
            game: 試合データ（bookmakers[]が空またはodds_fetch_deferred=Trueの場合に使用）

        Returns:
            オッズが取得されたゲームデータ
        """
        if not game.get("odds_fetch_deferred", False) and game.get("bookmakers"):
            # 既にオッズが取得済み
            return game

        game_id = game.get("id")
        enriched_game = game.copy()

        if game_id and self.game_manager:
            try:
                self.logger.info(f"🎯 Fetching odds on-demand for game {game_id}")
                odds_data = await self.game_manager.get_odds_realtime(game_id)
                if odds_data:
                    bookmakers = odds_data.get("bookmakers", [])
                    enriched_game["bookmakers"] = bookmakers
                    enriched_game.pop("odds_fetch_deferred", None)  # フラグを削除
                    self.logger.info(f"✅ On-demand enriched game {game_id} with {len(bookmakers)} bookmakers")
                else:
                    enriched_game["bookmakers"] = []
                    self.logger.warning(f"⚠️ No odds found for game {game_id} (on-demand)")

            except Exception as e:
                self.logger.warning(f"❌ Failed to fetch odds on-demand for game {game_id}: {e}")
                enriched_game["bookmakers"] = []
        else:
            enriched_game["bookmakers"] = []

        return enriched_game

    async def _fetch_via_direct_api(self, sport: str, date_range: List[datetime]) -> List[Dict]:
        """直接API呼び出しでの取得"""

        # 必要に応じて実装（現在はスタブ）
        self.logger.info("Direct API fetch not yet implemented")
        return []

    async def _fetch_minimal_future_games(self, sport: str, date_range: List[datetime]) -> List[Dict]:
        """最小限の未来試合検索（フォールバック）"""

        # 外部ゲームマネージャーも設定されていない場合のフォールバック
        self.logger.warning("No game manager or API key configured - returning empty games")
        return []

    def _filter_future_games_only(self, all_games: List[Dict]) -> List[Dict]:
        """未来の試合のみフィルタリング"""

        future_games = []
        now = datetime.now()

        for game in all_games:
            # ステータスチェック
            status = game.get("status", "")
            if status not in ["Not Started", "Scheduled", "Pre-Game", "TBD", "NS"]:
                continue

            # 時間チェック（可能な場合）
            game_datetime_str = game.get("datetime", "")
            if game_datetime_str:
                try:
                    # 簡易パース
                    if "T" in game_datetime_str:
                        game_dt_str = game_datetime_str.split(" ")[0]
                        game_dt = datetime.fromisoformat(game_dt_str.replace('Z', '+00:00'))

                        # 未来の試合のみ
                        if game_dt > now:
                            future_games.append(game)
                    else:
                        # パース失敗時は安全側で含める
                        future_games.append(game)
                except:
                    # パース失敗時は安全側で含める
                    future_games.append(game)
            else:
                # 日時情報がない場合は安全側で含める
                future_games.append(game)

        return future_games