#!/usr/bin/env python3
"""
包括的パーサー品質向上システム
- チーム名曖昧性解決
- スポーツ一貫性保証
- 信頼度ベース判定
- ロバストなエラーハンドリング
"""

import logging
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict, Counter
import re
from dataclasses import dataclass

@dataclass
class TeamCandidate:
    """チーム候補情報"""
    name: str
    full_name: str
    sport: str
    confidence: float
    method: str
    line_position: int
    aliases: List[str] = None

@dataclass
class GameCandidate:
    """ゲーム候補情報"""
    home_team: TeamCandidate
    away_team: TeamCandidate
    handicap: Optional[float] = None
    raw_handicap: Optional[str] = None
    confidence: float = 0.0

class UniversalParserQualitySystem:
    """包括的パーサー品質向上システム"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ambiguous_patterns = {
            # NPBの曖昧パターン
            "ライオンズ": ["西武", "埼玉西武ライオンズ"],
            "ジャイアンツ": ["巨人", "読売ジャイアンツ"],
            "ホークス": ["ソフトバンク", "福岡ソフトバンクホークス"],
            "イーグルス": ["楽天", "東北楽天ゴールデンイーグルス"],

            # サッカーの曖昧パターン
            "ユナイテッド": ["マンU", "マンチェスター・ユナイテッド"],
            "シティ": ["マンシティ", "マンチェスター・シティ"],
            "アーセナル": ["アーセナル", "アーセナルFC"],
        }

    def resolve_team_ambiguity(self, candidates: List[TeamCandidate], context: str) -> List[TeamCandidate]:
        """チーム名の曖昧性を包括的に解決"""

        # 1. スポーツ別グループ化
        sport_groups = defaultdict(list)
        for candidate in candidates:
            sport_groups[candidate.sport].append(candidate)

        # 2. 主要スポーツ判定（最多チーム数 + 信頼度加重）
        sport_scores = {}
        for sport, teams in sport_groups.items():
            count_score = len(teams) * 2  # チーム数の重み
            confidence_score = sum(team.confidence for team in teams)  # 信頼度の重み
            sport_scores[sport] = count_score + confidence_score

        primary_sport = max(sport_scores.keys(), key=lambda s: sport_scores[s])

        # 3. 行位置別の最適候補選択
        line_positions = {}
        for candidate in candidates:
            pos = candidate.line_position
            if pos not in line_positions:
                line_positions[pos] = []
            line_positions[pos].append(candidate)

        resolved_candidates = []
        for pos, pos_candidates in line_positions.items():
            # 主要スポーツを優先、次に信頼度
            primary_sport_candidates = [c for c in pos_candidates if c.sport == primary_sport]

            if primary_sport_candidates:
                best_candidate = max(primary_sport_candidates, key=lambda c: c.confidence)
                resolved_candidates.append(best_candidate)
            else:
                # 主要スポーツがない場合は最高信頼度
                best_candidate = max(pos_candidates, key=lambda c: c.confidence)
                resolved_candidates.append(best_candidate)

        self.logger.info(f"🎯 Ambiguity resolution: {len(candidates)} → {len(resolved_candidates)} candidates (primary sport: {primary_sport})")
        return resolved_candidates

    def create_optimal_pairs(self, teams: List[TeamCandidate], text: str) -> List[GameCandidate]:
        """最適なチームペアリングを実行"""

        # 1. 空行による試合境界の検出
        lines = text.split('\n')
        empty_line_positions = set(i for i, line in enumerate(lines) if not line.strip())

        # 2. チームを試合ブロックに分割
        game_blocks = self._split_teams_into_game_blocks(teams, empty_line_positions)

        # 3. 各ブロックからゲーム候補を生成
        game_candidates = []
        for block in game_blocks:
            if len(block) >= 2:
                # スポーツ一貫性チェック
                consistent_teams = self._ensure_sport_consistency(block)

                # ペアリング実行
                pairs = self._create_pairs_from_block(consistent_teams)
                game_candidates.extend(pairs)

        return game_candidates

    def _split_teams_into_game_blocks(self, teams: List[TeamCandidate], empty_lines: Set[int]) -> List[List[TeamCandidate]]:
        """チームを試合ブロックに分割"""

        sorted_teams = sorted(teams, key=lambda t: t.line_position)

        if not empty_lines:
            # 空行がない場合は2チームずつグループ化
            blocks = []
            for i in range(0, len(sorted_teams), 2):
                block = sorted_teams[i:i+2]
                if len(block) == 2:
                    blocks.append(block)
            return blocks

        # 空行で区切られたブロック作成
        blocks = []
        current_block = []

        for i, team in enumerate(sorted_teams):
            current_block.append(team)

            # 次のチームとの間に空行があるかチェック
            if i + 1 < len(sorted_teams):
                current_pos = team.line_position
                next_pos = sorted_teams[i + 1].line_position
                has_empty_between = any(current_pos < empty_pos < next_pos for empty_pos in empty_lines)

                if has_empty_between:
                    blocks.append(current_block)
                    current_block = []
            else:
                # 最後のチーム
                blocks.append(current_block)

        return blocks

    def _ensure_sport_consistency(self, teams: List[TeamCandidate]) -> List[TeamCandidate]:
        """ブロック内のスポーツ一貫性を保証"""

        if len(teams) <= 1:
            return teams

        # スポーツ別集計
        sport_counts = Counter(team.sport for team in teams)

        # 最頻スポーツを選択
        primary_sport = sport_counts.most_common(1)[0][0]

        # 主要スポーツのチームのみ抽出
        consistent_teams = [team for team in teams if team.sport == primary_sport]

        if len(consistent_teams) < len(teams):
            self.logger.warning(f"⚠️ Sport consistency filter: {len(teams)} → {len(consistent_teams)} teams (sport: {primary_sport})")

        return consistent_teams

    def _create_pairs_from_block(self, teams: List[TeamCandidate]) -> List[GameCandidate]:
        """ブロック内のチームからペアを作成"""

        pairs = []

        # 2チームずつペアリング
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                home_team = teams[i]
                away_team = teams[i + 1]

                # ゲーム候補作成
                game = GameCandidate(
                    home_team=home_team,
                    away_team=away_team,
                    confidence=min(home_team.confidence, away_team.confidence)
                )
                pairs.append(game)

        return pairs

    def validate_game_quality(self, games: List[GameCandidate]) -> List[GameCandidate]:
        """ゲーム品質の検証とフィルタリング"""

        validated_games = []

        for game in games:
            quality_score = self._calculate_game_quality(game)

            if quality_score >= 0.5:  # 品質閾値
                validated_games.append(game)
            else:
                self.logger.warning(f"⚠️ Low quality game filtered: {game.home_team.name} vs {game.away_team.name} (score: {quality_score:.2f})")

        return validated_games

    def _calculate_game_quality(self, game: GameCandidate) -> float:
        """ゲーム品質スコアの計算"""

        # 基本信頼度
        base_confidence = game.confidence

        # スポーツ一貫性
        sport_consistency = 1.0 if game.home_team.sport == game.away_team.sport else 0.5

        # チーム名の明確性（曖昧でない = 高スコア）
        home_clarity = 1.0 if game.home_team.name not in self.ambiguous_patterns else 0.8
        away_clarity = 1.0 if game.away_team.name not in self.ambiguous_patterns else 0.8

        # 総合品質スコア
        quality_score = (
            base_confidence * 0.4 +
            sport_consistency * 0.3 +
            (home_clarity + away_clarity) / 2 * 0.3
        )

        return min(quality_score, 1.0)

    def export_to_legacy_format(self, games: List[GameCandidate]) -> List[Dict]:
        """レガシー形式への変換"""

        legacy_games = []

        for game in games:
            legacy_game = {
                "team_a": game.home_team.name,
                "team_b": game.away_team.name,
                "sport": game.home_team.sport,
                "team_a_confidence": game.home_team.confidence,
                "team_b_confidence": game.away_team.confidence,
            }

            # ハンディキャップ情報追加
            if game.handicap is not None:
                legacy_game["handicap"] = game.handicap
            if game.raw_handicap is not None:
                legacy_game["raw_handicap"] = game.raw_handicap

            legacy_games.append(legacy_game)

        return legacy_games

def create_enhanced_team_candidate(team_dict: Dict) -> TeamCandidate:
    """既存の辞書形式からTeamCandidateオブジェクトを作成"""
    return TeamCandidate(
        name=team_dict.get("name", ""),
        full_name=team_dict.get("full_name", ""),
        sport=team_dict.get("sport", "unknown"),
        confidence=team_dict.get("confidence", 0.0),
        method=team_dict.get("method", "unknown"),
        line_position=team_dict.get("line_position", 0),
        aliases=team_dict.get("aliases", [])
    )