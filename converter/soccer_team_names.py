# converter/soccer_team_names.py
"""
サッカーチーム名の日本語⇔英語変換
主要リーグ対応：プレミア、ラ・リーガ、ブンデス、セリエA、リーグ1、Jリーグ
+ 代表チーム
"""

# クラブチーム名変換辞書
SOCCER_TEAM_MAP = {
    # ========== プレミアリーグ ==========
    "マンチェスターシティ": "Manchester City",
    "マンチェスターC": "Manchester City",
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
    "ウエストハム": "West Ham",
    "ブレントフォード": "Brentford",
    "フラム": "Fulham",
    "ウルブス": "Wolves",
    "ウォルバーハンプトン": "Wolves",
    "エバートン": "Everton",
    "エヴァートン": "Everton",
    "クリスタルパレス": "Crystal Palace",
    "ノッティンガム": "Nottingham Forest",
    "ノッテンガム": "Nottingham Forest",
    "フォレスト": "Nottingham Forest",
    "ボーンマス": "Bournemouth",
    "レスター": "Leicester",
    "リーズ": "Leeds",
    "サウサンプトン": "Southampton",
    "サンダーランド": "Sunderland",
    "ルートン": "Luton Town",  # 追加：昇格チーム
    # テスト用追加  
    "ヘタフェ": "Getafe",
    "Rオビエド": "Oviedo", 
    "レアルオビエド": "Real Oviedo",
    
    # Champions League追加マッピング（2024-25シーズン）
    "コペンハーゲン": "FC Copenhagen",  # API正式名称に統一
    "FCコペンハーゲン": "FC Copenhagen",
    "カイラト": "Kairat Almaty",
    "カイラト・アルマトイ": "Kairat Almaty",
    "カイラトアルマトイ": "Kairat Almaty",
    "フランクフルト": "Eintracht Frankfurt",
    "アイントラハト": "Eintracht Frankfurt",
    "ガラタサライ": "Galatasaray",
    "レーバークーゼン": "Bayer Leverkusen",
    "バイエルレバークーゼン": "Bayer Leverkusen",
    "ナポリ": "Napoli",
    "クラブブルージュ": "Club Brugge KV",  # API正式名称に統一
    "ブルージュ": "Club Brugge KV",
    "モナコ": "Monaco",
    "ASモナコ": "Monaco",
    "スポルティング": "Sporting CP",
    "スポルティングCP": "Sporting CP",
    "スポルティングリスボン": "Sporting CP",

    # 追加マッピング
    "ウルヴァーハンプトン": "Wolves",
    "ウルブス": "Wolves", 
    "ウェストハム": "West Ham",
    "トテナム": "Tottenham",
    "スパーズ": "Tottenham",
    "ブレントフォード": "Brentford",
    "ユヴェントス": "Juventus",
    "インテル": "Inter Milan",
    "フィオレンティーナ": "Fiorentina",
    "ビルバオ": "Athletic Club", 
    "Aマドリード": "Atletico Madrid",
    "アトレティコ": "Atletico Madrid",
    "ビジャレアル": "Villarreal",
    "バイエルン": "Bayern Munich",
    "ハンブルク": "Hamburger SV",
    "アヤックス": "Ajax",
    "ズウォレ": "PEC Zwolle",
    "レンジャーズ": "Rangers",
    "アバディーン": "Aberdeen",
    "ダンディー": "Dundee", 
    "マザーウェル": "Motherwell",
    "フォルカーク": "Falkirk",
    "セントミレン": "St Mirren",
    "ハーツ": "Heart of Midlothian",
    "リヴィングストン": "Livingston",
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
    "アスレティックビルバオ": "Athletic Club",
    "アスレチックビルバオ": "Athletic Club",
    "ビルバオ": "Athletic Club",
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
    "ヒローナ": "Girona",  # 追加：別表記
    "レバンテ": "Levante",
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
    "レーバークーゼン": "Bayer Leverkusen",
    "フランクフルト": "Eintracht Frankfurt",
    "アイントラハトフランクフルト": "Eintracht Frankfurt",
    "ウニオンベルリン": "Union Berlin",
    "ウニオン": "Union Berlin",
    "ハイデンハイム": "1. FC Heidenheim",
    "フライブルク": "SC Freiburg",
    "ホッフェンハイム": "1899 Hoffenheim",
    "ケルン": "1. FC Koln",
    "マインツ": "FSV Mainz 05",
    "ボルシアMG": "Borussia Monchengladbach",
    "メンヒェングラートバッハ": "Borussia Monchengladbach",
    "グラードバッハ": "Borussia Monchengladbach",
    "ヴォルフスブルク": "VfL Wolfsburg",
    "ボーフム": "Bochum",
    "アウクスブルク": "Augsburg",
    "シュツットガルト": "VfB Stuttgart",
    "ホルシュタインキール": "Holstein Kiel",
    "ザンクトパウリ": "FC St. Pauli",
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
    "レッチェ": "Lecce",
    "ジェノア": "Genoa",
    "エンポリ": "Empoli",
    "モンツァ": "Monza",
    "パルマ": "Parma",
    "クレモネーゼ": "Cremonese",
    # ========== リーグ・アン（フランス） ==========
    "パリサンジェルマン": "PSG",
    "パリ・サンジェルマン": "PSG",  # 追加：ドット表記
    "PSG": "PSG",
    "パリSG": "PSG",
    "マルセイユ": "Marseille",
    "モナコ": "Monaco",
    "リヨン": "Lyon",
    "OL": "Lyon",  # 追加：よくある略称
    "リール": "Lille",
    "ニース": "Nice",
    "レンヌ": "Rennes",
    "アンジェ": "Angers SCO",
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

    # ========== チャンピオンズリーグ主要チーム ==========
    "オリンピアコス": "Olympiakos",
    "パフォス": "Pafos",
    "スラビアプラハ": "Slavia Praha",
    "ボデグリムト": "Bodo/Glimt",
    "ボドグリムト": "Bodo/Glimt",
    "スパルタ": "Sparta Rotterdam",
    "スパルタプラハ": "Sparta Praha",
    "ユトレヒト": "Utrecht",
    "ズヴォレ": "PEC Zwolle",
    "NEC": "NEC Nijmegen",
    "フォルトゥナ": "Fortuna Sittard",
    "ヘント": "Gent",
    "アンデルヒト": "Anderlecht",
    "アンデルレヒト": "Anderlecht",
    "RSCアンデルレヒト": "Anderlecht",
    "クラブ・ブルッヘ": "Club Brugge KV",
    "クラブブルッヘ": "Club Brugge KV",
    "クラブ・ブルージュ": "Club Brugge KV",
    "クラブB": "Club Brugge KV",
    "ポルト": "Porto",
    "ベンフィカ": "Benfica",
    "スポルティング": "Sporting CP",
    "ガラタサライ": "Galatasaray",
    "フェネルバフチェ": "Fenerbahce",
    "セルティック": "Celtic",
    "レンジャーズ": "Rangers",

    # ========== セリエA 追加 ==========
    "ナポリ": "Napoli",
    "ローマ": "AS Roma",
    "ラツィオ": "Lazio",
    "アタランタ": "Atalanta",
    "ボローニャ": "Bologna",
    "トリノ": "Torino",

    # ========== ラ・リーガ 追加 ==========
    "セビージャ": "Sevilla",
    "バレンシア": "Valencia",
    "レアルベティス": "Real Betis",
    "セルタ": "Celta Vigo",
    "アラベス": "Alaves",

    # ========== ブンデスリーガ 追加 ==========
    "ハンブルク": "Hamburger SV",
    "バイヤーレバークーゼン": "Bayer Leverkusen",
    "バイヤン・ミュンヘン": "Bayern Munich",  # 追加：よくある表記
    "ヘルタ": "Hertha Berlin",
    "アウクスブルク": "FC Augsburg",
    "シャルケ": "Schalke 04",
    "シュトゥットガルト": "VfB Stuttgart",
    "ザンクトパウリ": "FC St. Pauli",

    # ========== エレディビジ ==========
    "ズウォレ": "PEC Zwolle",
    "フェイエノールト": "Feyenoord",
    "PSV": "PSV Eindhoven",
    "NEC": "NEC Nijmegen",
    "ゴーアヘッド": "Go Ahead Eagles",
    "フォレダム": "Fortuna Sittard",
    "トゥウェンテ": "FC Twente",
    "トゥエンテ": "FC Twente",
    "ブレダ": "NAC Breda",
    "ヘーレンフェーン": "SC Heerenveen",
    "AZ": "AZ Alkmaar",
    "フィテッセ": "Vitesse",

    # ========== リーグアン ==========
    "ニース": "Nice",
    "ナント": "Nantes",
    "オセール": "Auxerre",
    "モナコ": "Monaco",
    "マルセイユ": "Marseille",
    "リヨン": "Lyon",
    "パリSG": "Paris Saint Germain",
    "PSG": "Paris Saint Germain",
    "リール": "Lille",
    "レンヌ": "Rennes",

    # ========== プリメイラリーガ ==========
    "ポルト": "FC Porto",
    "スポルティング": "Sporting CP",
    "ナシオナル": "Nacional",
    "ファマリカン": "Famalicao",
    "ベンフィカ": "Benfica",
    "ブラガ": "SC Braga",
    "ボアビスタ": "Boavista",
    "モレイレンセ": "Moreirense",
    "エストリル": "Estoril",
    "リオアヴェ": "Rio Ave",
    "AVS": "AVS",

    # ========== スコティッシュ ==========
    "セルティック": "Celtic",
    "ハイパーニアン": "Hibernian",
    "ハイバーニアン": "Hibernian",
    "ダンディー": "Dundee",
    "ダンディーU": "Dundee United",
    "アバディーン": "Aberdeen",
    "フォルカーク": "Falkirk",
    "キルマーノック": "Kilmarnock",
    "セントジョンストン": "St Johnstone",

    # ========== ベルギー ==========
    "ワレゲム": "Zulte Waregem",
    "ルーヴェン": "OH Leuven",
    "デンデル": "FCV Dender EH",
    "サンジロワーズ": "Union St. Gilloise",
    "ラルヴィエール": "RFC Seraing",
    "ゲント": "KAA Gent",
    "アントワープ": "Royal Antwerp",
    "スタンダード": "Standard Liege",
    "アンデルレヒト": "RSC Anderlecht",
}

