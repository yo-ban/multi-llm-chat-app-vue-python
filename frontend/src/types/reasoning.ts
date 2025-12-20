export type ReasoningParameterType = 'effort' | 'budget' | 'level';

export type ReasoningEffortType = 'low' | 'medium' | 'high';

export type ReasoningLevelType = 'low' | 'high';

export interface EffortReasoningParams {
  type: 'effort';
  effort: ReasoningEffortType;
}

export interface BudgetReasoningParams {
  type: 'budget';
  budgetTokenLimit: number;
  budgetTokens: number;
}

export interface LevelReasoningParams {
  type: 'level';
  level: ReasoningLevelType;
  levels?: ReasoningLevelType[];
}

export type ReasoningParameters = EffortReasoningParams | BudgetReasoningParams | LevelReasoningParams;
