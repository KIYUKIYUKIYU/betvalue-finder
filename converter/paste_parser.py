# converter/paste_parser.py
# 貼り付け記法のパーサー（MLB/サッカー対応版）
# 空行分割と連続ハンデパターン対応版

from __future__ import annotations
import re
import sys
import os
from typing import List, Tuple, Optional, Dict, Any

# パスを追加（単体実行時のため）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # 統一ハンデ変換システムを使用
    from converter.unified_handicap_converter import jp_to_pinnacle, HandicapConversionError
    # HandicapParserも統合
    from converter.handicap_parser import HandicapParser
    
    def try_parse_jp(jp_str):
        """統一ハンデ変換システムを使ったパース"""
        try:
            pinnacle_value = jp_to_pinnacle(jp_str)
            return (True, pinnacle_value)
        except (HandicapConversionError, Exception):
            return (False, None)
            
except ImportError:
    # フォールバック：簡易実装
    def try_parse_jp(jp_str):
        mapping = {
            "0.1": (True, 0.05),
            "02": (True, 0.10), 
            "0半": (True, 0.5),
            "1半": (True, 1.5),
            "1.5": (True, 1.25),
            "1.8": (True, 1.40),
        }
        return mapping.get(jp_str, (False, None))

from converter.team_names import normalize_team_name, get_japanese_name

# サッカーチーム名変換を条件付きインポート
try:
    from converter.soccer_team_names import normalize_soccer_team
    SOCCER_SUPPORT = True
except ImportError:
    SOCCER_SUPPORT = False
    print("Warning: soccer_team_names.py not found. Soccer support disabled.")

# 貼り付け記法の行パターン
LINE_RE = re.compile(r"^\s*(?P<name>[^<>\r\n]+?)(?:<(?P<jp>[^>]+)>)?\s*$")

