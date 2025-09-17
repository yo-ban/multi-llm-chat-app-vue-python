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
    addMessage(role: MessageRole, text: string, images?: string[], streaming = false) {
      const newMessage: Message = {
        id: `msg-${uuidv4()}`,
        role,
        text,
        createdAt: new Date().toISOString(),
        ...(role === 'user' && images ? { images } : {}),
        ...(role === 'assistant' ? { streaming, streamedText: streaming ? '' : undefined } : {}),
      };
      this.$patch((state) => {
        state.messages.push(newMessage);
      });
    },
    updateStreamedMessage(text: string, image?: string) {
      this.$patch((state) => {
        const lastMessage = state.messages[state.messages.length - 1];
        if (lastMessage && lastMessage.role === 'assistant' && 'streaming' in lastMessage && lastMessage.streaming) {
          lastMessage.streamedText = text;
          if (image) {
            if (!lastMessage.images) {
              lastMessage.images = [image];
            } else {
              lastMessage.images = [...lastMessage.images, image];
            }
          }
        }
      });
    },
    stopStreaming() {
      this.$patch((state) => {
        for (let i = state.messages.length - 1; i >= 0; i--) {
          const message = state.messages[i];
          if (message.role === 'assistant' && 'streaming' in message && message.streaming) {
            message.text = message.streamedText || '';
            message.streamedText = undefined;
            message.streaming = false;
          } else {
            break;
          }
        }
      });
    },
    updateMessage(id: string, text: string) {
      this.$patch((state) => {
        const messageIndex = state.messages.findIndex(message => message.id === id);
        if (messageIndex !== -1) {
          state.messages[messageIndex] = {
            ...state.messages[messageIndex],
            text,
          };
        }
      });
    },
    deleteMessage(id: string) {
      this.$patch((state) => {
        const messageIndex = state.messages.findIndex(message => message.id === id);
        if (messageIndex !== -1) {
          const role = state.messages[messageIndex].role;

          if (role === 'user') {
            // ユーザーメッセージの次にアシスタントメッセージがあることを確認
            const deleteCount = (messageIndex + 1 < state.messages.length && 
                               state.messages[messageIndex + 1].role === 'assistant') ? 2 : 1;
            state.messages.splice(messageIndex, deleteCount);
          } else if (role === 'assistant') {
            // アシスタントメッセージの前にユーザーメッセージがあることを確認
            if (messageIndex > 0 && state.messages[messageIndex - 1].role === 'user') {
              state.messages.splice(messageIndex - 1, 2);
            } else {
              state.messages.splice(messageIndex, 1);
            }
          } else if (role === "error") {
            state.messages.splice(messageIndex, 1);
          }
        }
      });
    },
    deleteImage(messageId: string, imageIndex: number) {
      this.$patch((state) => {
        const messageIndex = state.messages.findIndex(message => message.id === messageId);
        if (messageIndex !== -1 && imageIndex >= 0) {
          const message = state.messages[messageIndex];
          if (message.images && message.images.length > imageIndex) {
            message.images = message.images.filter((_, idx) => idx !== imageIndex);
          }
        }
      });
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
        this.$patch({ messages });
      } catch (error) {
        console.error('Error loading messages:', error);
        this.$patch({ messages: [] });
        throw error;
      }
    },
    setMessages(messages: Message[]) {
      this.$patch({ messages });
    },
    clearMessages() {
      this.$patch({ messages: [] });
    },
    async resendMessage(messageId: string): Promise<Message | null> {
      const messageIndex = this.messages.findIndex(message => message.id === messageId);
      if (messageIndex === -1) return null;

      // 再送信するメッセージを取得
      const messageToResend = this.messages[messageIndex];
      
      // 新しいメッセージを作成
      const newMessage: Message = {
        id: `msg-${uuidv4()}`,
        role: messageToResend.role,
        text: messageToResend.text,
        createdAt: new Date().toISOString(),
        ...(messageToResend.role === 'user' && messageToResend.images ? { images: messageToResend.images } : {}),
      };
      
      // 状態を更新
      this.$patch((state) => {
        // メッセージ以降を削除（再送信するメッセージを含む）
        state.messages = state.messages.slice(0, messageIndex);
        // 新しいメッセージとして追加
        state.messages.push(newMessage);
      });
      
      return newMessage;
    },
  },
});