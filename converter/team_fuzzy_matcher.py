#!/usr/bin/env python3
"""
ファジーマッチング対応チーム名マッチャー
API先行アプローチによる堅牢なチーム名解決
"""

from difflib import SequenceMatcher
import re
from typing import List, Dict, Tuple, Optional


class TeamFuzzyMatcher:
    """ファジーマッチングによるチーム名解決"""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

        # 日本語→英語変換マッピング (基本的なもの)
        self.jp_to_en = {
            # サッカー主要チーム
            "スポルティング": "sporting",
            "カイラト": "kairat",
            "マンチェスター": "manchester",
            "マンチェスターシティ": "manchester city",
            "マンチェスターユナイテッド": "manchester united",
            "レアル": "real madrid",
            "レアルマドリード": "real madrid",
            "バルセロナ": "barcelona",
            "バイエルン": "bayern",
            "パリ": "paris saint germain",
            "リバプール": "liverpool",
            "チェルシー": "chelsea",
            "アーセナル": "arsenal",
            "トッテナム": "tottenham",
            "ユベントス": "juventus",
            "ミラン": "milan",
            "インテル": "inter",
            "ドルトムント": "borussia dortmund",
            "アトレティコ": "atletico madrid",
            "セビージャ": "sevilla",
            "ナポリ": "napoli",
            "ローマ": "roma",
            "フィオレンティーナ": "fiorentina",
            "ベンフィカ": "benfica",
            "ポルト": "porto",
            "アヤックス": "ajax",
            "PSV": "psv",
            "セルティック": "celtic",
            "レンジャーズ": "rangers"
        }

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """2つの文字列の類似度を計算（0.0〜1.0）"""
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def fuzzy_match_team(self, user_input: str, api_teams: List[str]) -> Optional[Tuple[str, float]]:
        """
        ファジーマッチング: ユーザー入力に最も近いAPIチーム名を見つける
        """
        best_match = None
        best_score = 0.0

        user_normalized = user_input.lower().strip()

        # 翻訳候補を生成
        candidates = [user_normalized]
        if user_normalized in self.jp_to_en:
            candidates.append(self.jp_to_en[user_normalized])

        for api_team in api_teams:
            api_normalized = api_team.lower().strip()

            # 複数の類似度計算手法
            scores = []

            for candidate in candidates:
                # 1. 完全文字列類似度
                scores.append(self.calculate_similarity(candidate, api_normalized))

                # 2. 部分マッチング（単語レベル）
                user_words = set(candidate.split())
                api_words = set(api_normalized.split())
                if api_words:
                    word_overlap = len(user_words & api_words) / len(api_words)
                    scores.append(word_overlap)

                # 3. 部分文字列マッチング
                if candidate in api_normalized:
                    scores.append(0.9)  # 高スコア

                # 4. 頭文字マッチング
                if len(candidate) >= 3 and api_normalized.startswith(candidate[:3]):
                    scores.append(0.8)

            # 最高スコアを採用
            final_score = max(scores) if scores else 0.0

            if final_score > best_score and final_score >= self.threshold:
                best_score = final_score
                best_match = api_team

        return (best_match, best_score) if best_match else None

    def api_first_team_matching(self, user_text: str, available_games: List[Dict]) -> Optional[Dict]:
        """
        API先行アプローチでチーム名マッチング
        """
        # 1. APIから利用可能なチーム名を抽出
        api_teams = set()
        for game in available_games:
            home = game.get("home", "")
            away = game.get("away", "")
            if home:
                api_teams.add(home)
            if away:
                api_teams.add(away)

        api_teams = list(api_teams)
        print(f"📋 利用可能APIチーム数: {len(api_teams)}")

        # 2. ユーザー入力からチーム名を抽出
        # "vs"、"対"、改行などで分割
        text_normalized = user_text.replace("対", " vs ").replace("\n", " vs ")
        team_parts = re.split(r'\s+vs\s+|\s+v\s+|\s+V\s+|\s+-\s+', text_normalized, flags=re.IGNORECASE)

        # ハンディキャップ記号を除去
        cleaned_parts = []
        for part in team_parts:
            # <数字>、(数字)、[数字] などを除去
            cleaned = re.sub(r'[<(\[][\.\\d\-\+半]+[>)\]]', '', part).strip()
            # 数字やオッズを除去
            cleaned = re.sub(r'\b\d+[\.\\d]*倍?\b', '', cleaned).strip()
            if cleaned and len(cleaned) > 1:
                cleaned_parts.append(cleaned)

        if len(cleaned_parts) < 2:
            print(f"❌ チーム名を2つ抽出できませんでした: {cleaned_parts}")
            return None

        print(f"🔍 抽出したチーム名: {cleaned_parts[:2]}")

        # 3. ファジーマッチングで最適なAPIチーム名を見つける
        matched_teams = []
        for user_team in cleaned_parts[:2]:  # 最初の2チームのみ
            match_result = self.fuzzy_match_team(user_team, api_teams)
            if match_result:
                api_team, score = match_result
                matched_teams.append(api_team)
                print(f"✅ '{user_team}' → '{api_team}' (類似度: {score:.2f})")
            else:
                print(f"❌ '{user_team}' にマッチするAPIチームが見つかりません")

        if len(matched_teams) < 2:
            print(f"❌ 2チームをマッチングできませんでした")
            return None

        # 4. マッチしたチーム名で試合を検索
        team1, team2 = matched_teams[0], matched_teams[1]
        for game in available_games:
            home = game.get("home", "")
            away = game.get("away", "")

            # 順序に関係なくマッチング
            if (home == team1 and away == team2) or (home == team2 and away == team1):
                print(f"🎯 試合発見: {home} vs {away}")
                return game

        print(f"❌ 試合が見つかりません: {team1} vs {team2}")
        return None

    def match_teams_fuzzy(self, team_names: List[str], games: List[Dict]) -> Optional[Dict]:
        """
        従来のmatch_teamsメソッドの代替
        ファジーマッチング版
        """
        if len(team_names) < 2:
            return None

        # APIから全チーム名を抽出
        api_teams = set()
        for game in games:
            home = game.get("home", "")
            away = game.get("away", "")
            if home:
                api_teams.add(home)
            if away:
                api_teams.add(away)

        api_teams = list(api_teams)

        # 各ユーザー入力チーム名をファジーマッチング
        matched_teams = []
        for user_team in team_names[:2]:
            match_result = self.fuzzy_match_team(user_team, api_teams)
            if match_result:
                matched_teams.append(match_result[0])
                print(f"🔍 FUZZY: '{user_team}' → '{match_result[0]}' (類似度: {match_result[1]:.2f})")

        if len(matched_teams) < 2:
            return None

        # マッチしたチーム名で試合検索
        team1, team2 = matched_teams[0], matched_teams[1]
        for game in games:
            home = game.get("home", "")
            away = game.get("away", "")

            if (home == team1 and away == team2) or (home == team2 and away == team1):
                return game

        return None