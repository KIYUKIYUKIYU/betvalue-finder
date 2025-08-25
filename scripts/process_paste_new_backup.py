#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
新しい貼り付け処理スクリプト
GameManagerを使用して試合を特定し、オッズを取得してEV計算

使用方法:
    python scripts/process_paste_new.py input/paste_20250825.txt
"""

import argparse
import os
import re
import sys
from datetime import datetime
from typing import List, Optional, Tuple

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_manager import MLBGameManager
from converter.baseball_rules import BaseballEV


# 貼り付けパターン
LINE_PATTERN = re.compile(r"^\s*(?P<team>[^<>\r\n]+?)(?:<(?P<handicap>[^>]+)>)?\s*$")


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
                    
                    # ハンデは片方のみ
                    if hc1:
                        games.append((team1, team2, hc1))
                    elif hc2:
                        games.append((team1, team2, hc2))
                    else:
                        games.append((team1, team2, None))
                    
                    lines = []
    
    return games


def process_mlb_game(manager: MLBGameManager, team1: str, team2: str, handicap: Optional[str]) -> None:
    """
    MLB試合を処理
    
    Args:
        manager: MLBGameManager
        team1: チーム1
        team2: チーム2  
        handicap: ハンデ（日本式）
    """
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
    
    # TODO: EV計算処理
    print("\n🎯 EV Calculation")
    print(f"   Handicap: {handicap}")
    print("   ⚠️  EV calculation not yet implemented")
    
    # 簡易的なEV計算例
    ev_calc = BaseballEV(jp_fullwin_odds=1.9, rakeback_pct=0.0)
    print(f"   JP Odds: {ev_calc.jp_fullwin_odds}")


def main():
    parser = argparse.ArgumentParser(
        description="Process paste file with new GameManager system"
    )
    parser.add_argument(
        "input_file",
        help="Input paste file (e.g., input/paste_20250825.txt)"
    )
    parser.add_argument(
        "--update-games",
        action="store_true",
        help="Update game information before processing"
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
    
    print("🚀 Paste Processor (New Version)")
    print(f"📄 Input: {args.input_file}")
    
    # 試合情報更新（オプション）
    if args.update_games:
        print("\n📊 Updating game information...")
        os.system(f"python scripts/update_games.py --sport mlb")
    
    # 貼り付けファイル解析
    games = parse_paste_file(args.input_file)
    print(f"\n📋 Found {len(games)} game(s) in paste file")
    
    # GameManager初期化
    mlb_manager = MLBGameManager(api_key)
    
    # 各試合を処理
    for team1, team2, handicap in games:
        process_mlb_game(mlb_manager, team1, team2, handicap)
    
    print("\n✅ Processing completed!")


if __name__ == "__main__":
    main()
