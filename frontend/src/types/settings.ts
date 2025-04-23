import type { Model } from './models';

export interface GlobalSettings {
  apiKeys: { [key: string]: boolean };
  defaultTemperature: number;
  defaultMaxTokens: number;
  defaultVendor: string;
  defaultModel: string;
  openrouterModels: Model[];
  titleGenerationVendor: string;
  titleGenerationModel: string;
}
