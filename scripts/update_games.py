#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
試合情報の定期更新スクリプト
毎日実行して最新の試合情報を取得

使用方法:
    python scripts/update_games.py --sport mlb
    python scripts/update_games.py --sport all --date 2025-08-25
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_manager import MLBGameManager


def get_api_key() -> str:
    """環境変数からAPIキーを取得"""
    api_key = os.environ.get("API_SPORTS_KEY", "").strip()
    if not api_key:
        print("❌ ERROR: API_SPORTS_KEY environment variable is not set")
        sys.exit(1)
    return api_key


def update_mlb(date: datetime, api_key: str) -> bool:
    """
    MLB試合情報を更新
    
    Args:
        date: 対象日
        api_key: APIキー
        
    Returns:
        成功したらTrue
    """
    print(f"\n📅 Updating MLB games for {date.strftime('%Y-%m-%d')}")
    print("=" * 60)
    
    try:
        manager = MLBGameManager(api_key)
        games = manager.fetch_games(date)
        
        if games:
            print(f"✅ Successfully fetched {len(games)} MLB games")
            
            # 試合一覧を表示
            print("\n📋 Game List:")
            for game in games[:5]:  # 最初の5試合のみ表示
                print(f"  • {game['away']} @ {game['home']} - {game['datetime']}")
            
            if len(games) > 5:
                print(f"  ... and {len(games) - 5} more games")
                
            return True
        else:
            print("⚠️ No games found for this date")
            return False
            
    except Exception as e:
        print(f"❌ Failed to update MLB games: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Update game information for betting analysis"
    )
    parser.add_argument(
        "--sport",
        choices=["mlb", "soccer", "all"],
        default="mlb",
        help="Sport to update (default: mlb)"
    )
    parser.add_argument(
        "--date",
        help="Target date (YYYY-MM-DD). Default: today"
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=0,
        help="Days ahead to fetch (for soccer). Default: 0"
    )
    
    args = parser.parse_args()
    
    # 日付を解析
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # デフォルトは今日（日本時間）
        target_date = datetime.now() + timedelta(hours=9)  # UTCから日本時間
    
    # APIキー取得
    api_key = get_api_key()
    
    print("🚀 Game Information Updater")
    print(f"📅 Target Date: {target_date.strftime('%Y-%m-%d')}")
    print(f"🏃 Sport: {args.sport.upper()}")
    
    # スポーツごとに更新
    success = False
    
    if args.sport in ["mlb", "all"]:
        success = update_mlb(target_date, api_key)
    
    if args.sport in ["soccer", "all"]:
        print("\n⚠️ Soccer support is not yet implemented")
        # TODO: SoccerGameManagerを実装後に追加
    
    # 結果
    if success:
        print("\n✅ Update completed successfully!")
    else:
        print("\n❌ Update failed or no games found")
        sys.exit(1)


if __name__ == "__main__":
    main()
