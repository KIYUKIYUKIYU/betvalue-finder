# alternate_spreads 実装設計書

**作成日**: 2025-10-16
**目的**: The Odds APIから複数ハンディキャップラインを取得し、線形補間を不要にする
**原則**: 場当たり的修正禁止、将来の拡張性確保、統合テスト実行、完全動作保証

---

## 1. 現状分析

### 1.1 問題点

**現在の実装**:
- エンドポイント: `/v4/sports/{sport}/odds`
- マーケット: `spreads`
- **結果**: 各試合1ラインのみ取得（例: -0.5 / +0.5）

**問題**:
- ユーザーが要求したライン（例: -0.2）が存在しない
- 線形補間の実装はあるが、データ不足で機能しない
- Stage 4で補間処理が実行されていない

### 1.2 発見された解決策

**The Odds APIの機能**:
- エンドポイント: `/v4/sports/{sport}/events/{eventId}/odds`
- マーケット: `alternate_spreads`
- **結果**: 複数ライン取得可能
  - NBA: 22アウトカム（-10.0 ~ +10.0、0.5刻み）
  - サッカー: 18アウトカム（-1.5 ~ +1.5、0.25刻み）

---

## 2. 設計方針

### 2.1 アーキテクチャ原則

1. **後方互換性**: 既存の`spreads`マーケットも引き続きサポート
2. **段階的移行**: フィーチャーフラグで新旧切り替え可能
3. **拡張性**: 将来的な新マーケット追加に対応
4. **テスタビリティ**: 各層でユニットテスト可能
5. **パフォーマンス**: APIリクエスト数を最小化

### 2.2 設計パターン

**Strategy Pattern**: マーケット取得戦略を抽象化

```
MarketStrategy (抽象)
├── SimpleSpreadsStrategy (現行: spreads, 1ライン)
└── AlternateSpreadsStrategy (新規: alternate_spreads, 複数ライン)
```

**Factory Pattern**: 戦略の選択を自動化

```
MarketStrategyFactory
└── create_strategy(sport, config) -> MarketStrategy
```

---

## 3. 実装設計

### 3.1 新規ファイル構成

```
game_manager/
├── market_strategy.py          # NEW: 戦略インターフェース
├── simple_spreads_strategy.py  # NEW: 現行方式（spreads）
├── alternate_spreads_strategy.py # NEW: 新方式（alternate_spreads）
├── market_strategy_factory.py  # NEW: ファクトリー
└── realtime_theodds_*.py       # MODIFY: 戦略を使用

converter/
└── odds_processor.py           # VERIFY: 互換性確認のみ

tests/
├── test_market_strategy.py     # NEW: ユニットテスト
├── test_alternate_spreads.py   # NEW: 統合テスト
└── test_e2e_pipeline.py        # NEW: E2Eテスト
```

### 3.2 クラス設計

#### 3.2.1 MarketStrategy (抽象基底クラス)

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class MarketStrategy(ABC):
    """オッズマーケット取得戦略の抽象基底クラス"""

    @abstractmethod
    async def fetch_odds(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        sport_key: str,
        event_id: str,
        **kwargs
    ) -> Optional[Dict]:
        """
        オッズデータを取得

        Returns:
            {
                'fixture_id': str,
                'bookmakers': [{
                    'id': int,
                    'name': str,
                    'bets': [{
                        'id': int,
                        'name': str,
                        'values': [{
                            'value': str,  # "Home -0.5"
                            'odd': str     # "1.95"
                        }]
                    }]
                }]
            }
        """
        pass

    @abstractmethod
    def get_market_name(self) -> str:
        """マーケット名を返す"""
        pass

    @abstractmethod
    def supports_multiple_lines(self) -> bool:
        """複数ライン対応か"""
        pass
