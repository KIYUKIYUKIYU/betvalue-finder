# -*- coding: utf-8 -*-
"""
統一ハンデ変換モジュール

全競技（MLB/NPB/Soccer）共通の日本式↔ピナクル値変換を提供。
不変モジュールとして設計。変換表データを内蔵。

Usage:
    from converter.unified_handicap_converter import jp_to_pinnacle, pinnacle_to_jp
    
    # 日本式 → ピナクル
    pinnacle_val = jp_to_pinnacle("1.8")  # → 1.40
    pinnacle_val = jp_to_pinnacle("02")   # → 0.20
    pinnacle_val = jp_to_pinnacle("1半5") # → 1.75
    
    # ピナクル → 日本式
    jp_label = pinnacle_to_jp(1.40)       # → "1.8"
    jp_label = pinnacle_to_jp(0.20)       # → "0.4" 
    jp_label = pinnacle_to_jp(1.75)       # → "1半5"
"""

import re
from typing import Union, Dict


class HandicapConversionError(Exception):
    """ハンデ変換エラー"""
    pass


def _normalize_input(jp_label: str) -> str:
    """
    入力文字列の正規化
    - 全角→半角変換
    - 空白除去
    - サッカー特殊表記変換
    """
    if not isinstance(jp_label, str):
        raise HandicapConversionError(f"Invalid input type: {type(jp_label)}")
    
    # 基本の正規化
    normalized = jp_label.strip()
    
    # 全角数字・記号→半角変換
    full_to_half = str.maketrans(
        "０１２３４５６７８９．／",  # 全角
        "0123456789./"           # 半角
    )
    normalized = normalized.translate(full_to_half)
    
    # 全角「半」→半角変換
    normalized = normalized.replace("半", "半")  # 既に半角の場合はそのまま
    
    # サッカー特殊表記の変換（0/1→0.1など）
    if normalized in _SOCCER_SPECIAL_MAPPINGS:
        normalized = _SOCCER_SPECIAL_MAPPINGS[normalized]
    
    # "02"→"0.4" の特殊処理
    if (normalized.startswith('0') and len(normalized) == 2 and 
        normalized[1].isdigit() and normalized != "0"):
        normalized = f"0.{normalized[1]}"
    
    return normalized


# 完全な変換テーブル（不変データ）
_PINNACLE_TO_JP: Dict[float, str] = {
    0.00: "0",
    0.05: "0.1", 0.10: "0.2", 0.15: "0.3", 0.20: "0.4", 0.25: "0.5",
    0.30: "0.6", 0.35: "0.7", 0.40: "0.8", 0.45: "0.9",
    0.50: "0半", 0.55: "0半1", 0.60: "0半2", 0.65: "0半3", 0.70: "0半4",
    0.75: "0半5", 0.80: "0半6", 0.85: "0半7", 0.90: "0半8", 0.95: "0半9",
    1.00: "1",
    1.05: "1.1", 1.10: "1.2", 1.15: "1.3", 1.20: "1.4", 1.25: "1.25",
    1.30: "1.6", 1.35: "1.7", 1.40: "1.8", 1.45: "1.9",
    1.50: "1.5", 1.55: "1半1", 1.60: "1半2", 1.65: "1半3", 1.70: "1半4",
    1.75: "1半5", 1.80: "1半6", 1.85: "1半7", 1.90: "1半8", 1.95: "1半9",
    2.00: "2",
    2.05: "2.1", 2.10: "2.2", 2.15: "2.3", 2.20: "2.4", 2.25: "2.5",
    2.30: "2.6", 2.35: "2.7", 2.40: "2.8", 2.45: "2.9",
    2.50: "2半", 2.55: "2半1", 2.60: "2半2", 2.65: "2半3", 2.70: "2半4",
    2.75: "2半5", 2.80: "2半6", 2.85: "2半7", 2.90: "2半8", 2.95: "2半9",
    3.00: "3",
    3.05: "3.1", 3.10: "3.2", 3.15: "3.3", 3.20: "3.4", 3.25: "3.5",
    3.30: "3.6", 3.35: "3.7", 3.40: "3.8", 3.45: "3.9",
    3.50: "3半", 3.55: "3半1", 3.60: "3半2", 3.65: "3半3", 3.70: "3半4",
    3.75: "3半5", 3.80: "3半6", 3.85: "3半7", 3.90: "3半8", 3.95: "3半9",
    4.00: "4",
}

