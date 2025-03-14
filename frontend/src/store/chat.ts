import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import type { Message } from '@/types/messages';
import type { MessageRole } from '@/types/common';

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [] as Message[],
  }),
  actions: {
    async addMessage(role: MessageRole, text: string, images?: string[], streaming = false) {
      const newMessage: Message = {
        id: `msg-${uuidv4()}`,
        role,
        text,
        createdAt: new Date().toISOString(),
        ...(role === 'user' && images ? { images } : {}),
        ...(role === 'assistant' ? { streaming, streamedText: streaming ? '' : undefined } : {}),
      };
      this.messages.push(newMessage as Message);
    },
    updateStreamedMessage(text: string, image?: string) {
      const lastMessage = this.messages[this.messages.length - 1];
      if (lastMessage && lastMessage.role === 'assistant' && 'streaming' in lastMessage && lastMessage.streaming) {
        lastMessage.streamedText = text;
        if (image) {
          if (!lastMessage.images) {
            lastMessage.images = [];
          }
          lastMessage.images.push(image);
        }
      }
    },
    stopStreaming() {
      for (let i = this.messages.length - 1; i >= 0; i--) {
        const message = this.messages[i];
        if (message.role === 'assistant' && 'streaming' in message && message.streaming) {
          message.text = message.streamedText || '';
          message.streamedText = undefined;
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