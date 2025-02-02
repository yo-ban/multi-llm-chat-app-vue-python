// src/services/conversation-export-import.ts
import { saveAs } from 'file-saver';
import type { Message } from '@/store/chat';
import type { Conversation } from '@/store/conversation';

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

export async function exportConversation(conversation: Conversation, messages: Message[]) {
  const exportData = {
    conversation: {
      conversationId: conversation.conversationId,
      title: conversation.title,
      createdAt: conversation.createdAt,
      updatedAt: conversation.updatedAt,
      system: conversation.system,
      personaId: conversation.personaId,
      settings: conversation.settings,
      historyLength: conversation.historyLength,
      files: conversation.files,
    },
    messages: messages,
  };

  const jsonString = JSON.stringify(exportData, null, 2);
  const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8' });

  if ('showSaveFilePicker' in window) {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: `${conversation.title}.json`,
        types: [{
          description: 'JSON file',
          accept: { 'application/json': ['.json'] },
        }],
      });
      if (handle) {
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
      }
    } catch (err: unknown) {
      if (typeof err === 'object' && err !== null && 'name' in err && (err as { name: string }).name !== 'AbortError') {
        console.error('Error saving file:', err);
        saveAs(blob, `${conversation.title}.json`);
      }
    }
  } else {
    saveAs(blob, `${conversation.title}.json`);
  }
}

export async function importConversation(file: File): Promise<{ conversation: Conversation; messages: Message[] }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const importedData = JSON.parse(event.target?.result as string);
        resolve(importedData);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = (error) => {
      reject(error);
    };
    reader.readAsText(file);
  });
}