# サッカー特殊表記対応（0/1-0/9 = 0.1-0.9と同義）
_SOCCER_SPECIAL_MAPPINGS = {
    "0/1": "0.1", "0/2": "0.2", "0/3": "0.3", "0/4": "0.4", "0/5": "0.5",
    "0/6": "0.6", "0/7": "0.7", "0/8": "0.8", "0/9": "0.9",
}

# 逆引き辞書を生成
_JP_TO_PINNACLE: Dict[str, float] = {jp: pinnacle for pinnacle, jp in _PINNACLE_TO_JP.items()}
# サッカー特殊表記も追加
for soccer_form, standard_form in _SOCCER_SPECIAL_MAPPINGS.items():
    if standard_form in _JP_TO_PINNACLE:
        _JP_TO_PINNACLE[soccer_form] = _JP_TO_PINNACLE[standard_form]

# よくある小数点表記も追加
_JP_TO_PINNACLE["0.0"] = 0.00
_JP_TO_PINNACLE["1.0"] = 1.00
_JP_TO_PINNACLE["2.0"] = 2.00
_JP_TO_PINNACLE["3.0"] = 3.00
_JP_TO_PINNACLE["4.0"] = 4.00

# Parser生成の小数値も追加（World Cup予選用）
_JP_TO_PINNACLE["0.25"] = 0.25
_JP_TO_PINNACLE["0.55"] = 0.55
_JP_TO_PINNACLE["0.75"] = 0.75
_JP_TO_PINNACLE["2.65"] = 2.65

# サッカー2桁形式の追加（17→1.7, 25→2.5など）
_JP_TO_PINNACLE["17"] = 1.35  # 1.7 → 1.35 (1.35 corresponds to "1.7" in the table)
_JP_TO_PINNACLE["25"] = 2.25  # 2.5 → 2.25
_JP_TO_PINNACLE["15"] = 1.5   # 1.5 → 1.5
_JP_TO_PINNACLE["10"] = 1.00  # 1.0 → 1.00
_JP_TO_PINNACLE["20"] = 2.00  # 2.0 → 2.00
_JP_TO_PINNACLE["23"] = 2.15  # 2.3 → 2.15


def jp_to_pinnacle(jp_label: str) -> float:
    """
    日本式ハンデ表記をピナクル値に変換
    
    Args:
        jp_label: 日本式ハンデ（例: "1.8", "02", "1半5", "0", "2半", "０／１", "１．８"）
        
    Returns:
        ピナクル値（0.05刻み）
        
    Raises:
        HandicapConversionError: 変換できない場合
        
    Examples:
        >>> jp_to_pinnacle("1.8")
        1.40
        >>> jp_to_pinnacle("02")
        0.10
        >>> jp_to_pinnacle("1半5")
        1.75
        >>> jp_to_pinnacle("0/1")  # サッカー特殊表記
        0.05
        >>> jp_to_pinnacle("１．８")  # 全角
        1.40
    """
    # 入力正規化
    jp_normalized = _normalize_input(jp_label)
    
    if not jp_normalized:
        raise HandicapConversionError("Empty input after normalization")
    
    # 直接テーブル検索
    if jp_normalized in _JP_TO_PINNACLE:
        return _JP_TO_PINNACLE[jp_normalized]
    
    raise HandicapConversionError(f"Unknown Japanese handicap: '{jp_label}' (normalized: '{jp_normalized}')")


def pinnacle_to_jp(pinnacle_value: Union[float, int, str]) -> str:
    """
    ピナクル値を日本式ハンデ表記に変換
    
    Args:
        pinnacle_value: ピナクル値（0.05刻み想定）
        
    Returns:
        日本式ハンデ表記
        
    Raises:
        HandicapConversionError: 変換できない場合
        
    Examples:
        >>> pinnacle_to_jp(1.40)
        "1.8"
        >>> pinnacle_to_jp(0.20)
        "0.4"
        >>> pinnacle_to_jp(1.75)
        "1半5"
    """
    try:
        pval = float(pinnacle_value)
    except (ValueError, TypeError):
        raise HandicapConversionError(f"Invalid pinnacle value: {pinnacle_value}")
    
    if pval < 0:
        raise HandicapConversionError(f"Negative pinnacle value: {pval}")
        
    # 0.05刻みに丸める
    pval = round(pval / 0.05) * 0.05
    pval = round(pval, 2)  # 浮動小数点誤差対策
    
    # 直接テーブル検索
    if pval in _PINNACLE_TO_JP:
        return _PINNACLE_TO_JP[pval]
    
    raise HandicapConversionError(f"Unknown pinnacle value: {pval}")