class PasteParser:
    """
    貼り付け記法をパースして構造化データに変換
    空行分割と連続ハンデパターン対応版
    """
    
    def __init__(self, sport: str = "mlb"):
        self.sport = sport.lower()
        self.api_games: Optional[List[Dict[str, Any]]] = None
    
    def set_api_games(self, api_games: List[Dict[str, Any]]):
        """APIから取得した試合データをセット（照合用）"""
        self.api_games = api_games
    
    def parse_text(self, text: str) -> List[Dict]:
        """
        貼り付けテキストをパースして試合リストを返す
        
        Returns:
            List[Dict]: 各試合の情報
                - team_a: チームA名（英語・正式名称）
                - team_b: チームB名（英語・正式名称）
                - team_a_jp: チームA名（日本語）
                - team_b_jp: チームB名（日本語）
                - line_a: チームAの日本式ライン（あれば）
                - line_b: チームBの日本式ライン（あれば）
                - fav_side: "a" or "b" or None（フェイバリット側）
                - fav_line_pinnacle: フェイバリットのピナクル値
        """
        lines = text.strip().split('\n')
        
        # ヘッダー行を除去して、内容行のみを抽出
        content_lines = []
        for line in lines:
            # [MLB]などのヘッダーはスキップ
            if line.strip() and not (line.strip().startswith('[') and line.strip().endswith(']')):
                content_lines.append(line)
            elif not line.strip():
                # 空行は区切りとして保持
                content_lines.append('')
        
        # 空行で分割してブロック化
        blocks = self._split_by_empty_lines(content_lines)
        
        # 各ブロックを処理
        all_games = []
        for block in blocks:
            if block:
                games = self._process_block(block)
                all_games.extend(games)
        
        return all_games
    
    def _split_by_empty_lines(self, lines: List[str]) -> List[List[str]]:
        """空行で分割してブロック化"""
        blocks = []
        current_block = []
        
        for line in lines:
            if line.strip() == '':
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(line)
        
        # 最後のブロックを追加
        if current_block:
            blocks.append(current_block)
        
        return blocks
    
    def _process_block(self, block: List[str]) -> List[Dict]:
        """各ブロックを処理"""
        # 各行からチーム名とラインを抽出
        pairs = self._extract_pairs(block)
        
        if len(pairs) == 2:
            # 2行の場合：そのままペアリング
            games = [(pairs[0], pairs[1])]
        elif len(pairs) >= 3:
            # 3行以上の場合：特殊処理
            games = self._handle_multi_lines(pairs)
        else:
            # 1行の場合：スキップ
            games = []
        
        # 試合情報を構造化
        return self._process_games(games)
    
    def _handle_multi_lines(self, pairs: List[Tuple[str, Optional[str]]]) -> List[Tuple]:
        """3行以上のブロックを処理（連続ハンデパターン対応）"""
        
        # APIデータとの照合を試みる
        if self.api_games:
            matched_games = self._match_with_api(pairs)
            if matched_games:
                return matched_games
        
        # 連続ハンデパターンの検出
        # 例：エンゼルス、カブス<1.3>、マリナーズ<1.4>、アスレチックス
        # → エンゼルス vs カブス、マリナーズ vs アスレチックス
        
        games = []
        handicap_indices = []
        
        # ハンデ付きの行のインデックスを取得
        for i, (name, jp_line) in enumerate(pairs):
            if jp_line:
                handicap_indices.append(i)
        
        # 連続ハンデパターンの判定
        if len(handicap_indices) >= 2:
            # 連続するハンデがある場合
            consecutive = True
            for i in range(len(handicap_indices) - 1):
                if handicap_indices[i+1] - handicap_indices[i] != 1:
                    consecutive = False
                    break
            
            if consecutive and handicap_indices[0] == 1:
                # パターン：通常、ハンデ1、ハンデ2、通常...
                # 0-1、2-3でペアリング
                for i in range(0, len(pairs), 2):
                    if i + 1 < len(pairs):
                        games.append((pairs[i], pairs[i+1]))
                return games
        
        # デフォルト：2行ずつペアリング
        for i in range(0, len(pairs) - 1, 2):
            games.append((pairs[i], pairs[i + 1]))
        
        return games
    
    def _match_with_api(self, pairs: List[Tuple[str, Optional[str]]]) -> Optional[List[Tuple]]:
        """APIデータと照合してペアリングを決定"""
        if not self.api_games:
            return None
        
        # チーム名を正規化
        normalized_teams = []
        for name, jp_line in pairs:
            en_name, _ = self._normalize_team_name(name)
            normalized_teams.append((en_name, name, jp_line))
        
        # APIデータと照合
        matched_pairs = []
        used_indices = set()
        
        for api_game in self.api_games:
            home = api_game.get('home_team', '')
            away = api_game.get('away_team', '')
            
            # 正規化
            if self.sport in ["mlb", "baseball"]:
                home = normalize_team_name(home) or home
                away = normalize_team_name(away) or away
            elif self.sport == "soccer" and SOCCER_SUPPORT:
                home = normalize_soccer_team(home, to_english=True)
                away = normalize_soccer_team(away, to_english=True)
            
            # マッチング
            home_idx = None
            away_idx = None
            
            for i, (en_name, orig_name, jp_line) in enumerate(normalized_teams):
                if i in used_indices:
                    continue
                    
                if en_name == home:
                    home_idx = i
                elif en_name == away:
                    away_idx = i
            
            # 両方マッチした場合
            if home_idx is not None and away_idx is not None:
                used_indices.add(home_idx)
                used_indices.add(away_idx)
                matched_pairs.append((pairs[home_idx], pairs[away_idx]))
        
        return matched_pairs if matched_pairs else None
    
    def _extract_pairs(self, lines: List[str]) -> List[Tuple[str, Optional[str]]]:
        """各行からチーム名と日本式ラインを抽出"""
        pairs = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 時間行をスキップ（HH:MM形式）
            if re.match(r'^\d{1,2}:\d{2}$', line):
                continue
                
            # まずHandicapParserでハンデを検出
            try:
                handicap_str, parsed_value = HandicapParser.detect_handicap_in_text(line)
                if handicap_str and parsed_value is not None:
                    # ハンデが見つかった場合、チーム名部分を抽出
                    team_part = line.replace(f"<{handicap_str}>", "").strip()
                    pairs.append((team_part, handicap_str))
                    continue
            except:
                pass
                
            # フォールバック：従来の正規表現
            m = LINE_RE.match(line)
            if not m:
                continue
            
            name = m.group("name").strip()
            jp = m.group("jp")
            jp = jp.strip() if jp else None
            pairs.append((name, jp))
        
        return pairs
    
    def _chunk_games(self, pairs: List[Tuple[str, Optional[str]]]) -> List[Tuple]:
        """2行ずつペアにして試合を構成（後方互換性のため残す）"""
        games = []
        for i in range(0, len(pairs) - 1, 2):
            games.append((pairs[i], pairs[i + 1]))
        return games
    
    def _normalize_team_name(self, name: str) -> Tuple[str, str]:
        """
        スポーツに応じてチーム名を正規化
        
        Returns:
            (英語名, 日本語名)
        """
        if self.sport == "soccer" and SOCCER_SUPPORT:
            # サッカーの場合
            en_name = normalize_soccer_team(name, to_english=True)
            
            # 既に英語の場合は日本語名を取得
            if en_name == name:
                jp_name = normalize_soccer_team(name, to_english=False)
                # 変換できなかった場合は元の名前を使用
                if jp_name == name:
                    jp_name = name
            else:
                # 日本語から英語に変換された場合
                jp_name = name
            
            return en_name, jp_name
            
        elif self.sport in ["mlb", "baseball"]:
            # MLBの場合（既存処理）
            en_name = normalize_team_name(name)
            if en_name:
                jp_name = get_japanese_name(en_name)
            else:
                # 正規化できなかった場合
                en_name = name
                jp_name = name
            
            return en_name, jp_name
            
        else:
            # その他のスポーツ（NBA等）は変換なし
            return name, name
    
    def _process_games(self, games: List[Tuple]) -> List[Dict]:
        """試合情報を構造化"""
        results = []
        
        for (name_a_raw, jp_a), (name_b_raw, jp_b) in games:
            # スポーツに応じたチーム名正規化
            en_a, jp_a_display = self._normalize_team_name(name_a_raw)
            en_b, jp_b_display = self._normalize_team_name(name_b_raw)
            
            # 正規化できなかった場合の警告
            if en_a == name_a_raw and self.sport in ["mlb", "soccer"]:
                print(f"Warning: Could not normalize team name: {name_a_raw} ({self.sport})")
            if en_b == name_b_raw and self.sport in ["mlb", "soccer"]:
                print(f"Warning: Could not normalize team name: {name_b_raw} ({self.sport})")
            
            # フェイバリット判定
            fav_side = None
            fav_line_pinnacle = None
            
            if jp_a:
                fav_side = "a"
                ok, pinn = try_parse_jp(jp_a)
                if ok:
                    fav_line_pinnacle = pinn
            elif jp_b:
                fav_side = "b"
                ok, pinn = try_parse_jp(jp_b)
                if ok:
                    fav_line_pinnacle = pinn
            
            results.append({
                "team_a": en_a,
                "team_b": en_b,
                "team_a_jp": jp_a_display,
                "team_b_jp": jp_b_display,
                "line_a": jp_a,
                "line_b": jp_b,
                "fav_side": fav_side,
                "fav_line_pinnacle": fav_line_pinnacle,
                "sport": self.sport,  # スポーツ種別も含める
            })
        
        return results

