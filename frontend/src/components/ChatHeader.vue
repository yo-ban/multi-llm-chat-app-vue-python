<template>
  <div class="chat-header">
    <div class="header-content">
      <h2 class="chat-title">{{ title }}</h2>
      <div class="model-name">
        Model: {{ displayedModel.name }} ({{ displayedModel.id }})
        <span v-if="displayedModel.supportsReasoning" class="model-feature">• Reasoning</span>
        <span v-if="displayedModel.imageGeneration" class="model-feature">• Image Generation</span>
        <span v-if="localSettings.websearch" class="model-feature">• Web Search</span>
      </div>
    </div>
    <div class="header-actions">
      <div class="model-selection" style="display:flex; align-items:center; margin-right:10px;">
        <PrimeDropdown 
          v-model="localSettings.vendor" 
          :options="Object.keys(MODELS)" 
          placeholder="Select Vendor" 
          @change="onVendorChange" 
          class="vendor-dropdown" 
          style="margin-right: 5px;"
        />
        <PrimeDropdown 
          v-model="localSettings.model" 
          :options="availableModels" 
          optionLabel="name" 
          optionValue="id" 
          placeholder="Select Model" 
          @change="onModelChange" 
          class="model-dropdown" 
        />
      </div>
      <VTooltip placement="top" popper-class="tooltip-content">
        <template #popper>
          {{ isWebSearchAvailable ? 'Web Search' : 'Web Search (Not available for this model)' }}
        </template>
        <div class="header-toggle">
          <PrimeInputSwitch
            v-model="localSettings.websearch"
            @change="onWebSearchChange"
            class="header-toggle-switch"
            :disabled="!isWebSearchAvailable"
          />
        </div>
      </VTooltip>
      <VTooltip placement="top" popper-class="tooltip-content">
        <template #popper>
          File Management
        </template>
        <button @click="openFileManagement" class="file-management-button">
          <font-awesome-icon icon="folder" size="lg" />
          <span v-if="hasFiles" class="file-badge">{{ fileCount }}</span>
        </button>
      </VTooltip>
      <VTooltip placement="top" popper-class="tooltip-content">
        <template #popper>
          Settings
        </template>
        <PrimeButton icon="pi pi-ellipsis-v" class="p-button-rounded p-button-text p-button-plain" @click="toggleMenu" aria-haspopup="true" aria-controls="overlay_menu" />
      </VTooltip>
      <PrimeMenu id="overlay_menu" ref="menu" :model="items" :popup="true" />
    </div>
    <PrimeDialog v-model:visible="modelSettingsDialogVisible" modal header="Model Settings" :style="{ width: '500px' }" :draggable="false" :closable="false">
      <div class="settings-content">
        <div class="settings-section">
          <!-- <h3 class="settings-section-header">Model Settings</h3> -->
          <div class="settings-item">
            <label for="vendor" class="settings-label">Vendor:</label>
            <div class="settings-control">
              <PrimeDropdown
                id="vendor"
                v-model="localSettings.vendor"
                :options="Object.keys(MODELS)"
                placeholder="Select Vendor"
                class="settings-dropdown"
              />
            </div>
          </div>
          <div class="settings-item">
            <label for="model" class="settings-label">Model:</label>
            <div class="settings-control">
              <PrimeDropdown
                id="model"
                v-model="localSettings.model"
                :options="availableModels"
                optionLabel="name"
                optionValue="id"
                placeholder="Select Model"
                class="settings-dropdown"
              />
            </div>
          </div>
          <div class="settings-item" v-if="!selectedModel.unsupportsTemperature">
            <label for="temperature" class="settings-label">Temperature:</label>
            <div class="settings-control">
              <div class="slider-container">
                <PrimeSlider
                  id="temperature"
                  v-model="localSettings.temperature"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  class="settings-slider"
                />
                <PrimeInputNumber
                  v-model="localSettings.temperature"
                  :min="0"
                  :max="1"
                  :step="0.1"
                  class="slider-input"
                />
              </div>
            </div>
          </div>
          <div class="settings-item">
            <label for="max-tokens" class="settings-label">Max Tokens:</label>
            <div class="settings-control">
              <div class="slider-container">
                <PrimeSlider
                  id="max-tokens"
                  v-model="localSettings.maxTokens"
                  :min="128"
                  :max="selectedModel.maxTokens"
                  :step="128"
                  class="settings-slider"
                />
                <PrimeInputNumber
                  v-model="localSettings.maxTokens"
                  :min="128"
                  :max="selectedModel.maxTokens"
                  :step="128"
                  class="slider-input"
                />
              </div>
            </div>
          </div>
          <div class="settings-item" v-if="selectedModel.supportsReasoning">
            <label for="reasoning-effort" class="settings-label">Reasoning Effort:</label>
            <div class="settings-control">
              <PrimeDropdown
                id="reasoning-effort"
                v-model="localSettings.reasoningEffort"
                :options="reasoningEffortOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="Select Reasoning Effort"
                class="settings-dropdown"
              />
              <small class="parameter-description">
                Controls how much effort the model puts into reasoning about responses.
                Higher values result in more thorough analysis but may increase response time.
              </small>
            </div>
          </div>
          <!-- <div class="settings-item">
            <label for="web-search" class="settings-label">Web Search:</label>
            <div class="settings-control">
              <PrimeToggleButton
                id="web-search"
                v-model="localSettings.websearch"
                onLabel="Enabled"
                offLabel="Disabled"
                class="settings-toggle"
              />
              <div class="parameter-description">
                Enable web search functionality using function calling
              </div>
            </div>
          </div> -->
        </div>
      </div>
      <template #footer>
        <div class="settings-footer">
          <PrimeButton label="Cancel" icon="pi pi-times" @click="closeModelSettingsDialog" class="p-button-text" />
          <PrimeButton label="Save" icon="pi pi-check" @click="saveModelSettings" class="p-button-primary" />
        </div>
      </template>
    </PrimeDialog>
    <PrimeDialog v-model:visible="conversationSettingsDialogVisible" modal header="Conversation Settings" :style="{ width: '600px' }" :draggable="false" :closable="false">
      <div class="settings-content">
        <div class="settings-section">
          <h3 class="settings-section-header">History Length</h3>
          <div class="settings-item">
            <VTooltip placement="top" popper-class="tooltip-content">
              <template #popper>
                Number of recent messages to send in API requests. 0 = unlimited.
              </template>
              <label for="history-length" class="settings-label">History Length:</label>
            </VTooltip>
            <div class="settings-control">
              <div class="slider-container">
                <PrimeSlider
                  id="history-length"
                  v-model="localHistoryLength"
                  :min="0"
                  :max="50"
                  :step="1"
                  class="settings-slider"
                />
                <PrimeInputNumber
                  v-model="localHistoryLength"
                  :min="0"
                  :max="50"
                  :step="1"
                  class="slider-input"
                />
              </div>
            </div>
          </div>
        </div>
        <div class="settings-section">
          <h3 class="settings-section-header">System Message</h3>
          <div class="settings-item">
            <div class="settings-control">
              <div class="system-message-container">
                <textarea id="system-message" v-model="localSystemMessage" rows="10" class="settings-textarea" readonly></textarea>
              </div>
              <PrimeButton label="Edit" @click="openSystemMessageDialog" class="edit-button" />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="settings-footer">
          <PrimeButton label="Cancel" icon="pi pi-times" @click="closeConversationSettingsDialog" class="p-button-text" />
          <PrimeButton label="Save" icon="pi pi-check" @click="saveConversationSettings" class="p-button-primary" />
        </div>
      </template>
    </PrimeDialog>
    <PrimeDialog v-model:visible="systemMessageDialogVisible" modal header="Edit System Message" :style="{ width: '600px' }" :closable="false" :draggable="false">
      <div class="system-message-dialog-content">
        <textarea v-model="localSystemMessage" rows="10" class="system-message-textarea"></textarea>
      </div>
      <template #footer>
        <div class="system-message-dialog-footer">
          <PrimeButton label="Cancel" icon="pi pi-times" @click="closeSystemMessageDialog" class="p-button-text" />
          <PrimeButton label="Save" icon="pi pi-check" @click="saveSystemMessage" class="p-button-primary" />
        </div>
      </template>
    </PrimeDialog>
