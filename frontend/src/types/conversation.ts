import type { APISettings } from './api';

export interface Conversation {
  conversationId: string;
  title: string;
  createdAt: string;
  updatedAt?: string;
  system?: string;
  personaId?: string;
  settings: APISettings;
  historyLength: number;
  files?: { [key: string]: string };
}

export interface ConversationState {
  currentConversationId: string | null;
  conversationList: Conversation[];
} 