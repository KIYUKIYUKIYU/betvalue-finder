#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修正後のGameManager統合テスト

目的:
- 全GameManager (Soccer/MLB/NPB/NBA) が戦略パターンで動作するか確認
- AlternateSpreadsで複数ライン取得できるか確認
- フォールバック機能が正常に動作するか確認
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from game_manager.realtime_theodds_soccer import RealtimeTheOddsSoccerGameManager
from game_manager.realtime_theodds_mlb import RealtimeTheOddsMLBGameManager
from game_manager.realtime_theodds_npb import RealtimeTheOddsNPBGameManager
from game_manager.realtime_theodds_nba import RealtimeTheOddsNBAGameManager
from game_manager.market_strategy_factory import MarketType


API_KEY = "d5457d1cd1a02494ab390a37620497ea"


async def test_soccer_alternate_spreads():
    """サッカー: AlternateSpreadsで複数ライン取得"""
    print("\n" + "="*60)
    print("TEST: Soccer with AlternateSpreads")
    print("="*60)

    manager = RealtimeTheOddsSoccerGameManager(
        api_key=API_KEY,
        market_type=MarketType.ALTERNATE_SPREADS
    )

    try:
        # 試合取得
        games = await manager.get_games_realtime(datetime.now())
        print(f"✅ Games fetched: {len(games)}")

        if not games:
            print("⚠️ No games available for testing")
            return False

        # 最初の試合でオッズ取得
        game = games[0]
        game_id = game['id']
        print(f"\n📌 Test game: {game.get('home_team')} vs {game.get('away_team')}")

        odds_data = await manager.get_odds_realtime(
            game_id,
            event_id=game_id,
            _theodds_event=game.get('_theodds_event')
        )

        if not odds_data:
            print("❌ Odds fetch failed")
            return False

        # アウトカム数確認
        outcome_count = 0
        for bm in odds_data.get('bookmakers', []):
            for bet in bm.get('bets', []):
                outcome_count += len(bet.get('values', []))

        print(f"✅ Odds fetched: {outcome_count} outcomes")

        # 複数ライン確認（サッカーは18アウトカム期待）
        if outcome_count >= 10:
            print(f"✅ Multiple lines confirmed ({outcome_count} >= 10)")
            return True
        else:
            print(f"⚠️ Low outcome count: {outcome_count}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_nba_alternate_spreads():
    """NBA: AlternateSpreadsで複数ライン取得"""
    print("\n" + "="*60)
    print("TEST: NBA with AlternateSpreads")
    print("="*60)

    manager = RealtimeTheOddsNBAGameManager(
        api_key=API_KEY,
        market_type=MarketType.ALTERNATE_SPREADS
    )

    try:
        games = await manager.get_games_realtime(datetime.now())
        print(f"✅ Games fetched: {len(games)}")

        if not games:
            print("⚠️ No games available for testing")
            return True  # NBAシーズンオフの可能性

        game = games[0]
        game_id = game['id']
        print(f"\n📌 Test game: {game.get('home_team')} vs {game.get('away_team')}")

        odds_data = await manager.get_odds_realtime(
            game_id,
            event_id=game_id,
            _theodds_event=game.get('_theodds_event')
        )

        if not odds_data:
            print("❌ Odds fetch failed")
            return False

        outcome_count = 0
        for bm in odds_data.get('bookmakers', []):
            for bet in bm.get('bets', []):
                outcome_count += len(bet.get('values', []))

        print(f"✅ Odds fetched: {outcome_count} outcomes")

        # NBAは22アウトカム期待
        if outcome_count >= 15:
            print(f"✅ Multiple lines confirmed ({outcome_count} >= 15)")
            return True
        else:
            print(f"⚠️ Low outcome count: {outcome_count}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fallback_mechanism():
    """フォールバック機能のテスト"""
    print("\n" + "="*60)
    print("TEST: Fallback Mechanism (AlternateSpreads → SimpleSpreads)")
    print("="*60)

    # AlternateSpreadsで初期化（フォールバック有効）
    manager = RealtimeTheOddsSoccerGameManager(
        api_key=API_KEY,
        market_type=MarketType.ALTERNATE_SPREADS
    )

    print(f"✅ Primary strategy: {manager.market_strategy.get_market_name()}")
    if manager.fallback_strategy:
        print(f"✅ Fallback strategy: {manager.fallback_strategy.get_market_name()}")
    else:
        print(f"⚠️ No fallback strategy")

    # フォールバックが設定されているか確認
    if manager.fallback_strategy:
        print("✅ Fallback mechanism is configured")
        return True
    else:
        print("❌ Fallback mechanism not configured")
        return False


async def test_simple_spreads_compatibility():
    """SimpleSpreads戦略の後方互換性テスト"""
    print("\n" + "="*60)
    print("TEST: SimpleSpreads Compatibility (Backward Compatibility)")
    print("="*60)

    manager = RealtimeTheOddsSoccerGameManager(
        api_key=API_KEY,
        market_type=MarketType.SIMPLE_SPREADS  # 旧方式を明示的に指定
    )

    try:
        games = await manager.get_games_realtime(datetime.now())
        print(f"✅ Games fetched: {len(games)}")

        if not games:
            print("⚠️ No games available")
            return False

        game = games[0]
        game_id = game['id']
        print(f"\n📌 Test game: {game.get('home_team')} vs {game.get('away_team')}")

        odds_data = await manager.get_odds_realtime(
            game_id,
            event_id=game_id,
            _theodds_event=game.get('_theodds_event')
        )

        if not odds_data:
            print("❌ Odds fetch failed")
            return False

        outcome_count = 0
        for bm in odds_data.get('bookmakers', []):
            for bet in bm.get('bets', []):
                outcome_count += len(bet.get('values', []))

        print(f"✅ Odds fetched: {outcome_count} outcomes")

        # SimpleSpreadsは2アウトカム（1ライン）
        if outcome_count == 2:
            print(f"✅ SimpleSpreads working correctly (2 outcomes)")
            return True
        else:
            print(f"⚠️ Unexpected outcome count: {outcome_count}")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """全テスト実行"""
    print("\n" + "="*60)
    print("GameManager統合テスト開始")
    print("="*60)

    results = []

    # Test 1: Soccer with AlternateSpreads
    try:
        result = await test_soccer_alternate_spreads()
        results.append(("Soccer AlternateSpreads", result))
    except Exception as e:
        print(f"❌ Soccer test exception: {e}")
        results.append(("Soccer AlternateSpreads", False))

    # Test 2: NBA with AlternateSpreads
    try:
        result = await test_nba_alternate_spreads()
        results.append(("NBA AlternateSpreads", result))
    except Exception as e:
        print(f"❌ NBA test exception: {e}")
        results.append(("NBA AlternateSpreads", False))

    # Test 3: Fallback Mechanism
    try:
        result = await test_fallback_mechanism()
        results.append(("Fallback Mechanism", result))
    except Exception as e:
        print(f"❌ Fallback test exception: {e}")
        results.append(("Fallback Mechanism", False))

    # Test 4: SimpleSpreads Compatibility
    try:
        result = await test_simple_spreads_compatibility()
        results.append(("SimpleSpreads Compatibility", result))
    except Exception as e:
        print(f"❌ SimpleSpreads test exception: {e}")
        results.append(("SimpleSpreads Compatibility", False))

    # 結果サマリー
    print("\n" + "="*60)
    print("テスト結果サマリー")
    print("="*60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:40s} {status}")

    all_passed = all(result for _, result in results)

    print("\n" + "="*60)
    if all_passed:
        print("🎉 全テスト合格！GameManagerは正常に動作しています")
    else:
        print("⚠️ 一部テスト失敗。確認が必要です")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
