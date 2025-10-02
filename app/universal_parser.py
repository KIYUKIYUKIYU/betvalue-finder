# -*- coding: utf-8 -*-
"""
universal_parser.py
あらゆる形式のベッティングデータを解析する汎用パーサー
"""

import re
from typing import List, Dict, Optional, Tuple
from converter.handicap_parser import HandicapParser

class UniversalBetParser:
    """汎用ベッティングデータパーサー"""
    
    # 略称辞書
    ABBREVIATIONS = {
        "Wソックス": "ホワイトソックス",
        "Rソックス": "レッドソックス", 
        "赤ソックス": "レッドソックス",
        "白ソックス": "ホワイトソックス",
        "Dバックス": "ダイヤモンドバックス",
        "Ｄバックス": "ダイヤモンドバックス",
    }
    
    # スキップパターン
    SKIP_PATTERNS = [
        r'^\d{1,2}:\d{2}$',  # 時刻
        r'^<.*リーグ>$',      # リーグ区分
        r'^<[^<>]*>$',        # 単独のタグ（<エール>、<CL>など）
        r'^\s*\[.*\]\s*$',          # [MLB]など
        r'^-+$',              # 区切り線
        r'^\d{4}/\d{2}/\d{2}', # 日付
        r'^最終締切',          # 締切表記
    ]
    
    def __init__(self, team_database: Optional[Dict[str, Dict]] = None):
        self.games = []
        self.pending_team = None
        self.pending_handicap = None
        self.team_database = team_database or {}
    
    def normalize_text(self, text: str) -> str:
        """テキストの正規化"""
        # 略称を変換
        for abbr, full in self.ABBREVIATIONS.items():
            text = text.replace(abbr, full)
        return text
    
    def should_skip(self, line: str) -> bool:
        """スキップすべき行かチェック"""
        for pattern in self.SKIP_PATTERNS:
            if re.match(pattern, line):
                return True
        return False

    def _lookup_sport_from_team(self, team_name: str) -> Optional[str]:
        """チーム名からsportを逆引き（キー名、aliases、部分一致で検索）"""
        if not team_name or not self.team_database:
            return None

        # 完全一致（キー名）
        if team_name in self.team_database:
            return self.team_database[team_name].get("sport")

        # aliases検索
        for db_team, info in self.team_database.items():
            aliases = info.get("aliases", [])
            if team_name in aliases:
                return info.get("sport")

        # 部分一致（キー名）
        for db_team, info in self.team_database.items():
            if team_name in db_team or db_team in team_name:
                return info.get("sport")

        return None

    def parse_handicap_value(self, text: str) -> Optional[str]:
        """ハンデ値を抽出（06→0.6, 1半8→1半8, 0/5→0.5）"""
        # 分数形式（0/5→0.5など）
        if re.match(r'^\d/\d$', text):
            # サッカー特殊表記の変換マッピング
            fraction_mappings = {
                "0/1": "0.1", "0/2": "0.2", "0/3": "0.3", "0/4": "0.4", "0/5": "0.5",
                "0/6": "0.6", "0/7": "0.7", "0/8": "0.8", "0/9": "0.9"
            }
            return fraction_mappings.get(text, text)

        # 数字のみ（01, 06, 08など）
        if re.match(r'^\d{2}$', text):
            return f"0.{text[1]}"

        # 整数のみ（0, 1, 2など）
        if re.match(r'^\d+$', text):
            return text

        # 1.1, 1.3など
        if re.match(r'^\d+\.\d+$', text):
            return text

        # 1半, 1半8など
        if '半' in text:
            return text

        return None
    
    def parse_line(self, line: str) -> Optional[Dict]:
        """1行を解析"""
        line = line.strip()
        
        if not line or self.should_skip(line):
            return None
        
        # パターン1: チーム名<ハンデ>チーム名（修正版：第2チーム名も取得）
        match = re.match(r'^(.+?)[<＜〈]([^>＞〉]+)[>＞〉](.+?)$', line)
        if match:
            team1 = match.group(1).strip()
            handicap_str = match.group(2).strip()
            team2 = match.group(3).strip()
            
            # HandicapParserで解析して数値変換
            handicap_parsed, handicap_value = HandicapParser.detect_handicap_in_text(f'<{handicap_str}>')
            return {
                'team1': team1,
                'team2': team2,
                'handicap': str(handicap_value) if handicap_value is not None else handicap_str,
                'raw_handicap': handicap_str,  # 元の文字列を保持
                'handicap_value': handicap_value,
                'type': 'team_vs_team_with_handicap'
            }
        
        # パターン2: チーム名 + 数字（Rソックス06, エヴァートン0/5）
        match = re.match(r'^(.+?)((?:\d{2}|\d+\.\d+|\d*半\d*|\d/\d))$', line)
        if match:
            team = match.group(1).strip()
            raw_handicap_str = match.group(2)
            handicap = self.parse_handicap_value(raw_handicap_str)
            if handicap:
                return {
                    'team': team,
                    'handicap': handicap,
                    'raw_handicap': raw_handicap_str,  # 元の文字列を保持
                    'type': 'team_with_suffix'
                }
        
        # パターン3: チーム名 - チーム名（対戦カード）
        if ' - ' in line:
            teams = line.split(' - ')
            if len(teams) == 2:
                return {
                    'home': teams[0].strip(),
                    'away': teams[1].strip(),
                    'type': 'matchup'
                }
        
        # パターン4: チーム名<ハンデ>（単体）
        match = re.match(r'^(.+?)[<＜〈]([^>＞〉]+)[>＞〉]$', line)
        if match:
            team = match.group(1).strip()
            handicap_str = match.group(2).strip()

            # HandicapParserで解析して数値変換
            handicap_parsed, handicap_value = HandicapParser.detect_handicap_in_text(f'<{handicap_str}>')
            return {
                'team': team,
                'handicap': str(handicap_value) if handicap_value is not None else handicap_str,
                'raw_handicap': handicap_str,  # 元の文字列を保持
                'handicap_value': handicap_value,
                'type': 'team_with_handicap'
            }

        # パターン5: チーム名 スペース ハンデ
        parts = line.split()
        if len(parts) == 2:
            team = parts[0]
            raw_handicap_str = parts[1]
            handicap = self.parse_handicap_value(raw_handicap_str)
            if handicap:
                return {
                    'team': team,
                    'handicap': handicap,
                    'raw_handicap': raw_handicap_str,  # 元の文字列を保持
                    'type': 'team_space_handicap'
                }

        # パターン6: 単純なチーム名
        return {
            'team': line,
            'type': 'team_only'
        }
    
    def parse(self, text: str) -> List[Dict]:
        """テキスト全体を解析"""
        # 旧式の正規化は削除（HandicapParserに委ねる）
        text = self.normalize_text(text)
        lines = text.strip().split('\n')
        
        parsed_items = []
        for line in lines:
            item = self.parse_line(line)
            if item:
                parsed_items.append(item)
        
        # パースされた項目からゲームを構築
        return self.build_games(parsed_items)
    
    def build_games(self, items: List[Dict]) -> List[Dict]:
        """パースされた項目からゲームを構築"""
        games = []
        pending_team = None
        pending_matchup = None
        
        for item in items:
            if item['type'] == 'matchup':
                # 対戦カード形式
                pending_matchup = item
                
            elif item['type'] == 'team_vs_team_with_handicap':
                # 新タイプ: チーム名<ハンデ>チーム名（修正版で追加）
                sport = (self._lookup_sport_from_team(item['team1']) or
                        self._lookup_sport_from_team(item['team2']))
                games.append({
                    'team_a': item['team1'],
                    'team_b': item['team2'],
                    'handicap': item['handicap'],
                    'raw_handicap': item.get('raw_handicap'),
                    'fav_team': item['team1'],  # ハンデ付きチーム（team1）= フェイバリット
                    'sport': sport
                })
                
            elif item['type'] in ['team_with_handicap', 'team_with_suffix']:
                # ハンデ付きチーム（従来タイプ）
                if pending_team:
                    # 前のチームとペア
                    sport = (self._lookup_sport_from_team(pending_team['team']) or
                            self._lookup_sport_from_team(item['team']))
                    games.append({
                        'team_a': pending_team['team'],
                        'team_b': item['team'],
                        'handicap': item['handicap'],
                        'raw_handicap': item.get('raw_handicap'),
                        'fav_team': item['team'],  # ハンデ付きチーム = フェイバリット
                        'sport': sport
                    })
                    pending_team = None
                elif pending_matchup:
                    # 対戦カードの補完
                    sport = (self._lookup_sport_from_team(pending_matchup['home']) or
                            self._lookup_sport_from_team(pending_matchup['away']) or
                            self._lookup_sport_from_team(item['team']))
                    games.append({
                        'team_a': pending_matchup['home'],
                        'team_b': pending_matchup['away'],
                        'handicap': item['handicap'],
                        'raw_handicap': item.get('raw_handicap'),
                        'fav_team': item['team'],  # ハンデ付きチーム = フェイバリット
                        'sport': sport
                    })
                    pending_matchup = None
                else:
                    pending_team = item
                    
            elif item['type'] == 'team_space_handicap':
                # スペース区切りハンデ（対戦カード後）
                if pending_matchup:
                    sport = (self._lookup_sport_from_team(pending_matchup['home']) or
                            self._lookup_sport_from_team(pending_matchup['away']) or
                            self._lookup_sport_from_team(item['team']))
                    games.append({
                        'team_a': pending_matchup['home'],
                        'team_b': pending_matchup['away'],
                        'handicap': item['handicap'],
                        'raw_handicap': item.get('raw_handicap'),
                        'fav_team': item['team'],  # ハンデ付きチーム = フェイバリット
                        'sport': sport
                    })
                    pending_matchup = None
                    
            elif item['type'] == 'team_only':
                # チーム名のみ
                if pending_team and 'handicap' in pending_team:
                    # ハンデ付きチームの相手
                    sport = (self._lookup_sport_from_team(pending_team['team']) or
                            self._lookup_sport_from_team(item['team']))
                    games.append({
                        'team_a': pending_team['team'],
                        'team_b': item['team'],
                        'handicap': pending_team['handicap'],
                        'raw_handicap': pending_team.get('raw_handicap'),
                        'fav_team': pending_team['team'],  # ハンデ付きチーム = フェイバリット
                        'sport': sport
                    })
                    pending_team = None
                else:
                    pending_team = item
        
        return games


# テスト用
if __name__ == "__main__":
    parser = UniversalBetParser()
    
    # テストケース1: 修正されたパターン（チーム名<ハンデ>チーム名）
    test1 = "レッドソックス<0.9>ヤンキース"
    result = parser.parse(test1)
    print("テスト1（修正されたパターン）:", result)
    
    # テストケース2: 数字後ろ形式（従来のまま）
    test2 = """
    オリオールズ
    Rソックス06
    """
    result = parser.parse(test2)
    print("テスト2:", result)
    
    # テストケース3: 対戦カード形式（従来のまま）
    test3 = """
    オリオールズ - 赤ソックス
    赤ソックス 0.3
    """
    result = parser.parse(test3)
    print("テスト3:", result)
    
    # テストケース4: 追加テスト
    test4 = "ドジャース<1.5>パドレス"
    result = parser.parse(test4)
    print("テスト4（追加テスト）:", result)