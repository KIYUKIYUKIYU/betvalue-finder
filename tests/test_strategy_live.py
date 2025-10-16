#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基盤コードの実APIテスト

目的:
- AlternateSpreadsStrategyの動作確認
- SimpleSpreadsStrategyの動作確認
- フォーマット互換性の検証
"""

import asyncio
import aiohttp
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_manager.alternate_spreads_strategy import AlternateSpreadsStrategy
from game_manager.simple_spreads_strategy import SimpleSpreadsStrategy
from game_manager.market_strategy_factory import MarketStrategyFactory, MarketType


API_KEY = "d5457d1cd1a02494ab390a37620497ea"


async def test_alternate_spreads_soccer():
    """サッカーでalternate_spreadsをテスト"""
    print("\n" + "="*60)
    print("TEST 1: AlternateSpreadsStrategy (Soccer)")
    print("="*60)

    # まずイベントIDを取得
    async with aiohttp.ClientSession() as session:
        url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "spreads",
            "bookmakers": "pinnacle",
            "oddsFormat": "decimal"
        }

        async with session.get(url, params=params) as response:
            if response.status != 200:
                print(f"❌ Failed to get events: {response.status}")
                return False

            games = await response.json()
            if not games:
                print("❌ No games available")
                return False

            game = games[0]
            event_id = game['id']
            sport_key = game['sport_key']
            home_team = game['home_team']
            away_team = game['away_team']

            print(f"📌 Test game: {home_team} vs {away_team}")
            print(f"   Event ID: {event_id}")
            print(f"   Sport key: {sport_key}")

    # AlternateSpreadsStrategyでオッズ取得
    strategy = AlternateSpreadsStrategy()

    async with aiohttp.ClientSession() as session:
        odds_data = await strategy.fetch_odds(
            session=session,
            api_key=API_KEY,
            sport_key=sport_key,
            event_id=event_id,
            regions="us",
            bookmakers="pinnacle"
        )

        if not odds_data:
            print("❌ fetch_odds returned None")
            return False

        print(f"\n✅ fetch_odds successful")
        print(f"   fixture_id: {odds_data.get('fixture_id')}")
        print(f"   bookmakers: {len(odds_data.get('bookmakers', []))}")

        # 詳細確認
        bookmakers = odds_data.get('bookmakers', [])
        if not bookmakers:
            print("❌ No bookmakers in odds_data")
            return False

        for bm in bookmakers:
            print(f"\n   Bookmaker: {bm.get('name')}")
            for bet in bm.get('bets', []):
                values = bet.get('values', [])
                print(f"      Bet: {bet.get('name')}")
                print(f"      Outcomes: {len(values)}")

                # サンプル表示（最初の5つ）
                print(f"\n      Sample outcomes:")
                for val in values[:5]:
                    print(f"         {val.get('value'):20s} → {val.get('odd')}")

                if len(values) > 5:
                    print(f"         ... ({len(values) - 5} more)")

                # 検証
                if len(values) < 10:
                    print(f"      ⚠️ Unexpected low outcome count: {len(values)}")
                    return False

        print("\n✅ AlternateSpreadsStrategy test PASSED")
        return True


async def test_simple_spreads_soccer():
    """サッカーでsimple_spreadsをテスト"""
    print("\n" + "="*60)
    print("TEST 2: SimpleSpreadsStrategy (Soccer)")
    print("="*60)

    # イベントIDを取得
    async with aiohttp.ClientSession() as session:
        url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "spreads",
            "bookmakers": "pinnacle",
            "oddsFormat": "decimal"
        }

        async with session.get(url, params=params) as response:
            games = await response.json()
            game = games[0]
            event_id = game['id']
            sport_key = game['sport_key']
            home_team = game['home_team']
            away_team = game['away_team']

            print(f"📌 Test game: {home_team} vs {away_team}")
            print(f"   Event ID: {event_id}")

    # SimpleSpreadsStrategyでオッズ取得
    strategy = SimpleSpreadsStrategy()

    async with aiohttp.ClientSession() as session:
        odds_data = await strategy.fetch_odds(
            session=session,
            api_key=API_KEY,
            sport_key=sport_key,
            event_id=event_id,
            regions="us",
            bookmakers="pinnacle"
        )

        if not odds_data:
            print("❌ fetch_odds returned None")
            return False

        print(f"\n✅ fetch_odds successful")

        # 詳細確認
        bookmakers = odds_data.get('bookmakers', [])
        for bm in bookmakers:
            print(f"\n   Bookmaker: {bm.get('name')}")
            for bet in bm.get('bets', []):
                values = bet.get('values', [])
                print(f"      Bet: {bet.get('name')}")
                print(f"      Outcomes: {len(values)}")

                for val in values:
                    print(f"         {val.get('value'):20s} → {val.get('odd')}")

                # 検証: 1ラインなので2アウトカム
                if len(values) != 2:
                    print(f"      ⚠️ Expected 2 outcomes, got {len(values)}")
                    return False

        print("\n✅ SimpleSpreadsStrategy test PASSED")
        return True


async def test_format_compatibility():
    """両戦略のフォーマット互換性をテスト"""
    print("\n" + "="*60)
    print("TEST 3: Format Compatibility")
    print("="*60)

    # 両戦略で同じ試合のオッズを取得
    async with aiohttp.ClientSession() as session:
        # イベント情報取得
        url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
        params = {
            "apiKey": API_KEY,
            "regions": "us",
            "markets": "spreads",
            "bookmakers": "pinnacle",
            "oddsFormat": "decimal"
        }

        async with session.get(url, params=params) as response:
            games = await response.json()
            game = games[0]
            event_id = game['id']
            sport_key = game['sport_key']

            print(f"📌 Test game: {game['home_team']} vs {game['away_team']}")

    # 両戦略でオッズ取得
    alternate_strategy = AlternateSpreadsStrategy()
    simple_strategy = SimpleSpreadsStrategy()

    async with aiohttp.ClientSession() as session:
        alternate_odds = await alternate_strategy.fetch_odds(
            session, API_KEY, sport_key, event_id
        )

        simple_odds = await simple_strategy.fetch_odds(
            session, API_KEY, sport_key, event_id
        )

    # フォーマット検証
    def validate_format(odds_data, strategy_name):
        print(f"\n   Validating {strategy_name} format...")

        if not isinstance(odds_data, dict):
            print(f"      ❌ Not a dict: {type(odds_data)}")
            return False

        if 'fixture_id' not in odds_data:
            print(f"      ❌ Missing 'fixture_id'")
            return False

        if 'bookmakers' not in odds_data:
            print(f"      ❌ Missing 'bookmakers'")
            return False

        bookmakers = odds_data['bookmakers']
        if not isinstance(bookmakers, list):
            print(f"      ❌ 'bookmakers' not a list")
            return False

        for bm in bookmakers:
            if 'id' not in bm or 'name' not in bm or 'bets' not in bm:
                print(f"      ❌ Invalid bookmaker structure")
                return False

            for bet in bm['bets']:
                if 'id' not in bet or 'name' not in bet or 'values' not in bet:
                    print(f"      ❌ Invalid bet structure")
                    return False

                for val in bet['values']:
                    if 'value' not in val or 'odd' not in val:
                        print(f"      ❌ Invalid value structure")
                        return False

        print(f"      ✅ Format valid")
        return True

    if not validate_format(alternate_odds, "AlternateSpreadsStrategy"):
        return False

    if not validate_format(simple_odds, "SimpleSpreadsStrategy"):
        return False

    print("\n✅ Format compatibility test PASSED")
    print("   Both strategies return identical data structures")
    return True


async def main():
    """全テスト実行"""
    print("\n" + "="*60)
    print("基盤コード実APIテスト開始")
    print("="*60)

    results = []

    # Test 1: AlternateSpreadsStrategy (Soccer)
    try:
        result = await test_alternate_spreads_soccer()
        results.append(("AlternateSpreads (Soccer)", result))
    except Exception as e:
        print(f"❌ Test 1 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("AlternateSpreads (Soccer)", False))

    # Test 2: SimpleSpreadsStrategy (Soccer)
    try:
        result = await test_simple_spreads_soccer()
        results.append(("SimpleSpreads (Soccer)", result))
    except Exception as e:
        print(f"❌ Test 2 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("SimpleSpreads (Soccer)", False))

    # Test 3: Format Compatibility (NBA)
    try:
        result = await test_format_compatibility()
        results.append(("Format Compatibility", result))
    except Exception as e:
        print(f"❌ Test 3 failed with exception: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Format Compatibility", False))

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
        print("🎉 全テスト合格！基盤コードは正常に動作しています")
    else:
        print("⚠️ 一部テスト失敗。修正が必要です")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
