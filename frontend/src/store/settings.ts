import { defineStore } from 'pinia';
import { MODELS } from '@/constants/models';
import type { GlobalSettings } from '@/types/settings';
import type { Model } from '@/types/models';
import { backendStorageService } from '@/services/storage/backend-storage-service';
import type { McpServersConfig, CanonicalToolDefinition } from '@/types/mcp';

const DEFAULT_GLOBAL_SETTINGS: GlobalSettings = {
  apiKeys: Object.keys(MODELS).reduce((acc, vendor) => {
    acc[vendor] = false; // デフォルトは未設定 (false)
    return acc;
  }, {} as { [key: string]: boolean }),
  defaultTemperature: 1.0,
  defaultMaxTokens: 4096,
  defaultVendor: 'anthropic',
  defaultModel: MODELS.anthropic.CLAUDE_HAIKU_4_5.id,
  openrouterModels: [],
  titleGenerationVendor: 'anthropic',
  titleGenerationModel: MODELS.anthropic.CLAUDE_HAIKU_4_5.id,
  // --- MCP Defaults ---
  mcpServersConfig: {},
  disabledMcpServers: [],
  disabledMcpTools: [],
  availableMcpTools: [],
};

export const useSettingsStore = defineStore('settings', {
  state: (): GlobalSettings => ({
    // Initialize with default values, loadSettings will overwrite
    ...DEFAULT_GLOBAL_SETTINGS,
  }),

  actions: {
    async loadSettings() {
      try {
        // Use backendStorageService to get settings from the API
        const savedSettings = await backendStorageService.getGlobalSettings();
        
        if (savedSettings) {
          // Merge backend settings with defaults
          const mergedSettings = {
            ...DEFAULT_GLOBAL_SETTINGS, 
            ...savedSettings,           
            apiKeys: { // apiKeys は boolean の辞書
              ...DEFAULT_GLOBAL_SETTINGS.apiKeys,
              ...(savedSettings.apiKeys || {}),
            },
            // Ensure openrouterModels is an array
            openrouterModels: savedSettings.openrouterModels || [],
            mcpServersConfig: savedSettings.mcpServersConfig || {},
            disabledMcpServers: savedSettings.disabledMcpServers || [],
            disabledMcpTools: savedSettings.disabledMcpTools || [],
            availableMcpTools: savedSettings.availableMcpTools || [], // 利用可能ツールリストも取得
          };
          this.$patch(mergedSettings); // ストア全体をマージした設定で更新
        } else {
          // No settings from backend (or error occurred), use defaults
          console.warn('No settings loaded from backend, using default settings.');
          this.$patch(DEFAULT_GLOBAL_SETTINGS);
        }
      } catch (error) {
          console.error('Failed to load settings from backend:', error);
          // Fallback to default settings in case of error
          this.$patch(DEFAULT_GLOBAL_SETTINGS);
      }
    },

    // changedApiKeys には実際のキー文字列または空文字列（削除用）が入る
    async saveSettings(adjustedSettings: Partial<GlobalSettings> & { changedApiKeys?: { [key: string]: string } }) {
      try {
        // バックエンドに送信するペイロードを作成
        // changedApiKeys を apiKeys として含める
        const { availableMcpTools, ...stateWithoutTools } = this.$state; // availableMcpToolsを除外
        const payloadToSend = {
          ...stateWithoutTools, // 現在のストアの状態をベースに（availableMcpTools除く）
          ...adjustedSettings, // 他の変更された設定をマージ
          changedApiKeys: adjustedSettings.changedApiKeys || {}, // 変更されたAPIキーを設定
          mcpServersConfig: adjustedSettings.mcpServersConfig ?? this.mcpServersConfig,
          disabledMcpServers: adjustedSettings.disabledMcpServers ?? this.disabledMcpServers,
          disabledMcpTools: adjustedSettings.disabledMcpTools ?? this.disabledMcpTools,
        };

        // バックエンドAPIは SettingsCreate 型 (apiKeys: Dict[str, str]) を期待している
        const savedSettingsResponse = await backendStorageService.saveGlobalSettings(payloadToSend); // API呼び出し

        // APIから返却された最新の状態でストアを更新
        // ネストされたオブジェクトは完全に置き換える必要があるため、個別に設定
        this.mcpServersConfig = savedSettingsResponse.mcpServersConfig || {};
        this.apiKeys = savedSettingsResponse.apiKeys || DEFAULT_GLOBAL_SETTINGS.apiKeys;
        
        // その他のフィールド（配列や単純な値）をpatch
        this.$patch({
          ...savedSettingsResponse,
          disabledMcpServers: savedSettingsResponse.disabledMcpServers || [],
          disabledMcpTools: savedSettingsResponse.disabledMcpTools || [],
          availableMcpTools: savedSettingsResponse.availableMcpTools || [], // 最新のツールリストで更新
        });
        console.log('Settings saved to backend and store updated.');
      } catch (error) {
        console.error('Failed to save settings to backend:', error);
        // Decide how to handle save errors (e.g., show notification to user)
        // Re-throw or handle locally
        throw error; // Re-throwing allows the component to catch it (e.g., stop loading indicator)
      }
    },

    getModelById(modelId: string): Model | null {
      if (this.defaultVendor === 'openrouter') {
        const model = this.openrouterModels.find(m => m.id === modelId);
        return model ? { ...model } : null;
      }
      
      // Need to handle the case where vendor might not be in MODELS if loaded from backend
      const vendorModels = MODELS[this.defaultVendor as keyof typeof MODELS] || {}; 
      const model = Object.values(vendorModels).find(m => m.id === modelId);
      return model ? { ...model } : null;
    },

    getEffectiveReasoningEffort(modelId: string): 'low' | 'medium' | 'high' | undefined {
      const model = this.getModelById(modelId);
      if (!model?.supportsReasoning || !model.reasoningParameters) {
        return undefined;
      }

      if (model.reasoningParameters.type !== 'effort') {
        return undefined;
      }

      return model.reasoningParameters.effort;
    },

    // Check if a given modelId is valid for the specified vendor
    // Returns the valid modelId, or a fallback if necessary
    validateModelSelection(modelId: string, vendor: string): string {
      // Only perform validation for OpenRouter vendor
      if (vendor !== 'openrouter') return modelId;
      
      // If there are OpenRouter models and the current model exists, keep it
      if (this.openrouterModels.length > 0) {
        const modelExists = this.openrouterModels.some(m => m.id === modelId);
        if (modelExists) {
          return modelId; // Model is valid
        } else if (this.openrouterModels.length > 0) {
          return this.openrouterModels[0].id; // Fallback to first available model
        }
      }
      
      // If we have no OpenRouter models yet, preserve the current selection
      return modelId;
    },

    /** 有効なMCPサーバー設定のリストを取得 */
    getActiveMcpServersConfig(): McpServersConfig {
      const activeConfig: McpServersConfig = {}
      const disabledSet = new Set(this.disabledMcpServers)
      for (const serverName in this.mcpServersConfig) {
        if (!disabledSet.has(serverName)) {
          activeConfig[serverName] = this.mcpServersConfig[serverName]
        }
      }
      return activeConfig
    },

    /** 利用可能なツールのうち、有効なものだけを取得 */
    getEnabledAvailableMcpTools(): CanonicalToolDefinition[] {
      const disabledSet = new Set(this.disabledMcpTools)
      return this.availableMcpTools.filter(tool => !disabledSet.has(tool.name))
    }
  },
});
