# -*- coding: utf-8 -*-
"""
converter/odds_processor.py
オッズ処理モジュール
APIレスポンスからハンデオッズを抽出し、補間用データ形式に変換
"""

from typing import Dict, List, Tuple, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)


class OddsProcessor:
    """オッズデータの抽出・処理を行うクラス"""
    
    # ハンデマーケット名のバリエーション
    HANDICAP_MARKETS = [
        "Asian Handicap",
        "Handicap",
        "Run Line",
        "Runline", 
        "Spreads",
        "Spread",
        "Alternative Handicap",
        "European Handicap"
    ]
    
    # 優先ブックメーカー
    PREFERRED_BOOKMAKERS = {
        4: "Pinnacle",
        2: "Bet365",
        8: "bet365"
    }
    
    def __init__(self):
        """初期化"""
        pass
    
    def extract_handicap_odds(
        self, 
        bookmakers: List[Dict[str, Any]],
        preferred_bookmaker_id: int = 4
    ) -> Dict[float, Tuple[float, float]]:
        """
        ブックメーカーデータからハンデオッズを抽出
        
        Args:
            bookmakers: APIレスポンスのbookmakersリスト
            preferred_bookmaker_id: 優先するブックメーカーID（デフォルト: 4=Pinnacle）
            
        Returns:
            {ライン値: (home_odds, away_odds)} の辞書
        """
        line_data = {}
        
        # 優先ブックメーカーを先に処理
        bookmakers_sorted = sorted(
            bookmakers,
            key=lambda x: 0 if x.get("id") == preferred_bookmaker_id else 1
        )
        
        for bookmaker in bookmakers_sorted:
            bm_id = bookmaker.get("id")
            bm_name = bookmaker.get("name", "Unknown")
            
            # ベットデータを処理
            for bet in bookmaker.get("bets", []):
                market_name = bet.get("name", "")
                
                # ハンデマーケットかチェック
                if not any(hm in market_name for hm in self.HANDICAP_MARKETS):
                    continue
                
                # バリューデータを処理
                for value in bet.get("values", []):
                    value_str = str(value.get("value", ""))
                    odds = value.get("odd")
                    
                    if not value_str or not odds:
                        continue
                    
                    try:
                        odd_val = float(odds)
                        
                        # API-Sports形式: "Home -1.5" や "Away +1.5"
                        if "Home" in value_str:
                            # "Home -1.5" から -1.5 を抽出
                            line_val = self._parse_handicap_from_string(value_str)
                            if line_val is not None:
                                if line_val not in line_data:
                                    line_data[line_val] = [None, None]
                                line_data[line_val][0] = odd_val
                                
                        elif "Away" in value_str:
                            # "Away +1.5" から +1.5 を抽出
                            line_val = self._parse_handicap_from_string(value_str)
                            if line_val is not None:
                                # Awayの場合は符号を反転（Home視点の統一ラインにする）
                                line_val = -line_val
                                if line_val not in line_data:
                                    line_data[line_val] = [None, None]
                                line_data[line_val][1] = odd_val
                            
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse value: {value_str} - {e}")
                        continue
        
        # タプルに変換してNoneペアを除外
        result = {}
        for line_val, (home_odd, away_odd) in line_data.items():
            if home_odd is not None and away_odd is not None:
                result[line_val] = (home_odd, away_odd)
        
        # デバッグ情報
        if result:
            logger.info(f"Extracted {len(result)} handicap lines")
            logger.debug(f"Lines: {sorted(result.keys())[:10]}")
        else:
            logger.warning("No handicap odds extracted")
        
        return result
    
    def _parse_handicap_from_string(self, value_str: str) -> Optional[float]:
        """
        "Home -1.5" や "Away +2.5" からハンデ値を抽出
        
        Args:
            value_str: "Home -1.5" 形式の文字列
            
        Returns:
            ハンデ値 or None
        """
        # 正規表現で数値部分を抽出
        match = re.search(r'[+-]?\d+\.?\d*', value_str)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def prepare_line_data(
        self, 
        odds_data: Dict[str, Any]
    ) -> Dict[float, Tuple[float, float]]:
        """
        オッズデータを補間用の形式に変換
        （mlb_from_paste_compare.pyのcollect_line_odds相当）
        
        Args:
            odds_data: GameManagerから取得したオッズデータ
            
        Returns:
            {ライン値: (home_odds, away_odds)} の辞書
        """
        bookmakers = odds_data.get("bookmakers", [])
        if not bookmakers:
            logger.warning("No bookmakers in odds_data")
            return {}
        
        return self.extract_handicap_odds(bookmakers)
    
    def get_available_lines(
        self, 
        odds_data: Dict[str, Any]
    ) -> List[float]:
        """
        利用可能なライン値のリストを取得
        
        Args:
            odds_data: オッズデータ
            
        Returns:
            ライン値のソート済みリスト
        """
        line_data = self.prepare_line_data(odds_data)
        return sorted(line_data.keys())
    
    def collect_line_odds_from_csv_row(
        self, 
        row: Dict[str, str]
    ) -> Tuple[Dict[float, float], Dict[float, float]]:
        """
        CSVの行データからライン別オッズを抽出
        （mlb_from_paste_compare.pyのcollect_line_odds関数の移植）
        
        Args:
            row: CSVの行データ
            
        Returns:
            (home_lines, away_lines) の辞書ペア
        """
        home_lines: Dict[float, float] = {}
        away_lines: Dict[float, float] = {}
        
        for k, v in row.items():
            if not v:
                continue
                
            if k.startswith("H_") or k.startswith("A_"):
                try:
                    odd = float(v)
                except ValueError:
                    continue
                    
                # ライン値を抽出（H_-1.5 → -1.5、H_+1.5 → 1.5）
                sign_val = k.split("_", 1)[1].replace("+", "")
                try:
                    line_val = float(sign_val)
                except ValueError:
                    continue
                    
                if k.startswith("H_"):
                    home_lines[line_val] = odd
                else:
                    away_lines[line_val] = odd
                    
        return home_lines, away_lines
    
    def _parse_handicap_value(self, handicap_str: str) -> float:
        """
        ハンデ文字列を数値に変換
        例: "-1.5", "+2.5", "1.5", "-0", "+0"
        
        Args:
            handicap_str: ハンデ文字列
            
        Returns:
            数値化されたハンデ値
        """
        # 先頭の+/-記号を処理
        handicap_str = str(handicap_str).strip()
        
        # 空文字列チェック
        if not handicap_str:
            raise ValueError("Empty handicap string")
        
        # +/-記号の処理
        if handicap_str.startswith("+"):
            return float(handicap_str[1:])
        elif handicap_str.startswith("-"):
            return float(handicap_str)
        else:
            # 記号なしの場合はプラスとみなす
            return float(handicap_str)
    
    def filter_bookmakers_by_id(
        self,
        bookmakers: List[Dict[str, Any]],
        bookmaker_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        指定IDのブックメーカーのみフィルタリング
        
        Args:
            bookmakers: ブックメーカーリスト
            bookmaker_ids: 抽出したいブックメーカーID
            
        Returns:
            フィルタリングされたブックメーカーリスト
        """
        filtered = []
        for bm in bookmakers:
            if int(bm.get("id", -1)) in bookmaker_ids:
                filtered.append(bm)
        return filtered
    
    def merge_odds_from_multiple_bookmakers(
        self,
        bookmakers: List[Dict[str, Any]],
        prefer_pinnacle: bool = True
    ) -> Dict[float, Tuple[float, float]]:
        """
        複数のブックメーカーからオッズをマージ
        Pinnacleを優先し、不足分を他で補完
        
        Args:
            bookmakers: ブックメーカーリスト
            prefer_pinnacle: Pinnacleを優先するか
            
        Returns:
            マージされたライン別オッズ
        """
        if prefer_pinnacle:
            # Pinnacle (ID: 4) を優先
            pinnacle_odds = self.extract_handicap_odds(bookmakers, preferred_bookmaker_id=4)
            
            # 不足分を他のブックメーカーで補完
            other_odds = self.extract_handicap_odds(bookmakers, preferred_bookmaker_id=2)
            
            # マージ（Pinnacleを優先）
            merged = dict(other_odds)
            merged.update(pinnacle_odds)
            
            return merged
        else:
            # すべて均等に処理
            return self.extract_handicap_odds(bookmakers)


# ヘルパー関数（既存コードとの互換性のため）
def extract_handicap_odds_from_bookmakers(
    bookmakers: List[Dict[str, Any]]
) -> Dict[float, Tuple[float, float]]:
    """
    ブックメーカーデータからハンデオッズを抽出（互換性用ラッパー）
    
    Args:
        bookmakers: APIレスポンスのbookmakersリスト
        
    Returns:
        {ライン値: (home_odds, away_odds)} の辞書
    """
    processor = OddsProcessor()
    return processor.extract_handicap_odds(bookmakers)


def prepare_odds_for_interpolation(
    odds_data: Dict[str, Any]
) -> Dict[float, Tuple[float, float]]:
    """
    オッズデータを補間用に準備（互換性用ラッパー）
    
    Args:
        odds_data: GameManagerから取得したオッズデータ
        
    Returns:
        {ライン値: (home_odds, away_odds)} の辞書
    """
    processor = OddsProcessor()
    return processor.prepare_line_data(odds_data)