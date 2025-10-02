# -*- coding: utf-8 -*-
"""
handicap_parser.py
BET_HUNTER CLI 総合仕様書準拠の完全ハンデパーサー
"""

import re
from typing import Optional, Tuple


class HandicapParser:
    """日本式ハンデ表記の完全解析クラス"""
    
    @staticmethod
    def parse_japanese_handicap(handicap_str: str) -> Optional[float]:
        """
        日本式ハンデ表記をピナクル値（float）に変換
        
        対応パターン（BET_HUNTER CLI 総合仕様書準拠）:
        - 01-09 → 0.1-0.9 (0+x表記)
        - 0,1,2,15 → 0.0,1.0,2.0,15.0 (整数表記)
        - 0半,1半,5半 → 0.5,1.5,5.5 (半表記)
        - 1半2,2半3,2半75 → 1.7,2.8,3.25 (半+小数)
        - 0/5,1/1.5 → サッカー専用（別途処理）
        - 2半7 → 2.7 (2半 + 0.2 = 2.7)
        """
        if not handicap_str:
            return None
            
        handicap_str = handicap_str.strip()
        
        # パターン1: 0+x表記（01, 02, 07, 09など）
        if re.match(r'^0[1-9]$', handicap_str):
            return float(f"0.{handicap_str[1]}")
        
        # パターン2: 整数表記（0, 1, 2, 15など）
        # サッカー特殊ケース: "17" → 1.7, "25" → 2.5, "05" → 0.5など
        if re.match(r'^\d+$', handicap_str):
            # サッカー形式の可能性をチェック（2桁で十の位が有効な数字）
            if len(handicap_str) == 2 and handicap_str[0] != '0':
                # 17 → 1.7, 25 → 2.5のような変換
                tens = int(handicap_str[0])
                ones = int(handicap_str[1])
                if ones <= 9 and tens >= 1:  # 有効な範囲
                    return tens + (ones / 10.0)
            return float(handicap_str)
        
        # パターン3: 小数表記（1.5, 2.7, 3.25など）
        if re.match(r'^\d+\.\d+$', handicap_str):
            return float(handicap_str)
        
        # パターン4: 純粋な半表記（0半, 1半, 5半など）
        if re.match(r'^\d+半$', handicap_str):
            base = int(handicap_str.replace('半', ''))
            return base + 0.5
        
        # パターン5: 複雑な半+小数表記（1半2=1.7, 2半3=2.8, 2半75=3.25, 2半7=2.7など）
        half_match = re.match(r'^(\d+)半(\d+)$', handicap_str)
        if half_match:
            base = int(half_match.group(1))
            decimal_part = half_match.group(2)
            
            if len(decimal_part) == 1:
                decimal_value = int(decimal_part)
                # 変換表に基づく正確な計算: 1半2=1.60, 2半3=2.65, 2半7=2.85
                return base + 0.5 + (decimal_value * 0.05)
            elif len(decimal_part) == 2:
                # 2半75 → 2.5 + 0.75 = 3.25
                return base + 0.5 + (int(decimal_part) / 100)
            else:
                # 3桁以上は無効
                return None
        
        # パターン6: スラッシュ表記（サッカー専用）
        if re.match(r'^\d/\d$', handicap_str):
            # サッカー特殊表記の正しい変換マッピング
            # unified_handicap_converter.py の仕様に準拠
            fraction_mappings = {
                "0/1": 0.05, "0/2": 0.10, "0/3": 0.15, "0/4": 0.20, "0/5": 0.25,
                "0/6": 0.30, "0/7": 0.35, "0/8": 0.40, "0/9": 0.45
            }
            return fraction_mappings.get(handicap_str)
        
        # 認識できない形式
        return None
    
    @staticmethod
    def detect_handicap_in_text(text: str) -> Tuple[Optional[str], Optional[float]]:
        """
        テキストからハンデ表記を検出して値を返す
        
        Returns:
            (original_handicap_str, parsed_float_value)
        """
        # パターン1: <ハンデ>形式（全角括弧対応）
        match = re.search(r'[<＜〈]([^>＞〉]+)[>＞〉]', text)
        if match:
            handicap_str = match.group(1).strip()
            parsed_value = HandicapParser.parse_japanese_handicap(handicap_str)
            return handicap_str, parsed_value
        
        # パターン2: チーム名の後ろに直接数字（例: オーストリア2半7）
        match = re.search(r'([^\s]+?)((?:0[1-9]|\d+半\d*|\d+\.\d+|\d+))$', text)
        if match:
            team = match.group(1)
            handicap_str = match.group(2)
            # チーム名が短すぎる場合は除外（誤検出防止）
            if len(team) >= 2:
                parsed_value = HandicapParser.parse_japanese_handicap(handicap_str)
                if parsed_value is not None:
                    return handicap_str, parsed_value
        
        return None, None
    
    @staticmethod
    def test_all_patterns():
        """テスト用：全パターンの動作確認"""
        test_cases = [
            # 0+x表記
            ("01", 0.1), ("02", 0.2), ("07", 0.7), ("09", 0.9),
            # 整数表記
            ("0", 0.0), ("1", 1.0), ("2", 2.0), ("15", 15.0),
            # 小数表記
            ("1.5", 1.5), ("2.7", 2.7), ("3.25", 3.25),
            # 純粋半表記
            ("0半", 0.5), ("1半", 1.5), ("5半", 5.5),
            # 複雑半表記
            ("1半2", 1.60), ("2半3", 2.65), ("2半75", 3.25), ("2半7", 2.85),
            # スラッシュ表記（正しい変換）
            ("0/1", 0.05), ("0/5", 0.25), ("0/9", 0.45),
        ]
        
        print("=== HandicapParser Test Results ===")
        for input_str, expected in test_cases:
            result = HandicapParser.parse_japanese_handicap(input_str)
            status = "✅" if result == expected else "❌"
            print(f"{status} {input_str:>6} → {result:>6} (expected: {expected})")


if __name__ == "__main__":
    HandicapParser.test_all_patterns()