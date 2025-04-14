import localforage from 'localforage';
import type { Message } from '@/types/messages';
import type { Conversation, ConversationFolder } from '@/types/conversation';
import type { GlobalSettings } from '@/types/settings';
import type { UserDefinedPersona } from '@/types/personas';
// import { MODELS } from '@/constants/models';

// --- Create dedicated localforage instances for each store ---
const settingsStore = localforage.createInstance({ name: 'chatAppDB', storeName: 'settings' });
const personasStore = localforage.createInstance({ name: 'chatAppDB', storeName: 'personas' });
const foldersStore = localforage.createInstance({ name: 'chatAppDB', storeName: 'folders' });
const conversationsMetaStore = localforage.createInstance({ name: 'chatAppDB', storeName: 'conversationsMeta' });
const conversationMessagesStore = localforage.createInstance({ name: 'chatAppDB', storeName: 'conversationMessages' });
const appStateStore = localforage.createInstance({ name: 'chatAppDB', storeName: 'appState' }); // For currentConversationId

const CURRENT_CONVERSATION_ID_KEY = 'currentConversationId';
const GLOBAL_SETTINGS_KEY = 'globalSettingsData';
export const MIGRATION_V1_TO_V2_COMPLETE_KEY = 'migrationV1ToV2Complete'; // Export the key

// Helper function to get all items from a store instance
async function getAllItems<T>(store: LocalForage): Promise<T[]> {
  const items: T[] = [];
  try {
    await store.iterate<T, void>((value, key) => {
      items.push(value);
    });
    return items;
  } catch (error) {
    console.error(`Error iterating over store ${store.config().storeName}:`, error);
    return []; // Return empty array on error
  }
}

/**
 * Updated StorageService Interface
 */
export interface StorageService {
  // Global Settings (using a fixed key)
  getGlobalSettings(): Promise<GlobalSettings | null>;
  saveGlobalSettings(settings: GlobalSettings): Promise<void>;

  // Personas (CRUD operations)
  getAllPersonas(): Promise<UserDefinedPersona[]>;
  savePersona(persona: UserDefinedPersona): Promise<void>;
  deletePersona(personaId: string): Promise<void>;

  // Folders (CRUD operations)
  getAllFolders(): Promise<ConversationFolder[]>;
  saveFolder(folder: ConversationFolder): Promise<void>;
  deleteFolder(folderId: string): Promise<void>;

  // Conversation Metadata (CRUD operations)
  getAllConversationMetas(): Promise<Conversation[]>; // Returns array of Conversation objects (meta only)
  saveConversationMeta(conversationMeta: Omit<Conversation, 'messages'>): Promise<void>; // Accepts meta only
  deleteConversationMeta(conversationId: string): Promise<void>;

  // Conversation Messages (CRUD operations)
  getConversationMessages(conversationId: string): Promise<Message[]>;
  saveConversationMessages(conversationId: string, messages: Message[]): Promise<void>; // Replaces updateConversationMessages
  deleteConversationMessages(conversationId: string): Promise<void>; // Replaces removeConversation

  // Combined Conversation Deletion
  deleteConversation(conversationId: string): Promise<void>; // Deletes both meta and messages

  // Current Conversation ID
  getCurrentConversationId(): Promise<string | null>;
  saveCurrentConversationId(conversationId: string | null): Promise<void>; // Allow saving null

  // Migration Status
  getMigrationStatus(key: string): Promise<boolean>;
  setMigrationStatus(key: string, status: boolean): Promise<void>;
}

/**
 * Updated IndexedDBStorageService Implementation
 */
class IndexedDBStorageService implements StorageService {

  async getGlobalSettings(): Promise<GlobalSettings | null> {
    try {
      // Default settings logic should ideally be in the settings store, 
      // this service should just load what's saved or null.
      const settings = await settingsStore.getItem<GlobalSettings>(GLOBAL_SETTINGS_KEY);
      return settings; // Return null if not found
    } catch (error) {
      console.error('Error getting global settings:', error);
      return null;
    }
  }

  async saveGlobalSettings(settings: GlobalSettings): Promise<void> {
    try {
      // Create a deep clone of the settings object
      const settingsToSave = JSON.parse(JSON.stringify(settings));
      await settingsStore.setItem(GLOBAL_SETTINGS_KEY, settingsToSave);
    } catch (error) {
      console.error('Error saving global settings:', error);
    }
  }

  async getAllPersonas(): Promise<UserDefinedPersona[]> {
    return getAllItems<UserDefinedPersona>(personasStore);
  }

