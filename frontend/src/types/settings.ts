import type { Model } from './models';
import type { ReasoningEffortType } from './reasoning';
import type { APISettings } from './api';

export interface GlobalSettings {
  apiKeys: { [key: string]: boolean };
  defaultTemperature: number;
  defaultMaxTokens: number;
  defaultVendor: string;
  defaultModel: string;
  /** 'effort' を使用するモデルに対する、ユーザーの優先デフォルト Reasoning 努力レベル。 */
  defaultReasoningEffort?: ReasoningEffortType;
  /** 'budget' を使用するモデルに対する、ユーザーの優先デフォルト開始予算トークン数。 */
  // defaultBudgetTokens?: number;
  defaultWebSearch: boolean;
  openrouterModels: Model[];
  titleGenerationVendor: string;
  titleGenerationModel: string;
}

export interface GlobalSettingsCreate {
  apiKeys?: { [key: string]: string }; // 送信時は string
  defaultTemperature?: number;
  defaultMaxTokens?: number;
  defaultVendor?: string;
  defaultModel?: string;
  /** 'effort' を使用するモデルに対する、ユーザーの優先デフォルト Reasoning 努力レベル。 */
  defaultReasoningEffort?: ReasoningEffortType;
  /** 'budget' を使用するモデルに対する、ユーザーの優先デフォルト開始予算トークン数。 */
  // defaultBudgetTokens?: number;
  defaultWebSearch?: boolean;
  openrouterModels?: Model[];
  titleGenerationVendor?: string;
  titleGenerationModel?: string;
}

export type { APISettings }; 