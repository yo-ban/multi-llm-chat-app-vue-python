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
  folderId?: string | null;
  files?: { [key: string]: string };
}

export interface ConversationFolder {
  id: string;
  name: string;
  isExpanded: boolean;
}

export interface ConversationState {
  currentConversationId: string | null;
  conversationList: Conversation[];
  folders: ConversationFolder[];
} 