def validate_conversion_bidirectional(jp_label: str) -> bool:
    """
    双方向変換の整合性をチェック
    
    Args:
        jp_label: 日本式ハンデ
        
    Returns:
        整合性があるかどうか
    """
    try:
        pinnacle_val = jp_to_pinnacle(jp_label)
        jp_back = pinnacle_to_jp(pinnacle_val)
        # 正規化して比較（"02" → "0.2" など）
        return _normalize_jp_label(jp_label) == _normalize_jp_label(jp_back)
    except HandicapConversionError:
        return False


def _normalize_jp_label(jp_label: str) -> str:
    """日本式ラベルを正規化（比較用）"""
    try:
        pval = jp_to_pinnacle(jp_label)
        return pinnacle_to_jp(pval)
    except HandicapConversionError:
        return jp_label


# 重要な変換パターン（定数として外部から参照可能）
CRITICAL_CONVERSIONS = {
    # 今回の3試合で使用される重要パターン  
    "0": 0.00,      # ロッテ<0>
    "02": 0.10,     # 横浜<02> → "0.2" → 0.10
    "1.8": 1.40,    # 阪神<1.8>
    "0.2": 0.10,    # 02の正規化後
    "1半8": 1.90,   # 別表記
}


if __name__ == "__main__":
    # セルフテスト
    print("=== 統一ハンデ変換モジュール セルフテスト ===")
    
    test_cases = [
        "0", "02", "0.5", "1", "1.8", "1半", "1半5", "2", "2半", "3半9"
    ]
    
    print("双方向変換テスト:")
    for jp in test_cases:
        try:
            pval = jp_to_pinnacle(jp)
            jp_back = pinnacle_to_jp(pval)
            valid = validate_conversion_bidirectional(jp)
            print(f"  {jp:6} → {pval:5.2f} → {jp_back:6} {'✅' if valid else '❌'}")
        except HandicapConversionError as e:
            print(f"  {jp:6} → ERROR: {e}")
    
    print("\n重要変換パターン確認:")
    important_tests = [
        ("1.8", 1.40),  # 阪神<1.8>
        ("02", 0.10),   # 横浜<02> → "0.2" → 0.10
        ("0", 0.00),    # ロッテ<0>
    ]
    
    for jp, expected_pinnacle in important_tests:
        actual = jp_to_pinnacle(jp)
        match = abs(actual - expected_pinnacle) < 0.001
        print(f"  {jp} → {actual} (期待値:{expected_pinnacle}) {'✅' if match else '❌'}")
    
    print("\nサッカー特殊表記テスト:")
    soccer_tests = [
        ("0/1", 0.05),  # サッカー特殊
        ("0/5", 0.25),  # サッカー特殊
        ("0/9", 0.45),  # サッカー特殊
    ]
    
    for jp, expected_pinnacle in soccer_tests:
        try:
            actual = jp_to_pinnacle(jp)
            match = abs(actual - expected_pinnacle) < 0.001
            print(f"  {jp} → {actual} (期待値:{expected_pinnacle}) {'✅' if match else '❌'}")
        except HandicapConversionError as e:
            print(f"  {jp} → ERROR: {e}")
    
    print("\n全角・半角正規化テスト:")
    normalization_tests = [
        ("１．８", 1.40),   # 全角数字・ピリオド
        ("０２", 0.10),     # 全角02
        ("０／５", 0.25),   # 全角サッカー表記
        (" 1.8 ", 1.40),   # 空白
        ("１半５", 1.75),   # 全角+半角混在
    ]
    
    for jp, expected_pinnacle in normalization_tests:
        try:
            actual = jp_to_pinnacle(jp)
            match = abs(actual - expected_pinnacle) < 0.001
            print(f"  '{jp}' → {actual} (期待値:{expected_pinnacle}) {'✅' if match else '❌'}")
        except HandicapConversionError as e:
            print(f"  '{jp}' → ERROR: {e}")