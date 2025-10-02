# -*- coding: utf-8 -*-
"""
SmartGameSelector (新規実装: 2025-09-14)
連戦問題解決のための賢いゲーム選択システム
閾値なし、優先順位ベースで最適な試合を自動選択

実装背景:
- パドレス vs ロッキーズ問題: 複数の同名チーム試合から正しい試合を自動選択
- 従来は手動選択が必要だったが、SmartGameSelectorで完全自動化
- チーム名マッチング + 時刻判定 + ステータス評価の3軸スコアリング
"""

from datetime import datetime
from typing import Dict, List, Optional
import logging
from converter.team_names import normalize_team_name

logger = logging.getLogger(__name__)


class SmartGameSelector:
    """賢いゲーム選択クラス - 連戦問題を解決"""
    
    @classmethod
    def select_best_game(cls, team_names: List[str], candidate_games: List[Dict]) -> Optional[Dict]:
        """
        複数候補から最適なゲームを自動選択
        ユーザーには選択理由は見せない
        """
        if not candidate_games:
            return None
            
        if len(candidate_games) == 1:
            return candidate_games[0]
            
        # 複数候補をスコアリング
        scored_games = []
        
        for game in candidate_games:
            score = cls._calculate_game_score(game, team_names)
            if score > 0:  # 有効なゲームのみ
                scored_games.append({
                    "game": game,
                    "score": score
                })
                
        if not scored_games:
            return None
            
        # 最高スコアのゲームを選択
        best_match = max(scored_games, key=lambda x: x["score"])
        
        # ログ出力（デバッグ用、ユーザーには見えない）
        if len(scored_games) > 1:
            team_str = " vs ".join(team_names)
            logger.info(f"Multiple games found for {team_str}, selected best match automatically")
            
        return best_match["game"]
    
    @classmethod
    def _calculate_game_score(cls, game: Dict, team_names: List[str] = None) -> float:
        """
        ゲームのスコア計算（優先順位ベース）
        高いスコア = より適切な選択
        """
        score = 0.0
        
        try:
            # 0. チーム名マッチング評価（最優先）
            if team_names and len(team_names) >= 2:
                # APIから来る英語チーム名
                home_team = game.get("home", "")
                away_team = game.get("away", "")
                
                # パーサーから来る日本語チーム名を英語に正規化
                target_team1_normalized = normalize_team_name(team_names[0])
                target_team2_normalized = normalize_team_name(team_names[1])
                
                match_score = 0
                
                # 正規化後の完全一致（最高優先）
                if target_team1_normalized and target_team2_normalized:
                    if ((home_team == target_team1_normalized and away_team == target_team2_normalized) or
                        (home_team == target_team2_normalized and away_team == target_team1_normalized)):
                        match_score = 1000
                
                # 正規化に失敗した場合の代替マッチング
                if match_score == 0:
                    home_team_lower = home_team.lower()
                    away_team_lower = away_team.lower()
                    target_team1_lower = team_names[0].lower()
                    target_team2_lower = team_names[1].lower()
                    
                    # 部分一致
                    if ((target_team1_lower in home_team_lower and target_team2_lower in away_team_lower) or
                        (target_team2_lower in home_team_lower and target_team1_lower in away_team_lower)):
                        match_score = 500
                    # 一方のチーム名のみ一致
                    elif (target_team1_lower in home_team_lower or target_team1_lower in away_team_lower or
                          target_team2_lower in home_team_lower or target_team2_lower in away_team_lower):
                        match_score = 100
                
                if match_score == 0:
                    # チーム名が全く一致しない場合は除外
                    return -2000.0
                    
                score += match_score
            
            # 1. ステータス評価（最重要）
            status = (game.get("status") or "").lower()
            if "not started" in status or "scheduled" in status:
                score += 100.0  # プリゲーム最優先
            elif "finished" in status or "final" in status:
                score = -1000.0  # 終了済みは除外
                return score
            elif any(word in status for word in ["live", "progress", "half"]):
                score = -500.0  # ライブ中も除外
                return score
                
            # 2. 時刻の妥当性評価
            datetime_str = game.get("datetime", "")
            if datetime_str:
                try:
                    game_dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    now = datetime.now(game_dt.tzinfo) if game_dt.tzinfo else datetime.now()
                    hours_diff = (game_dt - now).total_seconds() / 3600
                    
                    if hours_diff < -1:
                        # 1時間以上前は過去の試合
                        score = -1000.0
                        return score
                    elif hours_diff >= 0:
                        # 未来の試合は時間が近いほど高スコア
                        # 最大 50ポイント、時間が経つほど減少
                        time_score = max(0, 50 - abs(hours_diff - 12) * 2)
                        score += time_score
                        
                except Exception:
                    score += 10.0  # 日時パース失敗は低スコア
                    
            # 3. データ完整性評価
            if game.get("home") and game.get("away"):
                score += 20.0
            if game.get("id"):
                score += 10.0
                
            # 4. 試合情報の詳細度
            if game.get("league"):
                score += 5.0
            if game.get("raw"):  # 詳細データあり
                score += 5.0
                
        except Exception as e:
            logger.warning(f"Error calculating game score: {e}")
            score = 1.0  # エラー時は最低スコア
            
        return score
    
    @classmethod
    def filter_valid_pregame_only(cls, games: List[Dict]) -> List[Dict]:
        """
        有効なプリゲーム試合のみをフィルタ
        PregameFilterと組み合わせて使用
        """
        valid_games = []
        
        for game in games:
            score = cls._calculate_game_score(game, None)
            if score > 0:  # 正のスコアのみ有効
                valid_games.append(game)
                
        return valid_games