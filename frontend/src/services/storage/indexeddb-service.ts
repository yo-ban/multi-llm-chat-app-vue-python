import localforage from 'localforage';
import type { Message } from '@/types/messages';
import type { Conversation } from '@/types/conversation';
import type { GlobalSettings } from '@/types/settings';
import type { UserDefinedPersona } from '@/types/personas';
import { MODELS } from '@/constants/models';

// localforageのキー定数
const CONVERSATION_LIST_KEY = 'conversationList';
const CURRENT_CONVERSATION_ID_KEY = 'currentConversationId';
const GLOBAL_SETTINGS_KEY = 'globalSettings';
const USER_PERSONAS_KEY = 'userDefinedPersonas';

/**
 * ストレージサービスのインターフェース
 * クライアントサイドストレージ（IndexedDB）へのアクセスを提供
 */
export interface StorageService {
  // 初期化
  initialize(): Promise<void>;
  
  // グローバル設定
  getGlobalSettings(): Promise<GlobalSettings>;
  saveGlobalSettings(settings: GlobalSettings): Promise<void>;
  
  // 会話関連
  getConversationList(): Promise<Conversation[]>;
  saveConversationList(conversations: Conversation[]): Promise<void>;
  getCurrentConversationId(): Promise<string | null>;
  saveCurrentConversationId(conversationId: string): Promise<void>;
  removeConversation(conversationId: string): Promise<void>;
  
  // ペルソナ関連
  getUserPersonas(): Promise<UserDefinedPersona[]>;
  saveUserPersonas(personas: UserDefinedPersona[]): Promise<void>;
  
  // メッセージ関連
  getConversationMessages(conversationId: string): Promise<Message[]>;
  addMessageToConversation(conversationId: string, message: Message): Promise<void>;
  updateConversationMessages(conversationId: string, messages: Message[]): Promise<void>;
}

/**
 * IndexedDBを使用したストレージサービスの実装
 */
class IndexedDBStorageService implements StorageService {
  /**
   * ストレージを初期化する
   */
  async initialize(): Promise<void> {
    await localforage.createInstance({
      name: 'chatApp',
      storeName: 'conversations',
    });
  }

  /**
   * グローバル設定を取得する
   * @returns グローバル設定オブジェクト
   */
  async getGlobalSettings(): Promise<GlobalSettings> {
    // 保存されている設定を取得
    const savedSettings = await localforage.getItem<GlobalSettings>(GLOBAL_SETTINGS_KEY);
    
    // デフォルト設定
    const defaultSettings: GlobalSettings = {
      apiKeys: Object.keys(MODELS).reduce((acc, vendor) => {
        acc[vendor] = '';
        return acc;
      }, {} as { [key: string]: string }),
      defaultTemperature: 0.7,
      defaultMaxTokens: 4096,
      defaultVendor: 'anthropic',
      defaultModel: MODELS.anthropic.CLAUDE_3_5_SONNET.id,
      defaultReasoningEffort: 'medium',
      openrouterModels: [],
      defaultWebSearch: false,
      titleGenerationVendor: 'anthropic',
      titleGenerationModel: MODELS.anthropic.CLAUDE_3_HAIKU.id
    };
    
    // 保存されている設定がない場合はデフォルト設定を返す
    if (!savedSettings) {
      return defaultSettings;
    }
    
    // 保存された設定から、現在のMODELSに存在するベンダーのAPIキーのみを抽出
    const validApiKeys = Object.keys(MODELS).reduce((acc, vendor) => {
      acc[vendor] = savedSettings.apiKeys[vendor] || '';
      return acc;
    }, {} as { [key: string]: string });
    
    // 設定をマージして返す
    return {
      ...defaultSettings,
      ...savedSettings,
      apiKeys: validApiKeys, // 有効なAPIキーで上書き
      // defaultVendorが無効な場合はデフォルト値を使用
      defaultVendor: Object.keys(MODELS).includes(savedSettings.defaultVendor) 
        ? savedSettings.defaultVendor 
        : defaultSettings.defaultVendor,
      // defaultModelが無効な場合はデフォルト値を使用
      defaultModel: Object.values(MODELS).some(models => 
        Object.values(models).some(model => model.id === savedSettings.defaultModel)
      ) ? savedSettings.defaultModel : defaultSettings.defaultModel,
      // OpenRouterモデルの設定を保持
      openrouterModels: savedSettings.openrouterModels || [],
    };
  }

