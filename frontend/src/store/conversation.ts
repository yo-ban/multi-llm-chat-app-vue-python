import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import localforage from 'localforage';
import type { APISettings } from '@/types/api';
import {
  getConversationList,
  saveConversationList,
  getCurrentConversationId,
  setCurrentConversationId,
  removeConversation,
  updateConversationMessages
} from '@/services/indexeddb';
import { exportConversation, importConversation } from '@/services/conversation-export-import';
import type { Message } from '@/store/chat';
import { useSettingsStore } from '@/store/settings';

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

const CONVERSATION_LIST_KEY = 'conversationList';

export const useConversationStore = defineStore('conversation', {
  state: (): ConversationState => ({
    currentConversationId: null,
    conversationList: [],
  }),
  actions: {
    async initializeConversationStore() {
      this.conversationList = await getConversationList();
      this.currentConversationId = await getCurrentConversationId();
    },

    async updateConversationList() {
      const clonedConversationList = this.conversationList.map(conversation => ({
        ...conversation,
        settings: { ...conversation.settings },
      }));
      await localforage.setItem(CONVERSATION_LIST_KEY, clonedConversationList);
    },

    async createNewConversation() {
      const existingEmptyConversation = this.conversationList.find(
        (conversation) =>
          conversation.title === 'New Chat' && conversation.createdAt === conversation.updatedAt
      );
    
      if (existingEmptyConversation) {
        this.currentConversationId = existingEmptyConversation.conversationId;
        await setCurrentConversationId(this.currentConversationId);
      } else {
        const newConversationId = `conv-${uuidv4()}`;
        const nowDate = new Date().toISOString();
        const settingsStore = useSettingsStore();
        const model = settingsStore.getModelById(settingsStore.defaultModel);
        const newConversation: Conversation = {
          conversationId: newConversationId,
          title: 'New Chat',
          createdAt: nowDate,
          updatedAt: nowDate,
          system: '',
          settings: {
            model: settingsStore.defaultModel,
            maxTokens: settingsStore.defaultMaxTokens,
            vendor: settingsStore.defaultVendor,
            temperature: model?.unsupportsTemperature ? undefined : settingsStore.defaultTemperature,
            reasoningEffort: settingsStore.getEffectiveReasoningEffort(settingsStore.defaultModel),
            websearch: settingsStore.defaultWebSearch,
          },
          historyLength: 0,
        };
        this.conversationList.unshift(newConversation);
        await saveConversationList(this.conversationList);
        this.currentConversationId = newConversationId;
        await setCurrentConversationId(this.currentConversationId);
      }
    },
        
    async selectConversation(conversationId: string) {
      this.currentConversationId = conversationId;
      await setCurrentConversationId(this.currentConversationId);
    },

    async updateConversationTitle(conversationId: string, newTitle: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].title = newTitle;
        await saveConversationList(this.conversationList);
      }
    },
    
    async updateConversationSettings(conversationId: string, settings: APISettings) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].settings = settings;
        await saveConversationList(this.conversationList);
      }
    },

    async updateConversationSystem(conversationId: string, system: string, personaId: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].system = system;
        this.conversationList[conversationIndex].personaId = personaId;
        await saveConversationList(this.conversationList);
      }
    },
    
    async updateConversationHistoryLength(conversationId: string, historyLength: number) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].historyLength = historyLength;
        await saveConversationList(this.conversationList);
      }
    },

    async updateConversationDate(conversationId: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].updatedAt = new Date().toISOString();
        await saveConversationList(this.conversationList);
      }
    },

    async updateConversationFiles(conversationId: string, files: { [key: string]: string }) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].files = files;
        await saveConversationList(this.conversationList);
      }
    },

    async deleteConversationFile(conversationId: string, fileName: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        const conversation = this.conversationList[conversationIndex];
        if (conversation.files) {
          delete conversation.files[fileName];
          await saveConversationList(this.conversationList);
        }
      }
    },

    async deleteConversation(conversationId: string) {
      this.conversationList = this.conversationList.filter(c => c.conversationId !== conversationId);
      await saveConversationList(this.conversationList);
      await removeConversation(conversationId);

      if (this.currentConversationId === conversationId) {
        if (this.conversationList.length === 0){
          await this.createNewConversation()
        } else { 
          this.currentConversationId = this.conversationList[0].conversationId;
          await setCurrentConversationId(this.currentConversationId);
        }
      }
    },

    async exportConversation(messages: Message[]) {
      const currentConversation = this.conversationList.find(
        conversation => conversation.conversationId === this.currentConversationId
      );

      if (currentConversation) {
        await exportConversation(currentConversation, messages);
      }
    },

    async importConversation(file: File) {
      try {
        const importedData = await importConversation(file);
        const importedConversation = importedData.conversation;
        const importedMessages = importedData.messages;
    
        // 新しい会話IDを生成
        const newConversationId = `conv-${uuidv4()}`
    
        // インポートされた会話に新しいIDを割り当てる
        const newConversation: Conversation = {
          ...importedConversation,
          conversationId: newConversationId,
        };
    
        // 会話リストに新しい会話を追加
        this.conversationList.unshift(newConversation);
    
        // メッセージをIndexedDBに保存
        await updateConversationMessages(newConversationId, importedMessages);
        await saveConversationList(this.conversationList);
    
        // 現在の会話を選択
        this.currentConversationId = newConversationId;
      } catch (error) {
        console.error('Error importing conversation:', error);
        throw error;
      }
    },
  },
});