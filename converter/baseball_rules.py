# -*- coding: utf-8 -*-
"""
Baseball (MLB) Japanese-handicap EV utilities — turnover rakeback only.

- 日本式⇔ピナクル変換：同梱「## 1. 変換表（ピナクル → 日本式）.txt」に準拠（0.05刻み）。
- EV は丸勝ちオッズ O（既定 1.9）を基準に計算。
- レーキバックは turnover 方式のみ（勝敗に無関係に賭け金に対して r が返る）。
- レーキバック既定は 0%（=0.0）。ユーザー指定時のみ反映。0.5%刻み（0.005）に丸める。
"""

import os
from typing import Dict, Tuple, Optional, List


# -------------------------
# 変換表ローダ
# -------------------------
class ConversionTable:
    """
    変換表ファイル「## 1. 変換表（ピナクル → 日本式）.txt」を読み、
    ピナクル値 <-> 日本式ラベル の双方向辞書を提供する。
    想定フォーマット：
      - 1行あたり「pinnacle_value, jp_label」 または  タブ区切り/空白区切り
      - ヘッダ行や # 始まりは無視
    """
    def __init__(self, table_path: Optional[str] = None) -> None:
        if table_path is None:
            # converter/ から 1つ上のルートに置かれた変換表を想定
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
            table_path = os.path.join(root, "## 1. 変換表（ピナクル → 日本式）.txt")
        self.table_path = table_path
        self.value_to_label: Dict[float, str] = {}
        self.label_to_value: Dict[str, float] = {}
        self._load()

    @staticmethod
    def _split_flex(line: str) -> List[str]:
        """
        1行を柔軟に分割。まずカンマ、次にタブ、最後に空白で分ける。
        返り値は空要素を除去。
        """
        for sep in [",", "\t"]:
            if sep in line:
                parts = [p.strip() for p in line.split(sep)]
                return [p for p in parts if p]
        # フォールバック：空白分割
        parts = [p.strip() for p in line.split()]
        return [p for p in parts if p]

    def _load(self) -> None:
        if not os.path.exists(self.table_path):
            raise FileNotFoundError(f"変換表が見つかりません: {self.table_path}")

        with open(self.table_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    continue
                # ヘッダっぽい行はスキップ
                if "ピナクル" in line or "日本式" in line or "====" in line:
                    continue

                parts = self._split_flex(line)
                if len(parts) < 2:
                    continue
                # 先頭は数値（ピナクル値）、2つ目は日本式ラベルと想定
                try:
                    val = float(parts[0])
                except ValueError:
                    continue
                label = parts[1]
                if not label:
                    continue
                self.value_to_label[val] = label
                self.label_to_value[label] = val

        if not self.value_to_label or not self.label_to_value:
            raise ValueError("変換表の読み込みに失敗しました（有効な行が見つかりません）。")

    def jp_to_value(self, jp_label: str) -> float:
        jp_label = (jp_label or "").strip()
        if jp_label not in self.label_to_value:
            raise KeyError(f"変換表に存在しない日本式ラベルです: {jp_label}")
        return self.label_to_value[jp_label]

    def value_to_jp(self, value: float) -> str:
        """
        ピナクル値を 0.05 刻みに丸めてから日本式ラベルへ。
        """
        stepped = round(round(float(value) / 0.05) * 0.05, 2)
        if stepped not in self.value_to_label:
            raise KeyError(f"変換表に存在しないピナクル値です: {value}（丸め={stepped}）")
        return self.value_to_label[stepped]


# -------------------------
# 基本ユーティリティ
# -------------------------
def remove_margin_fair_probs(odd_a: float, odd_b: float) -> Tuple[float, float]:
    """
    2択のマージン除去：pA, pB を返す。
    odd_a: 対象Aのオッズ、odd_b: 相手Bのオッズ
    """
    qa = 1.0 / float(odd_a)
    qb = 1.0 / float(odd_b)
    total = qa + qb
    if total <= 0:
        raise ValueError("無効なオッズ（合計逆数が0以下）")
    p_a = qa / total
    return p_a, 1.0 - p_a


def linear_interpolate(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    """
    (x1, y1) - (x2, y2) の線形補間
    """
    if x2 == x1:
        return y1
    t = (x - x1) / (x2 - x1)
    return y1 + t * (y2 - y1)


# -------------------------
# EV（turnover レーキバック）
# -------------------------
def quantize_rakeback(r: float) -> float:
    """
    レーキバック率 r を 0.5%（=0.005）刻みに丸める。
    許容範囲: [0.0, 0.03]
    例：0.016 -> 0.015, 0.001 -> 0.000
    """
    r = max(0.0, min(0.03, float(r)))
    stepped = round(round(r / 0.005) * 0.005, 3)
    return stepped


def ev_pct_fullwin_turnover(fair_prob: float, payout_odds: float = 1.9, rakeback_pct: float = 0.0) -> float:
    """
    シンプルなレーキバック方式のEV%：
      実効配当 = 基本配当 + レーキバック
      EV = 公正勝率 × 実効配当 - 1.0
      EV% = EV × 100

    例: 公正勝率50%、配当1.9、レーキバック1.5%の場合
        EV = 0.50 × (1.9 + 0.015) - 1.0 = 0.50 × 1.915 - 1.0 = -0.425%
    """
    p = float(fair_prob)
    base_odds = float(payout_odds)
    r = quantize_rakeback(rakeback_pct)

    # シンプルな実効配当計算
    effective_odds = base_odds + r

    # EV計算
    ev = p * effective_odds - 1.0
    return ev * 100.0


class BaseballEV:
    """
    MLB向けEV。丸勝ち配当と（turnover）レーキバックを外部から設定可能。
    - jp_fullwin_odds: 日本式の丸勝ち配当 O（既定 1.9）
    - rakeback_pct: レーキバック率 r（既定 0.0 = 0%）
    """
    def __init__(self, jp_fullwin_odds: float = 1.9, rakeback_pct: float = 0.0) -> None:
        self.jp_fullwin_odds = float(jp_fullwin_odds)
        self.rakeback_pct = quantize_rakeback(rakeback_pct)
        self.conv = ConversionTable()

    # --- 変換 ---
    def jp_label_to_pinnacle_value(self, jp_label: str) -> float:
        return self.conv.jp_to_value(jp_label)

    def pinnacle_value_to_jp_label(self, value: float) -> str:
        return self.conv.value_to_jp(value)

    # --- EV ---
    def ev_pct_plain(self, fair_prob: float) -> float:
        """レーキ無しのEV%（後方互換）"""
        ev = float(fair_prob) * self.jp_fullwin_odds - 1.0
        return ev * 100.0

    def ev_pct_with_rakeback(self, fair_prob: float) -> float:
        """turnover レーキ込みのEV%"""
        return ev_pct_fullwin_turnover(
            fair_prob=fair_prob,
            payout_odds=self.jp_fullwin_odds,
            rakeback_pct=self.rakeback_pct,
        )