```

#### 3.2.2 SimpleSpreadsStrategy (現行方式)

```python
class SimpleSpreadsStrategy(MarketStrategy):
    """spreadsマーケット戦略（現行: 1ライン）"""

    async def fetch_odds(self, session, api_key, sport_key, event_id, **kwargs):
        # 現在の実装と同じ
        # /v4/sports/{sport_key}/odds?eventIds={event_id}
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
        params = {
            "apiKey": api_key,
            "regions": kwargs.get("regions", "us"),
            "markets": "spreads",
            "bookmakers": kwargs.get("bookmakers", "pinnacle"),
            "oddsFormat": "decimal",
            "eventIds": event_id
        }

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    return self._format_odds_data(data[0])
        return None

    def get_market_name(self) -> str:
        return "spreads"

    def supports_multiple_lines(self) -> bool:
        return False
```

#### 3.2.3 AlternateSpreadsStrategy (新方式)

```python
class AlternateSpreadsStrategy(MarketStrategy):
    """alternate_spreadsマーケット戦略（新規: 複数ライン）"""

    async def fetch_odds(self, session, api_key, sport_key, event_id, **kwargs):
        # NEW: イベント単位エンドポイント
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds"
        params = {
            "apiKey": api_key,
            "regions": kwargs.get("regions", "us"),
            "markets": "alternate_spreads",
            "bookmakers": kwargs.get("bookmakers", "pinnacle"),
            "oddsFormat": "decimal"
        }

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return self._format_odds_data(data)
        return None

    def get_market_name(self) -> str:
        return "alternate_spreads"

    def supports_multiple_lines(self) -> bool:
        return True

    def _format_odds_data(self, event: Dict) -> Dict:
        """alternate_spreadsデータをAPI-Sports互換形式に変換"""
        # SimpleSpreadsStrategyと同じフォーマット処理
        # 複数のハンディキャップラインが含まれる点が異なる
        pass
```

#### 3.2.4 MarketStrategyFactory

```python
from typing import Optional
from enum import Enum

class MarketType(Enum):
    SIMPLE_SPREADS = "spreads"
    ALTERNATE_SPREADS = "alternate_spreads"

class MarketStrategyFactory:
    """マーケット戦略のファクトリー"""

    @staticmethod
    def create_strategy(
        market_type: MarketType,
        logger: Optional[logging.Logger] = None
    ) -> MarketStrategy:
        """戦略インスタンスを生成"""
        if market_type == MarketType.ALTERNATE_SPREADS:
            return AlternateSpreadsStrategy(logger)
        elif market_type == MarketType.SIMPLE_SPREADS:
            return SimpleSpreadsStrategy(logger)
        else:
            raise ValueError(f"Unknown market type: {market_type}")
```

### 3.3 GameManager修正設計

#### realtime_theodds_soccer.py の修正点

```python
class RealtimeTheOddsSoccerGameManager(RealtimeGameManager):
    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, cache_dir="data/theodds_soccer", **kwargs)

        # NEW: マーケット戦略を設定
        market_type = kwargs.get("market_type", MarketType.ALTERNATE_SPREADS)
        self.market_strategy = MarketStrategyFactory.create_strategy(
            market_type, self.logger
        )

        # 既存のコード...

    async def _fetch_odds_async(self, game_id: str, **kwargs) -> Optional[Dict]:
        """
        オッズを取得（戦略パターン使用）
        """
        try:
            event_id = kwargs.get("event_id", game_id)
            theodds_event = kwargs.get("_theodds_event")

            if not theodds_event:
                theodds_event = self._events_cache.get(event_id)

            if not theodds_event:
                self.logger.warning(f"⚠️ No event metadata for {event_id}")
                return None

            sport_key = theodds_event.get("sport_key")

            # NEW: 戦略を使ってオッズ取得
            await self._ensure_session()
            odds_data = await self.market_strategy.fetch_odds(
                session=self._session,
                api_key=self.api_key,
                sport_key=sport_key,
                event_id=event_id,
                regions="us",
                bookmakers="pinnacle"
            )

            if odds_data:
                self.logger.info(
                    f"✅ {self.market_strategy.get_market_name()} odds retrieved: "
                    f"{self._count_odds_lines(odds_data)} lines"
                )

            return odds_data

        except Exception as e:
            self.logger.warning(f"⚠️ Odds fetch failed for {game_id}: {e}")
            return None

    def _count_odds_lines(self, odds_data: Dict) -> int:
        """オッズライン数をカウント（デバッグ用）"""
        count = 0
        for bookmaker in odds_data.get('bookmakers', []):
            for bet in bookmaker.get('bets', []):
                count += len(bet.get('values', []))
        return count
