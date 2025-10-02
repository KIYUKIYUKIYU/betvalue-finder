# converter/team_names.py
"""
MLB全30チームの名前マッピング
正式名称、略称、日本語名、一般的な呼称をすべて網羅
"""

from typing import Dict, List, Optional

# メインの辞書：正式名称 -> エイリアスリスト
TEAM_ALIASES = {
    # アメリカンリーグ東地区
    "New York Yankees": {
        "aliases": ["Yankees", "NYY", "NY Yankees"],
        "japanese": ["ヤンキース", "ニューヨークヤンキース", "ニューヨーク・ヤンキース", "NYヤンキース"],
        "official_jp": "ヤンキース"
    },
    "Boston Red Sox": {
        "aliases": ["Red Sox", "BOS", "Boston"],
        "japanese": ["レッドソックス", "ボストンレッドソックス", "ボストン・レッドソックス", "Rソックス"],
        "official_jp": "レッドソックス"
    },
    "Tampa Bay Rays": {
        "aliases": ["Rays", "TB", "Tampa Bay", "Tampa"],
        "japanese": ["レイズ", "タンパベイレイズ", "タンパベイ・レイズ"],
        "official_jp": "レイズ"
    },
    "Toronto Blue Jays": {
        "aliases": ["Blue Jays", "TOR", "Toronto", "Jays"],
        "japanese": ["ブルージェイズ", "トロントブルージェイズ", "トロント・ブルージェイズ"],
        "official_jp": "ブルージェイズ"
    },
    "Baltimore Orioles": {
        "aliases": ["Orioles", "BAL", "Baltimore", "O's"],
        "japanese": ["オリオールズ", "ボルチモアオリオールズ", "ボルチモア・オリオールズ"],
        "official_jp": "オリオールズ"
    },
    
    # アメリカンリーグ中地区
    "Cleveland Guardians": {
        "aliases": ["Guardians", "CLE", "Cleveland"],
        "japanese": ["ガーディアンズ", "クリーブランドガーディアンズ", "クリーブランド・ガーディアンズ"],
        "official_jp": "ガーディアンズ"
    },
    "Minnesota Twins": {
        "aliases": ["Twins", "MIN", "Minnesota"],
        "japanese": ["ツインズ", "ミネソタツインズ", "ミネソタ・ツインズ"],
        "official_jp": "ツインズ"
    },
    "Chicago White Sox": {
        "aliases": ["White Sox", "CWS", "ChiSox"],
        "japanese": ["ホワイトソックス", "シカゴホワイトソックス", "シカゴ・ホワイトソックス", "Wソックス"],
        "official_jp": "ホワイトソックス"
    },
    "Detroit Tigers": {
        "aliases": ["Tigers", "DET", "Detroit"],
        "japanese": ["タイガース", "デトロイトタイガース", "デトロイト・タイガース"],
        "official_jp": "タイガース"
    },
    "Kansas City Royals": {
        "aliases": ["Royals", "KC", "Kansas City"],
        "japanese": ["ロイヤルズ", "カンザスシティロイヤルズ", "カンザスシティ・ロイヤルズ"],
        "official_jp": "ロイヤルズ"
    },
    
    # アメリカンリーグ西地区
    "Houston Astros": {
        "aliases": ["Astros", "HOU", "Houston"],
        "japanese": ["アストロズ", "ヒューストンアストロズ", "ヒューストン・アストロズ"],
        "official_jp": "アストロズ"
    },
    "Texas Rangers": {
        "aliases": ["Rangers", "TEX", "Texas"],
        "japanese": ["レンジャーズ", "テキサスレンジャーズ", "テキサス・レンジャーズ"],
        "official_jp": "レンジャーズ"
    },
    "Seattle Mariners": {
        "aliases": ["Mariners", "SEA", "Seattle", "M's"],
        "japanese": ["マリナーズ", "シアトルマリナーズ", "シアトル・マリナーズ"],
        "official_jp": "マリナーズ"
    },
    "Los Angeles Angels": {
        "aliases": ["Angels", "LAA", "LA Angels", "Anaheim Angels"],
        "japanese": ["エンゼルス", "ロサンゼルスエンゼルス", "ロサンゼルス・エンゼルス", "エンジェルス"],
        "official_jp": "エンゼルス"
    },
    "Oakland Athletics": {
        "aliases": ["Athletics", "A's", "OAK", "Oakland"],
        "japanese": ["アスレチックス", "オークランドアスレチックス", "オークランド・アスレチックス"],
        "official_jp": "アスレチックス"
    },
    
    # ナショナルリーグ東地区
    "Atlanta Braves": {
        "aliases": ["Braves", "ATL", "Atlanta"],
        "japanese": ["ブレーブス", "アトランタブレーブス", "アトランタ・ブレーブス"],
        "official_jp": "ブレーブス"
    },
    "New York Mets": {
        "aliases": ["Mets", "NYM", "NY Mets"],
        "japanese": ["メッツ", "ニューヨークメッツ", "ニューヨーク・メッツ"],
        "official_jp": "メッツ"
    },
    "Philadelphia Phillies": {
        "aliases": ["Phillies", "PHI", "Philadelphia", "Phils"],
        "japanese": ["フィリーズ", "フィラデルフィアフィリーズ", "フィラデルフィア・フィリーズ"],
        "official_jp": "フィリーズ"
    },
    "Washington Nationals": {
        "aliases": ["Nationals", "WSH", "Washington", "Nats"],
        "japanese": ["ナショナルズ", "ワシントンナショナルズ", "ワシントン・ナショナルズ"],
        "official_jp": "ナショナルズ"
    },
    "Miami Marlins": {
        "aliases": ["Marlins", "MIA", "Miami"],
        "japanese": ["マーリンズ", "マイアミマーリンズ", "マイアミ・マーリンズ"],
        "official_jp": "マーリンズ"
    },
    
    # ナショナルリーグ中地区
    "Milwaukee Brewers": {
        "aliases": ["Brewers", "MIL", "Milwaukee"],
        "japanese": ["ブリュワーズ", "ミルウォーキーブリュワーズ", "ミルウォーキー・ブリュワーズ"],
        "official_jp": "ブリュワーズ"
    },
    "St. Louis Cardinals": {
        "aliases": ["Cardinals", "STL", "St Louis", "Cards"],
        "japanese": ["カージナルス", "セントルイスカージナルス", "セントルイス・カージナルス"],
        "official_jp": "カージナルス"
    },
    "Chicago Cubs": {
        "aliases": ["Cubs", "CHC", "Chicago"],
        "japanese": ["カブス", "シカゴカブス", "シカゴ・カブス"],
        "official_jp": "カブス"
    },
    "Cincinnati Reds": {
        "aliases": ["Reds", "CIN", "Cincinnati"],
        "japanese": ["レッズ", "シンシナティレッズ", "シンシナティ・レッズ"],
        "official_jp": "レッズ"
    },
    "Pittsburgh Pirates": {
        "aliases": ["Pirates", "PIT", "Pittsburgh", "Bucs"],
        "japanese": ["パイレーツ", "ピッツバーグパイレーツ", "ピッツバーグ・パイレーツ"],
        "official_jp": "パイレーツ"
    },
    
    # ナショナルリーグ西地区
    "Los Angeles Dodgers": {
        "aliases": ["Dodgers", "LAD", "LA Dodgers"],
        "japanese": ["ドジャース", "ロサンゼルスドジャース", "ロサンゼルス・ドジャース", "LAドジャース"],
        "official_jp": "ドジャース"
    },
    "San Diego Padres": {
        "aliases": ["Padres", "SD", "San Diego"],
        "japanese": ["パドレス", "サンディエゴパドレス", "サンディエゴ・パドレス"],
        "official_jp": "パドレス"
    },
    "San Francisco Giants": {
        "aliases": ["Giants", "SF", "San Francisco"],
        "japanese": ["ジャイアンツ", "サンフランシスコジャイアンツ", "サンフランシスコ・ジャイアンツ"],
        "official_jp": "ジャイアンツ"
    },
    "Arizona Diamondbacks": {
        "aliases": ["Diamondbacks", "D-backs", "ARI", "Arizona"],
        "japanese": ["ダイヤモンドバックス", "アリゾナダイヤモンドバックス", "アリゾナ・ダイヤモンドバックス", "Dバックス"],
        "official_jp": "ダイヤモンドバックス"
    },
    "Colorado Rockies": {
        "aliases": ["Rockies", "COL", "Colorado"],
        "japanese": ["ロッキーズ", "コロラドロッキーズ", "コロラド・ロッキーズ"],
        "official_jp": "ロッキーズ"
    }
}

