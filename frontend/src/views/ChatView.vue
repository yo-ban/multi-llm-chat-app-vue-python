<template>
  <div class="chat-container">
    <ChatHeader
      :title="currentConversationTitle"
      :settings="currentConversationSettings"
      :persona-id="currentPersonaId"
      :history-length="currentConversationLength"
      :system-message="currentConversationSystemMessage"
      @update:settings="updateSettings"
      @update:history-length="updateHistoryLength"
      @update:system-message="updateSystemMessageManualy"
      @open-file-management="openFileManagement"
      @regenerate-conversation-title="reGenerateChatTitle"
    />
    <PrimeDialog v-model:visible="showFileManagement" modal closeOnEscape dismissableMask header="File Management" :style="{ width: '500px' }">
      <FileManagement />
    </PrimeDialog>
    <div class="token-count">
      Tokens:
      {{ totalTokens }} / {{ selectedModel.contextWindow }}
    </div>
    <div class="messages-container-wrapper" ref="messagesContainerWrapper">
      <div class="messages-container" ref="messagesContainer">
        <SystemMessageInput
          v-if="showSystemMessageInput"
          :value="systemMessage"
          :is-custom-selected="isCustomSystemMessageSelected"
          :persona-id="currentPersonaId"
          @update:system-message="updateSystemMessage"
          @update:persona-id="updatePersonaId"
          @update:is-custom-selected="updateIsCustomSystemMessageSelected"
        />
        <ChatMessage
          v-for="message in messages"
          :key="message.id"
          v-bind="message"
          :images="message.images"
          :streamed-text="isAssistantMessage(message) ? message.streamedText : undefined"
          :streaming="isAssistantMessage(message) ? message.streaming : isStreaming"
          :is-processing="isStreaming"
          :persona-id="currentPersonaId"
          @resend-message="resendMessage"
          @delete-message="deleteMessage"
          @delete-image="deleteImage"
          @save-edited-message="saveEditedMessage"
        />
        <div ref="bottomMarker"></div>
        <div class="bottom-space"></div>
      </div>
    </div>
    <div v-if="hasConversations" class="fade-effect"></div>
    <div v-if="isStreaming || activeToolCall" class="tool-call-indicator">
      <i v-if="activeToolCall" class="pi pi-search animate-pulse" style="margin-right: 8px"></i>
      <i v-else class="pi pi-spinner pi-spin" style="margin-right: 8px"></i>
      <span v-if="activeToolCall?.type === 'web_search'" class="tool-status">
        Searching<span class="animate-dots">...</span> {{ truncateText(activeToolCall.query, 30) }}
      </span>
      <span v-else-if="activeToolCall?.type === 'web_browsing'" class="tool-status">
        Browsing<span class="animate-dots">...</span> {{ truncateText(activeToolCall.url, 40) }}
      </span>
      <span v-else class="tool-status">
        <template v-if="hasStartedStreaming">
          Generating response<span class="animate-dots">...</span>
        </template>
        <template v-else>
          Waiting for response<span class="animate-dots">...</span>
        </template>
      </span>
    </div>
    <MessageInput
      v-if="hasConversations"
      :is-streaming="isStreaming"
      :error-message="errorMessage"
      @send-message="onSendMessage"
      @cancel-streaming="cancelStreaming"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { MODELS } from '@/constants/models';
import { DEFAULT_PERSONA } from '@/constants/personas';
import type { APISettings } from '@/types/api';

// Store
import { useChatStore } from '@/store/chat';
import { useConversationStore } from '@/store/conversation';
import { useSettingsStore } from '@/store/settings';

// Types
import type { Message, AssistantMessage, UserMessage } from '@/types/messages';
import type { MessageRole } from '@/types/common';
import type { Conversation } from '@/types/conversation';

// Services
import { llmService } from '@/services/domain/llm-service';
import { storageService } from '@/services/storage/indexeddb-service';

// Utils
import { generateSystemMessageWithFiles, countTokens } from '@/utils/message-utils';

// Components
import ChatHeader from '@/components/ChatHeader.vue';
import ChatMessage from '@/components/ChatMessage.vue';
import FileManagement from '@/components/FileManagement.vue'
import MessageInput from '@/components/MessageInput.vue';
import SystemMessageInput from '@/components/SystemMessageInput.vue';

