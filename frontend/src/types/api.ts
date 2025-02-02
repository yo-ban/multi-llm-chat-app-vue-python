export interface APISettings {
  vendor: string;
  model: string;
  maxTokens?: number;
  temperature?: number;
  reasoningEffort?: 'low' | 'medium' | 'high';  // For OpenAI reasoning models
  isReasoningSupported?: boolean;  // Flag to indicate if the model supports reasoning
  websearch?: boolean;  // Flag to enable web search functionality
}
