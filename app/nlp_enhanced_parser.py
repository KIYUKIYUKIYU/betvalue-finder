# -*- coding: utf-8 -*-
"""
NLP Enhanced Parser
機械学習・自然言語処理による高精度ベッティングデータ解析
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

# NLP関連のインポート (オプショナル)
try:
    import spacy
    from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
    NLP_AVAILABLE = True
except ImportError:
    spacy = None
    pipeline = None
    NLP_AVAILABLE = False

from app.universal_parser import UniversalBetParser
from converter.unified_handicap_converter import jp_to_pinnacle


@dataclass
class ParseResult:
    """パース結果と信頼度情報"""
    games: List[Dict]
    confidence: float
    method_used: str
    entities_found: List[Dict]
    processing_time: float
    fallback_used: bool = False


@dataclass
class EntityInfo:
    """抽出エンティティ情報"""
    text: str
    label: str
    confidence: float
    start_pos: int
    end_pos: int


class LocalNLPParser:
    """ローカルNLP機能を活用した高精度パーサー"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.team_database = self._build_enhanced_team_database()
        self.fallback_parser = UniversalBetParser(team_database=self.team_database)
        self.nlp_model = None
        self.ner_pipeline = None
        self.is_nlp_ready = False
        self._init_nlp_models()
        self.handicap_patterns = self._build_enhanced_handicap_patterns()
        self.confidence_weights = {
            "entity_quality": 0.4,
            "pattern_match": 0.3,
            "context_coherence": 0.2,
            "data_completeness": 0.1
        }

    def _init_nlp_models(self):
        if not NLP_AVAILABLE:
            self.logger.warning("NLP libraries not available. Using fallback mode.")
            return
        try:
            try:
                self.nlp_model = spacy.load("ja_core_news_sm")
                self.logger.info("✅ spaCy Japanese model loaded successfully")
            except OSError:
                self.logger.warning("⚠️ spaCy Japanese model not found. Install with: python -m spacy download ja_core_news_sm")
                self.nlp_model = None
            try:
                self.ner_pipeline = pipeline(
                    "ner",
                    model="cl-tohoku/bert-base-japanese-char",
                    aggregation_strategy="simple",
                    device=-1
                )
                self.logger.info("✅ Transformers NER pipeline loaded successfully")
            except Exception as e:
                self.logger.warning(f"⚠️ Transformers NER pipeline failed to load: {e}")
                self.ner_pipeline = None
            self.is_nlp_ready = (self.nlp_model is not None) or (self.ner_pipeline is not None)
            if self.is_nlp_ready:
                self.logger.info("🧠 NLP-enhanced parsing ready")
            else:
                self.logger.warning("⚠️ No NLP models available, using rule-based fallback")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize NLP models: {e}")
            self.is_nlp_ready = False

    def _build_enhanced_team_database(self) -> Dict[str, Dict]:
        import json
        import os
        team_database = {}
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        team_files = [
            "teams_mlb.json", "teams_npb.json", "teams_premier.json",
            "teams_laliga.json", "teams_bundesliga.json", "teams_serie_a.json",
            "teams_ligue1.json", "teams_eredivisie.json", "teams_primeira_liga.json",
            "teams_scottish_premiership.json", "teams_jupiler_league.json",
            "teams_champions_league.json", "teams_europa_league.json", "teams_national.json"
        ]
        total_teams = 0
        for file_name in team_files:
            file_path = os.path.join(data_dir, file_name)
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                        team_database.update(file_data)
                        total_teams += len(file_data)
            except Exception as e:
                self.logger.error(f"❌ Failed to load {file_name}: {e}")
        self.logger.info(f"🎯 Total teams loaded: {total_teams} teams")
        return team_database

    def _parse_japanese_handicap(self, s: str) -> Optional[float]:
        """
        日本式ハンディキャップをPinnacle数値に変換
        jp_to_pinnacle()を使用して正確な変換を行う
        """
        s = s.strip()
        try:
            # unified_handicap_converter の正しい変換ロジックを使用
            return jp_to_pinnacle(s)
        except Exception:
            # フォールバック: 単純な数値変換
            try:
                return float(s)
            except ValueError:
                return None

    def _build_enhanced_handicap_patterns(self) -> List[Dict]:
        return [
            {"pattern": r"<([^>]+)>", "type": "bracket_handicap", "confidence": 0.99},
            {"pattern": r"([+-]?\d+(?:\.\d+)?)", "type": "decimal", "confidence": 0.9},
        ]

    def parse(self, text: str) -> ParseResult:
        import time
        start_time = time.time()
        try:
            if self.is_nlp_ready:
                result = self._parse_with_nlp(text)
            else:
                result = self._parse_with_fallback(text)
            processing_time = time.time() - start_time
            result.processing_time = processing_time
            self.logger.info(f"🎯 Parse completed: {result.method_used}, confidence: {result.confidence:.2f}, time: {processing_time:.3f}s")
            return result
        except Exception as e:
            self.logger.error(f"❌ Parse failed: {e}")
            return self._parse_with_fallback(text)

    def _parse_with_nlp(self, text: str) -> ParseResult:
        entities = self._extract_entities(text)
        teams = self._identify_teams(entities, text)
        handicaps = self._extract_handicaps_enhanced(text, entities)
        games = self._build_games_from_entities(teams, handicaps, text)
        confidence = self._calculate_confidence(entities, teams, handicaps, games)
        if confidence < 0.6:
            fallback_result = self._parse_with_fallback(text)
            if fallback_result.confidence > confidence:
                fallback_result.fallback_used = True
                return fallback_result
        return ParseResult(
            games=games, confidence=confidence, method_used="nlp_enhanced",
            entities_found=[e.__dict__ for e in entities], processing_time=0.0, fallback_used=False
        )

    def _extract_entities(self, text: str) -> List[EntityInfo]:
        entities = []
        if self.nlp_model:
            doc = self.nlp_model(text)
            for ent in doc.ents:
                entities.append(EntityInfo(text=ent.text, label=ent.label_, confidence=0.8, start_pos=ent.start_char, end_pos=ent.end_char))
        if self.ner_pipeline and len(text) < 1000:
            try:
                ner_results = self.ner_pipeline(text)
                for result in ner_results:
                    entities.append(EntityInfo(text=result['word'], label=result['entity_group'], confidence=result['score'], start_pos=result['start'], end_pos=result['end']))
            except Exception as e:
                self.logger.warning(f"⚠️ Transformers NER failed: {e}")
        return entities

    def _identify_teams(self, entities: List[EntityInfo], text: str) -> List[Dict]:
        teams = []
        lines = text.split('\n')
        for line_idx, line in enumerate(lines):
            line = line.strip()
            if not line: continue
            for team_name, team_info in self.team_database.items():
                if team_name in line:
                    teams.append({"name": team_name, "full_name": team_info["full_name"], "sport": team_info["sport"], "confidence": 0.9, "method": "exact_match", "line_position": line_idx})
                else:
                    for alias in team_info.get("aliases", []):
                        if len(alias) <= 3:
                            if re.search(r'\b' + re.escape(alias) + r'\b', line, re.IGNORECASE):
                                teams.append({"name": team_name, "full_name": team_info["full_name"], "sport": team_info["sport"], "confidence": 0.8, "method": "word_boundary_match", "line_position": line_idx}); break
                        elif alias in line:
                            teams.append({"name": team_name, "full_name": team_info["full_name"], "sport": team_info["sport"], "confidence": 0.7, "method": "alias_match", "line_position": line_idx}); break
        seen = set()
        unique_teams = []
        for team in sorted(teams, key=lambda x: x["confidence"], reverse=True):
            if team["name"] not in seen:
                seen.add(team["name"])
                unique_teams.append(team)
        return unique_teams

    def _extract_handicaps_enhanced(self, text: str, entities: List[EntityInfo]) -> List[Dict]:
        handicaps = []
        lines = text.split('\n')
        for pattern_info in self.handicap_patterns:
            for i, line in enumerate(lines):
                for match in re.finditer(pattern_info["pattern"], line):
                    raw_value = match.group(1)
                    parsed_value = self._parse_japanese_handicap(raw_value)
                    if parsed_value is not None:
                        handicaps.append({"value": parsed_value, "raw_value": raw_value, "confidence": pattern_info["confidence"], "method": f"pattern_{pattern_info['type']}", "line_position": i})
        return handicaps

    def _build_games_from_entities(self, teams: List[Dict], handicaps: List[Dict], text: str) -> List[Dict]:
        from .enhanced_parser_system import (
            UniversalParserQualitySystem,
            create_enhanced_team_candidate,
            TeamCandidate
        )

        # 包括的品質向上システム適用
        quality_system = UniversalParserQualitySystem()

        # 既存の辞書形式からTeamCandidateオブジェクトに変換
        team_candidates = []
        for team in teams:
            team_candidate = create_enhanced_team_candidate(team)
            team_candidates.append(team_candidate)

        # 曖昧性解決
        resolved_teams = quality_system.resolve_team_ambiguity(team_candidates, text)

        # 最適ペアリング
        game_candidates = quality_system.create_optimal_pairs(resolved_teams, text)

        # 品質検証
        validated_games = quality_system.validate_game_quality(game_candidates)

        # レガシー形式に変換
        legacy_games = quality_system.export_to_legacy_format(validated_games)

        # ハンディキャップ情報を追加
        for game in legacy_games:
            # team_aとteam_bの情報を使って該当ハンディキャップを検索
            for candidate in game_candidates:
                if (candidate.home_team.name == game["team_a"] and
                    candidate.away_team.name == game["team_b"]):

                    # 対応するハンディキャップを検索
                    matched_handicap = self._find_handicap_for_teams(
                        {"name": candidate.home_team.name, "line_position": candidate.home_team.line_position},
                        {"name": candidate.away_team.name, "line_position": candidate.away_team.line_position},
                        handicaps
                    )

                    if matched_handicap:
                        game["handicap"] = matched_handicap["value"]
                        game["raw_handicap"] = matched_handicap["raw_value"]
                        game["handicap_confidence"] = matched_handicap["confidence"]

                        # フェイバリット判定
                        if matched_handicap["line_position"] == candidate.home_team.line_position:
                            game["fav_team"] = candidate.home_team.name
                        elif matched_handicap["line_position"] == candidate.away_team.line_position:
                            game["fav_team"] = candidate.away_team.name
                    break

        return legacy_games

    def _create_line_based_pairs(self, teams: List[Dict], text: str) -> List[Tuple[Dict, Dict]]:
        """リーグ名を区切りとしてテキストをブロックに分け、チームをペアリングする (Robust Version)"""
        from collections import defaultdict
        import re

        lines = text.split('\n')
        league_markers = []
        # リーグマーカー（例: <リーガ>）の位置を特定
        for i, line in enumerate(lines):
            match = re.match(r'[<\[](.+?)[>\ ]', line) # < > と [ ] 両方に対応
            if match:
                league_markers.append({"name": match.group(1), "line": i})
        
        # チームを行番号に基づいてソートしておく
        sorted_teams = sorted(teams, key=lambda x: x.get("line_position", 0))

        if not league_markers:
            # リーグマーカーがない場合は、空行による試合区切りを認識してペアにする
            return self._pair_teams_by_empty_line_separation(sorted_teams, text)

        # チームをリーグブロックに割り当てる
        blocks = defaultdict(list)
        for team in sorted_teams:
            team_line = team["line_position"]
            assigned_league = "default"
            for marker in reversed(league_markers):
                if team_line > marker["line"]:
                    assigned_league = f"{marker['name']}_{marker['line']}" # 同じリーグ名が複数ある場合も区別
                    break
            blocks[assigned_league].append(team)

        # 各ブロック内でペアリング
        pairs = []
        for league_name, teams_in_block in blocks.items():
            for i in range(0, len(teams_in_block) - 1, 2):
                pairs.append((teams_in_block[i], teams_in_block[i+1]))
                
        return pairs

    def _find_handicap_for_teams(self, team_a: Dict, team_b: Dict, handicaps: List[Dict]) -> Optional[Dict]:
        team_a_line = team_a.get("line_position", 0)
        team_b_line = team_b.get("line_position", 0)
        min_team_line = min(team_a_line, team_b_line)
        max_team_line = max(team_a_line, team_b_line)
        candidates = []
        for handicap in handicaps:
            h_line = handicap.get("line_position", 0)
            if min_team_line <= h_line <= max_team_line + 1:
                distance = min(abs(h_line - team_a_line), abs(h_line - team_b_line))
                candidates.append((handicap, distance))
        if candidates:
            candidates.sort(key=lambda x: (x[1], -x[0]["confidence"]))
            return candidates[0][0]
        return None

    def _calculate_confidence(self, entities: List[EntityInfo], teams: List[Dict], handicaps: List[Dict], games: List[Dict]) -> float:
        entity_quality = sum(e.confidence for e in entities) / len(entities) if entities else 0.0
        pattern_match = sum(t["confidence"] for t in teams) / len(teams) if teams else 0.0
        sports = [g.get("sport", "unknown") for g in games]
        context_coherence = 0.9 if len(set(sports)) == 1 and sports and sports[0] != "unknown" else 0.5
        data_completeness = sum(1 for g in games if "handicap" in g) / len(games) if games else 0.0
        return min((
            entity_quality * self.confidence_weights["entity_quality"] +
            pattern_match * self.confidence_weights["pattern_match"] +
            context_coherence * self.confidence_weights["context_coherence"] +
            data_completeness * self.confidence_weights["data_completeness"]
        ), 1.0)

    def _filter_teams_by_sport_consistency(self, teams: List[Dict]) -> List[Dict]:
        """スポーツの一貫性をチェックしてチームリストをフィルタリング"""
        if len(teams) <= 2:
            return teams

        # スポーツ別にチームをグループ化
        sports_groups = {}
        for team in teams:
            sport = team.get('sport', 'unknown')
            if sport not in sports_groups:
                sports_groups[sport] = []
            sports_groups[sport].append(team)

        # 最も多いスポーツを選択
        main_sport = max(sports_groups.keys(), key=lambda s: len(sports_groups[s]))

        # 同一行番号で複数スポーツにマッチしている場合、より高い信頼度を選択
        filtered_teams = []
        processed_lines = set()

        for team in sorted(teams, key=lambda x: (x.get("line_position", 0), -x.get("confidence", 0))):
            line_pos = team.get("line_position", 0)
            if line_pos not in processed_lines:
                # この行番号で最初のチーム（最高信頼度）のみ追加
                if team.get('sport') == main_sport:
                    filtered_teams.append(team)
                    processed_lines.add(line_pos)

        self.logger.info(f"🎯 Sport consistency filter: {len(teams)} → {len(filtered_teams)} teams (main sport: {main_sport})")
        return filtered_teams

    def _pair_teams_by_empty_line_separation(self, teams: List[Dict], text: str) -> List[Tuple[Dict, Dict]]:
        """空行による試合区切りを認識してチームをペアリング"""
        lines = text.split('\n')

        # 空行の位置を特定
        empty_lines = set(i for i, line in enumerate(lines) if not line.strip())

        # チームを行番号でソート
        sorted_teams = sorted(teams, key=lambda x: x.get("line_position", 0))

        if not empty_lines:
            # 空行がない場合は単純に2つずつペア（奇数個対応）
            pairs = []
            for i in range(0, len(sorted_teams), 2):
                team_pair = sorted_teams[i:i+2]
                if len(team_pair) == 2:
                    pairs.append(tuple(team_pair))
                # 奇数個の場合、最後の1つはスキップ
            return pairs

        # 試合ブロックを作成（空行で区切られた範囲内のチーム）
        blocks = []
        current_block = []

        for i, team in enumerate(sorted_teams):
            current_block.append(team)

            # 次のチームがあるかチェック
            if i + 1 < len(sorted_teams):
                current_line = team.get("line_position", 0)
                next_line = sorted_teams[i + 1].get("line_position", 0)

                # 現在のチームと次のチームの間に空行があるかチェック
                has_empty_between = any(current_line < empty_line < next_line for empty_line in empty_lines)

                if has_empty_between or len(current_block) >= 2:
                    blocks.append(current_block)
                    current_block = []
            else:
                # 最後のチーム
                blocks.append(current_block)

        # 各ブロックから2チームずつペアを作成
        pairs = []
        for block in blocks:
            if len(block) >= 2:
                pairs.append((block[0], block[1]))

        return pairs

    def _parse_with_fallback(self, text: str) -> ParseResult:
        self.logger.info("🔄 Using fallback rule-based parser")
        fallback_games = self.fallback_parser.parse(text)
        return ParseResult(games=fallback_games, confidence=0.7, method_used="rule_based_fallback", entities_found=[], processing_time=0.0, fallback_used=True)

class EnhancedUniversalParser:
    def __init__(self):
        self.nlp_parser = LocalNLPParser()
        self.logger = logging.getLogger(__name__)

    def parse(self, text: str) -> List[Dict]:
        result = self.nlp_parser.parse(text)
        self.logger.info(f"📊 Enhanced parse result: {len(result.games)} games, confidence: {result.confidence:.2f}")
        return result.games

    def parse_detailed(self, text: str) -> ParseResult:
        return self.nlp_parser.parse(text)