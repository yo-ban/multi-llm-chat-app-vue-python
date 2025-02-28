export interface ToolCall {
  type: string;
  status: 'start' | 'end';
  query?: string;
  url?: string;
}