const getCurrentDateString = (timezone: string): string => {
  const now = new Date();
  const options: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: '2-digit',
    timeZone: timezone
  };
  return now.toLocaleDateString('en-US', options);
};

const getFilteredMessages = (historyLength: number, messages: Message[]): Message[] => {
  return historyLength > 0
    ? historyLength % 2 === 1
      ? messages.slice(-historyLength)
      : messages.slice(-(historyLength + 1))
    : messages;
};

const chatStore = useChatStore();
const conversationStore = useConversationStore();
const settingsStore = useSettingsStore();

const currentConversation = computed<Conversation | undefined>(() => {
  return conversationStore.conversationList.find(
    conversation => conversation.conversationId === conversationStore.currentConversationId
  );
});

const currentConversationLength = computed(() => {
  return currentConversation.value ? currentConversation.value.historyLength : 0;
});

const currentConversationTitle = computed(() => {
  return currentConversation.value ? currentConversation.value.title : '';
});

const currentConversationSettings = computed<APISettings>(() => {
  if (!currentConversation.value) {
    return {
      vendor: 'anthropic',
      model: MODELS.anthropic.CLAUDE_3_5_SONNET.id,
      maxTokens: 4096,
      temperature: 0.5,
    };
  }

  // 現在の会話の設定を取得
  const settings = currentConversation.value.settings;
  
  // OpenRouterの場合、モデルの存在確認
  if (settings.vendor === 'openrouter') {
    // settingsStoreのvalidateModelSelectionメソッドを使用して有効なモデルIDを取得
    const validModelId = settingsStore.validateModelSelection(settings.model, settings.vendor);
    if (validModelId !== settings.model) {
      // モデルIDが変更された場合は、新しい設定を返す
      return {
        ...settings,
        model: validModelId
      };
    }
  }

  return settings;
});

const currentConversationSystemMessage = computed(() => {
  return currentConversation.value ? currentConversation.value.system || '' : '';
});

const hasConversations = computed(() => conversationStore.conversationList.length > 0);

const isStreaming = ref(false);
const abortController = ref<AbortController | null>(null);
const previousConversationID = ref('')

const isManuallyScrolled = ref(false);
const messagesContainerWrapper = ref<HTMLElement | null>(null);
const bottomMarker = ref<HTMLElement | null>(null);

const messages = computed(() => chatStore.messages);
const errorMessage = computed(() => {
  const errorMessage = chatStore.messages.find(message => message.role === 'error');
  return errorMessage ? errorMessage.text : '';
});

const showSystemMessageInput = ref(false);
const systemMessage = ref('');
const currentPersonaId = ref('');
const isCustomSystemMessageSelected = ref(false);

const totalTokens = computed(() => {
  const messages = generateSystemMessageWithFiles(systemMessage.value, currentConversation.value?.files) + chatStore.messages.map(message => message.text).join('\n');
  return countTokens(messages);
});


const selectedModel = computed(() => {
  const { vendor, model } = currentConversationSettings.value;
  console.log("model:", model)
  console.log("vendor:", vendor)
  
  // OpenRouterの場合は openrouterModels から検索
  if (vendor === 'openrouter') {
    // openrouterModels から指定されたモデルIDを検索
    const openRouterModel = settingsStore.openrouterModels.find(m => m.id === model);
    if (openRouterModel) {
      return openRouterModel;
    }
    
    // モデルが見つからない場合でも、openrouterModelsが空でなければそこから取得
    if (settingsStore.openrouterModels.length > 0) {
      // 現在選択されているモデルが存在しない場合は、一番目のモデルを返す
      return settingsStore.openrouterModels[0];
    }
    
    // openrouterModelsが空の場合は現在のモデルIDを持つ最小限のモデル情報を返す
    // （読み込み完了前の一時的な状態を処理するため）
    return {
      id: model,
      name: model.split('/').pop() || model,
      contextWindow: 8000,
      maxTokens: 8000,
      multimodal: false,
      supportsReasoning: false,
      unsupportsTemperature: false,
      supportFunctionCalling: false,
      imageGeneration: false
    };
  }
  
  // 通常のベンダー（OpenRouter以外）の場合は従来の実装を使用
  const vendorModels = MODELS[vendor] || {};
  for (const key in vendorModels) {
    if (vendorModels[key].id === model) {
      return vendorModels[key];
    }
  }
  
  // モデルが見つからない場合のフォールバック
  return MODELS.anthropic.CLAUDE_3_5_SONNET;
});

