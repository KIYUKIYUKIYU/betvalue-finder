# -*- coding: utf-8 -*-
"""
parsers/mlb.py
MLB専用パーサー
"""

import json
import os
import sys

# スタンドアロン実行対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from parsers.base import SportParserBase
except ModuleNotFoundError:
    from base import SportParserBase

from typing import Dict

class MLBParser(SportParserBase):
    """MLB専用パーサー"""
    
    def get_sport_name(self) -> str:
        """スポーツ名を返す"""
        return "MLB"
    
    def load_teams_data(self) -> Dict:
        """MLBチームデータをJSONから読み込み"""
        json_path = os.path.join(
            os.path.dirname(__file__),
            '../data/sports/mlb/teams.json'
        )
        
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"警告: {json_path} が見つかりません。デフォルトデータを使用します。")
            return self.get_default_teams_data()
    
    def load_rules(self) -> Dict:
        """MLB固有のルールを読み込み"""
        return {
            'team_count': 30,
            'leagues': ['アメリカンリーグ', 'ナショナルリーグ'],
            'handicap_format': 'runline',
            'extension': True,  # 延長あり
            'max_innings': 'unlimited'  # 延長無制限
        }
    
    def get_default_teams_data(self) -> Dict:
        """デフォルトのMLBチームデータ（ファイルがない場合のフォールバック）"""
        return {
            "teams": {
                "BAL": {
                    "id": "BAL",
                    "primary_name_jp": "オリオールズ",
                    "primary_name_en": "Orioles",
                    "aliases": {
                        "jp": ["ボルチモア", "ボルチモア・オリオールズ"],
                        "en": ["Baltimore", "Baltimore Orioles"]
                    },
                    "league": "AL",
                    "division": "East"
                },
                "BOS": {
                    "id": "BOS",
                    "primary_name_jp": "レッドソックス",
                    "primary_name_en": "Red Sox",
                    "aliases": {
                        "jp": ["Rソックス", "赤ソックス", "ボストン"],
                        "en": ["Boston", "Boston Red Sox", "BoSox"]
                    },
                    "league": "AL",
                    "division": "East"
                },
                "NYY": {
                    "id": "NYY",
                    "primary_name_jp": "ヤンキース",
                    "primary_name_en": "Yankees",
                    "aliases": {
                        "jp": ["ニューヨーク・ヤンキース", "NYヤンキース"],
                        "en": ["New York Yankees", "NY Yankees"]
                    },
                    "league": "AL",
                    "division": "East"
                },
                "TB": {
                    "id": "TB",
                    "primary_name_jp": "レイズ",
                    "primary_name_en": "Rays",
                    "aliases": {
                        "jp": ["タンパベイ", "タンパベイ・レイズ"],
                        "en": ["Tampa Bay", "Tampa Bay Rays"]
                    },
                    "league": "AL",
                    "division": "East"
                },
                "TOR": {
                    "id": "TOR",
                    "primary_name_jp": "ブルージェイズ",
                    "primary_name_en": "Blue Jays",
                    "aliases": {
                        "jp": ["トロント", "トロント・ブルージェイズ"],
                        "en": ["Toronto", "Toronto Blue Jays"]
                    },
                    "league": "AL",
                    "division": "East"
                },
                "CWS": {
                    "id": "CWS",
                    "primary_name_jp": "ホワイトソックス",
                    "primary_name_en": "White Sox",
                    "aliases": {
                        "jp": ["Wソックス", "白ソックス", "シカゴ・ホワイトソックス"],
                        "en": ["Chicago White Sox", "ChiSox"]
                    },
                    "league": "AL",
                    "division": "Central"
                },
                "LAD": {
                    "id": "LAD",
                    "primary_name_jp": "ドジャース",
                    "primary_name_en": "Dodgers",
                    "aliases": {
                        "jp": ["ロサンゼルス・ドジャース", "LAドジャース"],
                        "en": ["Los Angeles Dodgers", "LA Dodgers"]
                    },
                    "league": "NL",
                    "division": "West"
                },
                "SF": {
                    "id": "SF",
                    "primary_name_jp": "ジャイアンツ",
                    "primary_name_en": "Giants",
                    "aliases": {
                        "jp": ["サンフランシスコ", "サンフランシスコ・ジャイアンツ"],
                        "en": ["San Francisco", "San Francisco Giants"]
                    },
                    "league": "NL",
                    "division": "West"
                },
                "SD": {
                    "id": "SD",
                    "primary_name_jp": "パドレス",
                    "primary_name_en": "Padres",
                    "aliases": {
                        "jp": ["サンディエゴ", "サンディエゴ・パドレス"],
                        "en": ["San Diego", "San Diego Padres"]
                    },
                    "league": "NL",
                    "division": "West"
                },
                "HOU": {
                    "id": "HOU",
                    "primary_name_jp": "アストロズ",
                    "primary_name_en": "Astros",
                    "aliases": {
                        "jp": ["ヒューストン", "ヒューストン・アストロズ"],
                        "en": ["Houston", "Houston Astros"]
                    },
                    "league": "AL",
                    "division": "West"
                }
            }
        }


# テスト用
if __name__ == "__main__":
    parser = MLBParser()
    
    test_text = """
    22時締切
    [MLB]
    
    オリオールズ
    レッドソックス<0.1>
    
    ヤンキース13
    アストロズ
    
    ドジャース<1.5>
    ジャイアンツ
    """
    
    games = parser.parse(test_text)
    
    print("=" * 50)
    print("MLBパーサーテスト結果")
    print("=" * 50)
    
    for i, game in enumerate(games, 1):
        print(f"\n試合{i}:")
        print(f"  {game['team_a']} vs {game['team_b']}")
        print(f"  ハンデ: {game['handicap']}")
        print(f"  フェイバリット: {game['fav_team']}")
        print(f"  信頼度: {game['confidence']:.0%}")