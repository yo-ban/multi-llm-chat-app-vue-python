import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import localforage from 'localforage';
import type { APISettings } from '@/types/api';
import { storageService } from '@/services/storage/indexeddb-service';
import { conversationService } from '@/services/domain/conversation-service';
import type { Message } from '@/types/messages';
import { useSettingsStore } from '@/store/settings';
import type { Conversation, ConversationState, ConversationFolder } from '@/types/conversation';

const CONVERSATION_LIST_KEY = 'conversationList';
const CONVERSATION_FOLDERS_KEY = 'conversationFolders';

export const useConversationStore = defineStore('conversation', {
  state: (): ConversationState => ({
    currentConversationId: null,
    conversationList: [],
    folders: [],
  }),
  actions: {
    async initializeConversationStore() {
      // 会話リストの取得と初期化
      const savedConversations = await storageService.getConversationList();
      this.conversationList = savedConversations || [];
      
      // 現在の会話IDの取得と初期化
      this.currentConversationId = await storageService.getCurrentConversationId();
      
      // フォルダデータの読み込み
      try {
        const savedFolders = await localforage.getItem<ConversationFolder[]>(CONVERSATION_FOLDERS_KEY);
        // nullチェックと型変換を確実に行う
        this.folders = Array.isArray(savedFolders) ? savedFolders : [];
      } catch (error) {
        console.error('Error loading folders:', error);
        this.folders = [];
      }
    },

    async updateConversationList() {
      // 会話リストをシリアライズ可能な形に整形
      const serializableConversations = this.conversationList.map(conversation => {
        // 必要なプロパティのみを抽出したプレーンオブジェクトを作成
        return {
          conversationId: conversation.conversationId,
          title: conversation.title,
          createdAt: conversation.createdAt,
          updatedAt: conversation.updatedAt,
          system: conversation.system,
          personaId: conversation.personaId,
          settings: { ...conversation.settings },
          historyLength: conversation.historyLength,
          folderId: conversation.folderId,
          files: conversation.files ? { ...conversation.files } : undefined
        };
      });
      
      // シリアライズ可能な形にしたデータを保存
      await localforage.setItem(CONVERSATION_LIST_KEY, serializableConversations);
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
        
        // Ensure we have a valid default model, validate if using OpenRouter
        let modelId = settingsStore.defaultModel;
        if (settingsStore.defaultVendor === 'openrouter') {
          modelId = settingsStore.validateModelSelection(modelId, settingsStore.defaultVendor);
        }
        
        const model = settingsStore.getModelById(modelId);
        const newConversation: Conversation = {
          conversationId: newConversationId,
          title: 'New Chat',
          createdAt: nowDate,
          updatedAt: nowDate,
          system: '',
          settings: {
            model: modelId,
            maxTokens: settingsStore.defaultMaxTokens,
            vendor: settingsStore.defaultVendor,
            temperature: model?.unsupportsTemperature ? undefined : settingsStore.defaultTemperature,
            reasoningEffort: settingsStore.getEffectiveReasoningEffort(modelId),
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
        // If this is an OpenRouter vendor, validate the model selection
        if (settings.vendor === 'openrouter') {
          const settingsStore = useSettingsStore();
          settings.model = settingsStore.validateModelSelection(settings.model, settings.vendor);
        }
        
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

    // フォルダ関連のアクション
    async createFolder(name: string) {
      const folderId = `folder-${uuidv4()}`;
      const newFolder: ConversationFolder = {
        id: folderId,
        name,
        isExpanded: true
      };
      
      // フォルダを先頭に追加
      this.folders.unshift(newFolder);
      await this.saveFolders();
      return folderId;
    },
    
    async updateFolderName(folderId: string, newName: string) {
      const folderIndex = this.folders.findIndex(f => f.id === folderId);
      if (folderIndex !== -1) {
        this.folders[folderIndex].name = newName;
        await this.saveFolders();
      }
    },
    
    async deleteFolder(folderId: string) {
      // フォルダに属する会話をルートに戻す
      this.conversationList.forEach(conversation => {
        if (conversation.folderId === folderId) {
          conversation.folderId = null;
        }
      });
      
      this.folders = this.folders.filter(f => f.id !== folderId);
      await this.saveFolders();
      await this.updateConversationList();
    },
    
    async toggleFolderExpanded(folderId: string) {
      const folderIndex = this.folders.findIndex(f => f.id === folderId);
      if (folderIndex !== -1) {
        this.folders[folderIndex].isExpanded = !this.folders[folderIndex].isExpanded;
        await this.saveFolders();
      }
    },
    
    async moveConversationToFolder(conversationId: string, folderId: string | null) {
      const conversationIndex = this.conversationList.findIndex(c => c.conversationId === conversationId);
      if (conversationIndex !== -1) {
        this.conversationList[conversationIndex].folderId = folderId;
        await this.updateConversationList();
      }
    },
    
    async saveFolders() {
      // フォルダデータをシリアライズ可能な形に整形
      const serializableFolders = this.folders.map(folder => ({
        id: folder.id,
        name: folder.name,
        isExpanded: folder.isExpanded
      }));
      
      // シリアライズ可能な形にしたデータを保存
      await localforage.setItem(CONVERSATION_FOLDERS_KEY, serializableFolders);
    },
  },
  getters: {
    // フォルダ内の会話を取得するゲッター
    getConversationsInFolder: (state) => (folderId: string | null) => {
      return state.conversationList.filter(conversation => conversation.folderId === folderId);
    },
    
    // ルート（フォルダに属さない）会話を取得するゲッター
    getRootConversations: (state) => {
      return state.conversationList.filter(conversation => !conversation.folderId);
    }
  }
});