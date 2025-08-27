# -*- coding: utf-8 -*-
"""
parsers/base.py
すべてのスポーツパーサーの基底クラス
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import json
import re
import os

class SportParserBase(ABC):
    """すべてのスポーツパーサーの基底クラス"""
    
    def __init__(self):
        self.teams_data = self.load_teams_data()
        self.rules = self.load_rules()
        self.confidence_threshold = 0.3
    
    @abstractmethod
    def get_sport_name(self) -> str:
        """スポーツ名を返す"""
        pass
    
    @abstractmethod
    def load_teams_data(self) -> Dict:
        """チームデータをJSONから読み込み"""
        pass
    
    @abstractmethod
    def load_rules(self) -> Dict:
        """スポーツ固有のルールを読み込み"""
        pass
    
    def identify_team(self, text: str) -> Tuple[Optional[str], float]:
        """
        チーム名を識別し、信頼度スコアを返す
        戻り値: (正規化されたチーム名, 信頼度0.0-1.0)
        """
        if not self.teams_data:
            return (None, 0.0)
        
        # 1. 完全一致チェック（信頼度1.0）
        for team_id, data in self.teams_data.get('teams', {}).items():
            if text == data.get('primary_name_jp'):
                return (data['primary_name_jp'], 1.0)
            
            # エイリアスチェック
            aliases_jp = data.get('aliases', {}).get('jp', [])
            if text in aliases_jp:
                return (data['primary_name_jp'], 1.0)
        
        # 2. 部分一致チェック（信頼度0.7）
        for team_id, data in self.teams_data.get('teams', {}).items():
            primary = data.get('primary_name_jp')
            if primary and (primary in text or text in primary):
                return (primary, 0.7)
            
            # エイリアス部分一致
            for alias in data.get('aliases', {}).get('jp', []):
                if alias in text or text in alias:
                    return (data['primary_name_jp'], 0.7)
        
        # 3. 未知のチーム（信頼度0.2）
        if self._looks_like_team(text):
            return (text, 0.2)
        
        return (None, 0.0)
    
    def _looks_like_team(self, text: str) -> bool:
        """チーム名っぽいかの判定"""
        # カタカナまたは英字を含む
        if not re.search(r'[ァ-ヴーa-zA-Z]', text):
            return False
        
        # 最低2文字以上
        if len(text) < 2:
            return False
        
        # 記号だけではない
        if re.match(r'^[\d\[\]()<>（）\-_\s\.:：締切時]+$', text):
            return False
        
        return True
    
    def extract_handicap(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """ハンデ記号を抽出"""
        # <ハンデ>形式
        match = re.match(r'^(.+?)<(.+?)>$', line.strip())
        if match:
            return (match.group(1).strip(), match.group(2).strip())
        
        # 数字直付け（05, 14など）
        match = re.match(r'^(.+?)(\d{2})$', line.strip())
        if match:
            handicap_raw = match.group(2)
            if handicap_raw[0] == '0':
                handicap = f"0.{handicap_raw[1]}"
            else:
                handicap = f"{handicap_raw[0]}.{handicap_raw[1]}"
            return (match.group(1).strip(), handicap)
        
        # 日本式（1半、1半8など）
        match = re.match(r'^(.+?)(\d*半\d*)$', line.strip())
        if match:
            return (match.group(1).strip(), match.group(2))
        
        # 小数点付き
        match = re.match(r'^(.+?)(\d+\.\d+)$', line.strip())
        if match:
            return (match.group(1).strip(), match.group(2))
        
        # ハンデなし
        return (line.strip(), None)
    
    def parse(self, text: str) -> List[Dict]:
        """テキストを解析して試合リストを返す"""
        # 正規化（全角→半角など）
        text = text.replace('＜', '<').replace('＞', '>')
        
        # 行に分割
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # チーム情報を抽出
        teams = []
        for line in lines:
            team_text, handicap = self.extract_handicap(line)
            if team_text:
                team_name, confidence = self.identify_team(team_text)
                if confidence >= self.confidence_threshold:
                    teams.append({
                        'team': team_name or team_text,
                        'handicap': handicap,
                        'confidence': confidence,
                        'original': line
                    })
                elif confidence > 0:
                    # 低信頼度の警告
                    print(f"⚠ 低信頼度({confidence:.0%}): {team_text}")
        
        # 2チームずつペアリング
        games = []
        for i in range(0, len(teams), 2):
            if i + 1 < len(teams):
                team1 = teams[i]
                team2 = teams[i + 1]
                
                # ハンデがある方をフェイバリットに
                if team1['handicap']:
                    games.append({
                        'team_a': team1['team'],
                        'team_b': team2['team'],
                        'handicap': team1['handicap'],
                        'fav_team': team1['team'],
                        'confidence': min(team1['confidence'], team2['confidence'])
                    })
                elif team2['handicap']:
                    games.append({
                        'team_a': team1['team'],
                        'team_b': team2['team'],
                        'handicap': team2['handicap'],
                        'fav_team': team2['team'],
                        'confidence': min(team1['confidence'], team2['confidence'])
                    })
        
        return games