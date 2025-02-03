import type { MessageRole } from './common';

export interface BaseMessage {
  id: string;
  role: MessageRole;
  text: string;
  createdAt: string;
  images?: string[];
}

export interface UserMessage extends BaseMessage {
  role: 'user';
}

export interface AssistantMessage extends BaseMessage {
  role: 'assistant';
  streaming?: boolean;
  streamedText?: string;
}

export interface SystemMessage extends BaseMessage {
  role: 'system';
}

export interface ErrorMessage extends BaseMessage {
  role: 'error';
  code?: string;
}

export type Message = UserMessage | AssistantMessage | SystemMessage | ErrorMessage; 