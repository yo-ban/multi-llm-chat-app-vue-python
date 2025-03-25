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