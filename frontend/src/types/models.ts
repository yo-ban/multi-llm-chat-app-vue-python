import type { ReasoningEffort } from './common';

export interface Model {
    id: string;
    name: string;
    contextWindow: number;
    maxTokens: number;
    multimodal: boolean;
    supportsReasoning?: boolean;  // Whether the model supports reasoning
    defaultReasoningEffort?: ReasoningEffort;  // Default reasoning effort level
    unsupportsTemperature?: boolean;  // Whether the model does not support temperature parameter
    supportFunctionCalling?: boolean;  // Whether the model supports function calling (e.g. for web search)
    imageGeneration?: boolean;  // Whether the model supports image generation
}

export interface ModelVendor {
  [key: string]: Model;
}

export interface Models {
  [key: string]: ModelVendor;
}