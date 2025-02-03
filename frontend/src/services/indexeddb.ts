import localforage from 'localforage';
import type { Message } from '@/types/messages';
import type { Conversation } from '@/types/conversation';
import type { GlobalSettings } from '@/types/settings';
import type { UserDefinedPersona } from '@/types/personas';
import { MODELS } from '@/constants/models';

const CONVERSATION_LIST_KEY = 'conversationList';
const CURRENT_CONVERSATION_ID_KEY = 'currentConversationId';
const GLOBAL_SETTINGS_KEY = 'globalSettings';

export async function initializeIndexedDB() {
  await localforage.createInstance({
    name: 'chatApp',
    storeName: 'conversations',
  });
}


export async function getGlobalSettings(): Promise<GlobalSettings> {
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

  if (!savedSettings) {
    return defaultSettings;
  }

  // 保存された設定から、現在のMODELSに存在するベンダーのAPIキーのみを抽出
  const validApiKeys = Object.keys(MODELS).reduce((acc, vendor) => {
    acc[vendor] = savedSettings.apiKeys[vendor] || '';
    return acc;
  }, {} as { [key: string]: string });

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

export async function saveGlobalSettings(settings: GlobalSettings) {
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

export async function getConversationMessages(conversationId: string): Promise<Message[]> {
  const messages = await localforage.getItem<Message[]>(conversationId) || [];
  return messages.map((message: Message) => ({
    ...message,
    images: message.images || [],
  }));
}

export async function addMessageToConversation(conversationId: string, message: Message) {
  const messages = await getConversationMessages(conversationId);
  const clonedMessage = { ...message, images: message.images ? [...message.images] : [] };
  messages.push(clonedMessage);
  await localforage.setItem(conversationId, messages);
}

export async function updateConversationMessages(conversationId: string, messages: Message[]) {
  const clonedMessages = messages.map(message => ({
    ...message,
    images: message.images ? [...message.images] : [],
  }));
  await localforage.setItem(conversationId, clonedMessages);
}

export async function getConversationList(): Promise<Conversation[]> {
  const conversationList = await localforage.getItem<Conversation[]>(CONVERSATION_LIST_KEY);
  return conversationList || [];
}

export async function saveConversationList(conversationList: Conversation[]) {
  const clonedConversationList = conversationList.map(conversation => ({
    ...conversation,
    settings: { ...conversation.settings },
    files: { ...conversation.files }
  }));
  await localforage.setItem(CONVERSATION_LIST_KEY, clonedConversationList);
}

export async function getCurrentConversationId(): Promise<string | null> {
  return await localforage.getItem<string | null>(CURRENT_CONVERSATION_ID_KEY);
}

export async function setCurrentConversationId(conversationId: string | null) {
  await localforage.setItem(CURRENT_CONVERSATION_ID_KEY, conversationId);
}

export async function removeConversation(conversationId: string) {
  await localforage.removeItem(conversationId);
}

export async function getUserDefinedPersonas(): Promise<UserDefinedPersona[]> {
  const personas = await localforage.getItem<UserDefinedPersona[]>('userDefinedPersonas');
  return personas ? personas.map(persona => ({ ...persona })) : [];
}

export async function saveUserDefinedPersonas(personas: UserDefinedPersona[]) {
  const clonedPersonas = personas.map(persona => ({ ...persona }));
  await localforage.setItem('userDefinedPersonas', clonedPersonas);
}