```

---

## 4. 互換性保証

### 4.1 データフォーマット互換性

**重要**: 戦略パターンはどちらも同じフォーマットを返す

```python
# SimpleSpreadsStrategy 出力
{
    'fixture_id': 'xxx',
    'bookmakers': [{
        'id': 4,
        'name': 'Pinnacle',
        'bets': [{
            'id': 4,
            'name': 'Asian Handicap',
            'values': [
                {'value': 'Home -0.5', 'odd': '1.95'},
                {'value': 'Away +0.5', 'odd': '1.95'}
            ]  # ← 2アウトカムのみ
        }]
    }]
}

# AlternateSpreadsStrategy 出力
{
    'fixture_id': 'xxx',
    'bookmakers': [{
        'id': 4,
        'name': 'Pinnacle',
        'bets': [{
            'id': 4,
            'name': 'Asian Handicap',
            'values': [
                {'value': 'Home -1.5', 'odd': '2.83'},
                {'value': 'Away +1.5', 'odd': '1.46'},
                {'value': 'Home -1.0', 'odd': '2.50'},
                {'value': 'Away +1.0', 'odd': '1.60'},
                ...  # ← 18～22アウトカム
            ]
        }]
    }]
}
```

**下流への影響**:
- `converter/odds_processor.py`: **変更不要**（既に複数ライン対応済み）
- `converter/ev_evaluator.py`: **変更不要**（補間ロジックはそのまま）
- `app/pipeline_orchestrator.py`: **変更不要**（データ構造は同じ）

### 4.2 後方互換性テスト

```python
# tests/test_compatibility.py
def test_simple_spreads_format():
    """SimpleSpreadsStrategyが既存形式を返すことを確認"""
    strategy = SimpleSpreadsStrategy()
    # ... mock data
    assert format_matches_expected(result)

def test_alternate_spreads_format():
    """AlternateSpreadsStrategyが同じ形式を返すことを確認"""
    strategy = AlternateSpreadsStrategy()
    # ... mock data
    assert format_matches_expected(result)

def test_odds_processor_handles_both():
    """OddsProcessorが両戦略の出力を処理できることを確認"""
    processor = OddsProcessor()

    # SimpleSpreads出力
    simple_result = processor.extract_team_specific_handicap_odds(simple_data)
    assert len(simple_result['home_lines']) >= 1

    # AlternateSpreads出力
    alternate_result = processor.extract_team_specific_handicap_odds(alternate_data)
    assert len(alternate_result['home_lines']) >= 9  # 複数ライン
```

---

## 5. 設定管理

### 5.1 環境変数

```bash
# .env
THEODDS_MARKET_TYPE=alternate_spreads  # または spreads
THEODDS_ENABLE_FALLBACK=true           # spreads失敗時にalternate_spreadsへフォールバック
```

### 5.2 pipeline_orchestrator.py での設定

```python
class GameManagerFactory:
    def get_manager(self, sport: str) -> GameManager:
        sport_lower = sport.lower()

        # マーケット設定を読み込み
        market_type_str = os.getenv("THEODDS_MARKET_TYPE", "alternate_spreads")
        market_type = MarketType(market_type_str)

        if sport_lower in ['soccer', 'football']:
            if self.theodds_api_key:
                self.logger.info(f"🌟 Using The Odds API ({market_type.value}) for {sport}")
                return RealtimeTheOddsSoccerGameManager(
                    api_key=self.theodds_api_key,
                    market_type=market_type
                )
        # ... 他のスポーツも同様
