import { defineStore } from 'pinia';
import { MODELS } from '@/constants/models';
import type { GlobalSettings } from '@/types/settings';
import type { Model } from '@/types/models';
import { storageService } from '@/services/storage/indexeddb-service';

export const useSettingsStore = defineStore('settings', {
  state: (): GlobalSettings => ({
    apiKeys: Object.keys(MODELS).reduce((acc, vendor) => {
      acc[vendor] = '';
      return acc;
    }, {} as { [key: string]: string }),
    defaultTemperature: 0.7,
    defaultMaxTokens: 4096,
    defaultVendor: 'anthropic',
    defaultModel: MODELS.anthropic.CLAUDE_3_5_SONNET.id,
    defaultReasoningEffort: 'medium',  // Default reasoning effort for models that support it
    defaultWebSearch: false,  // Default web search setting
    openrouterModels: [],
    titleGenerationVendor: 'openai',  // Default vendor for title generation
    titleGenerationModel: 'openai-gpt-4o-mini',  // Default model for title generation
  }),

  actions: {
    async loadSettings() {
      const settings = await storageService.getGlobalSettings();
      this.$patch(settings);
    },

    async saveSettings(settings: GlobalSettings) {
      this.$patch(settings);
      await storageService.saveGlobalSettings(settings);
    },

    getModelById(modelId: string): Model | null {
      if (this.defaultVendor === 'openrouter') {
        return this.openrouterModels.find(m => m.id === modelId) || null;
      }
      
      const vendorModels = MODELS[this.defaultVendor] || {};
      return Object.values(vendorModels).find(m => m.id === modelId) || null;
    },

    getEffectiveReasoningEffort(modelId: string): 'low' | 'medium' | 'high' | undefined {
      const model = this.getModelById(modelId);
      if (!model?.supportsReasoning) {
        return undefined;
      }
      return this.defaultReasoningEffort || model.defaultReasoningEffort || 'medium';
    }
  },
});