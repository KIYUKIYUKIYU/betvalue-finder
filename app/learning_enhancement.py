#!/usr/bin/env python3
"""
パーサー学習機能強化システム
- ファインチューニング機能
- 継続学習機能
- カスタムルール拡張
- アクティブラーニング
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from collections import defaultdict, Counter

@dataclass
class LearningExample:
    """学習データの例"""
    input_text: str
    expected_teams: List[Dict]
    expected_games: List[Dict]
    feedback_type: str  # "correction", "validation", "new_pattern"
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    confidence_score: float = 1.0

@dataclass
class CustomRule:
    """カスタムルール定義"""
    rule_id: str
    pattern: str
    sport: str
    team_mapping: Dict[str, str]
    confidence: float
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 1.0

class ParserLearningSystem:
    """パーサー学習機能システム"""

    def __init__(self, learning_data_path: str = "learning_data"):
        self.logger = logging.getLogger(__name__)
        self.learning_data_path = learning_data_path
        self.learning_examples = []
        self.custom_rules = {}
        self.failed_cases = []

        # 学習データディレクトリの確保
        os.makedirs(learning_data_path, exist_ok=True)

        # 既存学習データの読み込み
        self._load_existing_data()

    def _load_existing_data(self):
        """既存の学習データを読み込み"""
        try:
            # 学習例データ
            examples_file = os.path.join(self.learning_data_path, "learning_examples.json")
            if os.path.exists(examples_file):
                with open(examples_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                        self.learning_examples.append(LearningExample(**item))

            # カスタムルールデータ
            rules_file = os.path.join(self.learning_data_path, "custom_rules.json")
            if os.path.exists(rules_file):
                with open(rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for rule_id, rule_data in data.items():
                        rule_data['created_at'] = datetime.fromisoformat(rule_data['created_at'])
                        self.custom_rules[rule_id] = CustomRule(**rule_data)

            # 失敗ケースデータ
            failed_file = os.path.join(self.learning_data_path, "failed_cases.json")
            if os.path.exists(failed_file):
                with open(failed_file, 'r', encoding='utf-8') as f:
                    self.failed_cases = json.load(f)

            self.logger.info(f"📚 学習データ読み込み完了: {len(self.learning_examples)}例, {len(self.custom_rules)}ルール, {len(self.failed_cases)}失敗ケース")

        except Exception as e:
            self.logger.warning(f"学習データ読み込みエラー: {e}")

    def _save_data(self):
        """学習データを保存"""
        try:
            # 学習例保存
            examples_file = os.path.join(self.learning_data_path, "learning_examples.json")
            examples_data = []
            for example in self.learning_examples:
                data = {
                    'input_text': example.input_text,
                    'expected_teams': example.expected_teams,
                    'expected_games': example.expected_games,
                    'feedback_type': example.feedback_type,
                    'timestamp': example.timestamp.isoformat(),
                    'user_id': example.user_id,
                    'confidence_score': example.confidence_score
                }
                examples_data.append(data)

            with open(examples_file, 'w', encoding='utf-8') as f:
                json.dump(examples_data, f, ensure_ascii=False, indent=2)

            # カスタムルール保存
            rules_file = os.path.join(self.learning_data_path, "custom_rules.json")
            rules_data = {}
            for rule_id, rule in self.custom_rules.items():
                rules_data[rule_id] = {
                    'rule_id': rule.rule_id,
                    'pattern': rule.pattern,
                    'sport': rule.sport,
                    'team_mapping': rule.team_mapping,
                    'confidence': rule.confidence,
                    'created_by': rule.created_by,
                    'created_at': rule.created_at.isoformat(),
                    'usage_count': rule.usage_count,
                    'success_rate': rule.success_rate
                }

            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=2)

            # 失敗ケース保存
            failed_file = os.path.join(self.learning_data_path, "failed_cases.json")
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_cases, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"学習データ保存エラー: {e}")

    def add_learning_example(self, input_text: str, expected_teams: List[Dict],
                           expected_games: List[Dict], feedback_type: str,
                           user_id: Optional[str] = None, confidence: float = 1.0):
        """学習例を追加"""
        example = LearningExample(
            input_text=input_text,
            expected_teams=expected_teams,
            expected_games=expected_games,
            feedback_type=feedback_type,
            user_id=user_id,
            confidence_score=confidence
        )

        self.learning_examples.append(example)
        self._save_data()

        self.logger.info(f"📝 学習例追加: {feedback_type} - {len(expected_games)}ゲーム")

    def add_custom_rule(self, pattern: str, sport: str, team_mapping: Dict[str, str],
                       confidence: float, created_by: str) -> str:
        """カスタムルールを追加"""
        rule_id = f"custom_{len(self.custom_rules)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        rule = CustomRule(
            rule_id=rule_id,
            pattern=pattern,
            sport=sport,
            team_mapping=team_mapping,
            confidence=confidence,
            created_by=created_by
        )

        self.custom_rules[rule_id] = rule
        self._save_data()

        self.logger.info(f"📋 カスタムルール追加: {rule_id} - {sport}")
        return rule_id

    def record_parsing_failure(self, input_text: str, error_details: Dict,
                             user_feedback: Optional[str] = None):
        """パース失敗を記録（アクティブラーニング用）"""
        failure_record = {
            'input_text': input_text,
            'error_details': error_details,
            'user_feedback': user_feedback,
            'timestamp': datetime.now().isoformat(),
            'resolved': False
        }

        self.failed_cases.append(failure_record)
        self._save_data()

        self.logger.warning(f"❌ パース失敗記録: {input_text[:50]}...")

    def get_suggestions_for_failed_case(self, input_text: str) -> List[Dict]:
        """失敗ケースに対する改善提案を生成"""
        suggestions = []

        # 類似パターンの検索
        similar_examples = self._find_similar_examples(input_text)
        if similar_examples:
            suggestions.append({
                'type': 'similar_pattern',
                'description': f'{len(similar_examples)}件の類似パターンが見つかりました',
                'examples': similar_examples[:3]  # 上位3件
            })

        # カスタムルールの提案
        rule_suggestions = self._suggest_custom_rules(input_text)
        if rule_suggestions:
            suggestions.extend(rule_suggestions)

        return suggestions

    def _find_similar_examples(self, input_text: str) -> List[LearningExample]:
        """類似の学習例を検索"""
        similar = []
        input_words = set(input_text.split())

        for example in self.learning_examples:
            example_words = set(example.input_text.split())
            similarity = len(input_words & example_words) / len(input_words | example_words)

            if similarity > 0.3:  # 30%以上の類似度
                similar.append((example, similarity))

        # 類似度でソート
        similar.sort(key=lambda x: x[1], reverse=True)
        return [ex for ex, _ in similar]

    def _suggest_custom_rules(self, input_text: str) -> List[Dict]:
        """カスタムルールの提案を生成"""
        suggestions = []

        # 頻出パターンの分析
        words = input_text.split()

        # 特殊文字パターンの検出
        if '<' in input_text and '>' in input_text:
            suggestions.append({
                'type': 'custom_rule',
                'description': 'ハンディキャップ表記の新しいパターンを検出',
                'suggested_pattern': r'<([^>]+)>',
                'confidence': 0.8
            })

        # チーム名パターンの検出
        potential_teams = [word for word in words if len(word) > 2 and word.isalpha()]
        if potential_teams:
            suggestions.append({
                'type': 'team_rule',
                'description': f'新しいチーム名候補: {", ".join(potential_teams)}',
                'suggested_teams': potential_teams,
                'confidence': 0.6
            })

        return suggestions

    def apply_custom_rules(self, input_text: str, existing_teams: List[Dict]) -> List[Dict]:
        """カスタムルールを適用してチーム認識を強化"""
        enhanced_teams = existing_teams.copy()

        for rule_id, rule in self.custom_rules.items():
            import re

            if re.search(rule.pattern, input_text):
                # ルール適用
                for original_name, mapped_name in rule.team_mapping.items():
                    if original_name in input_text:
                        # 既存チームの更新または新規追加
                        found = False
                        for team in enhanced_teams:
                            if team['name'] == original_name:
                                team['name'] = mapped_name
                                team['sport'] = rule.sport
                                team['confidence'] = max(team['confidence'], rule.confidence)
                                team['method'] = f'custom_rule_{rule_id}'
                                found = True
                                break

                        if not found:
                            # 新規チーム追加
                            enhanced_teams.append({
                                'name': mapped_name,
                                'full_name': mapped_name,
                                'sport': rule.sport,
                                'confidence': rule.confidence,
                                'method': f'custom_rule_{rule_id}',
                                'line_position': self._estimate_line_position(original_name, input_text)
                            })

                # 使用統計の更新
                rule.usage_count += 1

        return enhanced_teams

    def _estimate_line_position(self, team_name: str, text: str) -> int:
        """チーム名のテキスト内位置を推定"""
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if team_name in line:
                return i
        return 0

    def generate_training_dataset(self) -> Tuple[List[str], List[Dict]]:
        """ファインチューニング用のトレーニングデータセットを生成"""
        inputs = []
        targets = []

        for example in self.learning_examples:
            if example.confidence_score >= 0.8:  # 高信頼度の例のみ
                inputs.append(example.input_text)
                targets.append({
                    'teams': example.expected_teams,
                    'games': example.expected_games
                })

        self.logger.info(f"🎯 トレーニングデータセット生成: {len(inputs)}例")
        return inputs, targets

    def get_learning_statistics(self) -> Dict:
        """学習統計の取得"""
        stats = {
            'total_examples': len(self.learning_examples),
            'total_custom_rules': len(self.custom_rules),
            'total_failed_cases': len(self.failed_cases),
            'feedback_types': Counter(ex.feedback_type for ex in self.learning_examples),
            'sports_distribution': Counter(ex.expected_games[0]['sport'] if ex.expected_games else 'unknown'
                                         for ex in self.learning_examples),
            'most_active_rules': sorted(
                [(rule.rule_id, rule.usage_count, rule.success_rate)
                 for rule in self.custom_rules.values()],
                key=lambda x: x[1], reverse=True
            )[:5],
            'recent_activity': len([ex for ex in self.learning_examples
                                  if (datetime.now() - ex.timestamp).days <= 7])
        }

        return stats

    def suggest_improvements(self) -> List[Dict]:
        """システム改善の提案"""
        suggestions = []
        stats = self.get_learning_statistics()

        # データ量の評価
        if stats['total_examples'] < 50:
            suggestions.append({
                'type': 'data_collection',
                'priority': 'high',
                'description': 'より多くの学習データが必要です（現在: {}例）'.format(stats['total_examples']),
                'action': 'ユーザーフィードバックの収集を強化してください'
            })

        # 失敗ケースの分析
        if stats['total_failed_cases'] > stats['total_examples'] * 0.3:
            suggestions.append({
                'type': 'failure_analysis',
                'priority': 'high',
                'description': '失敗ケースが多すぎます（{}件）'.format(stats['total_failed_cases']),
                'action': 'パターン分析とルール追加を検討してください'
            })

        # カスタムルールの効果分析
        low_performance_rules = [rule for rule in self.custom_rules.values()
                               if rule.usage_count > 5 and rule.success_rate < 0.7]
        if low_performance_rules:
            suggestions.append({
                'type': 'rule_optimization',
                'priority': 'medium',
                'description': f'{len(low_performance_rules)}個のルールの成功率が低いです',
                'action': 'ルールの見直しまたは削除を検討してください'
            })

        return suggestions