  /**
   * グローバル設定を保存する
   * @param settings 保存する設定
   */
  async saveGlobalSettings(settings: GlobalSettings): Promise<void> {
    console.log('Saving global settings:', settings);
    // Deep clone the settings object to ensure all nested objects are properly copied
    const clonedSettings: GlobalSettings = {
      apiKeys: { ...settings.apiKeys },
      defaultTemperature: settings.defaultTemperature,
      defaultMaxTokens: settings.defaultMaxTokens,
      defaultVendor: settings.defaultVendor,
      defaultModel: settings.defaultModel,
      defaultReasoningEffort: settings.defaultReasoningEffort,
      openrouterModels: settings.openrouterModels.map(model => ({
        id: model.id,
        name: model.name,
        contextWindow: model.contextWindow,
        maxTokens: model.maxTokens,
        multimodal: model.multimodal,
        supportFunctionCalling: model.supportFunctionCalling || false
      })),
      defaultWebSearch: settings.defaultWebSearch,
      titleGenerationVendor: settings.titleGenerationVendor,
      titleGenerationModel: settings.titleGenerationModel
    };
    
    console.log('Cloned settings:', clonedSettings);
    try {
      await localforage.setItem(GLOBAL_SETTINGS_KEY, clonedSettings);
      console.log('Global settings saved successfully');
    } catch (error) {
      console.error('Error saving global settings:', error);
      throw error; // Re-throw the error to handle it in the calling code
    }
  }

  /**
   * 会話リストを取得する
   * @returns 会話オブジェクトの配列
   */
  async getConversationList(): Promise<Conversation[]> {
    const list = await localforage.getItem<Conversation[]>(CONVERSATION_LIST_KEY);
    return list || [];
  }

  /**
   * 会話リストを保存する
   * @param conversations 保存する会話リスト
   */
  async saveConversationList(conversations: Conversation[]): Promise<void> {
    // ディープクローンを作成して保存
    const clonedConversationList = conversations.map(conversation => ({
      ...conversation,
      settings: { ...conversation.settings },
      files: { ...conversation.files }
    }));
    await localforage.setItem(CONVERSATION_LIST_KEY, clonedConversationList);
  }

  /**
   * 現在の会話IDを取得する
   * @returns 現在の会話ID、または会話がない場合はnull
   */
  async getCurrentConversationId(): Promise<string | null> {
    return localforage.getItem<string>(CURRENT_CONVERSATION_ID_KEY);
  }

  /**
   * 現在の会話IDを保存する
   * @param conversationId 保存する会話ID
   */
  async saveCurrentConversationId(conversationId: string): Promise<void> {
    await localforage.setItem(CURRENT_CONVERSATION_ID_KEY, conversationId);
  }

  /**
   * ユーザー定義のペルソナを取得する
   * @returns ユーザー定義のペルソナの配列
   */
  async getUserPersonas(): Promise<UserDefinedPersona[]> {
    const personas = await localforage.getItem<UserDefinedPersona[]>(USER_PERSONAS_KEY);
    // ディープクローンを返す
    return personas ? personas.map(persona => ({ ...persona })) : [];
  }

  /**
   * ユーザー定義のペルソナを保存する
   * @param personas 保存するペルソナの配列
   */
  async saveUserPersonas(personas: UserDefinedPersona[]): Promise<void> {
    // ディープクローンを作成して保存
    const clonedPersonas = personas.map(persona => ({ ...persona }));
    await localforage.setItem(USER_PERSONAS_KEY, clonedPersonas);
  }
  
  /**
   * 特定の会話のメッセージを取得する
   * @param conversationId 会話ID
   * @returns メッセージの配列
   */
  async getConversationMessages(conversationId: string): Promise<Message[]> {
    const messages = await localforage.getItem<Message[]>(conversationId) || [];
    return messages.map((message: Message) => ({
      ...message,
      images: message.images || [],
    }));
  }

  /**
   * 会話にメッセージを追加する
   * @param conversationId 会話ID
   * @param message 追加するメッセージ
   */
  async addMessageToConversation(conversationId: string, message: Message): Promise<void> {
    const messages = await this.getConversationMessages(conversationId);
    // 画像配列のディープクローンを作成
    const clonedMessage = { 
      ...message, 
      images: message.images ? [...message.images] : [] 
    };
    messages.push(clonedMessage);
    await localforage.setItem(conversationId, messages);
  }

  /**
   * 会話のメッセージを更新する
   * @param conversationId 会話ID
   * @param messages 更新後のメッセージ配列
   */
  async updateConversationMessages(conversationId: string, messages: Message[]): Promise<void> {
    // すべてのメッセージのディープクローンを作成
    const clonedMessages = messages.map(message => ({
      ...message,
      images: message.images ? [...message.images] : [],
    }));
    await localforage.setItem(conversationId, clonedMessages);
  }

  /**
   * 会話のメッセージをストレージから削除する
   * @param conversationId 削除する会話ID
   */
  async removeConversation(conversationId: string): Promise<void> {
    await localforage.removeItem(conversationId);
  }
}

// シングルトンインスタンスをエクスポート
export const storageService: StorageService = new IndexedDBStorageService(); 