</div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { MODELS } from '@/constants/models';
import type { APISettings } from '@/types/api';
import type { Model } from '@/types/models';
import { useConversationStore } from '@/store/conversation';
import { useChatStore } from '@/store/chat';
import { useSettingsStore } from '@/store/settings';
import { useToast } from 'primevue/usetoast';

const props = defineProps({
  title: {
    type: String,
    required: true,
  },
  settings: {
    type: Object,
    required: true,
  },
  historyLength: {
    type: Number,
    required: true,
  },
  systemMessage: {
    type: String,
    required: true,
  },
  personaId: {
    type: String,
    default: '',
  },
  files: {
    type: Object as () => { [key: string]: string },
    default: () => ({}),
  },
});

const emit = defineEmits(['update:settings', 'update:history-length', 'open-file-management', 'update:system-message', 'regenerate-conversation-title', 'refresh-context-window']);

const menu = ref();
const items = ref([
  {
    label: 'Model Settings',
    icon: 'pi pi-cog',
    command: () => {
      openModelSettingsDialog();
    },
    tabindex: '0',
    class: 'menu-item',
  },
  {
    label: 'Conversation Settings',
    icon: 'pi pi-comments',
    command: () => {
      openConversationSettingsDialog();
    },
    tabindex: '0',
    class: 'menu-item',
  },
  {
    label: 'Export Conversation',
    icon: 'pi pi-download',
    command: () => {
      exportConversation();
    },
    tabindex: '0',
    class: 'menu-item',
  },
]);

