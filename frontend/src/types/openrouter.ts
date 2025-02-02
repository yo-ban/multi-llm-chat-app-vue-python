export interface OpenRouterModelPricing {
    prompt: string;
    completion: string;
    image: string;
    request: string;
}

export interface OpenRouterModelArchitecture {
    modality: string;
    tokenizer: string;
    instruct_type: string | null;
}

export interface OpenRouterModelTopProvider {
    context_length: number;
    max_completion_tokens: number;
    is_moderated: boolean;
}

export interface OpenRouterModel {
    id: string;
    name: string;
    created: number;
    description?: string;
    context_length: number;
    architecture: OpenRouterModelArchitecture;
    pricing: OpenRouterModelPricing;
    top_provider: OpenRouterModelTopProvider;
    per_request_limits: any | null;
}

export interface OpenRouterModelsResponse {
    data: OpenRouterModel[];
} 