def normalize_team_name(input_name: str) -> Optional[str]:
    """
    任意の入力を正式なチーム名に変換
    
    Args:
        input_name: ユーザーが入力したチーム名（日本語/英語/略称など）
    
    Returns:
        正式なチーム名（API準拠）またはNone
    """
    if not input_name:
        return None
    
    input_clean = input_name.strip()
    input_lower = input_clean.lower()
    
    # 完全一致を優先
    for official_name, info in TEAM_ALIASES.items():
        # 正式名称との一致
        if input_lower == official_name.lower():
            return official_name
        
        # 英語エイリアスとの一致
        for alias in info["aliases"]:
            if input_lower == alias.lower():
                return official_name
        
        # 日本語名との一致
        for jp_name in info["japanese"]:
            if input_clean == jp_name:
                return official_name
    
    # 部分一致（緩いマッチング）
    for official_name, info in TEAM_ALIASES.items():
        # 英語エイリアスとの部分一致
        for alias in info["aliases"]:
            if input_lower in alias.lower() or alias.lower() in input_lower:
                return official_name
        
        # 日本語名との部分一致
        for jp_name in info["japanese"]:
            if input_clean in jp_name or jp_name in input_clean:
                return official_name
    
    return None

def get_japanese_name(official_name: str) -> str:
    """
    正式名称から日本語名を取得
    """
    if official_name in TEAM_ALIASES:
        return TEAM_ALIASES[official_name]["official_jp"]
    return official_name

def get_all_japanese_names() -> Dict[str, str]:
    """
    日本語名 -> 正式名称のマッピングを返す
    """
    result = {}
    for official_name, info in TEAM_ALIASES.items():
        result[info["official_jp"]] = official_name
        for jp_name in info["japanese"]:
            result[jp_name] = official_name
    return result

def get_todays_teams(games: List[Dict]) -> List[str]:
    """
    今日の試合に出場するチーム一覧
    """
    teams = set()
    for game in games:
        if "home" in game:
            teams.add(game["home"])
        if "away" in game:
            teams.add(game["away"])
    return sorted(list(teams))

# テスト用
if __name__ == "__main__":
    # テストケース
    test_cases = [
        "Yankees",
        "ヤンキース",
        "NYY",
        "New York Yankees",
        "Dodgers",
        "ドジャース",
        "LA Dodgers"
    ]
    
    for test in test_cases:
        result = normalize_team_name(test)
        print(f"{test} -> {result}")