const modelSettingsDialogVisible = ref(false);
const conversationSettingsDialogVisible = ref(false);
const systemMessageDialogVisible = ref(false);

const localPersonaId = ref(props.personaId);
const conversationStore = useConversationStore();
const chatStore = useChatStore();
const settingsStore = useSettingsStore();
const toast = useToast();

const localSettings = ref<APISettings>({
  vendor: props.settings.vendor,
  model: props.settings.model,
  temperature: props.settings.temperature,
  maxTokens: props.settings.maxTokens,
  reasoningEffort: props.settings.reasoningEffort,
  websearch: props.settings.websearch,
  multimodal: props.settings.multimodal,
  imageGeneration: props.settings.imageGeneration
});

const availableModels = computed(() => {
  if (localSettings.value.vendor === 'openrouter') {
    return settingsStore.openrouterModels;
  }
  return Object.values(MODELS[localSettings.value.vendor] || {});
});

const selectedModel = computed(() => {
  if (localSettings.value.vendor === 'openrouter') {
    // まず指定されたモデルIDを検索
    const model = settingsStore.openrouterModels.find(m => m.id === localSettings.value.model);
    if (model) return model;
    
    // モデルが見つからず、openrouterModelsが空でない場合は最初のモデルを返す
    if (settingsStore.openrouterModels.length > 0) {
      return settingsStore.openrouterModels[0];
    }
    
    // openrouterModelsが空の場合（非同期ロード中など）は仮のモデル情報を返す
    return {
      id: localSettings.value.model,
      name: localSettings.value.model.split('/').pop() || localSettings.value.model,
      contextWindow: 8000,
      maxTokens: 8000,
      multimodal: false,
      supportsReasoning: false,
      unsupportsTemperature: false,
      supportFunctionCalling: false,
      imageGeneration: false
    };
  }
  
  // OpenRouter以外の場合は従来のロジックを使用
  return Object.values(MODELS[localSettings.value.vendor] || {})
    .find((m) => m.id === localSettings.value.model) || MODELS.anthropic.CLAUDE_3_5_SONNET;
});

const displayedModel = ref(selectedModel.value);

const localHistoryLength = ref(props.historyLength || 0);
const localSystemMessage = ref(props.systemMessage || '');

const reasoningEffortOptions = ref([
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' },
]);

// Add new ref to track whether the dialog is open
const isModelDialogOpen = ref(false);

// APIキーのチェック関数を追加
const checkApiKey = (vendor: string) => {
  const apiKey = settingsStore.apiKeys[vendor];
  if (!apiKey) {
    toast.add({
      severity: 'warn',
      summary: 'API Key Required',
      detail: `Please set up your ${vendor.toUpperCase()} API key in Global Settings to use this vendor.`,
      life: 5000
    });
    return false;
  }
  return true;
};