```

---

## 6. テスト計画

### 6.1 ユニットテスト

**tests/test_market_strategy.py**:
- [ ] SimpleSpreadsStrategyが正しいURLを生成
- [ ] AlternateSpreadsStrategyが正しいURLを生成
- [ ] 両戦略が同じフォーマットを返す
- [ ] Factoryが正しい戦略を返す

### 6.2 統合テスト

**tests/test_alternate_spreads.py**:
- [ ] 実際のThe Odds APIから複数ライン取得
- [ ] サッカー: 18アウトカム確認
- [ ] NBA: 22アウトカム確認
- [ ] MLB/NPB: 複数ライン確認
- [ ] フォーマット変換が正しい

### 6.3 E2Eテスト

**tests/test_e2e_pipeline.py**:
- [ ] Stage 1-6 が正常に動作
- [ ] ユーザー要求ライン（-0.2など）がマッチング
- [ ] EV計算が成功
- [ ] 日本語翻訳が正しい
- [ ] 全スポーツで実行

---

## 7. 実装手順

### Phase 1: 基盤構築（30分）
1. ✅ 設計書作成
2. [ ] market_strategy.py 作成
3. [ ] simple_spreads_strategy.py 作成
4. [ ] alternate_spreads_strategy.py 作成
5. [ ] market_strategy_factory.py 作成

### Phase 2: GameManager修正（60分）
6. [ ] realtime_theodds_soccer.py 修正
7. [ ] realtime_theodds_mlb.py 修正
8. [ ] realtime_theodds_npb.py 修正
9. [ ] realtime_theodds_nba.py 修正

### Phase 3: テスト（60分）
10. [ ] ユニットテスト作成・実行
11. [ ] 統合テスト作成・実行
12. [ ] E2Eテスト作成・実行

### Phase 4: 検証（30分）
13. [ ] 全スポーツでパイプライン実行
14. [ ] パフォーマンス測定
15. [ ] ドキュメント更新

**合計所要時間**: 約3時間

---

## 8. リスク管理

### 8.1 潜在的リスク

| リスク | 影響 | 対策 |
|-------|------|------|
| alternate_spreads APIエラー | 高 | SimpleSpreadsへ自動フォールバック |
| APIリクエスト数増加 | 中 | キャッシング強化 |
| 下流処理の互換性問題 | 高 | 事前に互換性テスト実施 |
| スポーツ別の差異 | 中 | スポーツごとに個別テスト |

### 8.2 ロールバック計画

```python
# 環境変数で即座に切り替え可能
THEODDS_MARKET_TYPE=spreads  # ← 旧方式に戻す
```

---

## 9. 成功基準

### 9.1 機能要件
- [ ] 全スポーツで複数ライン取得成功
- [ ] サッカー: 9種類以上のライン
- [ ] NBA: 11種類以上のライン
- [ ] ユーザー要求ライン（-0.2など）がマッチング
- [ ] EV計算が成功

### 9.2 非機能要件
- [ ] 下流処理との完全互換性
- [ ] パフォーマンス劣化なし（±10%以内）
- [ ] 全テストケースが合格
- [ ] 後方互換性維持

---

## 10. まとめ

### 設計の特徴
1. **Strategy Pattern**: 戦略を切り替え可能
2. **Factory Pattern**: 自動選択
3. **後方互換性**: 既存コード変更最小限
4. **拡張性**: 新マーケット追加が容易
5. **テスタビリティ**: 各層で独立テスト可能

### 期待される効果
- ✅ 複数ハンディキャップライン取得
- ✅ 線形補間が不要に（データが十分）
- ✅ ユーザー要求ラインがマッチング
- ✅ EV計算の精度向上
- ✅ パイプラインの完全動作保証

---

**次のステップ**: Phase 1の実装開始