def parse_paste_text(text: str, sport: str = "mlb") -> List[Dict]:
    """
    便利関数：テキストをパースして試合リストを返す（時刻情報抽出対応）

    Args:
        text: 貼り付けテキスト
        sport: スポーツ種別 ("mlb", "soccer", "nba" など)

    Returns:
        試合情報のリスト（時刻情報も含む）
    """
    # 時刻情報を抽出
    try:
        from game_manager.time_parser import time_parser
        extracted_time = time_parser.extract_time_from_text(text)
    except Exception:
        extracted_time = None

    parser = PasteParser(sport)
    games = parser.parse_text(text)

    # 全ての試合に時刻情報を追加
    for game in games:
        game['extracted_time'] = extracted_time
        if extracted_time:
            game['is_deep_night'] = time_parser.is_deep_night_time(extracted_time)
        else:
            game['is_deep_night'] = False

    return games


# テスト用
if __name__ == "__main__":
    print("=== paste_parser.py テスト ===\n")
    
    # MLBテスト（連続ハンデパターン）
    mlb_text = """
[MLB]
ヤンキース
レッドソックス<0.5>

マーリンズ  
ブルージェイズ<1.1>

エンゼルス
カブス<1.3>
マリナーズ<1.4>
アスレチックス
"""
    
    print("【MLB解析結果】")
    mlb_games = parse_paste_text(mlb_text, "mlb")
    for i, game in enumerate(mlb_games, 1):
        print(f"{i}. {game['team_a_jp']} ({game['team_a']}) vs {game['team_b_jp']} ({game['team_b']})")
        if game['fav_side']:
            fav_team = game['team_a_jp'] if game['fav_side'] == 'a' else game['team_b_jp']
            print(f"   → フェイバリット: {fav_team}, ライン: {game['fav_line_pinnacle']}")
    
    # サッカーテスト（soccer_team_names.pyがある場合のみ）
    if SOCCER_SUPPORT:
        soccer_text = """
[サッカー]
マンC<0半>
リバプール

レアル<1半>
バルサ
"""
        
        print("\n【サッカー解析結果】")
        soccer_games = parse_paste_text(soccer_text, "soccer")
        for i, game in enumerate(soccer_games, 1):
            print(f"{i}. {game['team_a_jp']} ({game['team_a']}) vs {game['team_b_jp']} ({game['team_b']})")
            if game['fav_side']:
                fav_team = game['team_a_jp'] if game['fav_side'] == 'a' else game['team_b_jp']
                print(f"   → フェイバリット: {fav_team}, ライン: {game['fav_line_pinnacle']}")
    else:
        print("\n【サッカー】soccer_team_names.pyが見つかりません")