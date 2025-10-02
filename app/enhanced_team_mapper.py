# -*- coding: utf-8 -*-
"""
Enhanced Team Mapping System
動的マッピング・ファジーマッチング・自動学習対応
"""

import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
from difflib import SequenceMatcher
import time

# ComprehensiveTeamTranslatorのインポート
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from converter.comprehensive_team_translator import ComprehensiveTeamTranslator

@dataclass
class MappingResult:
    """マッピング結果"""
    original_name: str
    mapped_name: str
    confidence: float
    method: str  # 'exact', 'alias', 'fuzzy', 'learned'
    sport_hint: Optional[str] = None

@dataclass
class TeamInfo:
    """チーム情報"""
    official_name: str
    full_name: str
    aliases: List[str]
    sport: str
    league: str
    confidence: float = 1.0

class EnhancedTeamMapper:
    """拡張チームマッピングシステム"""

    def __init__(self, data_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), "data")

        # キャッシュとマッピング辞書
        self.team_database: Dict[str, TeamInfo] = {}
        self.fuzzy_cache: Dict[str, MappingResult] = {}
        self.learned_mappings: Dict[str, str] = {}

        # 設定
        self.fuzzy_threshold = 0.7  # ファジーマッチング閾値
        self.cache_ttl = 3600  # キャッシュ有効期間（秒）

        # ComprehensiveTeamTranslator 初期化
        self.team_translator = ComprehensiveTeamTranslator()

        # データベース読み込み
        self._load_team_database()
        self._load_learned_mappings()

    def _load_team_database(self):
        """チームデータベースを読み込み"""
        try:
            team_files = [
                ("teams_mlb.json", "baseball", "MLB"),
                ("teams_npb.json", "baseball", "NPB"),
                ("teams_premier.json", "soccer", "Premier League"),
                ("teams_laliga.json", "soccer", "La Liga"),
                ("teams_bundesliga.json", "soccer", "Bundesliga"),
                ("teams_serie_a.json", "soccer", "Serie A"),
                ("teams_ligue1.json", "soccer", "Ligue 1"),
                ("teams_eredivisie.json", "soccer", "Eredivisie"),
                ("teams_primeira_liga.json", "soccer", "Primeira Liga"),
                ("teams_scottish_premiership.json", "soccer", "Scottish Premiership"),
                ("teams_jupiler_league.json", "soccer", "Jupiler League"),
                ("teams_champions_league.json", "soccer", "Champions League"),
                ("teams_europa_league.json", "soccer", "Europa League"),
                ("teams_national.json", "soccer", "National Teams"),
            ]

            total_loaded = 0

            for filename, sport, league in team_files:
                filepath = os.path.join(self.data_dir, filename)
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_data = json.load(f)

                        for team_key, team_data in file_data.items():
                            # TeamInfo オブジェクトを作成
                            team_info = TeamInfo(
                                official_name=team_key,
                                full_name=team_data.get("full_name", team_key),
                                aliases=team_data.get("aliases", []),
                                sport=sport,
                                league=league
                            )

                            # メインキーで登録
                            self.team_database[team_key] = team_info

                            # エイリアスでも登録
                            for alias in team_info.aliases:
                                if alias not in self.team_database:
                                    self.team_database[alias] = team_info

                        total_loaded += len(file_data)
                        self.logger.info(f"Loaded {len(file_data)} teams from {filename}")

                    except Exception as e:
                        self.logger.error(f"Failed to load {filename}: {e}")

            self.logger.info(f"Total teams loaded: {len(self.team_database)} entries, {total_loaded} unique teams")

        except Exception as e:
            self.logger.error(f"Database loading failed: {e}")

    def _load_learned_mappings(self):
        """学習済みマッピングを読み込み"""
        learned_file = os.path.join(self.data_dir, "learned_mappings.json")
        try:
            if os.path.exists(learned_file):
                with open(learned_file, 'r', encoding='utf-8') as f:
                    self.learned_mappings = json.load(f)
                self.logger.info(f"Loaded {len(self.learned_mappings)} learned mappings")
        except Exception as e:
            self.logger.warning(f"Failed to load learned mappings: {e}")

    def _save_learned_mappings(self):
        """学習済みマッピングを保存"""
        learned_file = os.path.join(self.data_dir, "learned_mappings.json")
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(learned_file, 'w', encoding='utf-8') as f:
                json.dump(self.learned_mappings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save learned mappings: {e}")

    def map_team_name(self, team_name: str, sport_hint: Optional[str] = None) -> MappingResult:
        """
        チーム名をマッピング

        Args:
            team_name: マッピング対象のチーム名
            sport_hint: スポーツヒント ('mlb', 'npb', 'soccer')

        Returns:
            MappingResult: マッピング結果
        """
        if not team_name or not team_name.strip():
            return MappingResult(
                original_name=team_name,
                mapped_name=team_name,
                confidence=0.0,
                method="empty"
            )

        team_name = team_name.strip()
        original_name = team_name

        # 0. ComprehensiveTeamTranslator で日本語→英語翻訳
        translated_name = self.team_translator.translate_if_needed(team_name, sport_hint)
        if translated_name != team_name:
            self.logger.debug(f"Team name translated: '{team_name}' → '{translated_name}' (sport: {sport_hint})")
            team_name = translated_name

        # 1. 完全一致検索
        if team_name in self.team_database:
            team_info = self.team_database[team_name]
            return MappingResult(
                original_name=original_name,
                mapped_name=team_info.full_name,
                confidence=1.0,
                method="exact",
                sport_hint=sport_hint
            )

        # 2. 学習済みマッピング検索
        if team_name in self.learned_mappings:
            mapped_name = self.learned_mappings[team_name]
            return MappingResult(
                original_name=original_name,
                mapped_name=mapped_name,
                confidence=0.95,
                method="learned",
                sport_hint=sport_hint
            )

        # 3. 正規化後完全一致
        normalized_name = self._normalize_team_name(team_name)
        for key, team_info in self.team_database.items():
            if self._normalize_team_name(key) == normalized_name:
                return MappingResult(
                    original_name=original_name,
                    mapped_name=team_info.full_name,
                    confidence=0.9,
                    method="normalized",
                    sport_hint=sport_hint
                )

        # 4. ファジーマッチング
        fuzzy_result = self._fuzzy_match(team_name, sport_hint)
        if fuzzy_result and fuzzy_result.confidence >= self.fuzzy_threshold:
            return fuzzy_result

        # 5. フォールバック（元の名前をそのまま返す）
        return MappingResult(
            original_name=original_name,
            mapped_name=team_name,
            confidence=0.5,
            method="fallback",
            sport_hint=sport_hint
        )

    def _normalize_team_name(self, team_name: str) -> str:
        """チーム名の正規化"""
        # 小文字化
        normalized = team_name.lower()

        # 空白・記号除去
        normalized = re.sub(r'[.\s\-_]', '', normalized)

        # 一般的な語句の統一
        replacements = {
            'fc': '',
            'cf': '',
            'sc': '',
            'ac': '',
            'united': 'utd',
            'manchester': 'man',
            'real': 'r',
            'atletico': 'atletico',
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        return normalized

    def _fuzzy_match(self, team_name: str, sport_hint: Optional[str] = None) -> Optional[MappingResult]:
        """ファジーマッチング"""
        # キャッシュ確認
        cache_key = f"{team_name}_{sport_hint}"
        if cache_key in self.fuzzy_cache:
            cached = self.fuzzy_cache[cache_key]
            # TTL確認（簡易実装）
            return cached

        best_match = None
        best_score = 0.0
        best_team_info = None

        normalized_input = self._normalize_team_name(team_name)

        # スポーツヒントでフィルタリング
        candidates = self.team_database.items()
        if sport_hint:
            sport_filter = self._get_sport_filter(sport_hint)
            candidates = [(k, v) for k, v in candidates if v.sport in sport_filter]

        for db_name, team_info in candidates:
            # 各候補との類似度計算
            normalized_candidate = self._normalize_team_name(db_name)

            # 複数の類似度メトリクスを使用
            similarity_scores = [
                SequenceMatcher(None, normalized_input, normalized_candidate).ratio(),
                SequenceMatcher(None, team_name.lower(), db_name.lower()).ratio(),
            ]

            # エイリアスとも比較
            for alias in team_info.aliases:
                similarity_scores.append(
                    SequenceMatcher(None, normalized_input, self._normalize_team_name(alias)).ratio()
                )
                similarity_scores.append(
                    SequenceMatcher(None, team_name.lower(), alias.lower()).ratio()
                )

            # 最高スコアを採用
            max_score = max(similarity_scores)

            if max_score > best_score:
                best_score = max_score
                best_match = db_name
                best_team_info = team_info

        if best_match and best_score >= self.fuzzy_threshold:
            result = MappingResult(
                original_name=team_name,
                mapped_name=best_team_info.full_name,
                confidence=best_score,
                method="fuzzy",
                sport_hint=sport_hint
            )

            # キャッシュに保存
            self.fuzzy_cache[cache_key] = result

            return result

        return None

    def _get_sport_filter(self, sport_hint: str) -> List[str]:
        """スポーツヒントからフィルター条件を取得"""
        sport_map = {
            'mlb': ['baseball'],
            'npb': ['baseball'],
            'baseball': ['baseball'],
            'soccer': ['soccer'],
            'football': ['soccer'],
        }
        return sport_map.get(sport_hint.lower(), ['baseball', 'soccer'])

    def learn_mapping(self, original_name: str, correct_mapping: str):
        """マッピングを学習"""
        self.learned_mappings[original_name] = correct_mapping
        self.logger.info(f"Learned mapping: {original_name} -> {correct_mapping}")
        self._save_learned_mappings()

    def batch_map(self, team_names: List[str], sport_hint: Optional[str] = None) -> List[MappingResult]:
        """複数のチーム名を一括マッピング"""
        results = []
        for team_name in team_names:
            result = self.map_team_name(team_name, sport_hint)
            results.append(result)
        return results

    def get_mapping_stats(self) -> Dict[str, Any]:
        """マッピング統計を取得"""
        return {
            "total_teams_in_db": len(set(info.official_name for info in self.team_database.values())),
            "total_entries": len(self.team_database),
            "learned_mappings": len(self.learned_mappings),
            "fuzzy_cache_size": len(self.fuzzy_cache),
            "sports_coverage": list(set(info.sport for info in self.team_database.values())),
            "leagues_coverage": list(set(info.league for info in self.team_database.values()))
        }

    def add_missing_teams(self, missing_teams: List[Tuple[str, str, str, str]]):
        """不足チームを追加

        Args:
            missing_teams: [(japanese_name, english_name, sport, league), ...]
        """
        added_count = 0

        for jp_name, en_name, sport, league in missing_teams:
            if jp_name not in self.team_database:
                team_info = TeamInfo(
                    official_name=jp_name,
                    full_name=en_name,
                    aliases=[jp_name],
                    sport=sport,
                    league=league,
                    confidence=0.8  # 手動追加は信頼度やや低め
                )

                self.team_database[jp_name] = team_info
                added_count += 1

                self.logger.info(f"Added missing team: {jp_name} -> {en_name}")

        if added_count > 0:
            self.logger.info(f"Added {added_count} missing teams to database")

# テスト・デモ用関数
def demo_enhanced_mapping():
    """Enhanced Team Mapper のデモ"""
    print("=== Enhanced Team Mapping Demo ===")

    mapper = EnhancedTeamMapper()

    # テストケース
    test_cases = [
        ("アストンヴィラ", "soccer"),
        ("シュトットガルト", "soccer"),
        ("ヤンキース", "mlb"),
        ("レッドソックス", "baseball"),
        ("巨人", "npb"),
        ("不明チーム", None),  # 存在しないチーム
    ]

    print("📊 Mapping Results:")
    for team_name, sport_hint in test_cases:
        result = mapper.map_team_name(team_name, sport_hint)
        print(f"  '{team_name}' -> '{result.mapped_name}' "
              f"(confidence: {result.confidence:.3f}, method: {result.method})")

    # 統計表示
    stats = mapper.get_mapping_stats()
    print(f"\n📊 System Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    demo_enhanced_mapping()