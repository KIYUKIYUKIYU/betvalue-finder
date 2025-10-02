#!/usr/bin/env python3
"""
NPB チーム名マッピング
Personal系から抽出した12球団完全対応マッピング
"""

# NPB日本語チーム名マッピング（完全版）
NPB_TEAM_MAPPING = {
    # セントラル・リーグ
    '読売ジャイアンツ': 'Yomiuri Giants',
    '阪神タイガース': 'Hanshin Tigers',
    '横浜DeNAベイスターズ': 'Yokohama DeNA BayStars',
    '広島東洋カープ': 'Hiroshima Toyo Carp',
    '中日ドラゴンズ': 'Chunichi Dragons',
    '東京ヤクルトスワローズ': 'Tokyo Yakult Swallows',
    
    # パシフィック・リーグ
    '福岡ソフトバンクホークス': 'Fukuoka SoftBank Hawks',
    '千葉ロッテマリーンズ': 'Chiba Lotte Marines',
    '埼玉西武ライオンズ': 'Saitama Seibu Lions',
    'オリックス・バファローズ': 'Orix Buffaloes',
    '北海道日本ハムファイターズ': 'Hokkaido Nippon-Ham Fighters',
    '東北楽天ゴールデンイーグルス': 'Tohoku Rakuten Golden Eagles',
}

# 略称・通称マッピング（よく使われる）
NPB_TEAM_ALIASES = {
    # セリーグ略称
    'ジャイアンツ': '読売ジャイアンツ',
    '巨人': '読売ジャイアンツ',
    'G': '読売ジャイアンツ',
    
    'タイガース': '阪神タイガース',
    '阪神': '阪神タイガース',
    'T': '阪神タイガース',
    
    'ベイスターズ': '横浜DeNAベイスターズ',
    'DeNA': '横浜DeNAベイスターズ',
    '横浜': '横浜DeNAベイスターズ',
    'DB': '横浜DeNAベイスターズ',
    
    'カープ': '広島東洋カープ',
    '広島': '広島東洋カープ',
    'C': '広島東洋カープ',
    
    'ドラゴンズ': '中日ドラゴンズ',
    '中日': '中日ドラゴンズ',
    'D': '中日ドラゴンズ',
    
    'スワローズ': '東京ヤクルトスワローズ',
    'ヤクルト': '東京ヤクルトスワローズ',
    'S': '東京ヤクルトスワローズ',
    
    # パリーグ略称
    'ホークス': '福岡ソフトバンクホークス',
    'ソフトバンク': '福岡ソフトバンクホークス',
    'ソフト': '福岡ソフトバンクホークス',  # よく使われる略称
    'SB': '福岡ソフトバンクホークス',
    'H': '福岡ソフトバンクホークス',
    
    'マリーンズ': '千葉ロッテマリーンズ',
    'ロッテ': '千葉ロッテマリーンズ',
    'M': '千葉ロッテマリーンズ',
    
    'ライオンズ': '埼玉西武ライオンズ',
    '西武': '埼玉西武ライオンズ',
    'L': '埼玉西武ライオンズ',
    
    'バファローズ': 'オリックス・バファローズ',
    'オリックス': 'オリックス・バファローズ',
    'Bs': 'オリックス・バファローズ',
    
    'ファイターズ': '北海道日本ハムファイターズ',
    '日本ハム': '北海道日本ハムファイターズ',
    'ハム': '北海道日本ハムファイターズ',  # よく使われる略称
    'F': '北海道日本ハムファイターズ',
    
    'イーグルス': '東北楽天ゴールデンイーグルス',
    'ゴールデンイーグルス': '東北楽天ゴールデンイーグルス',
    '楽天': '東北楽天ゴールデンイーグルス',
    'E': '東北楽天ゴールデンイーグルス',
}

def get_npb_english_name(jp_name: str) -> str:
    """
    日本語チーム名から英語名を取得
    
    Args:
        jp_name: 日本語チーム名
        
    Returns:
        英語チーム名 または None
    """
    # 直接マッピング
    if jp_name in NPB_TEAM_MAPPING:
        return NPB_TEAM_MAPPING[jp_name]
    
    # 別名チェック
    if jp_name in NPB_TEAM_ALIASES:
        canonical_name = NPB_TEAM_ALIASES[jp_name]
        return NPB_TEAM_MAPPING.get(canonical_name)
    
    # 部分マッチ
    for jp_team, en_team in NPB_TEAM_MAPPING.items():
        if jp_name in jp_team or jp_team in jp_name:
            return en_team
    
    return None

def get_npb_full_name(short_name: str) -> str:
    """
    略称から正式チーム名を取得
    
    Args:
        short_name: 略称
        
    Returns:
        正式名 または None
    """
    # 既に正式名の場合
    if short_name in NPB_TEAM_MAPPING:
        return short_name
    
    # 略称から検索
    if short_name in NPB_TEAM_ALIASES:
        return NPB_TEAM_ALIASES[short_name]
    
    # 部分マッチ
    for alias, full_name in NPB_TEAM_ALIASES.items():
        if short_name in alias or alias in short_name:
            return full_name
    
    # 正式名からの部分マッチ
    for full_name in NPB_TEAM_MAPPING.keys():
        if short_name in full_name:
            return full_name
    
    return None