import type { ReasoningEffortType, ReasoningParameterType } from './reasoning';

export interface APISettings {
  vendor: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
  /** 定性的な Reasoning 努力レベル（該当する場合に送信）。 */
  reasoningEffort?: ReasoningEffortType;
  /** Reasoning のための開始トークン予算（該当する場合に送信）。 */
  budgetTokens?: number;
  /** 選択されたモデルが Reasoning をサポートしているかどうかのフラグ。 */
  isReasoningSupported?: boolean;
  /** オプション：バックエンドがどのパラメータセット（'effort' or 'budget'）を適用するか判断するのに役立ちます。 */
  reasoningParameterType?: ReasoningParameterType;
  toolUse?: boolean;
  multimodal?: boolean;
  imageGeneration?: boolean;
}

export interface APIResponse<T> {
  data: T;
  error?: string;
}
