import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';

export interface Message {
  id: string;
  role: string;
  text: string;
  images?: string[] | null;
  streaming?: boolean;
  streamedText?: string;
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as Message[],
  }),
  actions: {
    async addMessage(role: string, text: string, images?: string[], streaming = false) {
      const newMessage: Message = {
        id: `msg-${uuidv4()}`,
        role,
        text,
        images,
        streaming,
        streamedText: role === 'assistant' ? '' : undefined,
      };
      this.messages.push(newMessage);
    },
    updateStreamedMessage(text: string) {
      const lastMessage = this.messages[this.messages.length - 1];
      if (lastMessage && lastMessage.streaming) {
        lastMessage.streamedText = text;
      }
    },
    stopStreaming() {
      for (let i = this.messages.length - 1; i >= 0; i--) {
        const message = this.messages[i];
        if (message.streaming) {
          if (message.role === 'assistant') {
            message.text = message.streamedText || '';
            message.streamedText = undefined;
          }
          message.streaming = false;
        } else {
          break;
        }
      }
    },
    async updateMessage(id: string, text: string) {
      const messageIndex = this.messages.findIndex(message => message.id === id);
      if (messageIndex !== -1) {
        this.messages[messageIndex] = {
          ...this.messages[messageIndex],
          text,
        };
      }
    },
    deleteMessage(id: string) {
      this.messages = this.messages.filter(message => message.id !== id);
    },
  },
});