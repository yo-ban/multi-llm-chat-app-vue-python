import type { OpenRouterModelsResponse, OpenRouterModel } from '@/types/openrouter';

/**
 * OpenRouterサービスのインターフェース
 * OpenRouter APIとの通信を担当
 */
export interface OpenRouterService {
  /**
   * OpenRouterからモデル一覧を取得する
   * @returns OpenRouterのモデル一覧
   */
  fetchModels(): Promise<OpenRouterModel[]>;
  
  /**
   * OpenRouterモデルを内部アプリ用のカスタムモデル形式に変換する
   * @param model OpenRouterのモデル
   * @returns カスタムモデル形式
   */
  convertToCustomModel(model: OpenRouterModel): {
    id: string;
    name: string;
    contextWindow: number;
    maxTokens: number;
    multimodal: boolean;
    description: string;
    pricing: any;
    supportFunctionCalling: boolean;
  };
}

/**
 * OpenRouterサービスの実装クラス
 */
class OpenRouterServiceImpl implements OpenRouterService {
  /**
   * OpenRouterからモデル一覧を取得する
   * @returns OpenRouterのモデル一覧
   */
  async fetchModels(): Promise<OpenRouterModel[]> {
    try {
      const response = await fetch('https://openrouter.ai/api/v1/models');
      if (!response.ok) {
        throw new Error(`Failed to fetch models: ${response.statusText}`);
      }
      const data: OpenRouterModelsResponse = await response.json();
      return data.data;
    } catch (error) {
      console.error('Error fetching OpenRouter models:', error);
      throw error;
    }
  }
  
  /**
   * OpenRouterモデルを内部アプリ用のカスタムモデル形式に変換する
   * @param model OpenRouterのモデル
   * @returns カスタムモデル形式
   */
  convertToCustomModel(model: OpenRouterModel) {
    // top_provider から context_length と max_completion_tokens を取得
    // top_provider がない場合は、モデル自体の context_length を使用し、max_tokens はその75%をデフォルトとする
    const contextWindow = model.top_provider?.context_length || model.context_length;
    const maxTokens = model.top_provider?.max_completion_tokens || 0;

    // モダリティから multimodal かどうかを判定
    // 入力部分（->の左側）に image が含まれているかチェック
    const modalityInput = model.architecture.modality.split('->')[0];
    const isMultimodal = modalityInput.includes('image');

    console.log(`Model ${model.id} modality: ${model.architecture.modality}, isMultimodal: ${isMultimodal}`);

    return {
      id: model.id,
      name: model.name,
      contextWindow,
      maxTokens,
      multimodal: isMultimodal,
      description: model.description || '',
      pricing: model.pricing,
      supportFunctionCalling: false  // デフォルトでは無効
    };
  }
}

// シングルトンインスタンスをエクスポート
export const openRouterService = new OpenRouterServiceImpl(); 