interface ToolCall {
  type: string;
  status: 'start' | 'end';
  query?: string;
  url?: string;
}

const activeToolCall = ref<ToolCall | null>(null);
const hasStartedStreaming = ref(false);

function isAssistantMessage(message: Message): message is AssistantMessage {
  return message.role === 'assistant';
}

function truncateText(text: string | undefined, maxLength: number): string {
  if (!text) return '';
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// ツール呼び出しの状態を監視・更新
const onUpdate = async (text: string, toolCall?: ToolCall, isIndicator?: boolean, image?: string) => {
  if (!isIndicator && !chatStore.messages.some(message => 
    isAssistantMessage(message) && message.streaming
  )) {
    await chatStore.addMessage('assistant', '', undefined, true);
  }
  if (!isIndicator) {
    chatStore.updateStreamedMessage(text, image);
    hasStartedStreaming.value = true;
  }
  if (toolCall) {
    if (toolCall.status === 'start') {
      activeToolCall.value = toolCall;
      hasStartedStreaming.value = false;
    } else if (toolCall.status === 'end') {
      activeToolCall.value = null;
    }
  } else {
    activeToolCall.value = null;
  }
};

watch(
  () => conversationStore.currentConversationId,
  async (newConversationId) => {
    if (newConversationId) {
      if (isStreaming.value) {
        cancelStreaming()
        chatStore.stopStreaming();
        await updateConversationHistory(previousConversationID.value, chatStore.messages);
      }
      previousConversationID.value = newConversationId;
      const messages = await storageService.getConversationMessages(newConversationId);
      chatStore.messages = messages.map(message => ({
        ...message,
      }));
      if (messages.length === 0) {
        showSystemMessageInput.value = true
      } else {
        showSystemMessageInput.value = false
        nextTick(() => {
          scrollToBottom(false);
        });
      }
    } else {
      chatStore.messages = [];
      showSystemMessageInput.value = false;
    }
    systemMessage.value = currentConversation.value?.system || DEFAULT_PERSONA.systemMessage;
    currentPersonaId.value = currentConversation.value?.personaId || DEFAULT_PERSONA.id;
    isCustomSystemMessageSelected.value = systemMessage.value !== DEFAULT_PERSONA.systemMessage;
    fixStreamingMessages();
  },
  { immediate: true }
);

watch(
  () => {
    const lastMessage = messages.value[messages.value.length - 1];
    return lastMessage && isAssistantMessage(lastMessage) && lastMessage.streaming
      ? lastMessage.streamedText 
      : null;
  },
  () => {
    if (!isManuallyScrolled.value) {
      nextTick(() => {
        scrollToBottom(false);
      });
    }
  }
);

const showFileManagement = ref(false);

function openFileManagement() {
  showFileManagement.value = true;
}

function updateSystemMessage(newSystemMessage: string) {
  systemMessage.value = newSystemMessage;
}

async function updateSystemMessageManualy(newSystemMessage: string) {
  const currentConversationId = conversationStore.currentConversationId;
  if (currentConversationId) {
      await conversationStore.updateConversationSystem(currentConversationId, newSystemMessage, currentPersonaId.value);
  }
}

function fixStreamingMessages() {
  chatStore.messages.forEach((message) => {
    if (message.role === 'assistant' && 'streaming' in message) {
      (message as AssistantMessage).streaming = false;
    }
  });
}

function updatePersonaId(newPersonaId: string) {
  currentPersonaId.value = newPersonaId;
}

function updateIsCustomSystemMessageSelected(isCustomSelected: boolean) {
  isCustomSystemMessageSelected.value = isCustomSelected;
}

async function updateSettings(settings: APISettings) {
  if (conversationStore.currentConversationId) {
    // OpenRouterの場合は設定ストアの検証メソッドを使用
    if (settings.vendor === 'openrouter') {
      const validModelId = settingsStore.validateModelSelection(settings.model, settings.vendor);
      if (validModelId !== settings.model) {
        settings.model = validModelId;
      }
    }
    
    await conversationStore.updateConversationSettings(
      conversationStore.currentConversationId, 
      settings
    );
    console.log('Updated settings:', currentConversationSettings.value);
  }
}

async function updateHistoryLength(historyLength: number) {
  if (conversationStore.currentConversationId) {
    await conversationStore.updateConversationHistoryLength(conversationStore.currentConversationId, historyLength);
  }
}

async function onSendMessage(newMessage: string, uploadedImages: string[]) {
  hasStartedStreaming.value = false;
  const currentConversationId = conversationStore.currentConversationId;
  if (currentConversationId) {
    if (showSystemMessageInput.value) {
      await conversationStore.updateConversationSystem(currentConversationId, systemMessage.value, currentPersonaId.value);
      showSystemMessageInput.value = false;
    }
    await chatStore.addMessage('user' as MessageRole, newMessage, uploadedImages, false);
    await updateConversationHistory(currentConversationId, chatStore.messages);

    nextTick(() => {
      scrollToBottom();
    });
    await sendMessage();
  }
}

const updateConversationHistory = async (conversationId: string, messages: Message[]) => {
  if (conversationId) {
    await storageService.updateConversationMessages(conversationId, messages);
  }
};

async function reGenerateChatTitle() {
  const currentConversationId = conversationStore.currentConversationId;
  if (currentConversationId) {
    if (chatStore.messages.length >= 2) {
      llmService.generateChatTitle(chatStore.messages).then(async (title: string) => {
        await conversationStore.updateConversationTitle(currentConversationId, title);
      }).catch((error: Error) => {
        console.error('Error generating chat title:', error);
      });
    }
  }
}

async function sendMessage() {
  isStreaming.value = true;
  const currentConversationId = conversationStore.currentConversationId;
  
  try {
    abortController.value = new AbortController()

    console.log(currentConversationSettings.value)

    const apiMessages = getFilteredMessages(currentConversation.value?.historyLength || 0, chatStore.messages);
    const systemMessage = generateSystemMessageWithFiles(currentConversationSystemMessage.value.replaceAll("{{Date}}", getCurrentDateString("Asia/Tokyo")), currentConversation.value?.files)

    // Prepare API settings with proper handling of temperature and reasoning support
    const apiSettings = {
      ...currentConversationSettings.value,
      isReasoningSupported: selectedModel.value.supportsReasoning || false,
    };

    // Only include temperature if the model supports it
    if (selectedModel.value.unsupportsTemperature) {
      delete apiSettings.temperature;
    }

    await llmService.sendMessageToAPI(apiMessages, systemMessage, apiSettings, onUpdate, abortController.value.signal);

    chatStore.stopStreaming();

    if (chatStore.messages.length >= 2 && currentConversationTitle.value === "New Chat" && currentConversationId) {
      llmService.generateChatTitle(chatStore.messages).then(async (title: string) => {
        await conversationStore.updateConversationTitle(currentConversationId, title);
      }).catch((error: Error) => {
        console.error('Error generating chat title:', error);
      });
    }

  } catch (error) {
    chatStore.stopStreaming();
    if ((error as Error).name !== 'AbortError') {
      console.error('Error in sendMessage:', error);
      await chatStore.addMessage('error', `An error occurred while processing your request.\nTry to resend your message.\nDetail:\n${error}`);
    }
  } finally {
    if (currentConversationId) {
      await updateConversationHistory(currentConversationId, chatStore.messages);
      await conversationStore.updateConversationDate(currentConversationId)
    }
    isStreaming.value = false;
    abortController.value = null;
  }
}

function cancelStreaming() {
  if (abortController.value) {
    abortController.value.abort();
    isStreaming.value = false;
    hasStartedStreaming.value = false;
    activeToolCall.value = null
    chatStore.stopStreaming()
  }
}

async function saveEditedMessage(id: string, editedText: string) {
  await chatStore.updateMessage(id, editedText);

  // Update the conversation history with the current messages
  const currentConversationId = conversationStore.currentConversationId;
  if (currentConversationId) {
    await updateConversationHistory(currentConversationId, chatStore.messages);
  }
}

async function resendMessage(id: string) {
  hasStartedStreaming.value = false;
  const messageIndex = chatStore.messages.findIndex(message => message.id === id);
  console.log('Resending message with id:', id, 'Index:', messageIndex);
  if (messageIndex !== -1) {
    const resendMessage = chatStore.messages[messageIndex] as UserMessage;
    chatStore.messages.splice(messageIndex);
    await chatStore.addMessage('user', resendMessage.text, resendMessage.images, false);

    nextTick(() => {
      scrollToBottom();
    });

    await sendMessage();
  }
}

async function deleteMessage(id: string) {
  const messageIndex = chatStore.messages.findIndex(message => message.id === id);
  if (messageIndex !== -1) {
    const role = chatStore.messages[messageIndex].role;

    if (role === 'user') {
      chatStore.messages.splice(messageIndex, 2);
    } else if (role === 'assistant') {
      chatStore.messages.splice(messageIndex - 1, 2);
    } else if (role === "error") {
      chatStore.messages.splice(messageIndex, 1);
    }
    // Update the conversation history with the current messages
    const currentConversationId = conversationStore.currentConversationId;
    if (currentConversationId){
      await updateConversationHistory(currentConversationId, chatStore.messages);
    }
    if (chatStore.messages.length === 0) {
      showSystemMessageInput.value = true;
      systemMessage.value = currentConversation.value?.system || DEFAULT_PERSONA.systemMessage;
      isCustomSystemMessageSelected.value = systemMessage.value !== DEFAULT_PERSONA.systemMessage;
    }
  }
}

async function deleteImage(messageId: string, imageIndex: number) {
  const messageIndex = chatStore.messages.findIndex(message => message.id === messageId);
  if (messageIndex !== -1) {
    const message = chatStore.messages[messageIndex];
    if (message.images && message.images.length > imageIndex) {
      message.images = message.images.filter((_, idx) => idx !== imageIndex);
      await updateConversationHistory(conversationStore.currentConversationId!, chatStore.messages);
    }
  }
}

function onScroll() {
  const container = messagesContainerWrapper.value;
  if (container) {
    const { scrollTop, clientHeight, scrollHeight } = container;
    const isAtBottom = Math.abs(scrollTop + clientHeight - scrollHeight) <= 40;
    isManuallyScrolled.value = !isAtBottom;
  }
}

function scrollToBottom(smooth: boolean = true) {
  const container = messagesContainerWrapper.value;
  if (container) {
    container.scrollTo({
      top: container.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    });
  }
}

onMounted(async () => {
  await conversationStore.initializeConversationStore();
  if (!hasConversations.value) {
    conversationStore.createNewConversation();
  }
});

onMounted(() => {
  messagesContainerWrapper.value?.addEventListener('scroll', onScroll);
});

onBeforeUnmount(() => {
  messagesContainerWrapper.value?.removeEventListener('scroll', onScroll);
  cancelStreaming(); 
});
</script>

<style scoped>
.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fdfdfd;
  position: relative;
}