watch(
  () => props.personaId,
  (newPersonaId) => {
    localPersonaId.value = newPersonaId;
    console.log('Received Persona:', newPersonaId);
  }
);

watch(
  () => localSettings.value.vendor,
  (newVendor, oldVendor) => {
    if (newVendor === oldVendor) return;

    // OpenRouter の場合は特別処理：モデルリストが空でも現在の選択を維持する
    if (newVendor === 'openrouter') {
      // 何もしない - 既存のモデル選択を保持
      // displayedModel は selectedModel の computed プロパティで更新される
      displayedModel.value = selectedModel.value;
      
      // ダイアログが開いていない場合のみ設定を更新
      if (!isModelDialogOpen.value) {
        emit('update:settings', { ...localSettings.value });
      }
      return;
    }

    // OpenRouter 以外の場合は通常処理
    // 現在のモデルが新しいベンダーで利用可能かチェック
    const modelExists = availableModels.value.some((m: Model) => m.id === localSettings.value.model);
    
    // 現在のモデルが利用できない場合のみ、新しいモデルを選択
    if (!modelExists) {
      if (availableModels.value.length > 0) {
        localSettings.value.model = availableModels.value[0].id;
        localSettings.value.maxTokens = Math.min(
          localSettings.value.maxTokens || 4096,
          availableModels.value[0].maxTokens
        );
      } else {
        localSettings.value.model = MODELS.anthropic.CLAUDE_3_5_SONNET.id;
        localSettings.value.maxTokens = MODELS.anthropic.CLAUDE_3_5_SONNET.maxTokens;
      }
    }

    displayedModel.value = selectedModel.value;
    
    // Only emit updates when the dialog is not open or when changed from header dropdown
    if (!isModelDialogOpen.value) {
      emit('update:settings', { ...localSettings.value });
    }
  }
);

watch(
  () => props.settings,
  (newSettings) => {
    if (newSettings) {  
      console.log('Settings updated from props:', newSettings);
      localSettings.value = {
        vendor: newSettings.vendor,
        model: newSettings.model,
        temperature: selectedModel.value?.unsupportsTemperature ? undefined : (newSettings.temperature ?? settingsStore.defaultTemperature),
        maxTokens: newSettings.maxTokens,
        reasoningEffort: newSettings.reasoningEffort,
        websearch: newSettings.websearch,
        multimodal: newSettings.multimodal,
        imageGeneration: newSettings.imageGeneration
      };
      displayedModel.value = selectedModel.value;
    }
  },
  { deep: true }  // オブジェクトの深い変更も監視
);

watch(
  () => localSettings.value.model,
  (newModelId, oldModelId) => {
    if (newModelId === oldModelId) return;

    let model;
    if (localSettings.value.vendor === 'openrouter') {
      model = settingsStore.openrouterModels.find(m => m.id === newModelId);
    } else {
      model = Object.values(MODELS[localSettings.value.vendor] || {}).find((m) => m.id === newModelId);
    }
    
    if (model) {
      console.log('Model changed:', { 
        vendor: localSettings.value.vendor, 
        modelId: newModelId,
        maxTokens: model.maxTokens,
        supportsReasoning: model.supportsReasoning,
        supportFunctionCalling: model.supportFunctionCalling,
        unsupportsTemperature: model.unsupportsTemperature,
        multimodal: model.multimodal,
        imageGeneration: model.imageGeneration
      });
      
      localSettings.value.maxTokens = Math.min(localSettings.value.maxTokens || 4096, model.maxTokens);
      localSettings.value.isReasoningSupported = model.supportsReasoning || false;
      localSettings.value.multimodal = model.multimodal || false;
      localSettings.value.imageGeneration = model.imageGeneration || false;

      // Set reasoning effort based on model support and global default
      if (model.supportsReasoning && !localSettings.value.reasoningEffort) {
        localSettings.value.reasoningEffort = settingsStore.defaultReasoningEffort || 'medium';
      } else if (!model.supportsReasoning) {
        localSettings.value.reasoningEffort = undefined;
      }

      // Update web search availability based on function calling support
      if (!model.supportFunctionCalling) {
        localSettings.value.websearch = false;
      }

      // Handle temperature support
      if (model.unsupportsTemperature) {
        localSettings.value.temperature = undefined;
      } else if (localSettings.value.temperature === undefined) {
        localSettings.value.temperature = settingsStore.defaultTemperature;
      }
      
      displayedModel.value = model;
      
      // Only emit updates when the dialog is not open or when changed from header dropdown
      if (!isModelDialogOpen.value) {
        emit('update:settings', { ...localSettings.value });
      }
    }
  }
);

