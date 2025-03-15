import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import localforage from 'localforage';
import type { APISettings } from '@/types/api';
import { storageService } from '@/services/storage/indexeddb-service';
import { conversationService } from '@/services/domain/conversation-service';
import type { Message } from '@/types/messages';
import { useSettingsStore } from '@/store/settings';
import type { Conversation, ConversationState } from '@/types/conversation';

const CONVERSATION_LIST_KEY = 'conversationList';

export const useConversationStore = defineStore('conversation', {
  state: (): ConversationState => ({
    currentConversationId: null,
    conversationList: [],
  }),
  actions: {
    async initializeConversationStore() {
      this.conversationList = await storageService.getConversationList();
      this.currentConversationId = await storageService.getCurrentConversationId();
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
        await storageService.saveCurrentConversationId(this.currentConversationId);
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
            multimodal: model?.multimodal ?? false,
            imageGeneration: model?.imageGeneration ?? false,
          },
          historyLength: 0,
        };
        this.conversationList.unshift(newConversation);
        await storageService.saveConversationList(this.conversationList);
        this.currentConversationId = newConversationId;
        await storageService.saveCurrentConversationId(this.currentConversationId);
      }
    },
        
    async selectConversation(conversationId: string) {
      this.currentConversationId = conversationId;
      await storageService.saveCurrentConversationId(this.currentConversationId);
    },

    async updateConversationTitle(conversationId: string, newTitle: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].title = newTitle;
        await storageService.saveConversationList(this.conversationList);
      }
    },
    
    async updateConversationSettings(conversationId: string, settings: APISettings) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].settings = settings;
        await storageService.saveConversationList(this.conversationList);
      }
    },

    async updateConversationSystem(conversationId: string, system: string, personaId: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].system = system;
        this.conversationList[conversationIndex].personaId = personaId;
        await storageService.saveConversationList(this.conversationList);
      }
    },
    
    async updateConversationHistoryLength(conversationId: string, historyLength: number) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].historyLength = historyLength;
        await storageService.saveConversationList(this.conversationList);
      }
    },

    async updateConversationDate(conversationId: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].updatedAt = new Date().toISOString();
        await storageService.saveConversationList(this.conversationList);
      }
    },

    async updateConversationFiles(conversationId: string, files: { [key: string]: string }) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].files = files;
        await storageService.saveConversationList(this.conversationList);
      }
    },

    async deleteConversationFile(conversationId: string, fileName: string) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        const conversation = this.conversationList[conversationIndex];
        if (conversation.files) {
          delete conversation.files[fileName];
          await storageService.saveConversationList(this.conversationList);
        }
      }
    },

    async deleteConversation(conversationId: string) {
      this.conversationList = this.conversationList.filter(c => c.conversationId !== conversationId);
      await storageService.saveConversationList(this.conversationList);
      await storageService.removeConversation(conversationId);

      if (this.currentConversationId === conversationId) {
        if (this.conversationList.length === 0){
          await this.createNewConversation()
        } else { 
          this.currentConversationId = this.conversationList[0].conversationId;
          await storageService.saveCurrentConversationId(this.currentConversationId);
        }
      }
    },

    async exportConversation(messages: Message[]) {
      const currentConversation = this.conversationList.find(
        conversation => conversation.conversationId === this.currentConversationId
      );

      if (currentConversation) {
        await conversationService.exportConversation(currentConversation, messages);
      }
    },

    async importConversation(file: File) {
      try {
        const importedData = await conversationService.importConversation(file);
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
        await storageService.updateConversationMessages(newConversationId, importedMessages);
        await storageService.saveConversationList(this.conversationList);
    
        // 現在の会話を選択
        this.currentConversationId = newConversationId;
      } catch (error) {
        console.error('Error importing conversation:', error);
        throw error;
      }
    },

    async duplicateConversation(conversationId: string) {
      try {
        // 複製する会話を検索
        const conversationToDuplicate = this.conversationList.find(
          c => c.conversationId === conversationId
        );
        
        if (!conversationToDuplicate) {
          throw new Error(`Conversation with ID ${conversationId} not found`);
        }
        
        // 新しい会話IDを生成
        const newConversationId = `conv-${uuidv4()}`;
        const nowDate = new Date().toISOString();
        
        // 会話のディープコピーを作成
        const duplicatedConversation: Conversation = {
          ...JSON.parse(JSON.stringify(conversationToDuplicate)), // ディープコピー
          conversationId: newConversationId,
          title: `Copy-${nowDate} ${conversationToDuplicate.title}`,
          createdAt: nowDate,
          updatedAt: nowDate
        };
        
        // 複製した会話をリストに追加
        this.conversationList.unshift(duplicatedConversation);
        
        // 会話リストの変更を保存
        await storageService.saveConversationList(this.conversationList);
        
        // 元の会話のメッセージを取得
        const messages = await storageService.getConversationMessages(conversationId);
        
        // メッセージもコピーして保存（もし存在すれば）
        if (messages && messages.length > 0) {
          await storageService.updateConversationMessages(newConversationId, JSON.parse(JSON.stringify(messages)));
        }
        
        // 新しい会話を選択して返す
        this.currentConversationId = newConversationId;
        await storageService.saveCurrentConversationId(this.currentConversationId);
        
        return newConversationId;
      } catch (error) {
        console.error('Error duplicating conversation:', error);
        throw error;
      }
    },
  },
});