import type { ReasoningParameters } from './reasoning';

export interface Model {
  id: string;
  name: string;
  contextWindow: number;
  maxTokens: number;
  multimodal: boolean;
  /** モデルが Reasoning 機能（API で reasoning パラメータを受け付けるかなど）をサポートしているかどうかを示します。 */
  supportsReasoning: boolean;
  reasoningParameters?: ReasoningParameters;
  unsupportsTemperature?: boolean;
  supportFunctionCalling?: boolean;
  imageGeneration?: boolean;
}

export interface ModelVendor {
  [key: string]: Model;
}

export interface Models {
  [key: string]: ModelVendor;
}