import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';
import type { Message } from '@/types/messages';
import type { MessageRole } from '@/types/common';
import { storageService } from '@/services/storage/indexeddb-service';

export const useChatStore = defineStore('chat', {
  state: (): { messages: Message[] } => ({
    messages: [],
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
      this.messages.push(newMessage);
    },
    updateStreamedMessage(text: string, image?: string) {
      const lastMessage = this.messages[this.messages.length - 1];
      if (lastMessage && lastMessage.role === 'assistant' && 'streaming' in lastMessage && lastMessage.streaming) {
        lastMessage.streamedText = text;
        if (image) {
          if (!lastMessage.images) {
            lastMessage.images = [];
          }
          lastMessage.images = [...lastMessage.images, image];
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
    async deleteMessage(id: string) {
      const messageIndex = this.messages.findIndex(message => message.id === id);
      if (messageIndex !== -1) {
        const role = this.messages[messageIndex].role;

        if (role === 'user') {
          this.messages.splice(messageIndex, 2);
        } else if (role === 'assistant') {
          this.messages.splice(messageIndex - 1, 2);
        } else if (role === "error") {
          this.messages.splice(messageIndex, 1);
        }
      }
    },
    async deleteImage(messageId: string, imageIndex: number) {
      const messageIndex = this.messages.findIndex(message => message.id === messageId);
      if (messageIndex !== -1) {
        const message = this.messages[messageIndex];
        if (message.images && message.images.length > imageIndex) {
          message.images = message.images.filter((_, idx) => idx !== imageIndex);
        }
      }
    },
    async saveMessages(conversationId: string) {
      try {
        if (conversationId) {
          await storageService.saveConversationMessages(conversationId, this.messages);
        } else {
          console.error('Conversation ID is undefined');
        }
      } catch (error) {
        console.error('Error saving messages:', error);
        throw error;
      }
    },
    async loadMessages(conversationId: string) {
      try {
        const messages = await storageService.getConversationMessages(conversationId);
        this.messages = messages;
      } catch (error) {
        console.error('Error loading messages:', error);
        this.messages = [];
        throw error;
      }
    },
    setMessages(messages: Message[]) {
      this.messages = messages;
    },
    clearMessages() {
      this.messages = [];
    },
    async resendMessage(messageId: string): Promise<Message | null> {
      const messageIndex = this.messages.findIndex(message => message.id === messageId);
      if (messageIndex === -1) return null;

      // 再送信するメッセージを取得
      const messageToResend = this.messages[messageIndex];
      
      // メッセージ以降を削除（再送信するメッセージを含む）
      this.messages = this.messages.slice(0, messageIndex);
      
      // 新しいメッセージとして追加
      const newMessage: Message = {
        id: `msg-${uuidv4()}`,
        role: messageToResend.role,
        text: messageToResend.text,
        createdAt: new Date().toISOString(),
        ...(messageToResend.role === 'user' && messageToResend.images ? { images: messageToResend.images } : {}),
      };
      
      this.messages.push(newMessage);
      return newMessage;
    },
  },
});