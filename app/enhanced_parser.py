# -*- coding: utf-8 -*-
"""
Enhanced Multi-Layered Parser
最高精度のベッティングデータ解析システム
フォールバック機能とエラーハンドリング強化版
"""

import re
import json
import logging
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
import time

# 既存パーサーのインポート
from app.universal_parser import UniversalBetParser
from app.enhanced_team_mapper import EnhancedTeamMapper
from converter.unified_handicap_converter import jp_to_pinnacle

@dataclass
class EnhancedParseResult:
    """強化パース結果"""
    games: List[Dict]
    confidence: float
    method_used: str
    processing_time: float
    total_games_found: int
    errors: List[str]
    fallback_used: bool = False

class EnhancedBettingParser:
    """多段階フォールバック機能付き最高精度パーサー"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.universal_parser = UniversalBetParser()
        self.team_mapper = EnhancedTeamMapper()

        # スポーツ別チーム名正規化辞書
        self.team_normalizations = {
            # MLB チーム正規化
            "レッドソックス": "ボストン・レッドソックス",
            "ホワイトソックス": "シカゴ・ホワイトソックス",
            "ダイヤモンドバックス": "アリゾナ・ダイヤモンドバックス",
            "ドジャース": "ロサンゼルス・ドジャース",
            "エンゼルス": "ロサンゼルス・エンゼルス",
            "アスレチックス": "オークランド・アスレチックス",
            "アストロズ": "ヒューストン・アストロズ",
        }

        # パターンマッチング辞書（様々な入力形式に対応）
        self.format_patterns = {
            "standard_bracket": r'^(.+?)[<＜〈]([^>＞〉]+)[>＞〉](.*)$',
            "team_with_handicap": r'^(.+?)[<＜〈]([^>＞〉]+)[>＞〉]$',
            "simple_pair": r'^(.+?)\s+(.+?)$',
            "time_format": r'^\d{1,2}:\d{2}',
            "league_marker": r'^\[.+\]$',
            "section_divider": r'^[-=]+$'
        }

    def parse_with_confidence(self, text: str, sport_hint: Optional[str] = None) -> EnhancedParseResult:
        """
        信頼度付きパース処理

        Args:
            text: 入力テキスト
            sport_hint: スポーツヒント ("mlb", "npb", "soccer" など)

        Returns:
            EnhancedParseResult: 詳細な解析結果
        """
        start_time = time.time()
        errors = []

        # Step 1: 前処理とクリーニング
        cleaned_text = self._preprocess_text(text)

        # Step 2: Universal Parser でのベース解析
        try:
            base_result = self.universal_parser.parse(cleaned_text)
            confidence = self._calculate_confidence(base_result, cleaned_text)
            method_used = "universal_parser"

        except Exception as e:
            self.logger.error(f"Universal parser failed: {e}")
            errors.append(f"Universal parser error: {str(e)}")
            # フォールバック処理
            base_result = self._fallback_parse(cleaned_text)
            confidence = 0.5  # フォールバック使用時は信頼度低下
            method_used = "fallback_parser"

        # Step 3: 結果の後処理と品質向上
        enhanced_result = self._enhance_parsing_result(base_result, sport_hint)

        # Step 3.5: Enhanced Team Mapping 適用
        mapped_result = self._apply_enhanced_mapping(enhanced_result, sport_hint)

        # Step 4: 最終検証
        validated_result = self._validate_games(mapped_result)

        processing_time = time.time() - start_time

        return EnhancedParseResult(
            games=validated_result,
            confidence=confidence,
            method_used=method_used,
            processing_time=processing_time,
            total_games_found=len(validated_result),
            errors=errors,
            fallback_used=(method_used == "fallback_parser")
        )

    def _preprocess_text(self, text: str) -> str:
        """テキストの前処理"""
        # 全角括弧を半角に統一
        text = text.replace('＜', '<').replace('＞', '>').replace('〈', '<').replace('〉', '>')

        # 不要な空行を削除
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # リーグマーカーの除去（必要に応じて）
        filtered_lines = []
        for line in lines:
            if not re.match(r'^\[.+\]$', line):  # [MLB] などを除去
                filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _calculate_confidence(self, games: List[Dict], original_text: str) -> float:
        """解析結果の信頼度計算"""
        if not games:
            return 0.0

        # 基本信頼度
        base_confidence = min(len(games) / 15.0, 1.0)  # 最大15試合想定

        # 品質チェック
        quality_score = 0.0
        for game in games:
            # チーム名の妥当性
            if self._is_valid_team_name(game.get('team_a', '')):
                quality_score += 0.3
            if self._is_valid_team_name(game.get('team_b', '')):
                quality_score += 0.3

            # ハンディキャップの妥当性
            if 'handicap' in game and self._is_valid_handicap(game['handicap']):
                quality_score += 0.4

        if games:
            quality_score /= len(games)

        return min((base_confidence + quality_score) / 2.0, 1.0)

    def _is_valid_team_name(self, team_name: str) -> bool:
        """チーム名の妥当性チェック"""
        if not team_name or len(team_name) < 2:
            return False

        # 明らかに不正なパターンをチェック
        invalid_patterns = [
            r'^\d+$',  # 数字のみ
            r'^[<>\[\]]+$',  # 記号のみ
            r'^\d{1,2}:\d{2}$',  # 時刻形式
        ]

        for pattern in invalid_patterns:
            if re.match(pattern, team_name):
                return False

        return True

    def _is_valid_handicap(self, handicap: str) -> bool:
        """ハンディキャップの妥当性チェック"""
        try:
            # 文字列を数値に変換できるかチェック
            float_val = float(handicap)
            # 合理的な範囲内かチェック
            return -10.0 <= float_val <= 10.0
        except (ValueError, TypeError):
            return False

    def _enhance_parsing_result(self, games: List[Dict], sport_hint: Optional[str]) -> List[Dict]:
        """パース結果の品質向上"""
        enhanced_games = []

        for game in games:
            enhanced_game = game.copy()

            # チーム名の正規化
            if 'team_a' in enhanced_game:
                enhanced_game['team_a'] = self._normalize_team_name(
                    enhanced_game['team_a'], sport_hint
                )
            if 'team_b' in enhanced_game:
                enhanced_game['team_b'] = self._normalize_team_name(
                    enhanced_game['team_b'], sport_hint
                )

            # ハンディキャップの正規化
            if 'handicap' in enhanced_game:
                enhanced_game['handicap'] = self._normalize_handicap(
                    enhanced_game['handicap']
                )

            # スポーツ情報の推定
            if not enhanced_game.get('sport'):
                enhanced_game['sport'] = self._detect_sport(enhanced_game, sport_hint)

            enhanced_games.append(enhanced_game)

        return enhanced_games

    def _apply_enhanced_mapping(self, games: List[Dict], sport_hint: Optional[str]) -> List[Dict]:
        """Enhanced Team Mapping を適用"""
        mapped_games = []

        for game in games:
            mapped_game = game.copy()

            # team_a のマッピング
            if 'team_a' in game and game['team_a']:
                mapping_result = self.team_mapper.map_team_name(game['team_a'], sport_hint)
                mapped_game['team_a'] = mapping_result.mapped_name
                mapped_game['team_a_original'] = mapping_result.original_name
                mapped_game['team_a_mapping_confidence'] = mapping_result.confidence
                mapped_game['team_a_mapping_method'] = mapping_result.method

            # team_b のマッピング
            if 'team_b' in game and game['team_b']:
                mapping_result = self.team_mapper.map_team_name(game['team_b'], sport_hint)
                mapped_game['team_b'] = mapping_result.mapped_name
                mapped_game['team_b_original'] = mapping_result.original_name
                mapped_game['team_b_mapping_confidence'] = mapping_result.confidence
                mapped_game['team_b_mapping_method'] = mapping_result.method

            # fav_team のマッピング（存在する場合）
            if 'fav_team' in game and game['fav_team']:
                fav_mapping = self.team_mapper.map_team_name(game['fav_team'], sport_hint)
                mapped_game['fav_team'] = fav_mapping.mapped_name
                mapped_game['fav_team_mapping_confidence'] = fav_mapping.confidence

            # マッピング品質スコアを計算
            team_a_conf = mapped_game.get('team_a_mapping_confidence', 0.5)
            team_b_conf = mapped_game.get('team_b_mapping_confidence', 0.5)
            mapped_game['mapping_quality'] = (team_a_conf + team_b_conf) / 2

            mapped_games.append(mapped_game)

        self.logger.info(f"Applied enhanced mapping to {len(mapped_games)} games")
        return mapped_games

    def _normalize_team_name(self, team_name: str, sport_hint: Optional[str]) -> str:
        """チーム名の正規化"""
        if not team_name:
            return team_name

        # 正規化辞書を適用
        normalized = self.team_normalizations.get(team_name, team_name)

        # スポーツヒントに基づく追加処理
        if sport_hint == "mlb":
            # MLB特有の処理
            pass
        elif sport_hint == "npb":
            # NPB特有の処理
            pass

        return normalized

    def _normalize_handicap(self, handicap: Union[str, float]) -> str:
        """ハンディキャップの正規化（Pinnacle形式に変換）"""
        try:
            if isinstance(handicap, (int, float)):
                # 数値の場合、Pinnacle形式に変換
                return str(jp_to_pinnacle(str(handicap)))

            # 文字列の場合、数値変換してからPinnacle形式に変換
            float_val = float(handicap)
            return str(jp_to_pinnacle(str(float_val)))
        except (ValueError, TypeError):
            # 変換できない場合はそのまま返す
            return str(handicap)

    def _detect_sport(self, game: Dict, sport_hint: Optional[str]) -> str:
        """スポーツの自動検出"""
        if sport_hint:
            return sport_hint

        # チーム名からスポーツを推定
        team_a = game.get('team_a', '').lower()
        team_b = game.get('team_b', '').lower()

        # MLB チーム名パターン
        mlb_keywords = ['ヤンキース', 'レッドソックス', 'ドジャース', 'アストロズ']
        for keyword in mlb_keywords:
            if keyword in team_a or keyword in team_b:
                return 'mlb'

        # デフォルト
        return 'unknown'

    def _validate_games(self, games: List[Dict]) -> List[Dict]:
        """最終ゲーム検証"""
        validated_games = []

        for game in games:
            # 基本的な妥当性チェック
            if not self._is_game_valid(game):
                self.logger.warning(f"Invalid game filtered out: {game}")
                continue

            validated_games.append(game)

        return validated_games

    def _is_game_valid(self, game: Dict) -> bool:
        """ゲームの妥当性チェック"""
        # 必須フィールドの存在確認
        required_fields = ['team_a', 'team_b']
        for field in required_fields:
            if field not in game or not game[field]:
                return False

        # チーム名の重複チェック
        if game['team_a'] == game['team_b']:
            return False

        # チーム名の妥当性
        if not self._is_valid_team_name(game['team_a']):
            return False
        if not self._is_valid_team_name(game['team_b']):
            return False

        return True

    def _fallback_parse(self, text: str) -> List[Dict]:
        """フォールバックパーサー（Universal Parser失敗時）"""
        self.logger.info("Using fallback parser")

        # シンプルな正規表現ベース解析
        games = []
        lines = text.strip().split('\n')

        current_team = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # パターン1: チーム<ハンディ>
            match = re.match(r'^(.+?)<(.+?)>$', line)
            if match:
                team = match.group(1).strip()
                handicap = match.group(2).strip()

                if current_team:
                    games.append({
                        'team_a': current_team,
                        'team_b': team,
                        'handicap': handicap,
                        'fav_team': team
                    })
                    current_team = None
                else:
                    current_team = {'team': team, 'handicap': handicap}
            else:
                # パターン2: チーム名のみ
                if current_team and 'handicap' in current_team:
                    games.append({
                        'team_a': current_team['team'],
                        'team_b': line,
                        'handicap': current_team['handicap'],
                        'fav_team': current_team['team']
                    })
                    current_team = None
                else:
                    current_team = line

        return games

    # 公開メソッド
    def parse(self, text: str, sport_hint: Optional[str] = None) -> List[Dict]:
        """
        シンプルなパースインターフェース（互換性維持）
        """
        result = self.parse_with_confidence(text, sport_hint)
        return result.games


# テスト用
if __name__ == "__main__":
    parser = EnhancedBettingParser()

    test_data = """[ＭＬＢ]

オリオールズ
レイズ<0.7>

レンジャーズ<0.6>
ツインズ"""

    result = parser.parse_with_confidence(test_data, sport_hint="mlb")

    print("=== Enhanced Parser Test ===")
    print(f"Games found: {result.total_games_found}")
    print(f"Confidence: {result.confidence:.3f}")
    print(f"Method: {result.method_used}")
    print(f"Processing time: {result.processing_time:.3f}s")
    print(f"Errors: {result.errors}")

    for i, game in enumerate(result.games, 1):
        print(f"{i:2d}. {game}")