watch(
  () => settingsStore.openrouterModels,
  (newModels) => {
    if (localSettings.value.vendor === 'openrouter') {
      // Use validateModelSelection to check and get a valid model ID
      const validModelId = settingsStore.validateModelSelection(localSettings.value.model, localSettings.value.vendor);
      if (validModelId !== localSettings.value.model) {
        localSettings.value.model = validModelId;
        displayedModel.value = selectedModel.value;
        emit('update:settings', { ...localSettings.value });
      }
    }
  },
  { immediate: true }
);

// Add a new watcher to handle model updates when the selected model changes
watch(selectedModel, (newModel) => {
  if (localSettings.value.vendor === 'openrouter') {
    // Use the validateModelSelection method here too
    const validModelId = settingsStore.validateModelSelection(localSettings.value.model, localSettings.value.vendor);
    if (validModelId !== localSettings.value.model) {
      localSettings.value.model = validModelId;
    }
  }
}, { immediate: true });

const hasFiles = computed(() => {
  const currentConversation = conversationStore.conversationList.find(
    (c) => c.conversationId === conversationStore.currentConversationId
  );
  return currentConversation ? Object.keys(currentConversation.files || {}).length > 0 : false;
});

const fileCount = computed(() => {
  const currentConversation = conversationStore.conversationList.find(
    (c) => c.conversationId === conversationStore.currentConversationId
  );
  return currentConversation ? Object.keys(currentConversation.files || {}).length : 0;
});

async function exportConversation() {
  await conversationStore.exportConversation(chatStore.messages);
}

function openFileManagement() {
  emit('open-file-management');
}

function toggleMenu(event: Event) {
  menu.value.toggle(event);
}

function openModelSettingsDialog() {
  isModelDialogOpen.value = true;
  modelSettingsDialogVisible.value = true;
}

function closeModelSettingsDialog() {
  isModelDialogOpen.value = false;
  modelSettingsDialogVisible.value = false;
  localSettings.value = {
    vendor: props.settings.vendor,
    model: props.settings.model,
    temperature: props.settings.temperature,
    maxTokens: props.settings.maxTokens,
    reasoningEffort: props.settings.reasoningEffort,
    websearch: props.settings.websearch,
    multimodal: props.settings.multimodal,
    imageGeneration: props.settings.imageGeneration
  };
  displayedModel.value = selectedModel.value;
}

function saveModelSettings() {
  emit('update:settings', { ...localSettings.value });
  closeModelSettingsDialog();
  displayedModel.value = selectedModel.value;
}

function openConversationSettingsDialog() {
  localHistoryLength.value = props.historyLength;
  localSystemMessage.value = props.systemMessage;  
  conversationSettingsDialogVisible.value = true;
}

function closeConversationSettingsDialog() {
  conversationSettingsDialogVisible.value = false;
  localHistoryLength.value = props.historyLength;
  localSystemMessage.value = props.systemMessage;  
}

async function saveConversationSettings() {
  emit('update:history-length', localHistoryLength.value);
  closeConversationSettingsDialog();
}

function openSystemMessageDialog() {
  localSystemMessage.value = props.systemMessage;
  systemMessageDialogVisible.value = true;
}

function closeSystemMessageDialog() {
  systemMessageDialogVisible.value = false;
  localSystemMessage.value = props.systemMessage;
}

function saveSystemMessage() {
  emit('update:system-message', localSystemMessage.value);
  displayedModel.value = selectedModel.value;
  systemMessageDialogVisible.value = false;
}

// ヘッダーのドロップダウンでの変更時に即座に保存
function onVendorChange() {
  // APIキーが設定されているかチェック
  if (!checkApiKey(localSettings.value.vendor)) {
    // APIキーが設定されていない場合は、設定ダイアログを開く
    // openModelSettingsDialog();
    return;
  }
  emit('update:settings', { ...localSettings.value });
  displayedModel.value = selectedModel.value;
}

