# -*- coding: utf-8 -*-
"""
universal_parser.py
あらゆる形式のベッティングデータを解析する汎用パーサー
"""

import re
from typing import List, Dict, Optional, Tuple

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
        r'^\[.*\]$',          # [MLB]など
        r'^-+$',              # 区切り線
        r'^\d{4}/\d{2}/\d{2}', # 日付
        r'^最終締切',          # 締切表記
    ]
    
    def __init__(self):
        self.games = []
        self.pending_team = None
        self.pending_handicap = None
    
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
    
    def parse_handicap_value(self, text: str) -> Optional[str]:
        """ハンデ値を抽出（06→0.6, 1半8→1半8）"""
        # 数字のみ（01, 06, 08など）
        if re.match(r'^\d{2}$', text):
            return f"0.{text[1]}"
        
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
        
        # パターン1: チーム名<ハンデ>
        match = re.match(r'^(.+?)<(.+?)>$', line)
        if match:
            return {
                'team': match.group(1).strip(),
                'handicap': match.group(2).strip(),
                'type': 'team_with_handicap'
            }
        
        # パターン2: チーム名 + 数字（Rソックス06）
        match = re.match(r'^(.+?)((?:\d{2}|\d+\.\d+|\d*半\d*))$', line)
        if match:
            team = match.group(1).strip()
            handicap = self.parse_handicap_value(match.group(2))
            if handicap:
                return {
                    'team': team,
                    'handicap': handicap,
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
        
        # パターン4: チーム名 スペース ハンデ
        parts = line.split()
        if len(parts) == 2:
            team = parts[0]
            handicap = self.parse_handicap_value(parts[1])
            if handicap:
                return {
                    'team': team,
                    'handicap': handicap,
                    'type': 'team_space_handicap'
                }
        
        # パターン5: 単純なチーム名
        return {
            'team': line,
            'type': 'team_only'
        }
    
    def parse(self, text: str) -> List[Dict]:
        """テキスト全体を解析"""
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
                
            elif item['type'] in ['team_with_handicap', 'team_with_suffix']:
                # ハンデ付きチーム
                if pending_team:
                    # 前のチームとペア
                    games.append({
                        'team_a': pending_team['team'],
                        'team_b': item['team'],
                        'handicap': item['handicap'],
                        'fav_team': item['team']
                    })
                    pending_team = None
                elif pending_matchup:
                    # 対戦カードの補完
                    games.append({
                        'team_a': pending_matchup['home'],
                        'team_b': pending_matchup['away'],
                        'handicap': item['handicap'],
                        'fav_team': item['team']
                    })
                    pending_matchup = None
                else:
                    pending_team = item
                    
            elif item['type'] == 'team_space_handicap':
                # スペース区切りハンデ（対戦カード後）
                if pending_matchup:
                    games.append({
                        'team_a': pending_matchup['home'],
                        'team_b': pending_matchup['away'],
                        'handicap': item['handicap'],
                        'fav_team': item['team']
                    })
                    pending_matchup = None
                    
            elif item['type'] == 'team_only':
                # チーム名のみ
                if pending_team and 'handicap' in pending_team:
                    # ハンデ付きチームの相手
                    games.append({
                        'team_a': pending_team['team'],
                        'team_b': item['team'],
                        'handicap': pending_team['handicap'],
                        'fav_team': pending_team['team']
                    })
                    pending_team = None
                else:
                    pending_team = item
        
        return games


# テスト用
if __name__ == "__main__":
    parser = UniversalBetParser()
    
    # テストケース1: 数字後ろ形式
    test1 = """
    オリオールズ
    Rソックス06
    """
    
    result = parser.parse(test1)
    print("テスト1:", result)
    
    # テストケース2: 対戦カード形式
    test2 = """
    オリオールズ - 赤ソックス
    赤ソックス 0.3
    """
    
    result = parser.parse(test2)
    print("テスト2:", result)