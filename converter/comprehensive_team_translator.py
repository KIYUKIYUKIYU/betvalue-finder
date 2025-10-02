# -*- coding: utf-8 -*-
"""
包括的チーム名翻訳システム
日本語チーム名を英語に変換するための包括的辞書
"""

class ComprehensiveTeamTranslator:
    """包括的チーム名翻訳システム"""

    def __init__(self):
        # 包括的日本語→英語チーム名マッピング
        self.team_translation_dict = {
            # ========== ヨーロッパサッカー ==========

            # ドイツ（ブンデスリーガ）
            'バイエルン': 'bayern',
            'ブレーメン': 'bremen',
            'ボルシア': 'borussia',
            'シャルケ': 'schalke',
            'ハンブルク': 'hamburg',
            'ケルン': 'koln',
            'フランクフルト': 'frankfurt',
            'レバークーゼン': 'leverkusen',
            'ドルトムント': 'dortmund',
            'ヴォルフスブルク': 'wolfsburg',
            'ヘルタ': 'hertha',
            'アウクスブルク': 'augsburg',
            'マインツ': 'mainz',
            'フライブルク': 'freiburg',
            'ホッフェンハイム': 'hoffenheim',
            'ライプツィヒ': 'leipzig',
            'ウニオン': 'union',
            'ボーフム': 'bochum',

            # スペイン（ラ・リーガ）
            'レアル・マドリード': 'real madrid',
            'レアル': 'real madrid',
            'Rマドリード': 'real madrid',
            'バルセロナ': 'barcelona',
            'バルサ': 'barcelona',
            'アトレティコ': 'atletico',
            'セビージャ': 'sevilla',
            'バレンシア': 'valencia',
            'ビルバオ': 'bilbao',
            'レアル・ソシエダ': 'real sociedad',
            'ソシエダ': 'sociedad',
            'レアルソシエダ': 'real sociedad',
            'ベティス': 'betis',
            'ビジャレアル': 'villarreal',
            'エスパニョール': 'espanyol',
            'ジローナ': 'girona',
            'セルタ': 'celta',
            'ヘタフェ': 'getafe',
            'マジョルカ': 'mallorca',
            'アラベス': 'alaves',
            'カディス': 'cadiz',
            'グラナダ': 'granada',
            'オサスナ': 'osasuna',
            'エルチェ': 'elche',
            'レバンテ': 'levante',
            'ラージョ': 'rayo',

            # イタリア（セリエA）
            'ユベントス': 'juventus',
            'ユーベ': 'juventus',
            'ミラン': 'milan',
            'インテル': 'inter',
            'ローマ': 'roma',
            'ナポリ': 'napoli',
            'ラツィオ': 'lazio',
            'フィオレンティーナ': 'fiorentina',
            'アタランタ': 'atalanta',
            'ボローニャ': 'bologna',
            'トリノ': 'torino',
            'サンプドリア': 'sampdoria',
            'ジェノア': 'genoa',
            'ウディネーゼ': 'udinese',
            'パルマ': 'parma',
            'カリアリ': 'cagliari',
            'レッチェ': 'lecce',
            'ヴェローナ': 'verona',
            'ヴェネツィア': 'venezia',
            'ベネヴェント': 'benevento',
            'サッスオーロ': 'sassuolo',
            'サッスオロ': 'sassuolo',
            'スペツィア': 'spezia',
            'エンポリ': 'empoli',
            'クレモネーゼ': 'cremonese',
            'モンツァ': 'monza',
            'ピサ': 'pisa',

            # フランス（リーグアン）
            'パリ・サンジェルマン': 'paris saint germain',
            'パリSG': 'psg',
            'PSG': 'psg',
            'マルセイユ': 'marseille',
            'リヨン': 'lyon',
            'モナコ': 'monaco',
            'リール': 'lille',
            'ニース': 'nice',
            'レンヌ': 'rennes',
            'ストラスブール': 'strasbourg',
            'モンペリエ': 'montpellier',
            'ナント': 'nantes',
            'ランス': 'reims',
            'ブレスト': 'brest',
            'アンジェ': 'angers',
            'パリFC': 'paris fc',
            'トゥールーズ': 'toulouse',
            'ロリアン': 'lorient',
            'メス': 'metz',
            'サンテティエンヌ': 'saint etienne',
            'トロワ': 'troyes',
            'クレルモン': 'clermont',
            'アジャクシオ': 'ajaccio',
            'オセール': 'auxerre',

            # イングランド（プレミアリーグ）
            'マンチェスター・ユナイテッド': 'manchester united',
            'マンU': 'manchester united',
            'マンチェスター・シティ': 'manchester city',
            'マンシティ': 'manchester city',
            'リヴァプール': 'liverpool',
            'チェルシー': 'chelsea',
            'アーセナル': 'arsenal',
            'トッテナム': 'tottenham',
            'スパーズ': 'tottenham',
            'ニューカッスル': 'newcastle',
            'ウェストハム': 'west ham',
            'エヴァートン': 'everton',
            'レスター': 'leicester',
            'ブライトン': 'brighton',
            'アストン・ヴィラ': 'aston villa',
            'ヴィラ': 'villa',
            'ウルヴス': 'wolves',
            'ワトフォード': 'watford',
            'クリスタル・パレス': 'crystal palace',
            'バーンリー': 'burnley',
            'ブレントフォード': 'brentford',
            'アストンビラ': 'aston villa',
            'アストンヴィラ': 'aston villa',
            'フラム': 'fulham',
            'ノリッジ': 'norwich',
            'リーズ': 'leeds',
            'サウサンプトン': 'southampton',
            'シェフィールド': 'sheffield',
            'フラム': 'fulham',
            'ボーンマス': 'bournemouth',
            'ハダースフィールド': 'huddersfield',

            # オランダ（エールディビジ）
            'アヤックス': 'ajax',
            'PSV': 'psv',
            'フェイエノールト': 'feyenoord',
            'AZ': 'az',
            'トゥエンテ': 'twente',
            'FC Twente': 'twente',
            'フィテッセ': 'vitesse',
            'ユトレヒト': 'utrecht',
            'ヘーレンフェーン': 'heerenveen',
            'フローニンゲン': 'groningen',
            'フォルトゥナ': 'fortuna',
            'エメン': 'emmen',
            'ズヴォレ': 'zwolle',
            'ヘラクレス': 'heracles',
            'ウィレム': 'willem',
            'スパルタ': 'sparta',
            'カンブール': 'cambuur',
            'GAイーグルス': 'go ahead eagles',
            'RKC': 'rkc',
            'NEC': 'nec',

            # ベルギー（ジュピラーリーグ）
            'アンデルレヒト': 'anderlecht',
            'ブルージュ': 'club brugge',
            'ゲント': 'gent',
            'スタンダール': 'standard',
            'ヘンク': 'genk',
            'アントワープ': 'antwerp',
            'シャルルロワ': 'charleroi',
            'メヘレン': 'mechelen',
            'オーステンデ': 'oostende',
            'ベールスホット': 'beerschot',
            'ルーヴェン': 'leuven',
            'セルクル': 'cercle',
            'ズルテ': 'zulte',
            'ワレヘム': 'waregem',
            'コルトレイク': 'kortrijk',
            'ロイヤル・エクセル': 'royal excel',
            'ユニオン': 'union',
            'ユニオンベルリン': 'union berlin',
            'シュツットガルト': 'stuttgart',
            'ハンブルガー': 'hamburger sv',
            'ハンブルク': 'hamburger sv',
            'ケルン': 'koln',
            'テルスター': 'telstar',
            'ゴーアヘッド': 'go ahead eagles',
            'シャルルロワ': 'charleroi',
            'メヘレン': 'mechelen',
            'デンデル': 'denderleeuw',
            'ラルヴィエール': 'la louviere',
            'アルヴェルカ': 'alverca',
            'ギマランイス': 'guimaraes',
            'ナシオナル': 'nacional',
            'ファマリカン': 'famalicao',
            'リオアヴェ': 'rio ave',
            'サークルB': 'cercle brugge',
            'オイペン': 'eupen',

            # スコットランド
            'セルティック': 'celtic',
            'セルティック・グラスゴー': 'celtic',
            'レンジャーズ・グラスゴー': 'rangers',

            # スイス
            'ヤングボーイズ': 'young boys',
            'バーゼル': 'basel',

            # トルコ
            'フェネルバフチェ': 'fenerbahce',
            'ガラタサライ': 'galatasaray',
            'ベシクタシュ': 'besiktas',

            # ブルガリア
            'ルドゴレツ': 'ludogorets',

            # ギリシャ
            'パナシナイコス': 'panathinaikos',
            'オリンピアコス': 'olympiacos',

            # チェコ
            'プルゼニ': 'plzen',
            'スパルタ・プラハ': 'sparta prague',
            'スラビア・プラハ': 'slavia prague',

            # スウェーデン
            'マルメ': 'malmo',

            # オーストリア
            'ザルツブルク': 'salzburg',
            'シュトゥルム': 'sturm graz',

            # ノルウェー
            'ブラン': 'brann',

            # ルーマニア
            'FCSB': 'fcsb',

            # クロアチア
            'ザグレブ': 'dinamo zagreb',
            'ディナモ・ザグレブ': 'dinamo zagreb',

            # イスラエル
            'テルアビブ': 'maccabi tel aviv',
            'マッカビ・テルアビブ': 'maccabi tel aviv',

            # ハンガリー
            'フェレンツバロシュ': 'ferencvaros',

            # デンマーク
            'ミッティラント': 'midtjylland',

            # セルビア
            'レッドスター': 'red star',
            'ツルヴェナ・ズヴェズダ': 'red star',

            # イングランド（追加）
            'フォレスト': 'nottingham forest',
            'ノッティンガム・フォレスト': 'nottingham forest',

            # ポルトガル（プリメイラリーガ）
            'ポルト': 'porto',
            'ベンフィカ': 'benfica',
            'SL Benfica': 'benfica',
            'スポルティング': 'sporting',
            'ブラガ': 'braga',
            'ヴィトーリア': 'vitoria',
            'マリティモ': 'maritimo',
            'ボアヴィスタ': 'boavista',
            'パソス': 'pacos',
            'サンタクララ': 'santa clara',
            'ファマリカン': 'famalicao',
            'トンデラ': 'tondela',
            'モレイレンセ': 'moreirense',
            'アルーカ': 'arouca',
            'エストリル': 'estoril',
            'チャベス': 'chaves',
            'ヴィゼラ': 'vizela',
            'カーザ・ピア': 'casa pia',
            'ジル': 'gil',

            # ========== MLB（メジャーリーグ） ==========
            'ヤンキース': 'yankees',
            'レッドソックス': 'red sox',
            'ブルージェイズ': 'blue jays',
            'オリオールズ': 'orioles',
            'レイズ': 'rays',
            'ガーディアンズ': 'guardians',
            'ツインズ': 'twins',
            'ホワイトソックス': 'white sox',
            'タイガース': 'tigers',
            'ロイヤルズ': 'royals',
            'アストロズ': 'astros',
            'エンゼルス': 'angels',
            'マリナーズ': 'mariners',
            'レンジャーズ': 'rangers',
            'アスレチックス': 'athletics',
            'ブレーブス': 'braves',
            'メッツ': 'mets',
            'フィリーズ': 'phillies',
            'マーリンズ': 'marlins',
            'ナショナルズ': 'nationals',
            'カージナルス': 'cardinals',
            'ブリュワーズ': 'brewers',
            'カブス': 'cubs',
            'レッズ': 'reds',
            'パイレーツ': 'pirates',
            'ドジャース': 'dodgers',
            'パドレス': 'padres',
            'ジャイアンツ': 'giants',
            'ダイヤモンドバックス': 'diamondbacks',
            'ロッキーズ': 'rockies',

            # 略称対応
            'Wソックス': 'white sox',
            'Rソックス': 'red sox',
            'Dバックス': 'diamondbacks',

            # ========== NPB（日本プロ野球） ==========
            '読売ジャイアンツ': 'giants',
            'ジャイアンツ': 'giants',
            '巨人': 'giants',
            '阪神タイガース': 'tigers',
            'タイガース': 'tigers',
            '阪神': 'tigers',
            '中日ドラゴンズ': 'dragons',
            'ドラゴンズ': 'dragons',
            '中日': 'dragons',
            '横浜DeNAベイスターズ': 'baystars',
            'ベイスターズ': 'baystars',
            'DeNA': 'baystars',
            '広島東洋カープ': 'carp',
            'カープ': 'carp',
            '広島': 'carp',
            '東京ヤクルトスワローズ': 'swallows',
            'スワローズ': 'swallows',
            'ヤクルト': 'swallows',
            '福岡ソフトバンクホークス': 'hawks',
            'ホークス': 'hawks',
            'ソフトバンク': 'hawks',
            '北海道日本ハムファイターズ': 'fighters',
            'ファイターズ': 'fighters',
            '日本ハム': 'fighters',
            '埼玉西武ライオンズ': 'lions',
            'ライオンズ': 'lions',
            '西武': 'lions',
            '千葉ロッテマリーンズ': 'marines',
            'マリーンズ': 'marines',
            'ロッテ': 'marines',
            '東北楽天ゴールデンイーグルス': 'eagles',
            'イーグルス': 'eagles',
            '楽天': 'eagles',
            'オリックスバファローズ': 'buffaloes',
            'バファローズ': 'buffaloes',
            'オリックス': 'buffaloes',
        }

    def translate_team_name(self, japanese_name: str, sport_hint: str = None) -> str:
        """日本語チーム名を英語に翻訳"""
        if not japanese_name:
            return japanese_name

        # 完全一致チェック
        if japanese_name in self.team_translation_dict:
            base_translation = self.team_translation_dict[japanese_name]

            # スポーツ別の特別処理
            if sport_hint and japanese_name == 'レンジャーズ':
                if sport_hint.lower() in ['mlb', 'baseball']:
                    return 'texas rangers'
                elif sport_hint.lower() in ['soccer', 'football']:
                    return 'rangers'  # サッカーの場合は短縮形

            return base_translation

        # 部分一致チェック（長いものから）
        for jp_name, en_name in sorted(self.team_translation_dict.items(), key=len, reverse=True):
            if jp_name in japanese_name:
                # 同様にスポーツ別処理
                if sport_hint and jp_name == 'レンジャーズ':
                    if sport_hint.lower() in ['mlb', 'baseball']:
                        return 'texas rangers'
                    elif sport_hint.lower() in ['soccer', 'football']:
                        return 'rangers'
                return en_name

        return japanese_name

    def has_japanese_characters(self, text: str) -> bool:
        """テキストに日本語文字が含まれているかチェック"""
        return any('\u3040' <= char <= '\u309F' or  # ひらがな
                  '\u30A0' <= char <= '\u30FF' or  # カタカナ
                  '\u4E00' <= char <= '\u9FAF'     # 漢字
                  for char in text)

    def translate_if_needed(self, team_name: str, sport_hint: str = None) -> str:
        """必要に応じて日本語チーム名を翻訳"""
        if self.has_japanese_characters(team_name):
            return self.translate_team_name(team_name, sport_hint)
        return team_name