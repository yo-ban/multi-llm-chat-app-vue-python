import { defineStore } from 'pinia';
import { MODELS } from '@/constants/models';
import type { GlobalSettings } from '@/types/settings';
import type { Model } from '@/types/models';
import { backendStorageService } from '@/services/storage/backend-storage-service';

const DEFAULT_GLOBAL_SETTINGS: GlobalSettings = {
  apiKeys: Object.keys(MODELS).reduce((acc, vendor) => {
    acc[vendor] = '';
    return acc;
  }, {} as { [key: string]: string }),
  defaultTemperature: 0.7,
  defaultMaxTokens: 4096,
  defaultVendor: 'anthropic',
  defaultModel: MODELS.anthropic.CLAUDE_3_5_SONNET.id,
  defaultReasoningEffort: 'medium',
  defaultWebSearch: false,
  openrouterModels: [],
  titleGenerationVendor: 'openai',
  titleGenerationModel: 'openai-gpt-4o-mini',
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
            apiKeys: { // Ensure all vendors exist, even if not saved yet
              ...DEFAULT_GLOBAL_SETTINGS.apiKeys,
              ...(savedSettings.apiKeys || {}),
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

    async saveSettings(settings: GlobalSettings) {
      try {
        // Use backendStorageService to save settings via the API
        await backendStorageService.saveGlobalSettings(settings);
        // Update the local store state after successful save
        this.$patch(settings);
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
        return this.openrouterModels.find(m => m.id === modelId) || null;
      }
      
      // Need to handle the case where vendor might not be in MODELS if loaded from backend
      const vendorModels = MODELS[this.defaultVendor as keyof typeof MODELS] || {}; 
      return Object.values(vendorModels).find(m => m.id === modelId) || null;
    },

    getEffectiveReasoningEffort(modelId: string): 'low' | 'medium' | 'high' | undefined {
      const model = this.getModelById(modelId);
      if (!model?.supportsReasoning) {
        return undefined;
      }
      // Use the current state's default value
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