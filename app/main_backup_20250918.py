# -*- coding: utf-8 -*-
"""
BACKUP FILE - 2025-09-18 Before Intelligent Pregame Implementation
Original main.py with current pregame logic
"""

# This is a complete backup of the current main.py before implementing
# the intelligent pregame selection system.
# Restored from: /mnt/c/Users/yfuku/Desktop/betvalue-finder/app/main.py

# [BACKUP] Original get_pregame_games_by_sport function:
def get_pregame_games_by_sport_ORIGINAL(game_manager, sport: str):
    """競技別プリゲーム試合取得 - ORIGINAL VERSION"""
    now = datetime.now()  # 日本時間基準
    print(f"🔍 DEBUG Step3: get_pregame_games_by_sport called with sport: {sport}")
    print(f"🔍 DEBUG Step3: Current time: {now}")

    if sport.lower() == "npb":
        # NPB: 今日のプリゲーム
        target_date = now
        buffer_minutes = 30
    elif sport.lower() == "mlb":
        # MLB: 今日と明日の両方を検索（アメリカ時差対応）
        target_date = now  # 今日の試合も含める
        buffer_minutes = 30
        print(f"🔍 DEBUG Step3: MLB date calculation (FIXED)")
        print(f"   Current time (JST): {now}")
        print(f"   Target date: {target_date}")
        print(f"   Searching games for: {target_date.strftime('%Y-%m-%d')}")
    elif sport.lower() == "soccer":
        # Soccer: 日本時間基準での日付調整（早朝4:00までは前日扱い）
        if now.hour < 4:
            # 早朝（0:00-3:59）は前日の試合として扱う（例: 9/18 4:00am = 9/17 28:00）
            target_date = now.date() - timedelta(days=1)
            target_date = datetime.combine(target_date, datetime.min.time())
        else:
            # 4:00以降は当日の試合として扱う
            target_date = now
        buffer_minutes = 60
    else:
        # その他: 今日のプリゲーム
        target_date = now
        buffer_minutes = 30

    try:
        # リアルタイムAPI + プリゲームフィルタ
        if hasattr(game_manager, 'fetch_pregame_games'):
            return game_manager.fetch_pregame_games(target_date, buffer_minutes=buffer_minutes)
        else:
            # フォールバック: 通常のfetch_gamesを使用
            all_games = game_manager.fetch_games(target_date)
            from game_manager.pregame_filter import PregameFilter
            return PregameFilter.filter_pregame_games(all_games or [], buffer_minutes)
    except Exception as e:
        logging.warning(f"Failed to fetch pregame games for {sport}: {e}")
        # 最終フォールバック: キャッシュから取得してフィルタ
        try:
            cached_games = game_manager.load_latest_cache() or []
            from game_manager.pregame_filter import PregameFilter
            return PregameFilter.filter_pregame_games(cached_games, buffer_minutes)
        except Exception as cache_error:
            logging.warning(f"Cache fallback also failed: {cache_error}")
            return []  # 空リストを返す

# BACKUP TIMESTAMP: 2025-09-18 Before Intelligent System Implementation
# REASON: Preserving original pregame logic before major refactoring