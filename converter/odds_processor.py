# -*- coding: utf-8 -*-
from typing import Dict, List, Tuple, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)

class OddsProcessor:
    def extract_team_specific_handicap_odds(self, bookmakers: List[Dict[str, Any]]) -> Dict[str, Any]:
        home_lines, away_lines = [], []
        for bookmaker in bookmakers:
            for bet in bookmaker.get("bets", []):
                if "asian handicap" in str(bet.get("name", "")).lower():
                    for value in bet.get("values", []):
                        try:
                            value_str = value.get("value", "")
                            line_val = self._parse_handicap_from_string(value_str)
                            if line_val is not None:
                                line_data = {"handicap": line_val, "odds": float(value.get("odd"))}

                                # 全てのハンディキャップデータを取得（APIの全データを活用）
                                if "Home" in value_str:
                                    home_lines.append(line_data)
                                elif "Away" in value_str:
                                    away_lines.append(line_data)

                        except (ValueError, TypeError): continue
        return {"home_lines": sorted(home_lines, key=lambda x: x["handicap"]), "away_lines": sorted(away_lines, key=lambda x: x["handicap"])}

    def _parse_handicap_from_string(self, value_str: str) -> Optional[float]:
        match = re.search(r'[+-]?\d+\.?\d*', value_str)
        return float(match.group()) if match else None

    def convert_team_specific_to_legacy_format(self, team_specific_data: Dict[str, Any]) -> Dict[float, Tuple[float, float]]:
        home_lines = team_specific_data.get("home_lines", [])
        away_lines = team_specific_data.get("away_lines", [])

        # HomeとAwayの全ラインを辞書化
        home_lines_map = {line["handicap"]: line["odds"] for line in home_lines}
        away_lines_map = {line["handicap"]: line["odds"] for line in away_lines}

        legacy_data = {}

        # 全てのユニークなハンディキャップ値を取得
        all_handicaps = set()
        for line in home_lines:
            all_handicaps.add(abs(line["handicap"]))
        for line in away_lines:
            all_handicaps.add(abs(line["handicap"]))

        # 全てのユニークなハンディキャップ値（符号付き）を取得
        all_signed_handicaps = set()
        for line in home_lines:
            all_signed_handicaps.add(line["handicap"])
        for line in away_lines:
            all_signed_handicaps.add(line["handicap"])

        # 各ハンディキャップについてペアを作成（同じハンディキャップ値でペアリング）
        for handicap in all_signed_handicaps:
            home_odds = home_lines_map.get(handicap)
            away_odds = away_lines_map.get(handicap)

            # Home/Awayのどちらかでもオッズが存在する場合はペアを作成
            # 片方がNoneの場合は補完処理でカバー
            if home_odds is not None or away_odds is not None:
                legacy_data[handicap] = (home_odds, away_odds)

        return legacy_data