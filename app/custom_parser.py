# -*- coding: utf-8 -*-
"""
app/custom_parser.py
信頼できる部品を組み合わせた、新しい堅牢なカスタムパーサー
(責務分離・リファクタリング版)
"""

import re
import json
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

# チーム名辞書の読み込み
def load_team_database() -> Dict[str, Any]:
    import os
    team_database = {}
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    team_files = [
        "teams_mlb.json", "teams_npb.json", "teams_premier.json",
        "teams_laliga.json", "teams_bundesliga.json", "teams_serie_a.json",
        "teams_ligue1.json", "teams_eredivisie.json", "teams_primeira_liga.json",
        "teams_scottish_premiership.json", "teams_jupiler_league.json",
        "teams_champions_league.json", "teams_national.json", "teams_europa_league.json"
    ]
    for file_name in team_files:
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    team_database.update(json.load(f))
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to load {file_name}: {e}")
    return team_database

TEAM_DATABASE = load_team_database()

# --- 1. エンティティ抽出 --- 
def extract_entities(text: str) -> List[Dict]:
    entities = []
    lines = text.split('\n')

    # チーム名を抽出
    for i, line in enumerate(lines):
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        if not clean_line or re.match(r'[<[](.+?)[>]]', line) or "〆切" in line:
            continue
        
        found_teams_in_line = []
        for key, team_info in TEAM_DATABASE.items():
            all_names = [key] + team_info.get("aliases", [])
            for name in all_names:
                if name in clean_line:
                    found_teams_in_line.append({"type": "team", "text": key, "line": i, "info": team_info})
                    break
        
        if found_teams_in_line:
            best_match = max(found_teams_in_line, key=lambda x: len(x['text']))
            entities.append(best_match)

    # ハンデを抽出
    handicap_pattern = r'<([^>]+)>'
    for i, line in enumerate(lines):
        for match in re.finditer(handicap_pattern, line):
            entities.append({"type": "handicap", "text": match.group(1), "line": i})
            
    return entities

# --- 2. ペアリング --- 
def pair_games_by_league_blocks(text: str, entities: List[Dict]) -> List[Dict]:
    lines = text.split('\n')
    league_markers = []
    for i, line in enumerate(lines):
        match = re.match(r'[<[](.+?)[>]]', line)
        if match:
            league_markers.append({"name": match.group(1), "line": i})

    teams = sorted([e for e in entities if e['type'] == 'team'], key=lambda x: x["line"])
    handicaps = [e for e in entities if e['type'] == 'handicap']

    if not league_markers:
        team_pairs = [tuple(teams[i:i+2]) for i in range(0, len(teams), 2)]
    else:
        blocks = defaultdict(list)
        for team in teams:
            assigned_league = "default"
            for marker in reversed(league_markers):
                if team["line"] > marker["line"]:
                    assigned_league = f"{marker['name']}_{marker['line']}"
                    break
            blocks[assigned_league].append(team)
        team_pairs = []
        for league_name, teams_in_block in blocks.items():
            for i in range(0, len(teams_in_block), 2):
                if i + 1 < len(teams_in_block):
                    team_pairs.append((teams_in_block[i], teams_in_block[i+1]))

    games = []
    for team_a_entity, team_b_entity in team_pairs:
        game = {
            "team_a_jp": team_a_entity["text"],
            "team_b_jp": team_b_entity["text"],
            "team_a": team_a_entity["info"]["full_name"],
            "team_b": team_b_entity["info"]["full_name"],
        }
        for h in handicaps:
            if team_a_entity["line"] == h["line"] or team_b_entity["line"] == h["line"]:
                game["jp_line"] = h["text"]
                break
        games.append(game)
        
    return games

# --- 統括関数 --- 
def parse_text(text: str) -> List[Dict]:
    """パーサーのメイン関数。抽出とペアリングのみを行う。"""
    entities = extract_entities(text)
    games = pair_games_by_league_blocks(text, entities)
    return games
