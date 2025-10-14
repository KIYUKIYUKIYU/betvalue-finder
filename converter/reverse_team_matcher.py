import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from difflib import SequenceMatcher
from datetime import datetime
import os


class ReverseTeamMatcher:
    """
    APIの英語チーム名を日本語に変換してユーザー入力とマッチング (あいまい検索対応)
    統一された単一のDB `database/unified_teams.json` のみを参照する。
    """

    def __init__(self, enable_logging: bool = True):
        self.english_to_japanese: Dict[str, Set[str]] = {}
        self.enable_logging = enable_logging
        self.base_dir = Path(__file__).parent.parent
        self.failure_log_path = self.base_dir / "logs" / "mapping_failures.jsonl"
        self._load_unified_dictionary()

    def _load_unified_dictionary(self):
        """単一の統合JSONファイルからすべてのデータを読み込む"""
        unified_db_path = self.base_dir / "database" / "unified_teams.json"

        if not unified_db_path.exists():
            raise FileNotFoundError(f"Unified database not found: {unified_db_path}")

        try:
            with open(unified_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.english_to_japanese = {key: set(aliases) for key, aliases in data.items()}

        except Exception as e:
            print(f"❌ 統合データベースの読み込みに失敗しました: {e}")
            raise

    def normalize(self, text: str) -> str:
        """正規化: 日本語の表記揺れを吸収し、比較可能な文字列を生成"""
        if not text:
            return ""

        # 1. カタカナをひらがなに変換
        hira_text = []
        for char in text:
            ord_val = ord(char)
            if 0x30A1 <= ord_val <= 0x30F6:
                hira_text.append(chr(ord_val - 0x60))
            else:
                hira_text.append(char)
        text = "".join(hira_text)

        # 2. 全体を小文字に変換 (アルファベット用)
        text = text.lower()

        # 3. ひらがな、英数字以外のすべての文字を削除
        cleaned_text = []
        for char in text:
            is_hira = 'ぁ' <= char <= 'ん'
            is_alpha = 'a' <= char <= 'z'
            is_num = '0' <= char <= '9'
            if is_hira or is_alpha or is_num:
                cleaned_text.append(char)

        return "".join(cleaned_text)

    def match(self, api_team_english: str, user_teams_japanese: List[str]) -> bool:
        """APIチーム名(英語)とユーザー入力(日本語リスト)をマッチング (あいまい検索対応版)"""
        if not api_team_english or not user_teams_japanese:
            return False

        api_lower = api_team_english.lower().strip()
        japanese_candidates = self.english_to_japanese.get(api_lower, set())

        if not japanese_candidates:
            # マッチング失敗: DBに未登録
            self._log_failure(api_team_english, user_teams_japanese[0], "not_in_db")
            return False

        user_team_input = user_teams_japanese[0]
        if not user_team_input:
            return False

        user_team_normalized = self.normalize(user_team_input)

        for candidate in japanese_candidates:
            candidate_normalized = self.normalize(candidate)
            if not candidate_normalized:
                continue

            # 1. 完全一致（正規化後）
            if user_team_normalized == candidate_normalized:
                return True

            # 2. あいまい検索（類似度スコア）
            ratio = SequenceMatcher(None, user_team_normalized, candidate_normalized).ratio()
            if ratio >= 0.85:  # 類似度のしきい値
                return True

        # マッチング失敗: DBにあるが候補が一致せず
        self._log_failure(api_team_english, user_team_input, "no_match")
        return False

    def get_japanese_candidates(self, api_team_english: str) -> Set[str]:
        api_lower = api_team_english.lower().strip()
        return self.english_to_japanese.get(api_lower, set())

    def get_english_name(self, japanese_name: str) -> Optional[str]:
        """
        日本語チーム名から英語チーム名を取得 (パーサー用)

        The Odds API互換性のため、最も長い完全形のチーム名を優先的に返す。
        例: "bha" より "brighton & hove albion" を優先
        """
        japanese_normalized = japanese_name.strip()
        matched_keys = []

        # マッチする全てのキーを収集
        for english, japanese_candidates in self.english_to_japanese.items():
            if japanese_normalized in japanese_candidates:
                matched_keys.append(english)

        if not matched_keys:
            return None

        # 最も長いキーを選択（完全形のチーム名を優先）
        # 例: ["bha", "brighton", "brighton & hove albion"] → "brighton & hove albion"
        longest_key = max(matched_keys, key=len)
        return longest_key.title()

    def get_sport(self, team_name: str) -> Optional[str]:
        # この機能は辞書一元化で一旦廃止。必要ならDB構造の拡張が必要。
        return None

    def _log_failure(self, api_team: str, user_input: str, failure_type: str):
        """
        マッチング失敗をログに記録

        Args:
            api_team: APIから取得した英語チーム名
            user_input: ユーザーが入力した日本語チーム名
            failure_type: 失敗の種類 ("not_in_db" or "no_match")
        """
        if not self.enable_logging:
            return

        try:
            # ログディレクトリ作成
            self.failure_log_path.parent.mkdir(parents=True, exist_ok=True)

            # ログエントリ構築
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "api_team": api_team,
                "user_input": user_input,
                "normalized_input": self.normalize(user_input),
                "failure_type": failure_type
            }

            # JSONL形式で追記（1行1エントリ）
            with open(self.failure_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

        except Exception as e:
            # ログ書き込み失敗は無視（マッチング処理に影響させない）
            pass


_reverse_matcher = None


def get_reverse_matcher() -> ReverseTeamMatcher:
    """シングルトンインスタンスを取得"""
    global _reverse_matcher
    if _reverse_matcher is None:
        _reverse_matcher = ReverseTeamMatcher()
    return _reverse_matcher
