import type { Model } from '@/types/models';


export const MODELS: { [key: string]: { [key: string]: Model } } = {
  anthropic: {
    CLAUDE_3_7_SONNET: {
      id: 'claude-3-7-sonnet-20250219',
      name: 'Claude 3.7 Sonnet',
      contextWindow: 200000,
      maxTokens: 8192,
      multimodal: true
    },
    CLAUDE_3_7_SONNET_THINKING: {
      id: 'claude-3-7-sonnet-20250219-thinking',
      name: 'Claude 3.7 Sonnet (with Thinking)',
      contextWindow: 200000,
      maxTokens: 128000,
      multimodal: true,
      supportsReasoning: true,
      defaultReasoningEffort: 'low',
    },
    CLAUDE_3_5_SONNET: {
      id: 'claude-3-5-sonnet-20241022',
      name: 'Claude 3.5 Sonnet',
      contextWindow: 200000,
      maxTokens: 8192,
      multimodal: true
    },
    CLAUDE_3_HAIKU: {
      id: 'claude-3-haiku-20240307',
      name: 'Claude 3 Haiku',
      contextWindow: 200000,
      maxTokens: 4096,
      multimodal: true
    }
  },
  openai: {
    OPENAI_GPT_4_O: {
      id: 'openai-gpt-4o',
      name: 'GPT-4o',
      contextWindow: 128000,
      maxTokens: 16384,
      multimodal: true,
      supportsReasoning: false,
      supportFunctionCalling: true,
    },
    OPENAI_GPT_4_O_MINI: {
      id: 'openai-gpt-4o-mini',
      name: 'GPT-4o Mini',
      contextWindow: 128000,
      maxTokens: 16384,
      multimodal: true,
      supportsReasoning: false,
      supportFunctionCalling: true,
    },
    OPENAI_O1: {
      id: 'openai-o1',
      name: 'o1',
      contextWindow: 200000,
      maxTokens: 100000,
      multimodal: true,
      supportsReasoning: true,
      defaultReasoningEffort: 'medium',
      unsupportsTemperature: true,
      supportFunctionCalling: true,
    },
    OPENAI_O3_MINI: {
      id: 'openai-o3-mini',
      name: 'o3-mini',
      contextWindow: 200000,
      maxTokens: 100000,
      multimodal: false,
      supportsReasoning: true,
      defaultReasoningEffort: 'medium',
      unsupportsTemperature: true,
      supportFunctionCalling: true,
    },
    OPENAI_CHATGPT_4_O: {
      id: 'openai-chatgpt-4o-latest',
      name: 'ChatGPT-4o',
      contextWindow: 128000,
      maxTokens: 16384,
      multimodal: true,
      supportsReasoning: false,
    },
  },
  google: {
    GEMINI_2_0_FLASH: {
      id: 'gemini-2.0-flash',
      name: 'Gemini 2.0 Flash',
      contextWindow: 1048576,
      maxTokens: 8192,
      multimodal: true,
      supportFunctionCalling: true,
    },
    GEMINI_2_0_PRO_EXP: {
      id: 'gemini-2.0-pro-exp-02-05',
      name: 'Gemini 2.0 Pro Experimental',
      contextWindow: 2097152,
      maxTokens: 8192,
      multimodal: true,
    },
    GEMINI_2_0_FLASH_THINKING_EXP: {
      id: 'gemini-2.0-flash-thinking-exp-01-21',
      name: 'Gemini 2.0 Flash Thinking Experimental',
      contextWindow: 1048576,
      maxTokens: 65536,
      multimodal: true,
      supportsReasoning: true,
    }
  },
  openrouter: {
    
  },
};