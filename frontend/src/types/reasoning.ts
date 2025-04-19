export type ReasoningParameterType = 'effort' | 'budget';

export type ReasoningEffortType = 'low' | 'medium' | 'high';

export interface EffortReasoningParams {
  type: 'effort';
  effort: ReasoningEffortType;
}

export interface BudgetReasoningParams {
  type: 'budget';
  budgetTokenLimit: number;
  budgetTokens: number;
}

export type ReasoningParameters = EffortReasoningParams | BudgetReasoningParams;