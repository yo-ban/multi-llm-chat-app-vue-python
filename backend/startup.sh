#!/bin/bash
set -e

# マイグレーションの実行
echo "Running database migrations..."
cd /app
python -m alembic upgrade head

# アプリケーションの起動
echo "Starting application..."
exec "$@" 