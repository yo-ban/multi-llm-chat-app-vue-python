import type { Model } from './models';

export interface GlobalSettings {
  apiKeys: { [key: string]: string };
  defaultTemperature: number;
  defaultMaxTokens: number;
  defaultVendor: string;
  defaultModel: string;
  defaultReasoningEffort?: 'low' | 'medium' | 'high';  // Default reasoning effort for models that support it
  defaultWebSearch: boolean;  // Default web search setting
  openrouterModels: Model[];
  titleGenerationVendor: string;  // Vendor for generating chat titles
  titleGenerationModel: string;   // Model for generating chat titles
}

export interface APISettings {
  vendor: string;
  model: string;
  temperature: number;
  maxTokens: number;
} 