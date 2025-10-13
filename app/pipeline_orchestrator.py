# -*- coding: utf-8 -*-
"""
Pipeline Orchestrator
エンドツーエンドのベッティング分析パイプラインを統合管理
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# ロギングシステムのインポート
from app.logging_system import log_manager


def convert_to_day_crossing_format(iso_datetime_str: str) -> str:
    """
    ISO 8601形式の日時を日跨ぎ表記に変換
    例: "2025-10-06T04:00:00Z" → "10/5 28:00"

    Args:
        iso_datetime_str: ISO 8601形式の日時文字列

    Returns:
        日跨ぎ表記の文字列 (例: "10/5 28:00")
    """
    if not iso_datetime_str:
        return None

    try:
        # ISO 8601形式をパース (UTC)
        dt = datetime.fromisoformat(iso_datetime_str.replace('Z', '+00:00'))

        # 日本時間に変換 (UTC+9)
        jst_dt = dt + timedelta(hours=9)

        # 時間が0~3時の場合、前日の24+時間表記に変換
        if jst_dt.hour < 4:
            # 前日の日付を取得
            prev_day = jst_dt - timedelta(days=1)
            # 24+時間形式
            hour_24plus = 24 + jst_dt.hour
            return f"{prev_day.month}/{prev_day.day} {hour_24plus}:{jst_dt.minute:02d}"
        else:
            # 通常の時間表記
            return f"{jst_dt.month}/{jst_dt.day} {jst_dt.hour}:{jst_dt.minute:02d}"

    except Exception as e:
        logging.warning(f"日時変換エラー: {iso_datetime_str} - {e}")
        return iso_datetime_str


def get_sort_key_from_datetime(iso_datetime_str: str) -> int:
    """
    ISO 8601形式の日時からソート用のキーを生成

    Args:
        iso_datetime_str: ISO 8601形式の日時文字列

    Returns:
        ソート用の整数キー (UNIX timestamp)
    """
    if not iso_datetime_str:
        return 999999999999  # 日時がない場合は最後尾に

    try:
        dt = datetime.fromisoformat(iso_datetime_str.replace('Z', '+00:00'))
        return int(dt.timestamp())
    except Exception as e:
        logging.warning(f"日時ソートキー生成エラー: {iso_datetime_str} - {e}")
        return 999999999999


def create_english_to_japanese_team_dict() -> dict:
    """
    英語→日本語チーム名の逆引き辞書を作成

    Returns:
        dict: 正規化された英語チーム名 → 日本語チーム名の辞書
    """
    from converter.comprehensive_team_translator import ComprehensiveTeamTranslator

    translator = ComprehensiveTeamTranslator()
    reverse_dict = {}

    for jp_name, en_key in translator.team_translation_dict.items():
        # 正規化: 小文字・スペース除去
        normalized = en_key.lower().replace(' ', '')
        reverse_dict[normalized] = jp_name

    return reverse_dict


def translate_team_to_japanese(english_name: str, reverse_dict: dict) -> str:
    """
    英語チーム名を日本語に翻訳

    Args:
        english_name: 英語チーム名（例: "Real Madrid"）
        reverse_dict: 逆引き辞書

    Returns:
        日本語チーム名（例: "レアル・マドリード"）
    """
    if not english_name:
        return english_name

    # 正規化
    normalized = english_name.lower().replace(' ', '')

    # 完全一致
    if normalized in reverse_dict:
        return reverse_dict[normalized]

    # 部分一致（fallback）
    for en_key, jp_name in reverse_dict.items():
        if normalized in en_key or en_key in normalized:
            return jp_name

    # 翻訳できない場合は元の名前を返す
    return english_name


def translate_league_name_to_japanese(api_league_name: str) -> str:
    """
    APIリーグ名を日本語表記に変換

    Args:
        api_league_name: APIから取得したリーグ名（例: "soccer_spain_la_liga"）

    Returns:
        日本語リーグ名（例: "ラ・リーガ"）
    """
    # 包括的なリーグ名翻訳マッピング
    league_translations = {
        # サッカー - ヨーロッパ主要リーグ
        "soccer_spain_la_liga": "ラ・リーガ",
        "soccer_italy_serie_a": "セリエA",
        "soccer_france_ligue_one": "リーグアン",
        "soccer_england_epl": "プレミアリーグ",
        "soccer_germany_bundesliga": "ブンデスリーガ",
        "soccer_netherlands_eredivisie": "エールディビジ",
        "soccer_portugal_primeira_liga": "プリメイラリーガ",
        "soccer_belgium_first_div": "ベルギーリーグ",
        "soccer_scotland_premiership": "スコットランドリーグ",
        "soccer_turkey_super_league": "スュペル・リグ",

        # サッカー - その他ヨーロッパ
        "soccer_austria_bundesliga": "オーストリアリーグ",
        "soccer_switzerland_superleague": "スイスリーグ",
        "soccer_denmark_superliga": "デンマークリーグ",
        "soccer_sweden_allsvenskan": "スウェーデンリーグ",
        "soccer_norway_eliteserien": "ノルウェーリーグ",
        "soccer_russia_premier_league": "ロシアリーグ",
        "soccer_greece_super_league": "ギリシャリーグ",
        "soccer_poland_ekstraklasa": "ポーランドリーグ",
        "soccer_czech_republic_fnl": "チェコリーグ",

        # サッカー - 南米
        "soccer_brazil_campeonato": "ブラジルリーグ",
        "soccer_argentina_primera_division": "アルゼンチンリーグ",
        "soccer_colombia_primera_a": "コロンビアリーグ",
        "soccer_chile_primera_division": "チリリーグ",
        "soccer_uruguay_primera_division": "ウルグアイリーグ",

        # サッカー - 北中米
        "soccer_mexico_ligamx": "リーガMX",
        "soccer_usa_mls": "MLS",

        # サッカー - アジア
        "soccer_japan_j_league": "Jリーグ",
        "soccer_korea_k_league": "Kリーグ",
        "soccer_china_super_league": "中国スーパーリーグ",
        "soccer_australia_aleague": "Aリーグ",

        # サッカー - 国際大会
        "soccer_uefa_champs_league": "チャンピオンズリーグ",
        "soccer_uefa_europa_league": "ヨーロッパリーグ",
        "soccer_uefa_europa_conference_league": "カンファレンスリーグ",
        "soccer_conmebol_copa_libertadores": "コパ・リベルタドーレス",
        "soccer_fifa_world_cup": "ワールドカップ",
        "soccer_uefa_european_championship": "ユーロ",
        "soccer_copa_america": "コパ・アメリカ",

        # 野球 - MLB
        "baseball_mlb": "MLB",
        "americanfootball_mlb": "MLB",

        # 野球 - NPB
        "baseball_japan_npb": "NPB",
        "baseball_npb": "NPB",

        # 野球 - その他
        "baseball_kbo": "KBO",
        "baseball_cpbl": "CPBL",

        # バスケットボール - NBA
        "basketball_nba": "NBA",
        "basketball_nba_preseason": "NBA(プレシーズン)",

        # バスケットボール - その他
        "basketball_euroleague": "ユーロリーグ",
        "basketball_ncaab": "NCAA",
        "basketball_wnba": "WNBA",
        "basketball_nbl": "NBL",
        "basketball_spain_acb": "ACB",

        # アメフト
        "americanfootball_nfl": "NFL",
        "americanfootball_ncaaf": "NCAA(アメフト)",

        # アイスホッケー
        "icehockey_nhl": "NHL",
        "icehockey_sweden_hockey_league": "SHL",
        "icehockey_khl": "KHL",

        # テニス
        "tennis_atp": "ATP",
        "tennis_wta": "WTA",

        # その他
        "rugbyleague_nrl": "NRL",
        "cricket_test_match": "クリケット(テスト)",
        "cricket_odi": "クリケット(ODI)",
        "cricket_t20": "クリケット(T20)",
        "golf_masters": "マスターズ",
        "boxing": "ボクシング",
        "mma_ufc": "UFC",
    }

    # 変換マッピングに存在すれば日本語名を返す
    if api_league_name and api_league_name.lower() in league_translations:
        return league_translations[api_league_name.lower()]

    # 存在しない場合は元の名前を整形して返す
    if api_league_name:
        # アンダースコアを削除して大文字化
        return api_league_name.replace('_', ' ').upper()

    return "不明"


def group_and_sort_games_by_league(games: List[Dict]) -> List[Dict]:
    """
    試合をリーグ別にグルーピングし、各リーグ内で時間順にソート

    Args:
        games: 試合データのリスト

    Returns:
        リーグ別・時間順にソートされた試合データのリスト
    """
    from collections import defaultdict

    # リーグ別にグルーピング
    games_by_league = defaultdict(list)
    for game in games:
        league = game.get('sport', 'Unknown')
        games_by_league[league].append(game)

    # 各リーグ内で時間順にソート
    sorted_games = []
    for league in sorted(games_by_league.keys()):  # リーグ名でソート
        league_games = games_by_league[league]
        # 試合開始時刻でソート (raw dateを使用)
        league_games.sort(key=lambda g: get_sort_key_from_datetime(
            g.get('_raw_game_date')  # 内部的に保持するraw date
        ))
        sorted_games.extend(league_games)

    return sorted_games

# 既存コンポーネントのインポート
from app.nlp_enhanced_parser import EnhancedUniversalParser as EnhancedBettingParser
from app.enhanced_team_mapper import EnhancedTeamMapper
from converter.unified_handicap_converter import jp_to_pinnacle
from converter.ev_evaluator import EVEvaluator
from game_manager.realtime_soccer import RealtimeSoccerGameManager
from game_manager.realtime_theodds_soccer import RealtimeTheOddsSoccerGameManager
from game_manager.realtime_mlb import RealtimeMLBGameManager
from game_manager.realtime_npb import RealtimeNPBGameManager
from game_manager.realtime_theodds_nba import RealtimeTheOddsNBAGameManager
from converter.comprehensive_team_translator import ComprehensiveTeamTranslator
from converter.odds_processor import OddsProcessor
from converter.unified_line_evaluator import UnifiedLineEvaluator
# MockJapaneseBookmaker removed - using original parser output instead

class PipelineStage(Enum):
    """パイプライン段階"""
    PARSING = "parsing"
    API_FETCHING = "api_fetching"
    GAME_MATCHING = "game_matching"
    ODDS_RETRIEVAL = "odds_retrieval"
    EV_CALCULATION = "ev_calculation"
    FINALIZATION = "finalization"

@dataclass
class PipelineResult:
    """パイプライン実行結果"""
    success: bool
    total_time: float
    stages_completed: List[PipelineStage]
    games_processed: List[Dict]
    errors: List[str]
    warnings: List[str]
    statistics: Dict[str, Any]
    overall_confidence: float = 0.0
    total_processing_time: float = 0.0

@dataclass
class StageResult:
    """各段階の実行結果"""
    stage: PipelineStage
    success: bool
    execution_time: float
    input_count: int
    output_count: int
    data: Any
    errors: List[str]
    warnings: List[str]

class GameManagerFactory:
    """
    GameManager Factory - スポーツ別のGameManagerを生成

    統一設計対応版: 既存の呼び出しと完全な後方互換性を保ちつつ、
    統一設定ベースの生成もサポート
    """

    def __init__(self, api_key: str, use_unified: bool = False, theodds_api_key: Optional[str] = None):
        """
        Args:
            api_key: API-Sports APIキー
            use_unified: 統一設計を使用するか（デフォルト: False = 既存動作維持）
            theodds_api_key: The Odds API キー（指定時はThe Odds APIを使用）
        """
        self.api_key = api_key
        self.theodds_api_key = theodds_api_key
        self.use_unified = use_unified
        self.logger = log_manager.main_logger

    def get_manager(self, sport: str):
        """
        スポーツに対応するGameManagerを取得

        既存の呼び出しと完全互換性を保証。
        use_unified=True の場合は統一設計を使用。
        """
        if sport is None:
            self.logger.warning(f"Sport is None - team names not recognized")
            raise ValueError("チーム名を認識できませんでした。正しいチーム名を入力してください。")
        sport_lower = sport.lower()

        # 既存動作を完全維持（デフォルト）
        if sport_lower in ['soccer', 'football']:
            # The Odds APIキーが指定されている場合は The Odds API を使用
            if self.theodds_api_key:
                self.logger.info(f"🌟 Using The Odds API for {sport}")
                return RealtimeTheOddsSoccerGameManager(api_key=self.theodds_api_key)
            else:
                # Soccer は __init__ 内で cache_dir="data/soccer" をハードコードしているため指定不要
                return RealtimeSoccerGameManager(api_key=self.api_key)
        elif sport_lower in ['mlb', 'baseball']:
            return RealtimeMLBGameManager(api_key=self.api_key, cache_dir="data/mlb", enable_retries=False)
        elif sport_lower in ['npb']:
            return RealtimeNPBGameManager(api_key=self.api_key, cache_dir="data/npb")
        elif sport_lower in ['nba', 'basketball']:
            if self.theodds_api_key:
                self.logger.info(f"🌟 Using The Odds API for {sport}")
                return RealtimeTheOddsNBAGameManager(api_key=self.theodds_api_key)
            else:
                self.logger.warning(f"NBA requires The Odds API key")
                raise ValueError("NBA requires The Odds API key")
        else:
            self.logger.warning(f"Unknown sport: {sport}, using Soccer manager as fallback")
            if self.theodds_api_key:
                return RealtimeTheOddsSoccerGameManager(api_key=self.theodds_api_key)
            else:
                return RealtimeSoccerGameManager(api_key=self.api_key)

class BettingPipelineOrchestrator:
    """ベッティング分析パイプラインの統合オーケストレーター"""

    def __init__(self, api_key: str, theodds_api_key: Optional[str] = None):
        self.logger = log_manager.pipeline_logger
        self.api_key = api_key
        self.theodds_api_key = theodds_api_key

        # コンポーネントの初期化
        self.parser = EnhancedBettingParser()
        self.team_mapper = EnhancedTeamMapper()
        self.game_manager_factory = GameManagerFactory(api_key, theodds_api_key=theodds_api_key)
        self.odds_processor = OddsProcessor()
        self.line_evaluator = UnifiedLineEvaluator()
        self.team_translator = ComprehensiveTeamTranslator()
        # MockJapaneseBookmaker removed - using original parser output for jp_line

        # 英語→日本語チーム名翻訳用の逆引き辞書を初期化
        self.en_to_jp_team_dict = create_english_to_japanese_team_dict()

        # 設定
        self.default_sport_hint = "mixed"
        self.match_confidence_threshold = 0.7
        self.enable_ev_calculation = True

    async def execute_pipeline(
        self,
        customer_text: str,
        sport_hint: Optional[str] = None,
        jp_odds: float = 1.9,
        rakeback: float = 0.0
    ) -> PipelineResult:
        """
        完全なパイプラインを実行

        Args:
            customer_text: お客様の貼り付けテキスト
            sport_hint: スポーツヒント
            jp_odds: 日本式オッズ（デフォルト1.9）
            rakeback: レーキバック率（0.0-3.0%）

        Returns:
            PipelineResult: 実行結果
        """
        start_time = time.time()
        stages_completed = []
        all_errors = []
        all_warnings = []

        # EVEvaluatorを初期化
        ev_evaluator = EVEvaluator(jp_odds=jp_odds, rakeback=rakeback)
        statistics = {}

        self.logger.info("🚀 Starting betting analysis pipeline")

        pipeline_context = {
            'input_text_length': len(customer_text),
            'sport_hint': sport_hint,
            'pipeline_version': 'v4.0.0'
        }

        with log_manager.log_performance("Full Pipeline Execution", "pipeline"):

            try:
                # Stage 1: パーシング
                stage1_result = await self._execute_parsing_stage(customer_text, sport_hint)
                stages_completed.append(PipelineStage.PARSING)
                all_errors.extend(stage1_result.errors)
                all_warnings.extend(stage1_result.warnings)
                statistics["parsing"] = {
                    "time": stage1_result.execution_time,
                    "games_found": stage1_result.output_count
                }

                # ログ記録
                log_manager.log_pipeline_stage({
                    'stage_name': 'Parsing',
                    'success': stage1_result.success,
                    'processing_time': stage1_result.execution_time,
                    'input_summary': f"Text length: {len(customer_text)}",
                    'output_summary': f"Games detected: {stage1_result.output_count}",
                    'quality_metrics': {
                        'games_count': stage1_result.output_count,
                        'error_count': len(stage1_result.errors)
                    },
                    'error_message': '; '.join(stage1_result.errors) if stage1_result.errors else None
                })

                if not stage1_result.success or not stage1_result.data:
                    log_manager.log_error("Pipeline Stage 1 failed", Exception("Parsing stage failed"), pipeline_context)
                    return self._create_failed_result(start_time, stages_completed, all_errors, all_warnings, statistics)

                parsed_games = stage1_result.data
                log_manager.main_logger.info(f"🔍 DEBUG Stage1 完了: parsed_games={len(parsed_games)} games")
                for i, game in enumerate(parsed_games):
                    log_manager.main_logger.info(f"🔍 DEBUG Game {i+1}: {game.get('team_a', '?')} vs {game.get('team_b', '?')}")

                # Stage 2: API取得 (スポーツ別)
                log_manager.main_logger.info(f"🚀 About to call Stage2 with {len(parsed_games)} games")
                try:
                    stage2_result = await self._execute_api_fetching_stage(parsed_games)
                except ValueError as ve:
                    # ユーザー入力エラー（チーム名認識失敗など）を上位に伝播
                    raise ve
                log_manager.main_logger.info(f"✅ Stage2 completed successfully")
                log_manager.main_logger.info(f"🔍 DEBUG Stage2 result: success={stage2_result.success}, data_keys={list(stage2_result.data.keys()) if stage2_result.data else 'None'}")
                stages_completed.append(PipelineStage.API_FETCHING)
                all_errors.extend(stage2_result.errors)
                all_warnings.extend(stage2_result.warnings)
                statistics["api_fetching"] = {
                    "time": stage2_result.execution_time,
                    "api_games_found": stage2_result.output_count
                }

                # ログ記録
                log_manager.log_pipeline_stage({
                    'stage_name': 'API_Fetching',
                    'success': stage2_result.success,
                    'processing_time': stage2_result.execution_time,
                    'input_summary': f"Games to fetch: {len(parsed_games)}",
                    'output_summary': f"API games found: {stage2_result.output_count}",
                    'quality_metrics': {
                        'api_games_count': stage2_result.output_count,
                        'error_count': len(stage2_result.errors)
                    },
                    'error_message': '; '.join(stage2_result.errors) if stage2_result.errors else None
                })

                # API取得失敗でも続行（空のデータで進む）
                if not stage2_result.success:
                    log_manager.log_error("Pipeline Stage 2 failed", Exception("API fetching stage failed"), pipeline_context)
                    api_games_by_sport = {}  # 空のAPIゲームデータで続行
                else:
                    api_games_by_sport = stage2_result.data

                # Stage 3: ゲームマッチング
                stage3_result = await self._execute_matching_stage(parsed_games, api_games_by_sport)
                stages_completed.append(PipelineStage.GAME_MATCHING)
                all_errors.extend(stage3_result.errors)
                all_warnings.extend(stage3_result.warnings)
                statistics["matching"] = {
                    "time": stage3_result.execution_time,
                    "matches_found": stage3_result.output_count
                }

                # ログ記録
                log_manager.log_pipeline_stage({
                    'stage_name': 'Game_Matching',
                    'success': stage3_result.success,
                    'processing_time': stage3_result.execution_time,
                    'input_summary': f"Parsed games: {len(parsed_games)}",
                    'output_summary': f"Matches found: {stage3_result.output_count}",
                    'quality_metrics': {
                        'matches_count': stage3_result.output_count,
                        'match_rate': stage3_result.output_count / len(parsed_games) if parsed_games else 0
                    },
                    'error_message': '; '.join(stage3_result.errors) if stage3_result.errors else None
                })

                matched_games = stage3_result.data
                log_manager.main_logger.info(f"🔍 DEBUG Stage3 完了: matched_games={len(matched_games)} games")
                for i, game in enumerate(matched_games):
                    log_manager.main_logger.info(f"🔍 DEBUG Match {i+1}: {game.get('team_a', '?')} vs {game.get('team_b', '?')}, API ID: {game.get('api_game_id', 'None')}")

                # Stage 4: オッズ取得
                stage4_result = await self._execute_odds_retrieval_stage(matched_games, api_games_by_sport)
                stages_completed.append(PipelineStage.ODDS_RETRIEVAL)
                all_errors.extend(stage4_result.errors)
                all_warnings.extend(stage4_result.warnings)
                statistics["odds_retrieval"] = {
                    "time": stage4_result.execution_time,
                    "odds_retrieved": stage4_result.output_count
                }

                # ログ記録
                log_manager.log_pipeline_stage({
                    'stage_name': 'Odds_Retrieval',
                    'success': stage4_result.success,
                    'processing_time': stage4_result.execution_time,
                    'input_summary': f"Matched games: {len(matched_games)}",
                    'output_summary': f"Odds retrieved: {stage4_result.output_count}",
                    'quality_metrics': {
                        'odds_count': stage4_result.output_count,
                        'retrieval_rate': stage4_result.output_count / len(matched_games) if matched_games else 0
                    },
                    'error_message': '; '.join(stage4_result.errors) if stage4_result.errors else None
                })

                games_with_odds = stage4_result.data
                log_manager.main_logger.info(f"🔍 DEBUG Stage4 完了: games_with_odds={len(games_with_odds)} games")
                for i, game in enumerate(games_with_odds):
                    has_odds = bool(game.get('odds_data') or game.get('raw_odds'))
                    log_manager.main_logger.info(f"🔍 DEBUG Odds {i+1}: {game.get('team_a', '?')} vs {game.get('team_b', '?')}, Odds: {has_odds}")

                # Stage 5: EV計算
                stage5_result = await self._execute_ev_calculation_stage(games_with_odds, ev_evaluator, rakeback)
                stages_completed.append(PipelineStage.EV_CALCULATION)
                all_errors.extend(stage5_result.errors)
                all_warnings.extend(stage5_result.warnings)
                statistics["ev_calculation"] = {
                    "time": stage5_result.execution_time,
                    "calculations_done": stage5_result.output_count
                }

                # ログ記録
                log_manager.log_pipeline_stage({
                    'stage_name': 'EV_Calculation',
                    'success': stage5_result.success,
                    'processing_time': stage5_result.execution_time,
                    'input_summary': f"Games with odds: {len(games_with_odds)}",
                    'output_summary': f"EV calculations: {stage5_result.output_count}",
                    'quality_metrics': {
                        'calculations_count': stage5_result.output_count
                    },
                    'error_message': '; '.join(stage5_result.errors) if stage5_result.errors else None
                })

                final_games = stage5_result.data
                log_manager.main_logger.info(f"🔍 DEBUG Stage5 完了: final_games={len(final_games)} games")
                for i, game in enumerate(final_games):
                    log_manager.main_logger.info(f"🔍 DEBUG Final {i+1}: {game.get('team_a', '?')} vs {game.get('team_b', '?')}, EV: {game.get('ev_percentage', 'None')}")

                # Stage 6: 最終処理
                stage6_result = await self._execute_finalization_stage(final_games, api_games_by_sport)
                stages_completed.append(PipelineStage.FINALIZATION)
                statistics["finalization"] = {
                    "time": stage6_result.execution_time,
                    "final_games": stage6_result.output_count
                }

                # ログ記録
                log_manager.log_pipeline_stage({
                    'stage_name': 'Finalization',
                    'success': stage6_result.success,
                    'processing_time': stage6_result.execution_time,
                    'input_summary': f"Final games: {len(final_games)}",
                    'output_summary': f"Processed games: {stage6_result.output_count}",
                    'quality_metrics': {
                        'final_games_count': stage6_result.output_count
                    }
                })

                total_time = time.time() - start_time

                # 最終成功ログ
                log_manager.log_business_event('pipeline_completed', {
                    'games_processed': len(stage6_result.data),
                    'success_rate': len(stages_completed) / 6,
                    'total_time': total_time,
                    'stages_completed': [stage.value for stage in stages_completed]
                })

                self.logger.info(f"✅ Pipeline completed successfully in {total_time:.3f}s")

                log_manager.main_logger.info(f"🔍 DEBUG Stage6 完了: games_processed={len(stage6_result.data)} games")
                for i, game in enumerate(stage6_result.data):
                    log_manager.main_logger.info(f"🔍 DEBUG Processed {i+1}: {game.get('team_a', '?')} vs {game.get('team_b', '?')}")

                # 信頼度を計算
                confidence = self._calculate_overall_confidence(stage6_result.data, stages_completed, all_errors, all_warnings)

                return PipelineResult(
                    success=True,
                    total_time=total_time,
                    stages_completed=stages_completed,
                    games_processed=stage6_result.data,
                    errors=all_errors,
                    warnings=all_warnings,
                    statistics=statistics,
                    overall_confidence=confidence,
                    total_processing_time=total_time
                )

            except ValueError as ve:
                # ユーザー入力エラーは再raise（APIエンドポイントでHTTP 400として処理される）
                log_manager.main_logger.warning(f"⚠️ User input error in pipeline: {str(ve)}")
                raise ve
            except Exception as e:
                log_manager.main_logger.error(f"💥 EXCEPTION CAUGHT: {type(e).__name__}: {str(e)}")
                log_manager.log_error("Pipeline execution failed", e, pipeline_context)
                self.logger.error(f"❌ Pipeline failed with exception: {e}")
                all_errors.append(f"Pipeline exception: {str(e)}")
                return self._create_failed_result(start_time, stages_completed, all_errors, all_warnings, statistics)

    async def _execute_parsing_stage(self, customer_text: str, sport_hint: Optional[str]) -> StageResult:
        """Stage 1: パーシング段階"""
        stage_start = time.time()
        errors = []
        warnings = []

        try:
            self.logger.info("🔍 Executing parsing stage")
            self.logger.info(f"🔍 DEBUG: customer_text length={len(customer_text)}, sport_hint={sport_hint}")
            self.logger.info(f"🔍 DEBUG: parser type={type(self.parser)}")

            # Enhanced Parser で解析
            parse_result = self.parser.parse_detailed(customer_text)

            self.logger.info(f"🔍 DEBUG: parse_result type={type(parse_result)}")
            if parse_result is None:
                self.logger.error("🚨 parse_with_confidence returned None!")
                errors.append("Parser returned None result")
                return StageResult(
                    stage=PipelineStage.PARSING,
                    success=False,
                    execution_time=time.time() - stage_start,
                    input_count=1,
                    output_count=0,
                    data=[],
                    errors=errors,
                    warnings=warnings
                )

            self.logger.info(f"🔍 DEBUG: parse_result.games length={len(parse_result.games) if hasattr(parse_result, 'games') else 'NO GAMES ATTR'}")

            if not parse_result.games:
                errors.append("No games found in customer text")
                return StageResult(
                    stage=PipelineStage.PARSING,
                    success=False,
                    execution_time=time.time() - stage_start,
                    input_count=1,
                    output_count=0,
                    data=[],
                    errors=errors,
                    warnings=warnings
                )

            self.logger.info(f"✅ Parsing completed: {len(parse_result.games)} games found")

            return StageResult(
                stage=PipelineStage.PARSING,
                success=True,
                execution_time=time.time() - stage_start,
                input_count=1,
                output_count=len(parse_result.games),
                data=parse_result.games,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.error(f"💥 PARSING STAGE EXCEPTION: {type(e).__name__}: {str(e)}")
            import traceback
            self.logger.error(f"💥 TRACEBACK: {traceback.format_exc()}")
            errors.append(f"Parsing stage failed: {str(e)}")
            return StageResult(
                stage=PipelineStage.PARSING,
                success=False,
                execution_time=time.time() - stage_start,
                input_count=1,
                output_count=0,
                data=[],
                errors=errors,
                warnings=warnings
            )

    async def _execute_api_fetching_stage(self, parsed_games: List[Dict]) -> StageResult:
        """Stage 2: API取得段階"""
        stage_start = time.time()
        errors = []
        warnings = []

        try:
            log_manager.main_logger.info(f"🌐 Executing API fetching stage with {len(parsed_games)} games")
            self.logger.info("🌐 Executing API fetching stage")

            # スポーツ別にゲームをグループ化（sportフィールドも更新）
            games_by_sport = {}
            for game in parsed_games:
                sport = game.get('sport', 'mixed')
                log_manager.main_logger.info(f"🔍 GAME DEBUG: {game.get('team_a', '?')} vs {game.get('team_b', '?')} has sport='{sport}'")

                # 'mixed'の場合は実際のスポーツを推定
                if sport == 'mixed' or sport == 'unknown':
                    # 日本の野球チーム（NPB）とNBAチームを素早く特定
                    team_a = game.get('team_a', '')
                    team_b = game.get('team_b', '')
                    # NPB teams - both Japanese and English names
                    npb_teams_jp = ['西武', 'ロッテ', '巨人', '阪神', '中日', '広島', 'ヤクルト', '横浜', 'オリックス', 'ソフトバンク', '楽天', '日本ハム']
                    npb_teams_en = ['lions', 'marines', 'giants', 'tigers', 'dragons', 'carp', 'swallows', 'baystars', 'buffaloes', 'hawks', 'eagles', 'fighters']
                    nba_teams_jp = ['レイカーズ', 'ウォリアーズ', 'セルティックス', 'ヒート', 'ネッツ', 'バックス', 'サンズ', 'ナゲッツ', 'クリッパーズ', 'マーベリックス']
                    nba_teams_en = ['lakers', 'warriors', 'celtics', 'heat', 'nets', 'bucks', 'suns', 'nuggets', 'clippers', 'mavericks', 'knicks', 'raptors']

                    # Check NPB first (Japanese and English)
                    if any(jp_team in team_a or jp_team in team_b for jp_team in npb_teams_jp) or \
                       any(en_team in team_a.lower() or en_team in team_b.lower() for en_team in npb_teams_en):
                        detected_sport = 'npb'
                        sport = detected_sport
                        game['sport'] = sport
                        log_manager.main_logger.info(f"🏟️ NPB DETECTION: {game.get('team_a', '?')} vs {game.get('team_b', '?')} -> NPB")
                    elif any(nba_team in team_a or nba_team in team_b for nba_team in nba_teams_jp) or \
                         any(nba_team in team_a.lower() or nba_team in team_b.lower() for nba_team in nba_teams_en):
                        detected_sport = 'nba'
                        sport = detected_sport
                        game['sport'] = sport
                        log_manager.main_logger.info(f"🏀 NBA DETECTION: {game.get('team_a', '?')} vs {game.get('team_b', '?')} -> NBA")
                    else:
                        # より高度な検出が必要な場合のみAPI呼び出し
                        try:
                            # 同期関数なのでタイムアウトなしで実行（最適化済み）
                            detection_result = self._detect_sport_with_api_match(game)
                            detected_sport = detection_result.get('sport', 'soccer')
                            matched_game = detection_result.get('matched_game')

                            log_manager.main_logger.info(f"🔍 SPORT DETECTION: {game.get('team_a', '?')} vs {game.get('team_b', '?')} -> '{detected_sport}'")
                            sport = detected_sport
                            game['sport'] = sport

                            # APIマッチング結果がある場合は保存
                            if matched_game:
                                game['_api_matched_game'] = matched_game
                                log_manager.main_logger.info(f"💾 API match saved: {matched_game.get('home')} vs {matched_game.get('away')}")
                        except Exception as e:
                            log_manager.main_logger.warning(f"⚠️ Sport detection error: {e}")
                            sport = 'soccer'  # デフォルトフォールバック
                            game['sport'] = sport

                if sport not in games_by_sport:
                    games_by_sport[sport] = []
                games_by_sport[sport].append(game)

            api_games_by_sport = {}
            total_api_games = 0

            # スポーツ別にAPIからゲームを取得
            for sport, games in games_by_sport.items():
                try:
                    game_manager = self.game_manager_factory.get_manager(sport)

                    # 今日と明日の試合を取得 (スポーツ検出と同期)
                    today = datetime.now()
                    tomorrow = today + timedelta(days=1)

                    # 両日のゲームを取得（タイムアウト処理付き）
                    try:
                        games_today = await asyncio.wait_for(
                            game_manager.get_games_realtime(today),
                            timeout=15.0  # 15秒でタイムアウト
                        )
                        games_tomorrow = await asyncio.wait_for(
                            game_manager.get_games_realtime(tomorrow),
                            timeout=15.0  # 15秒でタイムアウト
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning(f"⏰ API timeout for {sport} games - using empty list")
                        games_today = []
                        games_tomorrow = []
                    api_games = games_today + games_tomorrow

                    # PregameFilterを適用（未来の試合のみ）
                    from game_manager.pregame_filter import PregameFilter
                    log_manager.main_logger.info(f"🔍 DEBUG BEFORE FILTER: {sport} has {len(api_games)} games")
                    pregame_games = PregameFilter.filter_pregame_games(api_games, buffer_minutes=0)
                    filtered_count = len(api_games) - len(pregame_games)
                    log_manager.main_logger.info(f"🔍 DEBUG AFTER FILTER: {sport} has {len(pregame_games)} games, filtered {filtered_count}")
                    if filtered_count > 0:
                        self.logger.info(f"🔍 {sport}: Filtered out {filtered_count} past/live games")

                    api_games_by_sport[sport] = pregame_games
                    total_api_games += len(pregame_games)

                    self.logger.info(f"✅ {sport}: {len(pregame_games)} pregame API games retrieved")
                    log_manager.main_logger.info(f"🌐 API FETCH: {sport} fetched {len(api_games)} games")

                except ValueError as ve:
                    # チーム名認識エラーなど、ユーザーに伝えるべきエラー
                    log_manager.main_logger.error(f"🚨 USER ERROR for {sport}: {str(ve)}")
                    raise ve
                except Exception as e:
                    error_msg = f"Failed to fetch {sport} games: {str(e)}"
                    errors.append(error_msg)
                    warnings.append(f"Continuing without {sport} games")
                    api_games_by_sport[sport] = []
                    log_manager.main_logger.error(f"🚨 API FETCH EXCEPTION for {sport}: {str(e)}")
                    import traceback
                    log_manager.main_logger.error(f"🚨 TRACEBACK: {traceback.format_exc()}")

            return StageResult(
                stage=PipelineStage.API_FETCHING,
                success=len(api_games_by_sport) > 0,
                execution_time=time.time() - stage_start,
                input_count=len(parsed_games),
                output_count=total_api_games,
                data=api_games_by_sport,
                errors=errors,
                warnings=warnings
            )

        except ValueError as ve:
            # ユーザー入力エラーは再raise（上位でHTTP 400として処理される）
            raise ve
        except Exception as e:
            errors.append(f"API fetching stage failed: {str(e)}")
            return StageResult(
                stage=PipelineStage.API_FETCHING,
                success=False,
                execution_time=time.time() - stage_start,
                input_count=len(parsed_games),
                output_count=0,
                data={},
                errors=errors,
                warnings=warnings
            )

    async def _execute_matching_stage(self, parsed_games: List[Dict], api_games_by_sport: Dict[str, List[Dict]]) -> StageResult:
        """Stage 3: ゲームマッチング段階"""
        stage_start = time.time()
        errors = []
        warnings = []
        matched_games = []

        try:
            self.logger.info("🎯 Executing game matching stage")
            log_manager.main_logger.info(f"🎯 MATCHING: Processing {len(parsed_games)} parsed games")
            log_manager.main_logger.info(f"🎯 MATCHING: Available sports in API data: {list(api_games_by_sport.keys())}")

            for game in parsed_games:
                sport = game.get('sport', 'unknown')
                api_games = api_games_by_sport.get(sport, [])

                log_manager.main_logger.info(f"🔍 Processing game: {game.get('team_a', '?')} vs {game.get('team_b', '?')}, sport='{sport}', api_games_count={len(api_games)}")

                # Stage2でAPIマッチング済みの場合は直接使用
                if '_api_matched_game' in game:
                    matched_api_game = game['_api_matched_game']
                    api_home = matched_api_game.get('home', '')
                    api_away = matched_api_game.get('away', '')

                    log_manager.main_logger.info(f"🚀 Using pre-matched API game: {api_home} vs {api_away}")

                    # パーサー出力を保存
                    original_team_a = game.get('team_a', '')
                    original_team_b = game.get('team_b', '')

                    # 事前マッチング成功
                    matched_game = game.copy()
                    matched_game['team_a'] = api_home  # The Odds API公式英語名（内部処理用）
                    matched_game['team_b'] = api_away  # The Odds API公式英語名（内部処理用）
                    matched_game['team_a_original'] = original_team_a  # パーサー出力を保存
                    matched_game['team_b_original'] = original_team_b  # パーサー出力を保存
                    matched_game['api_game_id'] = matched_api_game.get('id')
                    matched_game['api_game_data'] = matched_api_game
                    matched_game['sport'] = matched_api_game.get('sport_key', game.get('sport', 'soccer'))  # sport_keyで更新
                    matched_game['match_confidence'] = 1.0  # APIマッチング済みなので最高信頼度
                    matched_games.append(matched_game)

                    log_manager.main_logger.info(f"✅ Pre-matched: '{original_team_a}' vs '{original_team_b}' -> API: '{api_home}' vs '{api_away}' (ID: {matched_api_game.get('id')})")
                    continue

                # 従来のマッチング処理（APIマッチングがない場合のフォールバック）
                if not api_games:
                    warnings.append(f"No API games available for sport: {sport}")
                    continue

                try:
                    # パーサー出力（日本語/英語混在）を保存
                    original_team_a = game.get('team_a', '')
                    original_team_b = game.get('team_b', '')

                    # 翻訳サービスで英語ヒントを生成
                    team_a_en_hint = self.team_translator.translate_if_needed(original_team_a) if original_team_a else ''
                    team_b_en_hint = self.team_translator.translate_if_needed(original_team_b) if original_team_b else ''

                    log_manager.main_logger.info(f"🔄 Translation: '{original_team_a}' -> '{team_a_en_hint}', '{original_team_b}' -> '{team_b_en_hint}'")

                    game_manager = self.game_manager_factory.get_manager(sport)
                    team_names_en = [team_a_en_hint, team_b_en_hint]

                    # フォールバックマッチング実行（英語ヒントを使用）
                    matched_api_game = game_manager.match_teams(team_names_en, api_games)

                    if matched_api_game:
                        # フォールバックマッチング成功
                        # The Odds APIの公式英語名を採用

                        # DEBUG: APIレスポンスの構造を確認
                        log_manager.main_logger.info(f"🔍 DEBUG matched_api_game keys: {list(matched_api_game.keys())}")
                        log_manager.main_logger.info(f"🔍 DEBUG matched_api_game: {matched_api_game}")

                        # 防御的フィールドアクセス: 複数のフィールド名パターンに対応
                        api_home = (matched_api_game.get('home_team') or
                                   matched_api_game.get('home') or
                                   matched_api_game.get('homeTeam') or '')
                        api_away = (matched_api_game.get('away_team') or
                                   matched_api_game.get('away') or
                                   matched_api_game.get('awayTeam') or '')

                        # 空チーム名検証: 将来的な類似問題の早期検出
                        if not api_home or not api_away:
                            log_manager.main_logger.warning(
                                f"⚠️ API response missing team names for game ID {matched_api_game.get('id')}. "
                                f"Available fields: {list(matched_api_game.keys())}"
                            )
                            warnings.append(f"API team names missing for: {original_team_a} vs {original_team_b}")
                            continue

                        matched_game = game.copy()
                        matched_game['team_a'] = api_home  # The Odds API公式英語名（内部処理用）
                        matched_game['team_b'] = api_away  # The Odds API公式英語名（内部処理用）
                        matched_game['team_a_original'] = original_team_a  # パーサー出力を保存
                        matched_game['team_b_original'] = original_team_b  # パーサー出力を保存
                        matched_game['api_game_id'] = matched_api_game.get('id')
                        matched_game['api_game_data'] = matched_api_game
                        matched_game['sport'] = matched_api_game.get('sport_key', game.get('sport', 'soccer'))  # sport_keyで更新
                        matched_game['match_confidence'] = 0.8  # フォールバック信頼度
                        matched_games.append(matched_game)

                        log_manager.main_logger.info(f"✅ Fallback match: '{original_team_a}' vs '{original_team_b}' -> API: '{api_home}' vs '{api_away}' (ID: {matched_api_game.get('id')})")
                    else:
                        # マッチング失敗
                        warnings.append(f"No match found for: {original_team_a} vs {original_team_b} (en hints: {team_a_en_hint} vs {team_b_en_hint})")
                        log_manager.main_logger.info(f"❌ No match found for: {original_team_a} vs {original_team_b} (en hints: {team_a_en_hint} vs {team_b_en_hint})")

                except Exception as e:
                    error_msg = f"Matching failed for {game.get('team_a', 'N/A')} vs {game.get('team_b', 'N/A')}: {str(e)}"
                    errors.append(error_msg)
                    log_manager.main_logger.error(f"❌ {error_msg}")

            self.logger.info(f"✅ Matching completed: {len(matched_games)}/{len(parsed_games)} games matched")

            return StageResult(
                stage=PipelineStage.GAME_MATCHING,
                success=len(matched_games) > 0,
                execution_time=time.time() - stage_start,
                input_count=len(parsed_games),
                output_count=len(matched_games),
                data=matched_games,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            errors.append(f"Matching stage failed: {str(e)}")
            return StageResult(
                stage=PipelineStage.GAME_MATCHING,
                success=False,
                execution_time=time.time() - stage_start,
                input_count=len(parsed_games),
                output_count=0,
                data=[],
                errors=errors,
                warnings=warnings
            )

    async def _execute_odds_retrieval_stage(self, matched_games: List[Dict], api_games_by_sport: Dict[str, List[Dict]]) -> StageResult:
        """Stage 4: オッズ取得段階"""
        stage_start = time.time()
        errors = []
        warnings = []
        games_with_odds = []

        self.logger.info("🚨🚨🚨 EXECUTING ODDS RETRIEVAL STAGE - NEW CODE LOADED 🚨🚨🚨")

        try:
            self.logger.info("💰 Executing odds retrieval stage")

            for game in matched_games:
                api_game_id = game.get('api_game_id')
                sport = game.get('sport', 'unknown')

                if not api_game_id:
                    warnings.append(f"No API game ID for: {game.get('team_a')} vs {game.get('team_b')}")
                    continue

                try:
                    # GameManagerからオッズを取得
                    game_manager = self.game_manager_factory.get_manager(sport)
                    self.logger.info(f"🎲 PIPELINE: About to call get_odds_realtime for {sport} game {api_game_id}")
                    self.logger.info(f"🎲 PIPELINE: GameManager type: {type(game_manager).__name__}")

                    # Check if manager has the method
                    if not hasattr(game_manager, 'get_odds_realtime'):
                        self.logger.error(f"❌ PIPELINE: GameManager {type(game_manager).__name__} does not have get_odds_realtime method")
                        available_methods = [method for method in dir(game_manager) if not method.startswith('_') and callable(getattr(game_manager, method))]
                        self.logger.error(f"❌ PIPELINE: Available methods: {available_methods}")
                        raise AttributeError(f"GameManager {type(game_manager).__name__} does not have get_odds_realtime method")

                    # Extract _theodds_event from api_game_data if available (for The Odds API)
                    api_game_data = game.get('api_game_data', {})
                    self.logger.info(f"🔍 PIPELINE DEBUG: api_game_data keys = {list(api_game_data.keys()) if api_game_data else 'None'}")
                    theodds_event = api_game_data.get('_theodds_event')
                    self.logger.info(f"🔍 PIPELINE DEBUG: theodds_event = {theodds_event is not None}")

                    # Pass _theodds_event as kwarg so The Odds API can use it
                    kwargs = {'force_refresh': True}
                    if theodds_event:
                        kwargs['_theodds_event'] = theodds_event
                        self.logger.info(f"🎲 PIPELINE: Passing _theodds_event with sport_key={theodds_event.get('sport_key')}")
                    else:
                        self.logger.warning(f"⚠️ PIPELINE: No _theodds_event found for game {api_game_id}")

                    odds_data = await game_manager.get_odds_realtime(api_game_id, **kwargs)
                    self.logger.info(f"🎲 PIPELINE: get_odds_realtime returned {type(odds_data)} with value: {odds_data}")

                    game_with_odds = game.copy()  # 常にゲームを追加

                    if odds_data:
                        self.logger.info(f"🎲 PIPELINE: Processing odds_data with bookmakers: {len(odds_data.get('bookmakers', []))}")

                        # DEBUG: オッズデータの構造を確認
                        import json
                        self.logger.info(f"📊 ODDS DATA STRUCTURE: {json.dumps(odds_data, indent=2, ensure_ascii=False)}")

                        # オッズデータの処理
                        processed_odds = self.odds_processor.extract_team_specific_handicap_odds(
                            odds_data.get('bookmakers', [])
                        )

                        self.logger.info(f"🎲 PIPELINE: Processed odds result: {type(processed_odds)} with {len(processed_odds.get('home_lines', []))} home + {len(processed_odds.get('away_lines', []))} away lines")

                        if processed_odds and (processed_odds.get('home_lines') or processed_odds.get('away_lines')):
                            game_with_odds['odds_data'] = processed_odds
                            game_with_odds['raw_odds'] = odds_data
                            self.logger.info(f"✅ Odds retrieved for: {game.get('team_a')} vs {game.get('team_b')}")
                        else:
                            game_with_odds['error'] = "No handicap odds found"
                            warnings.append(f"No handicap odds found for: {game.get('team_a')} vs {game.get('team_b')}")
                            self.logger.warning(f"⚠️ PIPELINE: No handicap odds found - processed_odds: {processed_odds}")
                    else:
                        game_with_odds['error'] = "No odds data available"
                        warnings.append(f"No odds data returned for game ID: {api_game_id}")
                        self.logger.warning(f"⚠️ PIPELINE: No odds data returned for game ID: {api_game_id}")

                    games_with_odds.append(game_with_odds)

                except Exception as e:
                    error_msg = f"Odds retrieval failed for game ID {api_game_id}: {str(e)}"
                    errors.append(error_msg)

                    # 例外が発生した場合でもゲームを追加
                    game_with_odds = game.copy()
                    game_with_odds['error'] = f"Odds retrieval failed: {str(e)}"
                    games_with_odds.append(game_with_odds)

            self.logger.info(f"✅ Odds retrieval completed: {len(games_with_odds)}/{len(matched_games)} games have odds")

            return StageResult(
                stage=PipelineStage.ODDS_RETRIEVAL,
                success=True,  # 常に成功（ゲームがあれば処理完了とみなす）
                execution_time=time.time() - stage_start,
                input_count=len(matched_games),
                output_count=len(games_with_odds),
                data=games_with_odds,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            errors.append(f"Odds retrieval stage failed: {str(e)}")
            return StageResult(
                stage=PipelineStage.ODDS_RETRIEVAL,
                success=False,
                execution_time=time.time() - stage_start,
                input_count=len(matched_games),
                output_count=0,
                data=[],
                errors=errors,
                warnings=warnings
            )

    async def _execute_ev_calculation_stage(self, games_with_odds: List[Dict], ev_evaluator, rakeback: float) -> StageResult:
        """Stage 5: EV計算段階"""
        stage_start = time.time()
        errors = []
        warnings = []
        games_with_ev = []

        try:
            self.logger.info("🧮 Executing EV calculation stage")

            if not self.enable_ev_calculation:
                self.logger.info("EV calculation disabled, skipping")
                return StageResult(
                    stage=PipelineStage.EV_CALCULATION,
                    success=True,
                    execution_time=time.time() - stage_start,
                    input_count=len(games_with_odds),
                    output_count=len(games_with_odds),
                    data=games_with_odds,
                    errors=errors,
                    warnings=warnings
                )

            for game in games_with_odds:
                try:
                    game_with_ev = game.copy()  # 常にゲームを追加

                    # お客様のハンディキャップを取得
                    customer_handicap = game.get('handicap')
                    if not customer_handicap:
                        game_with_ev['error'] = "No customer handicap"
                        warnings.append(f"No customer handicap for: {game.get('team_a')} vs {game.get('team_b')}")
                        games_with_ev.append(game_with_ev)
                        continue

                    # パーサー出力をそのまま使用（変換不要）
                    self.logger.info(f"🔍 DIRECT HANDICAP: customer_handicap={customer_handicap} (type: {type(customer_handicap)})")
                    try:
                        # Pinnacle API convention: favorites get negative handicaps, underdogs get positive
                        fav_team = game.get('fav_team', '')
                        team_a = game.get('team_a', '')
                        is_favorite = fav_team in team_a

                        if float(customer_handicap) == 0.0:
                            pinnacle_line = 0.0  # No sign change needed for handicap=0
                        else:
                            pinnacle_line = -float(customer_handicap) if is_favorite else float(customer_handicap)

                        self.logger.info(f"🔍 HANDICAP CONVERSION: {customer_handicap} -> {pinnacle_line} (fav={fav_team}, is_fav={is_favorite})")
                    except Exception as e:
                        self.logger.error(f"❌ HANDICAP CONVERSION FAILED: {customer_handicap} - {e}")
                        game_with_ev['error'] = f"Invalid handicap format: {customer_handicap} - {e}"
                        warnings.append(f"Invalid handicap format: {customer_handicap} - {e}")
                        games_with_ev.append(game_with_ev)
                        continue

                    # オッズ取得後にfav_teamを実際のオッズベースで再決定
                    odds_data = game.get('odds_data', {})
                    self.logger.info(f"🔍 ODDS CONVERSION: Converting odds_data for {game.get('team_a')} vs {game.get('team_b')}")
                    self.logger.info(f"🔍 ODDS CONVERSION INPUT: {odds_data}")

                    # 実際のオッズでfav_team再決定
                    home_lines = odds_data.get('home_lines', [])
                    away_lines = odds_data.get('away_lines', [])

                    if home_lines and away_lines:
                        # ハンディキャップ0付近のオッズを取得
                        target_handicaps = [0.0, -0.25, 0.25, -0.5, 0.5]
                        home_base_odds = None
                        away_base_odds = None

                        for handicap in target_handicaps:
                            home_odds_at_line = next((line['odds'] for line in home_lines if line['handicap'] == handicap), None)
                            away_odds_at_line = next((line['odds'] for line in away_lines if line['handicap'] == handicap), None)

                            if home_odds_at_line and away_odds_at_line:
                                home_base_odds = home_odds_at_line
                                away_base_odds = away_odds_at_line
                                break

                        if home_base_odds and away_base_odds:
                            # 低オッズ = favorite
                            if home_base_odds < away_base_odds:
                                actual_fav_team = game.get('home_team_jp', game.get('team_a', ''))
                                self.logger.info(f"🔍 FAV_TEAM CORRECTION: HOME is favorite (odds: {home_base_odds} < {away_base_odds})")
                            else:
                                actual_fav_team = game.get('away_team_jp', game.get('team_b', ''))
                                self.logger.info(f"🔍 FAV_TEAM CORRECTION: AWAY is favorite (odds: {away_base_odds} < {home_base_odds})")

                            # fav_teamを修正
                            original_fav = game.get('fav_team', '')
                            if actual_fav_team:  # 空文字列でない場合のみ更新
                                game['fav_team'] = actual_fav_team
                                self.logger.info(f"🔍 FAV_TEAM UPDATE: '{original_fav}' -> '{actual_fav_team}'")

                    legacy_odds = self.odds_processor.convert_team_specific_to_legacy_format(odds_data)
                    self.logger.info(f"🔍 ODDS CONVERSION OUTPUT: {legacy_odds}")
                    self.logger.info(f"🔍 ODDS CONVERSION TYPE: {type(legacy_odds)}, LENGTH: {len(legacy_odds) if legacy_odds else 0}")

                    if not legacy_odds:
                        # オッズ取得失敗の詳細調査
                        self.logger.error(f"❌ ODDS RETRIEVAL FAILURE for {game.get('team_a')} vs {game.get('team_b')}")
                        self.logger.error(f"❌ Raw odds_data: {odds_data}")
                        self.logger.error(f"❌ Game data: {game}")
                        self.logger.error(f"❌ Game.id: {game.get('id')}")

                        # EV計算をスキップ
                        warnings.append(f"❌ No odds available for EV calculation: {game.get('team_a')} vs {game.get('team_b')}")

                        # EV計算結果を明示的にnullに設定
                        game_with_ev.update({
                            'ev_percentage_fav': None,
                            'verdict_fav': "オッズ取得失敗",
                            'ev_percentage_dog': None,
                            'verdict_dog': "オッズ取得失敗",
                            'odds_source': "failed",
                            'pinnacle_line': pinnacle_line,
                            'legacy_odds': None,
                            'ev_calculated': False
                        })
                        games_with_ev.append(game_with_ev)
                        continue
                    else:
                        game_with_ev['odds_source'] = "real"  # 実際のオッズ使用を記録

                    # 双方向EV計算用のデバッグログ
                    self.logger.info(f"🔍 BIDIRECTIONAL EV CALC: {game.get('team_a')} vs {game.get('team_b')}")
                    self.logger.info(f"🔍 INPUT DATA: pinnacle_line={pinnacle_line}, legacy_odds={legacy_odds}")

                    # パーサーからの情報を使用してフェイバリット側を特定
                    requested_team = game.get('fav_team')  # パーサーから取得したフェイバリットチーム名
                    team_a = game.get('team_a', '')  # パーサーからの team_a
                    team_b = game.get('team_b', '')  # パーサーからの team_b

                    # team_a/team_b とのマッチングでサイド決定（同じ言語での比較）
                    if requested_team == team_a:
                        requested_side = "home"  # team_a は通常 home に配置
                    elif requested_team == team_b:
                        requested_side = "away"  # team_b は通常 away に配置
                    else:
                        self.logger.warning(f"⚠️ TEAM MATCHING FAILED: fav_team='{requested_team}', team_a='{team_a}', team_b='{team_b}'")
                        # フォールバック: team_a をフェイバリットとして仮定
                        requested_side = "home"
                        requested_team = team_a

                    self.logger.info(f"🔍 REQUESTED BET: team={requested_team}, side={requested_side}, line={pinnacle_line}")

                    # ユーザーが指定したチーム・ラインでEV計算
                    self.logger.info(f"🔍 BEFORE EVALUATE: Calling evaluate_simplified_line with legacy_odds={legacy_odds}, pinnacle_line={pinnacle_line}, requested_side={requested_side}")
                    requested_result = ev_evaluator.evaluate_simplified_line(
                        legacy_odds,
                        pinnacle_line,
                        requested_side
                    )
                    self.logger.info(f"🔍 AFTER EVALUATE: returned type={type(requested_result)}, value={requested_result}")
                    self.logger.info(f"🔍 REQUESTED RESULT: {requested_result}")

                    # 対戦相手チームのEV計算
                    # 重要: 両チームとも同じピナクルラインを使用して、同じオッズペアから公正確率を計算
                    opposite_side = "away" if requested_side == "home" else "home"

                    self.logger.info(f"🔍 OPPOSITE BET: side={opposite_side}, line={pinnacle_line} (同じラインを使用)")
                    opposite_result = ev_evaluator.evaluate_simplified_line(
                        legacy_odds,
                        pinnacle_line,
                        opposite_side
                    )
                    self.logger.info(f"🔍 OPPOSITE RESULT: {opposite_result}")

                    # Use original parser output for jp_line (Japanese bookmaker representation)
                    # jp_line: パーサーからの元の値（日本ブックメーカー表記）
                    # pinnacle_line: 符号調整済み（Pinnacle API互換）
                    raw_h = game.get('raw_handicap')
                    if raw_h is not None and raw_h != '':
                        game_with_ev['jp_line'] = raw_h  # ✅ Use raw format like "1.2" or "0半7"
                    else:
                        # フォールバック: handicap値をJP表記に逆変換
                        h_val = game.get('handicap', 0)
                        try:
                            from converter.unified_handicap_converter import pinnacle_to_jp
                            game_with_ev['jp_line'] = pinnacle_to_jp(float(h_val))
                        except:
                            game_with_ev['jp_line'] = str(h_val)
                    game_with_ev['pinnacle_line'] = pinnacle_line  # ✅ Pinnacle API compatible line
                    game_with_ev['jp_odds'] = legacy_odds                            # ✅ Use existing odds
                    game_with_ev['legacy_odds'] = legacy_odds                        # 既存レガシーオッズ
                    game_with_ev['ev_calculated'] = True

                    # デバッグ情報
                    self.logger.info(f"🏟️ LINE SEPARATION - jp_line: {game_with_ev['jp_line']}, pinnacle_line: {pinnacle_line}")
                    self.logger.info(f"💰 ODDS COMPARISON - jp_odds: {legacy_odds}, legacy_odds: {legacy_odds}")

                    # レーキバック込みEV結果を使用（包括的なnullチェックを追加）
                    requested_ev = requested_result.get('ev_pct_rake') if requested_result else None
                    opposite_ev = opposite_result.get('ev_pct_rake') if opposite_result else None
                    requested_verdict = requested_result.get('verdict') if requested_result else None
                    opposite_verdict = opposite_result.get('verdict') if opposite_result else None
                    requested_fair_odds = requested_result.get('fair_odds') if requested_result else None
                    opposite_fair_odds = opposite_result.get('fair_odds') if opposite_result else None
                    requested_raw_odds = requested_result.get('raw_odds') if requested_result else None
                    opposite_raw_odds = opposite_result.get('raw_odds') if opposite_result else None

                    self.logger.info(f"🔍 FINAL VALUES: requested_ev={requested_ev}, opposite_ev={opposite_ev}, requested_verdict={requested_verdict}, opposite_verdict={opposite_verdict}")

                    # リクエストされたチームの結果をメインとして表示
                    game_with_ev['ev_percentage'] = requested_ev if requested_ev is not None else 0.0
                    game_with_ev['ev_percentage_dog'] = opposite_ev if opposite_ev is not None else 0.0
                    game_with_ev['verdict'] = requested_verdict if requested_verdict else 'unknown'
                    game_with_ev['verdict_dog'] = opposite_verdict if opposite_verdict else 'unknown'
                    game_with_ev['fair_odds'] = requested_fair_odds if requested_fair_odds is not None else 0.0
                    game_with_ev['fair_odds_dog'] = opposite_fair_odds if opposite_fair_odds is not None else 0.0
                    game_with_ev['raw_odds_fav'] = requested_raw_odds
                    game_with_ev['raw_odds_dog'] = opposite_raw_odds
                    game_with_ev['rakeback_applied'] = rakeback

                    # 双方向オッズ情報を追加（両チームとも同じピナクルラインを使用）
                    game_with_ev['pinnacle_line_dog'] = pinnacle_line  # 対戦相手も同じPinnacleライン
                    game_with_ev['jp_line_dog'] = legacy_odds  # 日本式オッズ（対戦相手も同じ）

                    # アンダードッグチーム名を特定
                    fav_team = game_with_ev.get('fav_team')
                    team_a = game_with_ev.get('team_a')
                    team_b = game_with_ev.get('team_b')
                    if fav_team == team_a:
                        game_with_ev['underdog_team'] = team_b
                    else:
                        game_with_ev['underdog_team'] = team_a

                    games_with_ev.append(game_with_ev)

                except Exception as e:
                    error_msg = f"EV calculation failed for: {game.get('team_a')} vs {game.get('team_b')}: {str(e)}"
                    errors.append(error_msg)

                    # 例外が発生した場合でもゲームを追加
                    game_with_error = game.copy()
                    game_with_error['error'] = f"EV calculation failed: {str(e)}"
                    games_with_ev.append(game_with_error)

            self.logger.info(f"✅ EV calculation completed: {len(games_with_ev)}/{len(games_with_odds)} games calculated")

            return StageResult(
                stage=PipelineStage.EV_CALCULATION,
                success=True,
                execution_time=time.time() - stage_start,
                input_count=len(games_with_odds),
                output_count=len(games_with_ev),
                data=games_with_ev,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            errors.append(f"EV calculation stage failed: {str(e)}")
            return StageResult(
                stage=PipelineStage.EV_CALCULATION,
                success=False,
                execution_time=time.time() - stage_start,
                input_count=len(games_with_odds),
                output_count=0,
                data=[],
                errors=errors,
                warnings=warnings
            )

    async def _execute_finalization_stage(self, games_with_ev: List[Dict], api_games_by_sport: Dict[str, List[Dict]]) -> StageResult:
        """Stage 6: 最終処理段階 (改修版)"""
        stage_start = time.time()
        errors = []
        warnings = []

        try:
            self.logger.info("📋 Executing finalization stage")
            final_games = []

            api_games_lookup = {game['id']: game for sport_games in api_games_by_sport.values() for game in sport_games}

            for game in games_with_ev:
                # 1. api_game_dataから試合日時を取得し、日跨ぎ表記に変換
                api_game_data = game.get('api_game_data', {})
                game_date = None
                raw_date = None
                if api_game_data:
                    # The Odds API uses 'commence_time', API-SPORTS uses 'datetime'
                    raw_date = api_game_data.get('commence_time') or api_game_data.get('datetime')
                    game_date = convert_to_day_crossing_format(raw_date)

                # 2. ホーム・アウェイチームを特定（英語名→日本語翻訳）
                # Stage 3で team_a/team_b は既に The Odds API公式英語名に更新済み
                home_team_en = game.get('api_game_data', {}).get('home', game.get('team_a', ''))
                away_team_en = game.get('api_game_data', {}).get('away', game.get('team_b', ''))

                log_manager.main_logger.info(f"🌐 Stage6 Translation: EN='{home_team_en}' vs '{away_team_en}'")

                home_team_parsed = translate_team_to_japanese(home_team_en, self.en_to_jp_team_dict)
                away_team_parsed = translate_team_to_japanese(away_team_en, self.en_to_jp_team_dict)

                log_manager.main_logger.info(f"🇯🇵 Stage6 Result: JP='{home_team_parsed}' vs '{away_team_parsed}'")
                
                # 3. ホーム・アウェイそれぞれに結果を割り当て
                is_home_fav = game.get('fav_team') == home_team_parsed
                home_team_result = {
                    "raw_pinnacle_odds": game.get('raw_odds_fav') if is_home_fav else game.get('raw_odds_dog'),
                    "fair_odds": game.get('fair_odds') if is_home_fav else game.get('fair_odds_dog'),
                    "ev_percentage": game.get('ev_percentage') if is_home_fav else game.get('ev_percentage_dog'),
                    "verdict": game.get('verdict') if is_home_fav else game.get('verdict_dog'),
                }
                away_team_result = {
                    "raw_pinnacle_odds": game.get('raw_odds_dog') if is_home_fav else game.get('raw_odds_fav'),
                    "fair_odds": game.get('fair_odds_dog') if is_home_fav else game.get('fair_odds'),
                    "ev_percentage": game.get('ev_percentage_dog') if is_home_fav else game.get('ev_percentage'),
                    "verdict": game.get('verdict_dog') if is_home_fav else game.get('verdict'),
                }

                # リーグ名を日本語に変換
                sport_api_name = game.get('sport')
                # STAGE3で更新されなかった場合のフォールバック
                if sport_api_name in ['soccer', 'baseball', 'basketball']:  # 汎用名の場合
                    api_game_data = game.get('api_game_data', {})
                    sport_api_name = api_game_data.get('sport_key', sport_api_name)
                sport_jp_name = translate_league_name_to_japanese(sport_api_name)

                final_game = {
                    "game_date": game_date,
                    "_raw_game_date": raw_date,  # ソート用に保持
                    "sport": sport_api_name,  # API形式のリーグ名
                    "sport_jp": sport_jp_name,  # 日本語リーグ名
                    "home_team_jp": home_team_parsed,
                    "away_team_jp": away_team_parsed,
                    "match_confidence": game.get('match_confidence'),
                    "jp_line": game.get('jp_line', str(game.get('handicap', '0'))),
                    "pinnacle_line": game.get('pinnacle_line'),
                    "fav_team": game.get('fav_team'),
                    "home_team_odds": home_team_result,
                    "away_team_odds": away_team_result,
                    "raw_odds": game.get('raw_odds'),  # Stage 4からのオッズデータを保持
                    "odds_data": game.get('odds_data'),  # Stage 4からの処理済みオッズデータを保持
                    "error": game.get("error"),
                }
                final_games.append(final_game)

            # リーグ別にグルーピング & 時間順にソート
            final_games = group_and_sort_games_by_league(final_games)

            # ソート用の内部フィールドを削除
            for game in final_games:
                game.pop('_raw_game_date', None)

            self.logger.info(f"✅ Finalization completed: {len(final_games)} games finalized")

            return StageResult(
                stage=PipelineStage.FINALIZATION,
                success=True,
                execution_time=time.time() - stage_start,
                input_count=len(games_with_ev),
                output_count=len(final_games),
                data=final_games,
                errors=errors,
                warnings=warnings
            )

        except Exception as e:
            self.logger.error(f"💥 FINALIZATION STAGE EXCEPTION: {type(e).__name__}: {str(e)}")
            import traceback
            self.logger.error(f"💥 TRACEBACK: {traceback.format_exc()}")
            errors.append(f"Finalization stage failed: {str(e)}")
            return StageResult(
                stage=PipelineStage.FINALIZATION,
                success=False,
                execution_time=time.time() - stage_start,
                input_count=len(games_with_ev),
                output_count=0,
                data=[],
                errors=errors,
                warnings=warnings
            )

    def _create_failed_result(self, start_time: float, stages_completed: List[PipelineStage],
                            errors: List[str], warnings: List[str], statistics: Dict[str, Any]) -> PipelineResult:
        """失敗結果を作成"""
        return PipelineResult(
            success=False,
            total_time=time.time() - start_time,
            stages_completed=stages_completed,
            games_processed=[],
            errors=errors,
            warnings=warnings,
            statistics=statistics,
            overall_confidence=0.0,
            total_processing_time=time.time() - start_time
        )

    def _calculate_overall_confidence(self, games: List[Dict], stages_completed: List[PipelineStage],
                                     errors: List[str], warnings: List[str]) -> float:
        """全体の信頼度を計算（0.0-1.0）"""
        if not games:
            return 0.0

        # 基本信頼度: 完了した段階の割合
        total_stages = len(PipelineStage)
        stages_score = len(stages_completed) / total_stages

        # エラー・警告による減点
        error_penalty = min(len(errors) * 0.1, 0.5)  # エラー数×10%、最大50%減点
        warning_penalty = min(len(warnings) * 0.05, 0.2)  # 警告数×5%、最大20%減点

        # ゲーム処理状況による調整
        games_with_ev = sum(1 for game in games if game.get('ev_percentage') is not None)
        games_with_odds = sum(1 for game in games if game.get('pinnacle_odds') or game.get('fair_odds'))
        games_with_matches = sum(1 for game in games if game.get('api_game_id'))

        game_quality_score = 0.0
        if games:
            match_ratio = games_with_matches / len(games)
            odds_ratio = games_with_odds / len(games) if games_with_matches > 0 else 0
            ev_ratio = games_with_ev / len(games) if games_with_odds > 0 else 0

            game_quality_score = (match_ratio * 0.4 + odds_ratio * 0.3 + ev_ratio * 0.3)

        # 最終信頼度計算
        final_confidence = (stages_score * 0.5 + game_quality_score * 0.5) - error_penalty - warning_penalty
        return max(0.0, min(1.0, final_confidence))

    def _detect_sport_with_api_match(self, game: Dict) -> Dict:
        """階層型フォールバック戦略によるスポーツ検出（完全自動化）"""
        team_a = game.get('team_a', '').lower()
        team_b = game.get('team_b', '').lower()
        team_a_jp = game.get('team_a_original', game.get('team_a', ''))
        team_b_jp = game.get('team_b_original', game.get('team_b', ''))

        log_manager.main_logger.info(f"🔍 COMPREHENSIVE SPORT DETECTION: '{team_a}' vs '{team_b}'")
        log_manager.main_logger.info(f"🔤 Original names: '{team_a_jp}' vs '{team_b_jp}'")

        # === LEVEL 1: Enhanced Team Mapper データベース検索 ===
        try:
            from app.enhanced_team_mapper import EnhancedTeamMapper
            mapper = EnhancedTeamMapper()

            # チーム名のマッピング結果を取得
            result_a = mapper.map_team_name(team_a_jp, sport_hint=None)
            result_b = mapper.map_team_name(team_b_jp, sport_hint=None)

            log_manager.main_logger.info(f"🔍 LEVEL 1 - Database Mapping:")
            log_manager.main_logger.info(f"  {team_a_jp} → {result_a.mapped_name} (confidence: {result_a.confidence}, method: {result_a.method})")
            log_manager.main_logger.info(f"  {team_b_jp} → {result_b.mapped_name} (confidence: {result_b.confidence}, method: {result_b.method})")

            # データベースから直接スポーツを推定
            sport_detected = self._detect_sport_from_mapping_results(result_a, result_b)
            if sport_detected != 'unknown':
                log_manager.main_logger.info(f"✅ LEVEL 1 SUCCESS: Sport detected as '{sport_detected}' from database")
                return {'sport': sport_detected, 'detection_method': 'database_mapping', 'confidence': min(result_a.confidence, result_b.confidence)}

        except Exception as e:
            log_manager.main_logger.warning(f"⚠️ LEVEL 1 FAILED: Database mapping error: {str(e)}")

        # === LEVEL 2: API並行検索システム ===
        try:
            from datetime import datetime
            today = datetime.now()
            tomorrow = today + timedelta(days=1)

            log_manager.main_logger.info(f"🔍 LEVEL 2 - API Parallel Search")

            # チーム名の正規化
            def normalize_name(name: str) -> str:
                return name.lower().replace(' ', '').replace('.', '').replace('-', '').replace('_', '')

            # 全ての候補チーム名を準備
            team_candidates = [
                team_a, team_b, team_a_jp, team_b_jp,
                self.team_translator.translate_if_needed(team_a_jp, 'mlb'),
                self.team_translator.translate_if_needed(team_b_jp, 'mlb'),
                self.team_translator.translate_if_needed(team_a_jp, 'soccer'),
                self.team_translator.translate_if_needed(team_b_jp, 'soccer'),
                self.team_translator.translate_if_needed(team_a_jp),
                self.team_translator.translate_if_needed(team_b_jp)
            ]

            normalized_input_teams = {normalize_name(t) for t in team_candidates if t}
            log_manager.main_logger.info(f"  Normalized candidates: {list(normalized_input_teams)}")

            # API並行検索の実行
            api_result = self._parallel_api_search(normalized_input_teams, today, tomorrow)
            if api_result['sport'] != 'unknown':
                log_manager.main_logger.info(f"✅ LEVEL 2 SUCCESS: Sport detected as '{api_result['sport']}' via {api_result['source']} API")
                return api_result

        except Exception as e:
            log_manager.main_logger.warning(f"⚠️ LEVEL 2 FAILED: API search error: {str(e)}")

        # === LEVEL 3: 機械学習ベースの推論 ===
        try:
            log_manager.main_logger.info(f"🔍 LEVEL 3 - ML-based Classification")
            ml_result = self._ml_sport_classification(team_a, team_b, team_a_jp, team_b_jp)
            if ml_result != 'unknown':
                log_manager.main_logger.info(f"✅ LEVEL 3 SUCCESS: Sport detected as '{ml_result}' via machine learning")
                return {'sport': ml_result, 'detection_method': 'machine_learning', 'confidence': 0.7}

        except Exception as e:
            log_manager.main_logger.warning(f"⚠️ LEVEL 3 FAILED: ML classification error: {str(e)}")

        # === LEVEL 4: 学習機能付きフォールバック ===
        try:
            log_manager.main_logger.info(f"🔍 LEVEL 4 - Learning Fallback")
            fallback_result = self._learning_fallback(team_a, team_b, team_a_jp, team_b_jp)
            if fallback_result != 'unknown':
                log_manager.main_logger.info(f"✅ LEVEL 4 SUCCESS: Sport detected as '{fallback_result}' via learning fallback")
                return {'sport': fallback_result, 'detection_method': 'learning_fallback', 'confidence': 0.6}

        except Exception as e:
            log_manager.main_logger.warning(f"⚠️ LEVEL 4 FAILED: Learning fallback error: {str(e)}")

        # === LEVEL 5: 最終フォールバック（全API総当たり） ===
        log_manager.main_logger.warning(f"⚠️ LEVEL 5 - Final Fallback: Using mixed sport with full API search")
        return {'sport': 'mixed', 'detection_method': 'final_fallback', 'confidence': 0.1}

    def _detect_sport_from_mapping_results(self, result_a, result_b) -> str:
        """Enhanced Team Mapperの結果からスポーツを推定"""
        try:
            # スポーツ特有のキーワードでスポーツを判定
            all_names = f"{result_a.mapped_name} {result_b.mapped_name}".lower()

            # MLBキーワード
            mlb_keywords = ['yankees', 'red sox', 'athletics', 'royals', 'astros', 'angels', 'dodgers', 'giants', 'mets', 'cubs']
            if any(keyword in all_names for keyword in mlb_keywords):
                return 'mlb'

            # NPBキーワード
            npb_keywords = ['giants', 'tigers', 'dragons', 'baystars', 'carp', 'swallows', 'hawks', 'fighters', 'lions', 'marines', 'eagles', 'buffaloes']
            japanese_context = any(ord(c) >= 0x3040 for c in f"{result_a.original_name} {result_b.original_name}")
            if japanese_context and any(keyword in all_names for keyword in npb_keywords):
                return 'npb'

            # Soccerキーワード
            soccer_keywords = ['fc', 'united', 'city', 'arsenal', 'chelsea', 'liverpool', 'barcelona', 'madrid', 'bayern', 'juventus']
            if any(keyword in all_names for keyword in soccer_keywords):
                return 'soccer'

            return 'unknown'

        except Exception as e:
            log_manager.main_logger.error(f"Error in mapping sport detection: {e}")
            return 'unknown'

    def _parallel_api_search(self, normalized_teams, today, tomorrow) -> Dict:
        """API並行検索システム"""
        try:
            # NPB検索
            try:
                from game_manager.npb import NPBGameManager
                npb_manager = NPBGameManager(self.api_key)
                npb_games = npb_manager.fetch_games(today) + npb_manager.fetch_games(tomorrow)

                for game in npb_games:
                    home = game.get('home', '').lower().replace(' ', '').replace('.', '').replace('-', '')
                    away = game.get('away', '').lower().replace(' ', '').replace('.', '').replace('-', '')
                    if home in normalized_teams or away in normalized_teams:
                        return {'sport': 'npb', 'source': 'NPB', 'matched_game': game, 'detection_method': 'api_search', 'confidence': 0.95}
            except Exception as e:
                log_manager.main_logger.warning(f"NPB API search failed: {e}")

            # MLB検索
            try:
                from game_manager.mlb import MLBGameManager
                mlb_manager = MLBGameManager(self.api_key)
                mlb_games = mlb_manager.fetch_games(today) + mlb_manager.fetch_games(tomorrow)

                for game in mlb_games:
                    home = game.get('home', '').lower().replace(' ', '').replace('.', '').replace('-', '')
                    away = game.get('away', '').lower().replace(' ', '').replace('.', '').replace('-', '')
                    if home in normalized_teams or away in normalized_teams:
                        return {'sport': 'mlb', 'source': 'MLB', 'matched_game': game, 'detection_method': 'api_search', 'confidence': 0.95}
            except Exception as e:
                log_manager.main_logger.warning(f"MLB API search failed: {e}")

            # Soccer検索
            try:
                from game_manager.soccer import SoccerGameManager
                soccer_manager = SoccerGameManager(self.api_key)
                soccer_games = soccer_manager.fetch_games(today) + soccer_manager.fetch_games(tomorrow)

                for game in soccer_games:
                    home = game.get('home', '').lower().replace(' ', '').replace('.', '').replace('-', '')
                    away = game.get('away', '').lower().replace(' ', '').replace('.', '').replace('-', '')
                    if home in normalized_teams or away in normalized_teams:
                        return {'sport': 'soccer', 'source': 'Soccer', 'matched_game': game, 'detection_method': 'api_search', 'confidence': 0.95}
            except Exception as e:
                log_manager.main_logger.warning(f"Soccer API search failed: {e}")

            return {'sport': 'unknown'}

        except Exception as e:
            log_manager.main_logger.error(f"Parallel API search failed: {e}")
            return {'sport': 'unknown'}

    def _ml_sport_classification(self, team_a, team_b, team_a_jp, team_b_jp) -> str:
        """機械学習ベースのスポーツ分類"""
        try:
            # 簡易的な特徴量ベース分類
            all_text = f"{team_a} {team_b} {team_a_jp} {team_b_jp}".lower()

            # 文字特徴量
            has_japanese = any(ord(c) >= 0x3040 for c in all_text)
            has_city_names = any(city in all_text for city in ['new york', 'los angeles', 'boston', 'chicago', 'seattle', 'oakland', 'kansas city'])
            has_soccer_terms = any(term in all_text for term in ['fc', 'united', 'city', 'arsenal', 'chelsea', 'liverpool'])
            has_baseball_terms = any(term in all_text for term in ['yankees', 'red sox', 'athletics', 'royals', 'astros', 'angels'])

            # ルールベース分類
            if has_baseball_terms or (has_city_names and not has_soccer_terms):
                return 'mlb'
            elif has_japanese and not has_city_names:
                return 'npb'
            elif has_soccer_terms:
                return 'soccer'

            return 'unknown'

        except Exception as e:
            log_manager.main_logger.error(f"ML classification failed: {e}")
            return 'unknown'

    def _learning_fallback(self, team_a, team_b, team_a_jp, team_b_jp) -> str:
        """学習機能付きフォールバック"""
        try:
            # チーム名パターンの学習
            all_names = [team_a, team_b, team_a_jp, team_b_jp]

            # アメリカ系チーム名パターン（MLB）
            american_patterns = ['new ', 'los ', 'san ', 'chicago', 'boston', 'seattle', 'oakland', 'kansas', 'yankees', 'athletics', 'royals']
            if any(pattern in name.lower() for name in all_names for pattern in american_patterns):
                log_manager.main_logger.info(f"✅ LEVEL 4 SUCCESS: Detected MLB via American patterns")
                return 'mlb'

            # 日本系チーム名パターン（NPB）
            japanese_patterns = ['ジャイアンツ', 'タイガース', 'ドラゴンズ', 'ベイスターズ', 'カープ', 'スワローズ', 'ホークス', 'ファイターズ', 'ライオンズ', 'マリーンズ', 'イーグルス', 'バファローズ',
                               '巨人', '阪神', '中日', 'DeNA', '広島', 'ヤクルト', 'ソフトバンク', '日本ハム', '西武', 'ロッテ', '楽天', 'オリックス']
            if any(pattern in name for name in all_names for pattern in japanese_patterns):
                log_manager.main_logger.info(f"✅ LEVEL 4 SUCCESS: Detected NPB via Japanese patterns")
                return 'npb'

            # ヨーロッパ系チーム名パターン（Soccer）
            european_patterns = ['manchester', 'liverpool', 'arsenal', 'chelsea', 'barcelona', 'madrid', 'bayern', 'juventus', 'united', 'city', 'fc']
            if any(pattern in name.lower() for name in all_names for pattern in european_patterns):
                log_manager.main_logger.info(f"✅ LEVEL 4 SUCCESS: Detected Soccer via European patterns")
                return 'soccer'

            # NBAチーム名パターン（NBA）
            nba_patterns_jp = ['レイカーズ', 'ウォリアーズ', 'セルティックス', 'ヒート', 'ネッツ', 'バックス', 'サンズ', 'ナゲッツ', 'クリッパーズ', 'マーベリックス', 'ニックス', 'ラプターズ']
            nba_patterns_en = ['lakers', 'warriors', 'celtics', 'heat', 'nets', 'bucks', 'suns', 'nuggets', 'clippers', 'mavericks', 'knicks', 'raptors', '76ers', 'sixers']
            if any(pattern in name for name in all_names for pattern in nba_patterns_jp) or \
               any(pattern in name.lower() for name in all_names for pattern in nba_patterns_en):
                log_manager.main_logger.info(f"✅ LEVEL 4 SUCCESS: Detected NBA via NBA patterns")
                return 'nba'

            # 追加パターン学習機能
            learned_mappings = self._load_learned_sport_mappings()
            team_combo = f"{team_a}_{team_b}".lower()
            if team_combo in learned_mappings:
                sport = learned_mappings[team_combo]
                log_manager.main_logger.info(f"✅ LEVEL 4 SUCCESS: Detected {sport} via learned mappings")
                return sport

            return 'unknown'

        except Exception as e:
            log_manager.main_logger.error(f"Learning fallback failed: {e}")
            return 'unknown'

    def _load_learned_sport_mappings(self) -> Dict[str, str]:
        """学習済みスポーツマッピングを読み込み"""
        try:
            import os
            import json
            learned_file = os.path.join("app", "data", "learned_sport_mappings.json")
            if os.path.exists(learned_file):
                with open(learned_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}

    def _save_learned_sport_mapping(self, team_a: str, team_b: str, sport: str):
        """スポーツマッピングを学習・保存"""
        try:
            import os
            import json
            team_combo = f"{team_a}_{team_b}".lower()
            learned_mappings = self._load_learned_sport_mappings()
            learned_mappings[team_combo] = sport

            os.makedirs(os.path.join("app", "data"), exist_ok=True)
            learned_file = os.path.join("app", "data", "learned_sport_mappings.json")
            with open(learned_file, 'w', encoding='utf-8') as f:
                json.dump(learned_mappings, f, ensure_ascii=False, indent=2)

            log_manager.main_logger.info(f"📚 Learned sport mapping: {team_combo} -> {sport}")
        except Exception as e:
            log_manager.main_logger.warning(f"Failed to save learned mapping: {e}")