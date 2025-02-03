import type { ReasoningEffort } from './common';

export interface APISettings {
  vendor: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
  reasoningEffort?: ReasoningEffort;
  isReasoningSupported?: boolean;
  websearch?: boolean;
  multimodal?: boolean;
}

export interface APIResponse<T> {
  data: T;
  error?: string;
}
