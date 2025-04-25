import type { Model } from './models'
// highlight-start
// 新しく作成した mcp.ts から型をインポート
import type { McpServersConfig, CanonicalToolDefinition } from './mcp'
// highlight-end

export interface GlobalSettings {
  /** APIキーのベンダーごとの設定状態 (true: 設定済み, false: 未設定) */
  apiKeys: Record<string, boolean> // { [key: string]: boolean } と同じ
  /** デフォルトのtemperature */
  defaultTemperature: number
  /** デフォルトのmax tokens */
  defaultMaxTokens: number
  /** デフォルトのベンダー */
  defaultVendor: string
  /** デフォルトのモデルID */
  defaultModel: string
  /** OpenRouterモデルのリスト */
  openrouterModels: Model[]
  /** タイトル生成に使用するベンダー */
  titleGenerationVendor: string
  /** タイトル生成に使用するモデルID */
  titleGenerationModel: string

  // highlight-start
  /**
   * DBに保存されているMCPサーバー設定の辞書
   * (キー: サーバー名, 値: ServerConfig)
   */
  mcpServersConfig: McpServersConfig
  /** 無効に設定されているMCPサーバー名のリスト */
  disabledMcpServers: string[]
  /** 無効に設定されているMCPツール名のリスト (例: "mcp-server1-toolA") */
  disabledMcpTools: string[]
  /**
   * 現在バックエンドで利用可能なMCPツール定義のリスト
   * (バックエンドが接続中のサーバーから取得した情報)
   */
  availableMcpTools: CanonicalToolDefinition[]
  // highlight-end
}

