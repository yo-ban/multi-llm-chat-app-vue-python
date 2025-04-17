"""
設定ドメイン関連の定数定義
"""

# アプリケーションで認識されているAPIキーベンダーのリスト
# フロントエンド (frontend/src/constants/models.ts) と同期させる
KNOWN_VENDORS = [
    "anthropic",
    "openai",
    "google",
    "xai",
    "openrouter",
    # 必要に応じて他のベンダーを追加
] 