#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新しい貼り付け処理スクリプト（完全版）
GameManagerを使用して試合を特定し、オッズを取得してEV計算

使用方法:
    python scripts/process_paste_new.py input/paste_20250825.txt
    python scripts/process_paste_new.py input/paste_20250825.txt --rakeback 0.015
"""

import argparse
import os
import re
import sys
from datetime import datetime
from typing import List, Optional, Tuple, Dict

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_manager import MLBGameManager
from converter.baseball_rules import BaseballEV, remove_margin_fair_probs
from converter.handicap_interpolator import HandicapInterpolator
from app.converter import jp_to_pinnacle


# 貼り付けパターン
LINE_PATTERN = re.compile(r"^\s*(?P<team>[^<>\r\n]+?)(?:<(?P<handicap>[^>]+)>)?\s*$")

# verdict判定のしきい値（%）
DEFAULT_THRESHOLD = {
    "clear_plus": 5.0,
    "plus": 0.0,
    "fair": -3.0
}


def parse_paste_file(filepath: str) -> List[Tuple[str, str, Optional[str]]]:
    """
    貼り付けファイルを解析
    
    Args:
        filepath: ファイルパス
        
    Returns:
        [(チーム1, チーム2, ハンデ), ...]
    """
    games = []
    current_sport = "mlb"  # デフォルト
    lines = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            # スポーツタグ
            if line.upper() in ["[MLB]", "[ＭＬＢ]"]:
                current_sport = "mlb"
                continue
            elif line.upper() in ["[SOCCER]", "[サッカー]"]:
                current_sport = "soccer"
                continue
            
            # 空行はスキップ
            if not line:
                continue
            
            # チーム名とハンデを抽出
            match = LINE_PATTERN.match(line)
            if match:
                team = match.group("team").strip()
                handicap = match.group("handicap")
                lines.append((team, handicap))
                
                # 2行で1試合
                if len(lines) == 2:
                    team1, hc1 = lines[0]
                    team2, hc2 = lines[1]
                    
                    # ハンデが付いている方を記録
                    if hc1:
                        games.append((team1, team2, hc1))
                    elif hc2:
                        games.append((team1, team2, hc2))
                    else:
                        games.append((team1, team2, None))
                    
                    lines = []
    
    return games


def extract_handicap_odds(bookmakers: List[Dict]) -> Dict[float, Tuple[float, float]]:
    """
    ブックメーカーデータからハンディキャップオッズを抽出
    
    Args:
        bookmakers: APIから取得したブックメーカーデータ
        
    Returns:
        {ライン値: (home_odds, away_odds), ...}
    """
    line_data = {}
    
    # Pinnacleを優先
    pinnacle_data = None
    for bm in bookmakers:
        if bm.get("id") == 4 or bm.get("name") == "Pinnacle":
            pinnacle_data = bm
            break
    
    # Pinnacleがなければ最初のブックメーカー
    if not pinnacle_data and bookmakers:
        pinnacle_data = bookmakers[0]
    
    if not pinnacle_data:
        return line_data
    
    # Asian Handicapマーケットを探す
    for bet in pinnacle_data.get("bets", []):
        bet_name = bet.get("name", "").lower()
        
        # ハンディキャップ系のマーケット
        if any(term in bet_name for term in ["handicap", "spread", "run line", "runline"]):
            # First Halfは除外
            if "first" in bet_name or "1st" in bet_name:
                continue
                
            for value_data in bet.get("values", []):
                value_str = value_data.get("value", "")
                odd = float(value_data.get("odd", 0))
                
                if not value_str or odd == 0:
                    continue
                
                # "Home -1.5" や "Away +2" のパターンを解析
                parts = value_str.split()
                if len(parts) >= 2:
                    side = parts[0].lower()
                    line_str = " ".join(parts[1:])
                    
                    try:
                        # 符号付きの数値を抽出
                        line_value = float(line_str)
                        
                        # Home視点のラインに統一
                        if side == "home":
                            # Homeの-1.5は、line_data[-1.5]のhome_oddsに格納
                            if line_value not in line_data:
                                line_data[line_value] = (odd, None)
                            else:
                                line_data[line_value] = (odd, line_data[line_value][1])
                        elif side == "away":
                            # Awayの+1.5は、Home視点で-1.5なので、line_data[-1.5]のaway_oddsに格納
                            home_line = -line_value
                            if home_line not in line_data:
                                line_data[home_line] = (None, odd)
                            else:
                                line_data[home_line] = (line_data[home_line][0], odd)
                    except ValueError:
                        continue
    
    # Noneを含むペアを除去
    clean_data = {}
    for line, (home_odd, away_odd) in line_data.items():
        if home_odd is not None and away_odd is not None:
            clean_data[line] = (home_odd, away_odd)
    
    return clean_data


def decide_verdict(ev_pct: float, thresholds: Dict[str, float]) -> str:
    """
    EV%からverdictを判定
    
    Args:
        ev_pct: EV%
        thresholds: しきい値辞書
        
    Returns:
        verdict文字列
    """
    if ev_pct >= thresholds["clear_plus"]:
        return "clear_plus"
    elif ev_pct >= thresholds["plus"]:
        return "plus"
    elif ev_pct >= thresholds["fair"]:
        return "fair"
    else:
        return "minus"


def process_mlb_game(
    manager: MLBGameManager, 
    team1: str, 
    team2: str, 
    handicap: Optional[str],
    jp_odds: float = 1.9,
    rakeback: float = 0.0,
    thresholds: Dict[str, float] = None
) -> None:
    """
    MLB試合を処理（完全版）
    
    Args:
        manager: MLBGameManager
        team1: チーム1
        team2: チーム2  
        handicap: ハンデ（日本式）
        jp_odds: 日本式配当
        rakeback: レーキバック率
        thresholds: verdict判定しきい値
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLD
        
    print("\n" + "=" * 60)
    print(f"🏟️  {team1} vs {team2}")
    
    # 試合を検索
    game = manager.match_teams([team1, team2])
    
    if not game:
        print("❌ 試合が見つかりません")
        print("   ※試合情報を更新してください: python scripts/update_games.py")
        return
    
    # 試合情報表示
    print(f"📅 {game['datetime']}")
    print(f"🏠 HOME: {game['home']} ({game.get('home_jp', '')})")
    print(f"✈️  AWAY: {game['away']} ({game.get('away_jp', '')})")
    
    if not handicap:
        print("⚠️  ハンデが指定されていません")
        return
    
    # どちらのチームにハンデが付いているか判定
    if team1 in [game.get('home_jp'), game['home'].split()[-1]]:
        fav_team = game['home']
        fav_side = "home"
    else:
        fav_team = game['away']
        fav_side = "away"
    
    # オッズ取得
    print(f"\n📊 Fetching odds for game ID: {game['id']}...")
    odds_data = manager.fetch_odds(game['id'])
    
    if not odds_data:
        print("❌ オッズを取得できませんでした")
        return
    
    # ブックメーカー情報
    bookmakers = odds_data.get("bookmakers", [])
    print(f"📚 Found odds from {len(bookmakers)} bookmaker(s)")
    
    for bm in bookmakers:
        print(f"   • {bm.get('name', 'Unknown')} (ID: {bm.get('id')})")
    
    # ハンディキャップオッズを抽出
    line_data = extract_handicap_odds(bookmakers)
    
    if not line_data:
        print("❌ ハンディキャップオッズが見つかりません")
        return
    
    print(f"\n📈 Available lines: {sorted(line_data.keys())}")
    
    # 日本式ハンデをピナクル値に変換
    try:
        pinnacle_value = jp_to_pinnacle(handicap)
        target_line = -pinnacle_value if fav_side == "home" else pinnacle_value
        print(f"🎯 Target: {handicap} (JP) → {pinnacle_value:.2f} (Pinnacle) → Line {target_line:+.2f} for {fav_side}")
    except Exception as e:
        print(f"❌ 日本式ハンデの変換に失敗: {handicap} - {e}")
        return
    
    # HandicapInterpolatorで補間
    interpolator = HandicapInterpolator()
    
    # 0.05刻みで補間
    interpolated = interpolator.interpolate_fine_lines(line_data, step=0.05)
    
    # ターゲットラインの公正確率を取得
    fair_probs = interpolator.calculate_fair_probs_for_line(interpolated, target_line)
    
    if not fair_probs:
        print(f"❌ ライン {target_line:+.2f} の確率を計算できません（補間範囲外）")
        return
    
    # 該当チームの勝率
    if fav_side == "home":
        team_fair_prob = fair_probs[0]  # Home側の確率
    else:
        team_fair_prob = fair_probs[1]  # Away側の確率
    
    # EV計算
    ev_calc = BaseballEV(jp_fullwin_odds=jp_odds, rakeback_pct=rakeback)
    ev_plain = ev_calc.ev_pct_plain(team_fair_prob)
    ev_with_rake = ev_calc.ev_pct_with_rakeback(team_fair_prob)
    
    # 実効配当
    effective_odds = jp_odds + (rakeback / team_fair_prob) if team_fair_prob > 0 else jp_odds
    
    # verdict判定
    verdict = decide_verdict(ev_with_rake, thresholds)
    
    # 結果表示
    print("\n" + "─" * 40)
    print(f"📊 計算結果 【{fav_team} {handicap}】")
    print("─" * 40)
    print(f"🎲 公正勝率: {team_fair_prob*100:.1f}%")
    print(f"💰 公正オッズ: {1/team_fair_prob:.3f}")
    print(f"📈 日本式EV: {ev_plain:+.1f}%")
    
    if rakeback > 0:
        print(f"🎁 レーキバック: {rakeback*100:.1f}%")
        print(f"💎 実効配当: {jp_odds:.2f} → {effective_odds:.3f}")
        print(f"🚀 EV(レーキ後): {ev_with_rake:+.1f}%")
    
    # Verdict表示（色付き風）
    verdict_symbols = {
        "clear_plus": "🌟 CLEAR PLUS",
        "plus": "✅ PLUS",
        "fair": "⚖️  FAIR",
        "minus": "❌ MINUS"
    }
    print(f"\n🏆 判定: {verdict_symbols.get(verdict, verdict.upper())}")
    
    # しきい値情報
    print(f"   (基準: clear_plus≥{thresholds['clear_plus']:.0f}%, plus≥{thresholds['plus']:.0f}%, fair≥{thresholds['fair']:.0f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="MLB貼り付け処理（完全版） - GameManager + EV計算対応"
    )
    parser.add_argument(
        "input_file",
        help="入力ファイル (例: input/paste_20250825.txt)"
    )
    parser.add_argument(
        "--update-games",
        action="store_true",
        help="処理前に試合情報を更新"
    )
    parser.add_argument(
        "--jp-odds",
        type=float,
        default=1.9,
        help="日本式配当（デフォルト: 1.9）"
    )
    parser.add_argument(
        "--rakeback",
        type=float,
        default=0.0,
        help="レーキバック率 0〜0.03（例: 0.015 = 1.5%%）"
    )
    parser.add_argument(
        "--th-clear-plus",
        type=float,
        default=5.0,
        help="clear_plusのしきい値（%%）"
    )
    parser.add_argument(
        "--th-plus",
        type=float,
        default=0.0,
        help="plusのしきい値（%%）"
    )
    parser.add_argument(
        "--th-fair",
        type=float,
        default=-3.0,
        help="fairのしきい値（%%）"
    )
    
    args = parser.parse_args()
    
    # ファイル存在確認
    if not os.path.exists(args.input_file):
        print(f"❌ File not found: {args.input_file}")
        sys.exit(1)
    
    # APIキー取得
    api_key = os.environ.get("API_SPORTS_KEY", "").strip()
    if not api_key:
        print("❌ API_SPORTS_KEY environment variable is not set")
        sys.exit(1)
    
    print("🚀 MLB Paste Processor (Complete Version)")
    print(f"📄 Input: {args.input_file}")
    print(f"💰 Settings: JP Odds={args.jp_odds}, Rakeback={args.rakeback*100:.1f}%")
    
    # 試合情報更新（オプション）
    if args.update_games:
        print("\n📊 Updating game information...")
        os.system(f"python scripts/update_games.py --sport mlb")
    
    # 貼り付けファイル解析
    games = parse_paste_file(args.input_file)
    print(f"\n📋 Found {len(games)} game(s) in paste file")
    
    # GameManager初期化
    mlb_manager = MLBGameManager(api_key)
    
    # しきい値辞書
    thresholds = {
        "clear_plus": args.th_clear_plus,
        "plus": args.th_plus,
        "fair": args.th_fair
    }
    
    # 各試合を処理
    for team1, team2, handicap in games:
        process_mlb_game(
            mlb_manager, 
            team1, 
            team2, 
            handicap,
            jp_odds=args.jp_odds,
            rakeback=args.rakeback,
            thresholds=thresholds
        )
    
    print("\n✅ Processing completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()