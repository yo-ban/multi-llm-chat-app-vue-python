// Tool input types - covers common JSON-serializable types
export type ToolInputValue = string | number | boolean | null | ToolInputValue[] | { [key: string]: ToolInputValue };

export interface ToolCall {
  type: string;
  status: 'start' | 'end';
  input?: Record<string, ToolInputValue>;
}