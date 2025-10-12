#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自律的マッピング更新パイプライン
週次自動実行: cron 毎週日曜 3:00AM
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import shutil

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.analyze_failure_log import FailureLogAnalyzer
from tools.mapping_candidate_generator import MappingCandidateGenerator


class AutonomousMappingPipeline:
    """自律的にマッピングを更新するパイプライン"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.unified_teams_path = self.base_dir / "database" / "unified_teams.json"
        self.backup_base = self.base_dir / "backups"
        self.logs_dir = self.base_dir / "logs"
        self.auto_update_log = self.logs_dir / "auto_update_history.json"

    def run(self):
        """パイプライン実行"""
        print("=" * 80)
        print("🤖 自律マッピング更新パイプライン開始")
        print(f"   実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        try:
            # STEP 1: 最新チーム取得
            self._step1_fetch_latest_teams()

            # STEP 2: 問題検出
            issues = self._step2_detect_issues()

            # STEP 3: 失敗ログ分析
            failure_report = self._step3_analyze_failures()

            if not failure_report:
                print("\n✅ 失敗ログが空です。更新不要。")
                return

            # STEP 4: 候補生成
            candidates = self._step4_generate_candidates(failure_report)

            # STEP 5: 信頼度で振り分け
            categorized = self._step5_categorize_candidates(candidates)

            # STEP 6: 高信頼度を自動適用
            backup_path = None
            if categorized["high_confidence"]:
                backup_path = self._step6_auto_apply(categorized["high_confidence"])

            # STEP 7: 中信頼度をキューに保存（Discord通知は別途実装）
            if categorized["medium_confidence"]:
                self._step7_save_pending_queue(categorized["medium_confidence"])

            # STEP 8: 既知の問題を修正
            self._step8_fix_known_issues()

            # STEP 9: 検証（高信頼度適用があった場合のみ）
            if backup_path:
                self._step9_validate(backup_path)

            print("\n" + "=" * 80)
            print("🎉 パイプライン完了")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ パイプラインエラー: {e}")
            raise

    def _step1_fetch_latest_teams(self):
        """STEP 1: API最新チーム取得"""
        print("\n📡 STEP 1: API最新チーム取得")

        lean_script = self.base_dir / "scripts" / "lean_collect_teams.py"

        if not lean_script.exists():
            print("   ⚠️  lean_collect_teams.py が見つかりません（スキップ）")
            return

        try:
            result = subprocess.run(
                ["python3", str(lean_script)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # 出力から取得件数を抽出（簡易実装）
                output = result.stdout
                print(f"   ✅ 実行完了")
                if "取得" in output:
                    for line in output.split('\n'):
                        if "取得" in line:
                            print(f"   {line.strip()}")
            else:
                print(f"   ⚠️  実行失敗: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("   ⚠️  タイムアウト（60秒）")
        except Exception as e:
            print(f"   ⚠️  エラー: {e}")

    def _step2_detect_issues(self) -> Dict:
        """STEP 2: マッピング問題検出"""
        print("\n🔍 STEP 2: マッピング問題検出")

        detect_script = self.base_dir / "tools" / "detect_wrong_mappings.py"

        if not detect_script.exists():
            print("   ⚠️  detect_wrong_mappings.py が見つかりません（スキップ）")
            return {}

        try:
            result = subprocess.run(
                ["python3", str(detect_script)],
                capture_output=True,
                text=True,
                timeout=30
            )

            # レポート読み込み
            report_path = self.logs_dir / "mapping_issues_report.json"
            if report_path.exists():
                with open(report_path, "r", encoding="utf-8") as f:
                    issues = json.load(f)

                print(f"   検出: {issues.get('total_issues', 0)}件")
                return issues
            else:
                print("   ✅ 問題なし")
                return {}

        except Exception as e:
            print(f"   ⚠️  エラー: {e}")
            return {}

    def _step3_analyze_failures(self) -> Dict:
        """STEP 3: 失敗ログ分析"""
        print("\n📊 STEP 3: 失敗ログ分析（過去7日）")

        analyzer = FailureLogAnalyzer(str(self.logs_dir / "mapping_failures.jsonl"))
        loaded = analyzer.load_log(days=7)

        print(f"   読み込み: {loaded}エントリ")

        if loaded == 0:
            print("   ⚠️  分析対象なし")
            return {}

        report = analyzer.analyze()
        print(f"   分析: {len(report)}チーム")

        return report

    def _step4_generate_candidates(self, failure_report: Dict) -> Dict:
        """STEP 4: マッピング候補生成"""
        print("\n💡 STEP 4: マッピング候補生成")

        generator = MappingCandidateGenerator()
        candidates = generator.generate_candidates(failure_report)

        print(f"   候補生成: {len(candidates)}チーム")

        return candidates

    def _step5_categorize_candidates(self, candidates: Dict) -> Dict:
        """STEP 5: 信頼度で振り分け"""
        print("\n⚖️  STEP 5: 信頼度で振り分け")

        high_confidence = {}    # 90点以上
        medium_confidence = {}  # 70-89点
        low_confidence = {}     # 70点未満

        for api_team, data in candidates.items():
            recommended = data.get("recommended_candidate")

            if not recommended:
                continue

            score = recommended["confidence"]
            japanese = recommended["japanese"]

            if score >= 90:
                high_confidence[api_team] = {
                    "japanese": japanese,
                    "confidence": score,
                    "source": recommended["source"]
                }
            elif score >= 70:
                medium_confidence[api_team] = {
                    "japanese": japanese,
                    "confidence": score,
                    "source": recommended["source"]
                }
            else:
                low_confidence[api_team] = {
                    "japanese": japanese,
                    "confidence": score,
                    "source": recommended["source"]
                }

        print(f"   高信頼度（自動適用）: {len(high_confidence)}件")
        print(f"   中信頼度（レビュー後適用）: {len(medium_confidence)}件")
        print(f"   低信頼度（手動レビュー）: {len(low_confidence)}件")

        return {
            "high_confidence": high_confidence,
            "medium_confidence": medium_confidence,
            "low_confidence": low_confidence
        }

    def _step6_auto_apply(self, high_confidence: Dict) -> Path:
        """STEP 6: 高信頼度マッピング自動適用"""
        print("\n✅ STEP 6: 高信頼度マッピング自動適用")

        # バックアップ作成
        backup_path = self._create_backup()
        print(f"   バックアップ: {backup_path}")

        # unified_teams.json 読み込み
        with open(self.unified_teams_path, "r", encoding="utf-8") as f:
            unified_teams = json.load(f)

        # 適用
        applied_count = 0
        for api_team, data in high_confidence.items():
            japanese = data["japanese"]

            # 既存エントリに追加（重複チェック）
            if api_team in unified_teams:
                if japanese not in unified_teams[api_team]:
                    unified_teams[api_team].append(japanese)
                    applied_count += 1
                    print(f"   + {api_team} → {japanese} (スコア: {data['confidence']:.1f})")
            else:
                # 新規エントリ
                unified_teams[api_team] = [japanese]
                applied_count += 1
                print(f"   + [新規] {api_team} → {japanese} (スコア: {data['confidence']:.1f})")

        # 保存
        with open(self.unified_teams_path, "w", encoding="utf-8") as f:
            json.dump(unified_teams, f, ensure_ascii=False, indent=2)

        print(f"   適用: {applied_count}件")

        # ログ記録
        self._log_auto_update(high_confidence, "auto_applied")

        return backup_path

    def _step7_save_pending_queue(self, medium_confidence: Dict):
        """STEP 7: 中信頼度をキューに保存"""
        print("\n📢 STEP 7: 中信頼度をレビューキューに保存")

        queue_path = self.logs_dir / "pending_review_queue.json"

        # 既存キューを読み込み
        if queue_path.exists():
            with open(queue_path, "r", encoding="utf-8") as f:
                queue = json.load(f)
        else:
            queue = []

        # 新規候補を追加
        timestamp = datetime.now().isoformat()
        for api_team, data in medium_confidence.items():
            queue.append({
                "timestamp": timestamp,
                "api_team": api_team,
                "japanese": data["japanese"],
                "confidence": data["confidence"],
                "source": data["source"],
                "status": "pending_review"
            })

        # 保存
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)

        print(f"   保存: {len(medium_confidence)}件")
        print(f"   キューファイル: {queue_path}")

    def _step8_fix_known_issues(self):
        """STEP 8: 既知の問題を修正"""
        print("\n🔧 STEP 8: 既知の問題を修正")

        fix_script = self.base_dir / "tools" / "fix_team_database.py"

        if not fix_script.exists():
            print("   ⚠️  fix_team_database.py が見つかりません（スキップ）")
            return

        try:
            result = subprocess.run(
                ["python3", str(fix_script)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                # 出力から修正件数を抽出
                output = result.stdout
                if "修正" in output:
                    for line in output.split('\n'):
                        if "修正" in line:
                            print(f"   {line.strip()}")
                else:
                    print("   ✅ 実行完了")
            else:
                print(f"   ⚠️  実行失敗: {result.stderr}")

        except Exception as e:
            print(f"   ⚠️  エラー: {e}")

    def _step9_validate(self, backup_path: Path):
        """STEP 9: 更新後検証（簡易版）"""
        print("\n🧪 STEP 9: 更新後検証")

        # 簡易検証: unified_teams.json が有効なJSONかチェック
        try:
            with open(self.unified_teams_path, "r", encoding="utf-8") as f:
                unified_teams = json.load(f)

            team_count = len(unified_teams)
            print(f"   ✅ JSON検証OK（{team_count}チーム）")

            # TODO: 実際の運用では失敗率をチェック
            # failure_rate_check() を実装する場合はここで実行

        except json.JSONDecodeError as e:
            print(f"   ❌ JSON検証失敗: {e}")
            print(f"   🔄 ロールバック実行中...")
            self._restore_from_backup(backup_path)
            raise

    def _create_backup(self) -> Path:
        """バックアップ作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_base / f"db_backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # unified_teams.json をバックアップ
        shutil.copy2(
            self.unified_teams_path,
            backup_dir / "unified_teams.json"
        )

        return backup_dir

    def _restore_from_backup(self, backup_path: Path):
        """バックアップから復元"""
        backup_file = backup_path / "unified_teams.json"

        if not backup_file.exists():
            print(f"   ❌ バックアップファイルが見つかりません: {backup_file}")
            return

        shutil.copy2(backup_file, self.unified_teams_path)
        print(f"   ✅ ロールバック完了: {backup_path}")

    def _log_auto_update(self, updates: Dict, action: str):
        """自動更新ログを記録"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "updates": updates
        }

        # 既存ログ読み込み
        if self.auto_update_log.exists():
            with open(self.auto_update_log, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        # 保存（最新100件のみ保持）
        with open(self.auto_update_log, "w", encoding="utf-8") as f:
            json.dump(logs[-100:], f, ensure_ascii=False, indent=2)


def main():
    """CLIとして実行"""
    pipeline = AutonomousMappingPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()
