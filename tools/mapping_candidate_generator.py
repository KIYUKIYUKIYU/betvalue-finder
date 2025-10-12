#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マッピング候補生成エンジン
失敗ログレポートから最適なマッピング候補を生成
"""

import sys
from pathlib import Path
from typing import Dict, List
import json

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from converter.auto_transliterator import AutoTransliterator
from tools.confidence_scorer import ConfidenceScorer


class MappingCandidateGenerator:
    """マッピング候補を生成し、信頼度でスコアリング"""

    def __init__(self):
        self.transliterator = AutoTransliterator()
        self.scorer = ConfidenceScorer()
        self.unified_teams_path = Path(__file__).parent.parent / "database" / "unified_teams.json"
        self.existing_mappings = self._load_existing_mappings()

    def _load_existing_mappings(self) -> Dict:
        """既存のマッピングを読み込み"""
        try:
            with open(self.unified_teams_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def generate_candidates(self, failure_report: Dict) -> Dict:
        """
        失敗レポートから候補を生成

        Args:
            failure_report: analyze_failure_log.pyの出力

        Returns:
            {
                "api_team": {
                    "candidates": [
                        {
                            "japanese": "カタカナ名",
                            "source": "user_input" | "transliteration" | "pattern",
                            "confidence": 85.5,
                            "reasoning": {...}
                        }
                    ],
                    "recommended_candidate": {...},  # 最高スコアの候補
                    "api_occurrences": 5,
                    "failure_types": {...}
                }
            }
        """
        results = {}

        for api_team, data in failure_report.items():
            candidates = []

            # 1. ユーザー入力ベース候補
            user_candidates = self._generate_user_input_candidates(
                api_team, data
            )
            candidates.extend(user_candidates)

            # 2. 音訳ベース候補
            transliteration_candidates = self._generate_transliteration_candidates(
                api_team, data
            )
            candidates.extend(transliteration_candidates)

            # 3. 既存パターンベース候補
            pattern_candidates = self._generate_pattern_candidates(
                api_team, data
            )
            candidates.extend(pattern_candidates)

            # スコア順にソート
            candidates.sort(key=lambda x: x["confidence"], reverse=True)

            # 推奨候補（最高スコア）
            recommended = candidates[0] if candidates else None

            results[api_team] = {
                "candidates": candidates,
                "recommended_candidate": recommended,
                "api_occurrences": data.get("api_occurrences", 0),
                "failure_types": data.get("failure_types", {})
            }

        return results

    def _generate_user_input_candidates(
        self, api_team: str, data: Dict
    ) -> List[Dict]:
        """ユーザー入力から候補を生成"""
        candidates = []
        user_inputs = data.get("user_inputs", {})

        for japanese, frequency in user_inputs.items():
            if not japanese:
                continue

            # 信頼度スコアリング
            score = self.scorer.score_mapping(
                api_team,
                japanese,
                {
                    "api_frequency": data.get("api_occurrences", 0),
                    "user_input_frequency": frequency,
                    "similar_existing_mappings": self._count_similar_patterns(api_team),
                    "has_official_translation": False
                }
            )

            candidates.append({
                "japanese": japanese,
                "source": "user_input",
                "confidence": score,
                "reasoning": {
                    "user_frequency": frequency,
                    "api_frequency": data.get("api_occurrences", 0),
                    "similar_patterns": self._count_similar_patterns(api_team)
                }
            })

        return candidates

    def _generate_transliteration_candidates(
        self, api_team: str, data: Dict
    ) -> List[Dict]:
        """音訳から候補を生成"""
        candidates = []

        try:
            japanese_options = self.transliterator.generate_japanese_candidates(api_team)

            for japanese in japanese_options:
                # 信頼度スコアリング
                score = self.scorer.score_mapping(
                    api_team,
                    japanese,
                    {
                        "api_frequency": data.get("api_occurrences", 0),
                        "user_input_frequency": 0,  # 音訳なのでユーザー入力なし
                        "similar_existing_mappings": self._count_similar_patterns(api_team),
                        "has_official_translation": False
                    }
                )

                candidates.append({
                    "japanese": japanese,
                    "source": "transliteration",
                    "confidence": score,
                    "reasoning": {
                        "transliteration_method": "auto",
                        "api_frequency": data.get("api_occurrences", 0)
                    }
                })

        except Exception as e:
            # 音訳失敗時は空リストを返す
            pass

        return candidates

    def _generate_pattern_candidates(
        self, api_team: str, data: Dict
    ) -> List[Dict]:
        """既存パターンから候補を生成"""
        candidates = []

        # 類似チームを検索
        similar_teams = self._find_similar_teams(api_team)

        for similar_english, similar_japanese_list in similar_teams[:3]:  # Top 3
            # 最初の日本語候補を使用
            if similar_japanese_list:
                japanese = similar_japanese_list[0]

                # api_teamに適用（例: Manchester City → Manchester United のパターン流用）
                # 簡易実装: そのまま使用（実際はより高度な変換が必要）

                score = self.scorer.score_mapping(
                    api_team,
                    japanese,
                    {
                        "api_frequency": data.get("api_occurrences", 0),
                        "user_input_frequency": 0,
                        "similar_existing_mappings": len(similar_teams),
                        "has_official_translation": False
                    }
                )

                # パターンベースはスコアを少し下げる（不確実性）
                score *= 0.8

                candidates.append({
                    "japanese": japanese,
                    "source": "pattern",
                    "confidence": score,
                    "reasoning": {
                        "similar_team": similar_english,
                        "pattern_count": len(similar_teams)
                    }
                })

        return candidates

    def _count_similar_patterns(self, api_team: str) -> int:
        """類似パターンのカウント"""
        count = 0
        api_lower = api_team.lower()
        words = api_lower.split()

        for existing_team in self.existing_mappings.keys():
            existing_lower = existing_team.lower()

            # 単語の重複をカウント
            existing_words = set(existing_lower.split())
            api_words = set(words)
            overlap = len(api_words & existing_words)

            if overlap > 0:
                count += 1

        return min(count, 10)  # 最大10

    def _find_similar_teams(self, api_team: str) -> List[tuple]:
        """類似チームを検索"""
        from difflib import SequenceMatcher

        similarities = []
        api_lower = api_team.lower()

        for existing_team, japanese_list in self.existing_mappings.items():
            existing_lower = existing_team.lower()

            # 文字列類似度
            ratio = SequenceMatcher(None, api_lower, existing_lower).ratio()

            if ratio > 0.3:  # 30%以上の類似度
                similarities.append((existing_team, japanese_list, ratio))

        # 類似度順にソート
        similarities.sort(key=lambda x: x[2], reverse=True)

        return [(team, jp_list) for team, jp_list, _ in similarities]

    def print_candidates(self, results: Dict, top_n: int = 5):
        """候補を見やすく表示"""
        print("\n" + "=" * 80)
        print(f"💡 マッピング候補生成結果 (Top {top_n})")
        print("=" * 80)

        # スコア順にソート
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1]["recommended_candidate"]["confidence"] if x[1]["recommended_candidate"] else 0,
            reverse=True
        )

        for i, (api_team, data) in enumerate(sorted_results[:top_n], 1):
            recommended = data["recommended_candidate"]

            if not recommended:
                continue

            confidence = recommended["confidence"]
            japanese = recommended["japanese"]
            source = recommended["source"]

            # 信頼度による絵文字
            if confidence >= 90:
                emoji = "✅"
                level = "高"
            elif confidence >= 70:
                emoji = "🟡"
                level = "中"
            else:
                emoji = "⚠️ "
                level = "低"

            print(f"\n{i}. {emoji} {api_team} → 「{japanese}」")
            print(f"   信頼度: {confidence:.1f}点 ({level}信頼度)")
            print(f"   出典: {source}")
            print(f"   API出現: {data['api_occurrences']}回")

            # 他の候補
            other_candidates = [c for c in data["candidates"] if c != recommended]
            if other_candidates and len(other_candidates) > 0:
                print(f"   その他候補:")
                for cand in other_candidates[:2]:  # 上位2件
                    print(f"     - 「{cand['japanese']}」 ({cand['confidence']:.1f}点, {cand['source']})")

        print("\n" + "=" * 80)


def main():
    """CLIとして実行"""
    import argparse

    parser = argparse.ArgumentParser(description="マッピング候補生成エンジン")
    parser.add_argument(
        "--report",
        required=True,
        help="失敗ログ分析レポート（JSON）"
    )
    parser.add_argument(
        "--output",
        help="候補レポートの出力先（JSON）"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="表示する上位N件"
    )

    args = parser.parse_args()

    # レポート読み込み
    with open(args.report, "r", encoding="utf-8") as f:
        failure_report = json.load(f)

    print(f"🔍 マッピング候補生成開始")
    print(f"   対象: {len(failure_report)}チーム")

    generator = MappingCandidateGenerator()
    results = generator.generate_candidates(failure_report)

    generator.print_candidates(results, top_n=args.top)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 候補レポート保存: {output_path}")


if __name__ == "__main__":
    main()
