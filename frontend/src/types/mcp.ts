/** Stdioサーバー固有の設定 */
export interface StdioServerConfig {
  type: 'stdio'
  command: string
  args?: string[]
  env?: Record<string, string> | null
}

/** HTTPサーバー固有の設定 */
export interface HttpServerConfig {
  type: 'http'
  url: string
  // 必要に応じて認証情報などを追加
}

/** MCPサーバー設定 (Stdio または Http) */
export type ServerConfig = StdioServerConfig | HttpServerConfig

/** MCPサーバー設定の辞書型 (キーはサーバー名) */
export type McpServersConfig = Record<string, ServerConfig>

/** カノニカル形式のツール定義 - 配列要素のスキーマ */
export interface CanonicalToolItemsSchema {
  /** 配列要素の型 ('string', 'integer', 'number', 'boolean', 'object', 'array') */
  type: string
}

/** カノニカル形式のツール定義 - パラメータ */
export interface CanonicalToolParameter {
  /** パラメータの型 ('string', 'integer', 'number', 'boolean', 'object', 'array', 'any') */
  type: string
  /** パラメータの説明 (オプション) */
  description?: string | null
  /** typeが'array'の場合の要素スキーマ (オプション) */
  items?: CanonicalToolItemsSchema | null
}

/** カノニカル形式のツール定義 */
export interface CanonicalToolDefinition {
  /** ツール名 (例: "mcp-server1-toolA") */
  name: string
  /** ツールの説明 (オプション) */
  description?: string | null
  /** パラメータ定義 (キーはパラメータ名) */
  parameters: Record<string, CanonicalToolParameter>
  /** 必須パラメータ名のリスト */
  required: string[]
}

