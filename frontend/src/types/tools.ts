export interface ToolCall {
  type: string;
  status: 'start' | 'end';
  input?: Record<string, any>;
}