# 代表チーム名変換辞書
NATIONAL_TEAM_MAP = {
    # 欧州
    "カザフスタン": "Kazakhstan",
    "ウェールズ": "Wales",
    "ジョージア": "Georgia",
    "トルコ": "Turkey",
    "リトアニア": "Lithuania",
    "マルタ": "Malta",
    "オランダ": "Netherlands",
    "ポーランド": "Poland",
    "スロバキア": "Slovakia",
    "ドイツ": "Germany",
    "ブルガリア": "Bulgaria",
    "スペイン": "Spain",
    "リヒテンシュタイン": "Liechtenstein",
    "ベルギー": "Belgium",
    "ルクセンブルク": "Luxembourg",
    "北アイルランド": "Northern Ireland",
    "フランス": "France",
    "イタリア": "Italy",
    "イングランド": "England",
    "スコットランド": "Scotland",
    "アイルランド": "Ireland",
    "ポルトガル": "Portugal",
    "スイス": "Switzerland",
    "オーストリア": "Austria",
    "チェコ": "Czech Republic",
    "クロアチア": "Croatia",
    "セルビア": "Serbia",
    "ボスニア・ヘルツェゴビナ": "Bosnia and Herzegovina",
    "スロベニア": "Slovenia",
    "ハンガリー": "Hungary",
    "ルーマニア": "Romania",
    "ギリシャ": "Greece",
    "デンマーク": "Denmark",
    "スウェーデン": "Sweden",
    "ノルウェー": "Norway",
    "フィンランド": "Finland",
    "アイスランド": "Iceland",
    "エストニア": "Estonia",
    "ラトビア": "Latvia",
    "ウクライナ": "Ukraine",
    "ベラルーシ": "Belarus",
    "ロシア": "Russia",
    "モルドバ": "Moldova",
    "北マケドニア": "North Macedonia",
    "アルバニア": "Albania",
    "モンテネグロ": "Montenegro",
    "アゼルバイジャン": "Azerbaijan",
    "アルメニア": "Armenia",
    "ボスニアヘルツェゴビナ": "Bosnia and Herzegovina",
    "ボスニア・ヘルツェゴビナ": "Bosnia and Herzegovina",
    "キプロス": "Cyprus",
    # 南米
    "アルゼンチン": "Argentina",
    "ベネズエラ": "Venezuela",
    "ウルグアイ": "Uruguay",
    "ペルー": "Peru",
    "コロンビア": "Colombia",
    "ボリビア": "Bolivia",
    "パラグアイ": "Paraguay",
    "エクアドル": "Ecuador",
    "ブラジル": "Brazil",
    "チリ": "Chile",
    # アフリカ
    "アルジェリア": "Algeria",
    "ギニア": "Guinea",
    "モロッコ": "Morocco",
    "チュニジア": "Tunisia",
    "エジプト": "Egypt",
    "ナイジェリア": "Nigeria",
    "ガーナ": "Ghana",
    "セネガル": "Senegal",
    "カメルーン": "Cameroon",
    "南アフリカ": "South Africa",
    "コートジボワール": "Ivory Coast",
    "ブルキナファソ": "Burkina Faso",
    "マリ": "Mali",
    "ケニア": "Kenya",
    "エチオピア": "Ethiopia",
    "ザンビア": "Zambia",
    "ジンバブエ": "Zimbabwe",
    "マダガスカル": "Madagascar",
    "ウガンダ": "Uganda",
    "コンゴ民主共和国": "DR Congo",
    "コンゴ": "Congo",
    "ガボン": "Gabon",
    "赤道ギニア": "Equatorial Guinea",
    "中央アフリカ": "Central African Republic",
    "チャド": "Chad",
    "スーダン": "Sudan",
    "南スーダン": "South Sudan",
    "リビア": "Libya",
    "モーリタニア": "Mauritania",
    "モザンビーク": "Mozambique",
    "アンゴラ": "Angola",
    "ボツワナ": "Botswana",
    "ナミビア": "Namibia",
    "レソト": "Lesotho",
    "スワジランド": "Eswatini",
    "マラウイ": "Malawi",
    "タンザニア": "Tanzania",
    "ルワンダ": "Rwanda",
    "ブルンジ": "Burundi",
    # アジア
    "日本": "Japan",
    "韓国": "South Korea",
    "中国": "China",
    "オーストラリア": "Australia",
    "サウジアラビア": "Saudi Arabia",
    "イラン": "Iran",
    "イラク": "Iraq",
    "アラブ首長国連邦": "United Arab Emirates",
    "UAE": "United Arab Emirates",
    "カタール": "Qatar",
    "クウェート": "Kuwait",
    "バーレーン": "Bahrain",
    "オマーン": "Oman",
    "イエメン": "Yemen",
    "ヨルダン": "Jordan",
    "レバノン": "Lebanon",
    "シリア": "Syria",
    "パレスチナ": "Palestine",
    "イスラエル": "Israel",
    "インド": "India",
    "バングラデシュ": "Bangladesh",
    "スリランカ": "Sri Lanka",
    "パキスタン": "Pakistan",
    "アフガニスタン": "Afghanistan",
    "ウズベキスタン": "Uzbekistan",
    "キルギス": "Kyrgyzstan",
    "タジキスタン": "Tajikistan",
    "トルクメニスタン": "Turkmenistan",
    "タイ": "Thailand",
    "ベトナム": "Vietnam",
    "マレーシア": "Malaysia",
    "シンガポール": "Singapore",
    "インドネシア": "Indonesia",
    "フィリピン": "Philippines",
    "ミャンマー": "Myanmar",
    "カンボジア": "Cambodia",
    "ラオス": "Laos",
    "ブルネイ": "Brunei",
    "東ティモール": "Timor-Leste",
    "モンゴル": "Mongolia",
    "ブータン": "Bhutan",
    "モルディブ": "Maldives",
    # 北中米・カリブ
    "アメリカ": "United States",
    "アメリカ合衆国": "United States",
    "米国": "United States",
    "カナダ": "Canada",
    "メキシコ": "Mexico",
    "コスタリカ": "Costa Rica",
    "パナマ": "Panama",
    "ホンジュラス": "Honduras",
    "エルサルバドル": "El Salvador",
    "グアテマラ": "Guatemala",
    "ベリーズ": "Belize",
    "ニカラグア": "Nicaragua",
    "ジャマイカ": "Jamaica",
    "キューバ": "Cuba",
    "ハイチ": "Haiti",
    "ドミニカ共和国": "Dominican Republic",
    "トリニダード・トバゴ": "Trinidad and Tobago",
    "バルバドス": "Barbados",
    # オセアニア
    "ニュージーランド": "New Zealand",
    "フィジー": "Fiji",
    "バヌアツ": "Vanuatu",
    "ソロモン諸島": "Solomon Islands",
    "パプアニューギニア": "Papua New Guinea",
    "サモア": "Samoa",
    "トンガ": "Tonga",
    "ニューカレドニア": "New Caledonia",
    "タヒチ": "Tahiti",
}