.messages-container-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 20px 10px 0;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  background-color: #fffdfa;
}

.bottom-space {
  height: 20px;
}

.fade-effect {
  position: absolute;
  bottom: 60px;
  left: 0;
  right: 0;
  height: 15px;
  background: linear-gradient(to bottom, rgba(253, 253, 253, 0), rgba(253, 253, 253, 0.8));
  pointer-events: none;
  z-index: 1;
}

.messages-container {
  width: 100%;
  max-width: 85%;
  min-width: 350px;
}

.token-count {
  position: fixed;
  top: 55px;
  right: 10px;
  background-color: rgba(0, 0, 0, 0.39);
  color: white;
  padding: 3px 5px;
  border-radius: 5px;
  font-size: 10px;
  z-index: 1000;
}

.file-list {
  margin-bottom: 20px;
}

.file-item {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.file-name {
  margin-right: 10px;
}

.delete-file-button {
  background: none;
  border: none;
  color: #ff0000;
  cursor: pointer;
}

.tool-call-indicator {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  z-index: 100;
  animation: slide-up 0.3s ease-out;
  max-width: 80%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.tool-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.animate-dots {
  display: inline-block;
  min-width: 16px;
  animation: dots 1.4s infinite;
}

@keyframes dots {
  0%, 20% {
    content: '.';
  }
  40%, 60% {
    content: '..';
  }
  80%, 100% {
    content: '...';
  }
}

@keyframes slide-up {
  from {
    transform: translate(-50%, 20px);
    opacity: 0;
  }
  to {
    transform: translate(-50%, 0);
    opacity: 1;
  }
}
</style>

<style>
/* グローバルスタイル（scoped外に配置） */
@keyframes dots {
  0%, 20% {
    content: '.';
  }
  40%, 60% {
    content: '..';
  }
  80%, 100% {
    content: '...';
  }
}

.animate-dots::after {
  content: '...';
  animation: dots 1.4s infinite;
}
</style>