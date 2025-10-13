#!/bin/bash
# Railway 起動スクリプト

# 必要なディレクトリを作成
mkdir -p logs
mkdir -p data/soccer
mkdir -p backups

# サーバー起動
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
# Railway deployment Mon Oct 13 11:32:41 JST 2025
