import type { Model } from './models';
import type { ReasoningEffort } from './common';
import type { APISettings } from './api';

export interface GlobalSettings {
  apiKeys: { [key: string]: boolean };
  defaultTemperature: number;
  defaultMaxTokens: number;
  defaultVendor: string;
  defaultModel: string;
  defaultReasoningEffort?: ReasoningEffort;
  defaultWebSearch: boolean;  // Default web search setting
  openrouterModels: Model[];
  titleGenerationVendor: string;  // Vendor for generating chat titles
  titleGenerationModel: string;   // Model for generating chat titles
}

export interface GlobalSettingsCreate {
  apiKeys?: { [key: string]: string }; // 送信時は string
  defaultTemperature?: number;
  defaultMaxTokens?: number;
  defaultVendor?: string;
  defaultModel?: string;
  defaultReasoningEffort?: ReasoningEffort;
  defaultWebSearch?: boolean;
  openrouterModels?: Model[];
  titleGenerationVendor?: string;
  titleGenerationModel?: string;
}

export type { APISettings }; 