  async savePersona(persona: UserDefinedPersona): Promise<void> {
    try {
      // Create a deep clone of the persona object
      const personaToSave = JSON.parse(JSON.stringify(persona));
      await personasStore.setItem(persona.id, personaToSave);
    } catch (error) {
      console.error(`Error saving persona ${persona.id}:`, error);
    }
  }

  async deletePersona(personaId: string): Promise<void> {
    try {
      await personasStore.removeItem(personaId);
    } catch (error) {
      console.error(`Error deleting persona ${personaId}:`, error);
    }
  }

  async getAllFolders(): Promise<ConversationFolder[]> {
    return getAllItems<ConversationFolder>(foldersStore);
  }

  async saveFolder(folder: ConversationFolder): Promise<void> {
    try {
      // Create a deep clone of the folder object
      const folderToSave = JSON.parse(JSON.stringify(folder));
      await foldersStore.setItem(folder.id, folderToSave);
    } catch (error) {
      console.error(`Error saving folder ${folder.id}:`, error);
    }
  }

  async deleteFolder(folderId: string): Promise<void> {
    try {
      await foldersStore.removeItem(folderId);
    } catch (error) {
      console.error(`Error deleting folder ${folderId}:`, error);
    }
  }

  async getAllConversationMetas(): Promise<Conversation[]> {
    // Cast needed as we store Omit<Conversation, 'messages'> but return Conversation[]
    const metas = await getAllItems<Omit<Conversation, 'messages'>>(conversationsMetaStore);
    // Ensure the shape matches Conversation (even if messages isn't present)
    return metas.map(meta => meta as Conversation);
  }

  async saveConversationMeta(conversationMeta: Omit<Conversation, 'messages'>): Promise<void> {
    try {
      // Create a deep clone of the conversation meta object
      const metaToSave = JSON.parse(JSON.stringify(conversationMeta));
      await conversationsMetaStore.setItem(conversationMeta.conversationId, metaToSave);
    } catch (error) {
      console.error(`Error saving conversation meta ${conversationMeta.conversationId}:`, error);
    }
  }

  async deleteConversationMeta(conversationId: string): Promise<void> {
    try {
      await conversationsMetaStore.removeItem(conversationId);
    } catch (error) {
      console.error(`Error deleting conversation meta ${conversationId}:`, error);
    }
  }

  async getConversationMessages(conversationId: string): Promise<Message[]> {
    try {
      const messages = await conversationMessagesStore.getItem<Message[]>(conversationId);
      return messages || [];
    } catch (error) {
      console.error(`Error getting messages for conversation ${conversationId}:`, error);
      return [];
    }
  }

  async saveConversationMessages(conversationId: string, messages: Message[]): Promise<void> {
    try {
      // Create a deep clone of the messages array
      const messagesToSave = JSON.parse(JSON.stringify(messages));
      await conversationMessagesStore.setItem(conversationId, messagesToSave);
    } catch (error) {
      console.error(`Error saving messages for conversation ${conversationId}:`, error);
    }
  }

  async deleteConversationMessages(conversationId: string): Promise<void> {
    try {
      await conversationMessagesStore.removeItem(conversationId);
    } catch (error) {
      console.error(`Error deleting messages for conversation ${conversationId}:`, error);
    }
  }

  async deleteConversation(conversationId: string): Promise<void> {
    // Delete both meta and messages
    await this.deleteConversationMeta(conversationId);
    await this.deleteConversationMessages(conversationId);
  }

  async getCurrentConversationId(): Promise<string | null> {
    try {
      return await appStateStore.getItem<string>(CURRENT_CONVERSATION_ID_KEY);
    } catch (error) {
      console.error('Error getting current conversation ID:', error);
      return null;
    }
  }

  async saveCurrentConversationId(conversationId: string | null): Promise<void> {
    try {
      if (conversationId === null) {
        await appStateStore.removeItem(CURRENT_CONVERSATION_ID_KEY);
      } else {
        await appStateStore.setItem(CURRENT_CONVERSATION_ID_KEY, conversationId);
      }
    } catch (error) {
      console.error('Error saving current conversation ID:', error);
    }
  }

  // --- Migration Status Methods ---
  async getMigrationStatus(key: string): Promise<boolean> {
    try {
      const status = await appStateStore.getItem<boolean>(key);
      return status === true; // Return true only if explicitly set to true
    } catch (error) {
      console.error(`Error getting migration status for key ${key}:`, error);
      return false; // Assume not migrated on error
    }
  }

  async setMigrationStatus(key: string, status: boolean): Promise<void> {
    try {
      await appStateStore.setItem(key, status);
    } catch (error) {
      console.error(`Error setting migration status for key ${key}:`, error);
      // Decide if we need to re-throw or handle this
    }
  }
}

// Singleton instance export
export const storageService: StorageService = new IndexedDBStorageService(); 