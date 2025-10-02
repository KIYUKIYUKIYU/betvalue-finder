from __future__ import annotations
import re
from typing import Tuple, Dict

# このファイルはハンデ変換の責務だけを持つ

def try_parse_jp(token: str) -> Tuple[bool, float]:
    if not token: return False, 0.0
    try:
        # "0/5" -> 0.5
        if '/' in token:
            parts = token.split('/')
            return True, float(parts[0]) + float(parts[1]) / 10.0
        # "1半" -> 1.5, "0半5" -> 0.75, "1半2" -> 1.75
        if '半' in token:
            if token.endswith('半'):
                return True, float(token.replace('半', '')) + 0.5
            else:
                base, sub = token.split('半')
                base_val = float(base) if base else 0
                # 0半5, 1半2, 0半7, 0半1 のような特殊形式
                if len(sub) == 1 and sub.isdigit():
                    return True, base_val + 0.5 + 0.25
                return True, base_val + 0.5
        # "1.2" -> 1.2
        return True, float(token)
    except (ValueError, TypeError):
        return False, 0.0