function onModelChange() {
  emit('update:settings', { ...localSettings.value });
  displayedModel.value = selectedModel.value;
}

function onWebSearchChange() {
  emit('update:settings', { ...localSettings.value });
}

// Add computed property to check if web search is available
const isWebSearchAvailable = computed(() => {
  return selectedModel.value.supportFunctionCalling || false;
});
</script>

<style scoped>
.chat-header {
  height: 50px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 20px;
  background-color: #34495e;
  color: white;
  border-bottom: 1px solid #2c3e50;
  z-index: 2;
}

.chat-title {
  margin: 0;
  font-size: 18px;
  font-weight: 400;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;
}

.model-name {
  font-size: 11px;
  color: #ffffff;
  margin-top: 2px;
  font-weight: 200;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;  
}

.model-feature {
  color: #4CAF50;
  margin-left: 5px;
}

.header-actions {
  display: flex;
  align-items: center;
}

.header-actions :deep(.p-button) {
  color: white;
}

.header-actions :deep(.p-button:hover) {
  background-color: rgba(255, 255, 255, 0.1);
}

.file-management-button {
  position: relative;
  margin-right: 10px;
  background-color: transparent;
  color: white;
  border: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  transition: background-color 0.3s;
}

.file-management-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.file-management-button :deep(svg) {
  font-size: 20px;
}

.file-badge {
  position: absolute;
  top: 0px;
  right: 0px;
  background-color: #d43e31;
  color: white;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 10px;
  font-weight: bold;
}

.settings-section {
  margin-bottom: 20px;
}

.settings-section-header {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 10px;
}

.settings-item {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.settings-label {
  flex: 0 0 120px;
  margin-right: 10px;
}

.settings-control {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.slider-container {
  display: flex;
  align-items: center;
}

.settings-slider {
  flex: 1;
  margin-right: 10px;
}

.slider-input {
  width: 80px;
}

.slider-input :deep(.p-inputnumber) {
  width: 80px;
}

.slider-input :deep(.p-inputnumber-input) {
  width: 100%;
  text-align: center;
}

.settings-dropdown {
  width: 100%;
}

.settings-toggle {
  width: 100%;
  margin-bottom: 5px;
}

.settings-toggle :deep(.p-button) {
  width: 100%;
  justify-content: center;
}

.parameter-description {
  margin-top: 8px;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  line-height: 1.4;
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
}

.settings-footer .p-button {
  margin-left: 10px;
}

.system-message-container {
  max-height: 350px;
  overflow-y: auto;
  margin-bottom: 10px;
}

.edit-button {
  width: 100%;
}

.system-message-dialog-content {
  display: flex;
  flex-direction: column;
}

.system-message-textarea {
  width: 100%;
  resize: vertical;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: inherit;
  font-size: 14px;
}

.system-message-dialog-footer {
  display: flex;
  justify-content: flex-end;
}

.settings-textarea {
  width: 100%;
  resize: none;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: inherit;
  font-size: 14px;
}

:deep(.menu-item) {
  &:focus {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }
}

:deep(.p-menuitem-link[aria-hidden="true"]) {
  aria-hidden: false !important;
}

:deep(.vendor-dropdown .p-dropdown-item),
:deep(.vendor-dropdown .p-dropdown-label) {
  text-transform: capitalize;
}

.header-toggle {
  margin-right: 10px;
  display: flex;
  align-items: center;
}

.header-toggle-switch {
  transform: scale(0.8);
}

.header-toggle-switch :deep(.p-inputswitch) {
  background: rgba(255, 255, 255, 0.2);
}

.header-toggle-switch :deep(.p-inputswitch:not(.p-disabled):hover) {
  background: rgba(255, 255, 255, 0.3);
}

.header-toggle-switch :deep(.p-inputswitch.p-inputswitch-checked) {
  background: rgba(76, 175, 80, 0.6);
}

.header-toggle-switch :deep(.p-inputswitch.p-inputswitch-checked:not(.p-disabled):hover) {
  background: rgba(76, 175, 80, 0.7);
}
</style>