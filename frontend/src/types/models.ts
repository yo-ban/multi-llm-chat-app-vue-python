export interface Model {
    id: string;
    name: string;
    contextWindow: number;
    maxTokens: number;
    multimodal: boolean;
    supportsReasoning?: boolean;  // Whether the model supports reasoning
    defaultReasoningEffort?: 'low' | 'medium' | 'high';  // Default reasoning effort level
    unsupportsTemperature?: boolean;  // Whether the model does not support temperature parameter
    supportFunctionCalling?: boolean;  // Whether the model supports function calling (e.g. for web search)
}

// Define a structure for user-configured models
export interface ModelConfiguration {
  id: string;           // Unique model identifier, e.g. "perplexity/sonar"
  name: string;         // A displayable name for the model
  contextWindow: number; // How much context the model supports
  maxTokens: number;    // Maximum tokens allowed by the model
  multimodal: boolean;  // Whether or not images are supported (true/false)
  supportsReasoning?: boolean;  // Whether the model supports reasoning
  defaultReasoningEffort?: 'low' | 'medium' | 'high';  // Default reasoning effort level
  unsupportsTemperature?: boolean;  // Whether the model does not support temperature parameter
  supportFunctionCalling?: boolean;  // Whether the model supports function calling (e.g. for web search)
}

export interface ModelVendor {
  [key: string]: Model;
}

export interface Models {
  [key: string]: ModelVendor;
}

export type ReasoningEffort = 'low' | 'medium' | 'high';