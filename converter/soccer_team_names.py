# converter/soccer_team_names.py
"""
サッカーチーム名の日本語⇔英語変換
主要リーグ対応：プレミア、ラ・リーガ、ブンデス、セリエA、リーグ1、Jリーグ
"""

# サッカーチーム名変換辞書
SOCCER_TEAM_MAP = {
    # ========== プレミアリーグ ==========
    "マンチェスターシティ": "Manchester City",
    "マンC": "Manchester City",
    "シティ": "Manchester City",
    
    "マンチェスターユナイテッド": "Manchester United",
    "マンU": "Manchester United",
    "ユナイテッド": "Manchester United",
    
    "アーセナル": "Arsenal",
    "リバプール": "Liverpool",
    "リヴァプール": "Liverpool",
    "チェルシー": "Chelsea",
    "トッテナム": "Tottenham",
    "スパーズ": "Tottenham",
    
    "ニューカッスル": "Newcastle",
    "ブライトン": "Brighton",
    "アストンビラ": "Aston Villa",
    "アストンヴィラ": "Aston Villa",
    "ウェストハム": "West Ham",
    
    "ブレントフォード": "Brentford",
    "フラム": "Fulham",
    "ウルブス": "Wolves",
    "ウォルバーハンプトン": "Wolves",
    "エバートン": "Everton",
    "エヴァートン": "Everton",
    
    "クリスタルパレス": "Crystal Palace",
    "ノッティンガム": "Nottingham Forest",
    "ボーンマス": "Bournemouth",
    "レスター": "Leicester",
    "リーズ": "Leeds",
    "サウサンプトン": "Southampton",
    
    # ========== ラ・リーガ ==========
    "レアルマドリード": "Real Madrid",
    "レアル": "Real Madrid",
    "マドリード": "Real Madrid",
    
    "バルセロナ": "Barcelona",
    "バルサ": "Barcelona",
    
    "アトレティコマドリード": "Atletico Madrid",
    "アトレティコ": "Atletico Madrid",
    "アトレチコ": "Atletico Madrid",
    
    "セビージャ": "Sevilla",
    "セビリア": "Sevilla",
    "ビジャレアル": "Villarreal",
    "ビリャレアル": "Villarreal",
    "レアルソシエダ": "Real Sociedad",
    "ソシエダ": "Real Sociedad",
    
    "ベティス": "Real Betis",
    "レアルベティス": "Real Betis",
    "アスレティックビルバオ": "Athletic Bilbao",
    "アスレチックビルバオ": "Athletic Bilbao",
    "ビルバオ": "Athletic Bilbao",
    
    "バレンシア": "Valencia",
    "ヘタフェ": "Getafe",
    "オサスナ": "Osasuna",
    "セルタ": "Celta Vigo",
    "エスパニョール": "Espanyol",
    "ラージョ": "Rayo Vallecano",
    "マジョルカ": "Mallorca",
    "カディス": "Cadiz",
    "エルチェ": "Elche",
    "ジローナ": "Girona",
    
    # ========== ブンデスリーガ ==========
    "バイエルン": "Bayern Munich",
    "バイエルンミュンヘン": "Bayern Munich",
    
    "ドルトムント": "Borussia Dortmund",
    "ボルシアドルトムント": "Borussia Dortmund",
    "BVB": "Borussia Dortmund",
    
    "ライプツィヒ": "RB Leipzig",
    "RBライプツィヒ": "RB Leipzig",
    
    "レバークーゼン": "Bayer Leverkusen",
    "バイヤーレバークーゼン": "Bayer Leverkusen",
    "レヴァークーゼン": "Bayer Leverkusen",
    
    "フランクフルト": "Eintracht Frankfurt",
    "アイントラハトフランクフルト": "Eintracht Frankfurt",
    
    "ウニオンベルリン": "Union Berlin",
    "フライブルク": "Freiburg",
    "ホッフェンハイム": "Hoffenheim",
    "ケルン": "FC Koln",
    "マインツ": "Mainz",
    
    "ボルシアMG": "Borussia Monchengladbach",
    "メンヒェングラートバッハ": "Borussia Monchengladbach",
    "グラードバッハ": "Borussia Monchengladbach",
    
    "ヴォルフスブルク": "Wolfsburg",
    "ボーフム": "Bochum",
    "アウクスブルク": "Augsburg",
    "シュツットガルト": "Stuttgart",
    "ヘルタ": "Hertha Berlin",
    "シャルケ": "Schalke",
    "ブレーメン": "Werder Bremen",
    
    # ========== セリエA ==========
    "ユベントス": "Juventus",
    "ユーベ": "Juventus",
    "ユヴェントス": "Juventus",
    
    "インテル": "Inter",
    "インテルミラノ": "Inter",
    
    "ACミラン": "AC Milan",
    "ミラン": "AC Milan",
    
    "ナポリ": "Napoli",
    "ローマ": "Roma",
    "ASローマ": "Roma",
    
    "ラツィオ": "Lazio",
    "アタランタ": "Atalanta",
    "フィオレンティーナ": "Fiorentina",
    
    "トリノ": "Torino",
    "サッスオーロ": "Sassuolo",
    "ヴェローナ": "Verona",
    "ボローニャ": "Bologna",
    "ウディネーゼ": "Udinese",
    
    "サンプドリア": "Sampdoria",
    "スペツィア": "Spezia",
    "サレルニターナ": "Salernitana",
    "カリアリ": "Cagliari",
    "ジェノア": "Genoa",
    "エンポリ": "Empoli",
    "モンツァ": "Monza",
    
    # ========== リーグ・アン（フランス） ==========
    "パリサンジェルマン": "PSG",
    "PSG": "PSG",
    "パリSG": "PSG",
    
    "マルセイユ": "Marseille",
    "モナコ": "Monaco",
    "リヨン": "Lyon",
    "リール": "Lille",
    "ニース": "Nice",
    "レンヌ": "Rennes",
    "ランス": "Reims",
    "モンペリエ": "Montpellier",
    "ナント": "Nantes",
    "ストラスブール": "Strasbourg",
    
    # ========== Jリーグ ==========
    "川崎フロンターレ": "Kawasaki Frontale",
    "川崎F": "Kawasaki Frontale",
    "横浜Fマリノス": "Yokohama F Marinos",
    "横浜FM": "Yokohama F Marinos",
    
    "鹿島アントラーズ": "Kashima Antlers",
    "鹿島": "Kashima Antlers",
    "浦和レッズ": "Urawa Reds",
    "浦和": "Urawa Reds",
    
    "名古屋グランパス": "Nagoya Grampus",
    "名古屋": "Nagoya Grampus",
    "ヴィッセル神戸": "Vissel Kobe",
    "神戸": "Vissel Kobe",
    
    "サンフレッチェ広島": "Sanfrecce Hiroshima",
    "広島": "Sanfrecce Hiroshima",
    "ガンバ大阪": "Gamba Osaka",
    "G大阪": "Gamba Osaka",
    
    "セレッソ大阪": "Cerezo Osaka",
    "C大阪": "Cerezo Osaka",
    "FC東京": "FC Tokyo",
    
    # ========== その他主要クラブ ==========
    "アヤックス": "Ajax",
    "PSV": "PSV",
    "フェイエノールト": "Feyenoord",
    
    "ポルト": "Porto",
    "ベンフィカ": "Benfica",
    "スポルティング": "Sporting CP",
    
    "ガラタサライ": "Galatasaray",
    "フェネルバフチェ": "Fenerbahce",
    
    "セルティック": "Celtic",
    "レンジャーズ": "Rangers",
}

