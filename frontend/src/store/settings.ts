import { defineStore } from 'pinia';
import { MODELS } from '@/constants/models';
import type { GlobalSettings } from '@/types/settings';
import type { Model } from '@/types/models';
import { backendStorageService } from '@/services/storage/backend-storage-service';

const DEFAULT_GLOBAL_SETTINGS: GlobalSettings = {
  apiKeys: Object.keys(MODELS).reduce((acc, vendor) => {
    acc[vendor] = false; // デフォルトは未設定 (false)
    return acc;
  }, {} as { [key: string]: boolean }),
  defaultTemperature: 0.7,
  defaultMaxTokens: 4096,
  defaultVendor: 'anthropic',
  defaultModel: MODELS.anthropic.CLAUDE_3_5_SONNET.id,
  defaultReasoningEffort: 'medium',
  // defaultBudgetTokens: 4096,
  defaultWebSearch: false,
  openrouterModels: [],
  titleGenerationVendor: 'anthropic',
  titleGenerationModel: MODELS.anthropic.CLAUDE_3_HAIKU.id,
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
            apiKeys: { 
              ...DEFAULT_GLOBAL_SETTINGS.apiKeys,
              ...(savedSettings.apiKeys || {}), // savedSettings.apiKeys は boolean 辞書のはず
            },
            // Ensure openrouterModels is an array
            openrouterModels: savedSettings.openrouterModels || [],
          };
          this.$patch(mergedSettings);
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
        const payloadToSend = {
          ...this.$state, // 現在のストアの状態をベースに
          ...adjustedSettings, // 他の変更された設定をマージ
          changedApiKeys: adjustedSettings.changedApiKeys || {}, // 変更されたAPIキーを設定
        };
        // バックエンドAPIは SettingsCreate 型 (apiKeys: Dict[str, str]) を期待している
        const savedSettingsResponse = await backendStorageService.saveGlobalSettings(payloadToSend); // API呼び出し

        // APIから返却された最新の状態 (apiKeys: boolean) でストアを更新
        this.$patch({
          ...savedSettingsResponse,
           // highlight-start
          // boolean の辞書でストアを更新
          apiKeys: savedSettingsResponse.apiKeys || DEFAULT_GLOBAL_SETTINGS.apiKeys 
           // highlight-end
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
      } else if (model.reasoningParameters.type === 'budget') {
        return undefined;
      } else {
        return model.reasoningParameters.effort;
      }
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
    }
  },
});