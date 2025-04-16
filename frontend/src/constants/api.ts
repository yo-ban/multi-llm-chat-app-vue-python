export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5200/api';
export const API_MESSAGES_ENDPOINT = '/messages';
export const API_EXTRACT_ENDPOINT = '/extract-text'
export const API_SETTINGS_ENDPOINT = '/settings';
// export const API_PERSONAS_ENDPOINT = '/personas';
// export const API_FOLDERS_ENDPOINT = '/folders';
// export const API_CONVERSATIONS_ENDPOINT = '/conversations';
// export const API_CHAT_ENDPOINT = '/chat';

/** 
認証:
POST /api/auth/register: ユーザー登録
POST /api/auth/login: ログイン (トークン発行)
POST /api/auth/logout: ログアウト
GET /api/auth/me: 認証済みユーザー情報の取得
設定 (Global Settings -> User Settings):
GET /api/settings: 認証ユーザーの設定を取得
PUT /api/settings: 認証ユーザーの設定を更新 (APIキーはこちらで安全に管理)
ペルソナ:
GET /api/personas: 認証ユーザーのペルソナ一覧を取得
POST /api/personas: 新しいペルソナを作成
GET /api/personas/{persona_id}: 特定のペルソナを取得
PUT /api/personas/{persona_id}: 特定のペルソナを更新
DELETE /api/personas/{persona_id}: 特定のペルソナを削除
フォルダ:
GET /api/folders: 認証ユーザーのフォルダ一覧を取得
POST /api/folders: 新しいフォルダを作成
GET /api/folders/{folder_id}: 特定のフォルダを取得 (含まれる会話のメタデータも返すか検討)
PUT /api/folders/{folder_id}: 特定のフォルダを更新
DELETE /api/folders/{folder_id}: 特定のフォルダを削除
会話 (Conversations):
GET /api/conversations: 認証ユーザーの会話メタデータ一覧を取得 (フォルダ別、最新順などのフィルタリング/ソート機能付き)
POST /api/conversations: 新しい会話を開始 (最初のメッセージと共に作成されることが多い) -> 既存のチャットエンドポイントと統合する方が自然
GET /api/conversations/{conversation_id}: 特定の会話のメタデータを取得
PUT /api/conversations/{conversation_id}: 会話のメタデータ（タイトル、フォルダなど）を更新
DELETE /api/conversations/{conversation_id}: 会話全体（メタデータとメッセージ）を削除
GET /api/conversations/{conversation_id}/messages: 特定の会話のメッセージ一覧を取得 (ページネーション必須)
POST /api/conversations/{conversation_id}/regenerate: (オプション) アシスタントの最後の応答を再生成
チャット処理 (既存の chat_handler と統合):
POST /api/chat/{conversation_id} (または /api/chat でリクエストボディに conversation_id を含める):
ユーザーからのメッセージを受け取る。
LLM API と通信する (バックエンドで管理している API キーを使用)。
ユーザーメッセージとアシスタントの応答をデータベースに保存する。
アシスタントの応答をストリーミングでクライアントに返す。
新しい会話の場合は、ここで conversations テーブルにレコードを作成する。
会話タイトルの自動生成などもこのフローに組み込む。
アプリ状態 (Current Conversation ID など):
これはクライアント側で管理する方がシンプルな場合が多いです (例: localStorage や Vuex/Pinia の状態)。バックエンドで管理する必要性は低いかもしれません。もし必要なら PUT /api/users/me/state のようなエンドポイントを用意します。
検索:
GET /api/search?q={query}: 会話タイトルやメッセージ内容を横断検索
2. 会話履歴のデータベース設計 (PostgreSQL を推奨)
会話履歴の検索性を考慮すると、リレーショナルデータベース (特に PostgreSQL) が強力な選択肢です。以下にテーブル設計の例を示します。
users テーブル: (認証用: FastAPI-Users などのライブラリ利用を推奨)
id (UUID, 主キー)
email (VARCHAR, UNIQUE)
hashed_password (VARCHAR)
is_active, is_superuser, is_verified (BOOLEAN)
created_at, updated_at (TIMESTAMP WITH TIME ZONE)
conversations テーブル: (会話のメタデータ)
id (UUID, 主キー)
user_id (UUID, users.id への外部キー, INDEX)
title (VARCHAR, NULL許容, INDEX または FULLTEXT INDEX)
created_at (TIMESTAMP WITH TIME ZONE, DEFAULT now())
updated_at (TIMESTAMP WITH TIME ZONE, DEFAULT now())
folder_id (UUID, folders.id への外部キー, NULL許容, INDEX)
system_prompt (TEXT, NULL許容)
model_vendor (VARCHAR)
model_id (VARCHAR)
settings_snapshot (JSONB) - 会話開始時のモデル設定（温度など）を保存
messages テーブル: (個々のメッセージ)
id (UUID, 主キー)
conversation_id (UUID, conversations.id への外部キー, INDEX)
user_id (UUID, users.id への外部キー, INDEX) - conversationから辿れるが、直接持っておくと権限チェックや検索で便利な場合がある
role (VARCHAR - 'user', 'assistant', 'system', 'tool')
content (TEXT) - ここに全文検索インデックスを作成 (GIN or GiST with tsvector)
timestamp (TIMESTAMP WITH TIME ZONE, DEFAULT now(), INDEX) - conversation_id との複合インデックスが有効
token_count (INTEGER, NULL許容)
model (VARCHAR, NULL許容) - アシスタントメッセージの場合
finish_reason (VARCHAR, NULL許容) - アシスタントメッセージの場合
metadata (JSONB, NULL許容) - 画像参照、ツール呼び出し/結果、引用元などの追加情報。GIN インデックスを特定のキーに作成可能。
folders テーブル:
id (UUID, 主キー)
user_id (UUID, users.id への外部キー, INDEX)
name (VARCHAR)
created_at, updated_at (TIMESTAMP WITH TIME ZONE)
personas テーブル: (内容は既存の UserDefinedPersona に合わせて)
id (UUID, 主キー)
user_id (UUID, users.id への外部キー, INDEX)
name (VARCHAR)
... (他のペルソナ属性)
created_at, updated_at (TIMESTAMP WITH TIME ZONE)
user_settings テーブル: (1ユーザー1レコード)
user_id (UUID, users.id への外部キー, 主キー)
api_keys_encrypted (BYTEA or TEXT) - 暗号化して保存
default_model_vendor (VARCHAR)
default_model_id (VARCHAR)
... (他の設定項目)
updated_at (TIMESTAMP WITH TIME ZONE)
 */