# 逆引き辞書（英語→日本語）
SOCCER_TEAM_MAP_REVERSE = {v: k for k, v in SOCCER_TEAM_MAP.items()}


def normalize_soccer_team(team_name: str, to_english: bool = True) -> str:
    """
    サッカーチーム名を正規化
    
    Args:
        team_name: チーム名
        to_english: True=英語に変換, False=日本語に変換
    
    Returns:
        変換後のチーム名（見つからない場合は元の名前を返す）
    """
    team_name = team_name.strip()
    
    if to_english:
        # 日本語→英語
        # 完全一致を試す
        if team_name in SOCCER_TEAM_MAP:
            return SOCCER_TEAM_MAP[team_name]
        
        # 部分一致を試す（「FC」などの接頭辞・接尾辞を無視）
        for jp_name, en_name in SOCCER_TEAM_MAP.items():
            if jp_name in team_name or team_name in jp_name:
                return en_name
        
        # 見つからない場合は元の名前を返す
        return team_name
    
    else:
        # 英語→日本語
        if team_name in SOCCER_TEAM_MAP_REVERSE:
            return SOCCER_TEAM_MAP_REVERSE[team_name]
        
        # 部分一致を試す
        for en_name, jp_name in SOCCER_TEAM_MAP_REVERSE.items():
            if en_name.lower() in team_name.lower() or team_name.lower() in en_name.lower():
                return jp_name
        
        return team_name


def get_team_variations(team_name: str) -> list:
    """
    チーム名の全バリエーションを取得
    
    Args:
        team_name: チーム名
    
    Returns:
        すべての表記バリエーションのリスト
    """
    variations = [team_name]
    
    # 日本語名のバリエーションを探す
    for jp_name, en_name in SOCCER_TEAM_MAP.items():
        if en_name == team_name or jp_name == team_name:
            # 同じ英語名を持つすべての日本語表記を収集
            for jp, en in SOCCER_TEAM_MAP.items():
                if en == en_name:
                    variations.append(jp)
            variations.append(en_name)
            break
    
    # 重複を除去
    return list(set(variations))


# テスト用
if __name__ == "__main__":
    print("=== サッカーチーム名変換テスト ===\n")
    
    # テストケース
    test_cases = [
        ("マンC", True),
        ("バルサ", True),
        ("PSG", False),
        ("Liverpool", False),
        ("ドルトムント", True),
        ("神戸", True),
        ("Manchester City", False),
        ("不明なチーム", True),
    ]
    
    for team, to_eng in test_cases:
        result = normalize_soccer_team(team, to_eng)
        direction = "→英語" if to_eng else "→日本語"
        print(f"{team:20} {direction}: {result}")
    
    print("\n=== バリエーション取得テスト ===\n")
    
    variations = get_team_variations("Manchester City")
    print(f"Manchester City のバリエーション: {variations}")