# 統合辞書
ALL_TEAMS_MAP = {**SOCCER_TEAM_MAP, **NATIONAL_TEAM_MAP}

# 逆引き辞書（英語→日本語）
ALL_TEAMS_MAP_REVERSE = {v: k for k, v in ALL_TEAMS_MAP.items()}


def normalize_soccer_team(team_name: str, to_english: bool = True) -> str:
    """
    サッカーチーム名を正規化（クラブ・代表対応）
    
    Args:
        team_name: チーム名
        to_english: True=英語に変換, False=日本語に変換
    
    Returns:
        変換後のチーム名（見つからない場合は元の名前を返す）
    """
    team_name = team_name.strip()
    
    if to_english:
        # 日本語→英語
        if team_name in ALL_TEAMS_MAP:
            return ALL_TEAMS_MAP[team_name]
        
        for jp_name, en_name in ALL_TEAMS_MAP.items():
            if jp_name in team_name or team_name in jp_name:
                return en_name
        
        return team_name
    
    else:
        # 英語→日本語
        if team_name in ALL_TEAMS_MAP_REVERSE:
            return ALL_TEAMS_MAP_REVERSE[team_name]
        
        for en_name, jp_name in ALL_TEAMS_MAP_REVERSE.items():
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
    
    for jp_name, en_name in ALL_TEAMS_MAP.items():
        if en_name == team_name or jp_name == team_name:
            for jp, en in ALL_TEAMS_MAP.items():
                if en == en_name:
                    variations.append(jp)
            variations.append(en_name)
            break
    
    return list(set(variations))
