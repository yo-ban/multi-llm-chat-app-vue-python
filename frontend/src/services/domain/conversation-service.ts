import { saveAs } from 'file-saver';
import type { Message } from '@/types/messages';
import type { Conversation } from '@/types/conversation';

declare global {
  interface Window {
    showSaveFilePicker: (options: SaveFilePickerOptions) => Promise<FileSystemFileHandle>;
  }
}

interface SaveFilePickerOptions {
  types?: {
    description?: string;
    accept?: { [mimeType: string]: string[] };
  }[];
  excludeAcceptAllOption?: boolean;
  suggestedName?: string;
}

/**
 * 会話サービスのインターフェース
 * 会話データの操作やインポート/エクスポートを担当
 */
export interface ConversationService {
  /**
   * 会話をJSONファイルとしてエクスポートする
   * @param conversation 会話データ
   * @param messages メッセージリスト
   */
  exportConversation(conversation: Conversation, messages: Message[]): Promise<void>;
  
  /**
   * JSONファイルから会話をインポートする
   * @param file インポートするJSONファイル
   * @returns 会話データとメッセージのセット
   */
  importConversation(file: File): Promise<{ conversation: Conversation; messages: Message[] }>;
}

/**
 * 会話サービスの実装クラス
 */
class ConversationServiceImpl implements ConversationService {
  /**
   * 会話をJSONファイルとしてエクスポートする
   * @param conversation 会話データ
   * @param messages メッセージリスト
   */
  async exportConversation(conversation: Conversation, messages: Message[]): Promise<void> {
    const exportData = {
      conversation: {
        conversationId: conversation.conversationId,
        title: conversation.title,
        createdAt: conversation.createdAt,
        updatedAt: conversation.updatedAt,
        system: conversation.system,
        personaId: conversation.personaId,
        settings: conversation.settings,
        files: conversation.files
      },
      messages
    };
    
    const jsonString = JSON.stringify(exportData, null, 2);
    const fileName = `${conversation.title || 'conversation'}.json`;
    
    // File System Access APIが利用可能な場合
    if ('showSaveFilePicker' in window) {
      try {
        const options: SaveFilePickerOptions = {
          suggestedName: fileName,
          types: [
            {
              description: 'JSON File',
              accept: { 'application/json': ['.json'] }
            }
          ]
        };
        
        const fileHandle = await window.showSaveFilePicker(options);
        const writable = await fileHandle.createWritable();
        await writable.write(jsonString);
        await writable.close();
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          console.error('Error saving file with File System Access API:', err);
          // フォールバックとしてfile-saverを使用
          this.saveWithFileSaver(jsonString, fileName);
        }
      }
    } else {
      // File System Access APIが利用できない場合はfile-saverを使用
      this.saveWithFileSaver(jsonString, fileName);
    }
  }
  
  /**
   * file-saverを使用してファイルを保存する
   * @param content ファイルの内容
   * @param fileName ファイル名
   */
  private saveWithFileSaver(content: string, fileName: string): void {
    const blob = new Blob([content], { type: 'application/json' });
    saveAs(blob, fileName);
  }
  
  /**
   * JSONファイルから会話をインポートする
   * @param file インポートするJSONファイル
   * @returns 会話データとメッセージのセット
   */
  async importConversation(file: File): Promise<{ conversation: Conversation; messages: Message[] }> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target?.result as string);
          
          if (!data.conversation || !data.messages) {
            throw new Error('Invalid conversation file format');
          }
          
          resolve({
            conversation: data.conversation,
            messages: data.messages
          });
        } catch (error) {
          reject(new Error('Could not parse the conversation file. Ensure it is a valid JSON file.'));
        }
      };
      
      reader.onerror = () => {
        reject(new Error('Error reading the file'));
      };
      
      reader.readAsText(file);
    });
  }
}

// シングルトンインスタンスをエクスポート
export const conversationService = new ConversationServiceImpl(); 