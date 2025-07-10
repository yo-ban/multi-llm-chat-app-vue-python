<template>
  <PrimeDialog 
    v-model:visible="dialogVisible"
    modal 
    :style="{ width: '800px' }" 
    :header="'Global Settings'"
    :closable="false"
    :draggable="false"
    @hide="onDialogHide"
  >
    <div class="settings-container">
      <div class="settings-sections">
        <div class="settings-navigation">
          <ul class="settings-tabs">
            <li 
              v-for="section in sections" 
              :key="section.id"
              :class="{ active: currentSection === section.id }"
              @click="currentSection = section.id"
            >
              {{ section.label }}
            </li>
          </ul>
        </div>
        
        <div class="settings-panel">
          <!-- 固定ヘッダー部分 -->
          <div class="settings-header">
            <h3>{{ sectionInfo.title }}</h3>
            <p class="description">{{ sectionInfo.description }}</p>
          </div>
          
          <!-- スクロール可能なコンテンツ部分 -->
          <div class="settings-content">
            <!-- API Keys -->
            <APIKeysSettings
              v-if="currentSection === 'api-keys'"
              :modelValue="tempSettings.apiKeys" 
              @update:changedKeys="updateChangedKeys"
              @reset="resetApiKeys"
              class="content-no-header"
            />
            
            <!-- Vendor & Model -->
            <VendorModelSelector
              v-if="currentSection === 'vendor-model'"
              v-model:vendor="tempSettings.defaultVendor"
              v-model:model="tempSettings.defaultModel"
              v-model:temperature="tempSettings.defaultTemperature"
              @model-info="updateFromModelInfo"
              class="content-no-header"
            />
            
            <!-- Title Generation -->
            <TitleGenerationSettings
              v-if="currentSection === 'title-generation'"
              v-model="titleGenerationSettings"
              @update:modelValue="updateTitleGenerationSettings"
              class="content-no-header"
            />

            <!-- OpenRouter -->
            <OpenRouterModelsSettings
              v-if="currentSection === 'openrouter'"
              v-model="tempSettings.openrouterModels"
              @update:model-value="updateOpenRouterModels"
              class="content-no-header"
            />

            <!-- MCP Servers & Tools -->
            <MCPSettings
              v-if="currentSection === 'mcp'"
              v-model:mcp-servers-config="tempSettings.mcpServersConfig"
              v-model:disabled-mcp-servers="tempSettings.disabledMcpServers"
              v-model:disabled-mcp-tools="tempSettings.disabledMcpTools"
              :available-mcp-tools="availableMcpTools"
              class="content-no-header"
            />
          </div>
        </div>
      </div>
    </div>
    
    <template #footer>
      <div class="dialog-footer">
        <span v-if="hasUnsavedChanges" class="unsaved-changes-message">
          <i class="pi pi-exclamation-circle" style="color: var(--yellow-500)"></i>
          You have unsaved changes
        </span>
        <div class="dialog-buttons">
          <PrimeButton
            label="Cancel"
            icon="pi pi-times"
            @click="onCancel"
            class="p-button-text"
          />
          <PrimeButton
            label="Save"
            icon="pi pi-check"
            @click="onSave"
            :loading="isSaving"
            :disabled="!hasUnsavedChanges"
            class="p-button-primary"
            :class="{ 'p-button-highlighted': hasUnsavedChanges }"
          />
        </div>
      </div>
    </template>
  </PrimeDialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue';
import { useSettingsStore } from '@/store/settings';
import { useConfirm } from 'primevue/useconfirm';
import type { GlobalSettings } from '@/types/settings';
import type { CanonicalToolDefinition } from '@/types/mcp';
import APIKeysSettings from './APIKeysSettings.vue';
import VendorModelSelector from './VendorModelSelector.vue';
import OpenRouterModelsSettings from './OpenRouterModelsSettings.vue';
import TitleGenerationSettings from './TitleGenerationSettings.vue';
import MCPSettings from './MCPSettings.vue';

const props = defineProps<{
  modelValue: boolean
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'save', settings: GlobalSettings): void
}>();

const settingsStore = useSettingsStore();
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
});

const currentSection = ref('api-keys');
const isSaving = ref(false);

// 変更されたAPIキーを保持する状態
const changedApiKeys = ref<{ [key: string]: string }>({});

// 子コンポーネントからの変更キーを更新
const updateChangedKeys = (keys: { [key: string]: string }) => {
  changedApiKeys.value = keys;
};

// APIキーの変更をリセット
const resetApiKeys = () => {
  changedApiKeys.value = {};
};

// 各セクションの情報を定義
const sections = [
  { 
    id: 'api-keys', 
    label: 'API Keys',
    title: 'API Keys Configuration',
    description: 'Configure API keys for each vendor. These keys are stored locally and never sent to our servers.'
  },
  { 
    id: 'vendor-model', 
    label: 'Default Model',
    title: 'Default Vendor & Model',
    description: 'Select the default vendor and model to use for new conversations.'
  },
  { 
    id: 'title-generation', 
    label: 'Title Generation',
    title: 'Title Generation Model',
    description: 'Configure the model used for generating chat titles.'
  },
  { 
    id: 'openrouter', 
    label: 'OpenRouter Models',
    title: 'OpenRouter Models',
    description: 'Configure custom models available through OpenRouter.'
  },
  {
    id: 'mcp',
    label: 'MCP Servers & Tools',
    title: 'MCP Servers & Tools',
    description: 'Manage Model Context Protocol (MCP) servers and enable/disable tools.'
  },
];

// 現在選択されているセクションの情報
const sectionInfo = computed(() => {
  const currentSectionInfo = sections.find(section => section.id === currentSection.value);
  return {
    title: currentSectionInfo?.title || '',
    description: currentSectionInfo?.description || ''
  };
});

const confirm = useConfirm();

// Helper functions
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

function copySettingsFromStore(): GlobalSettings {
  return deepClone(settingsStore.$state);
}

// 一時的な設定を保持 (reactive を使用してネストされたオブジェクトの変更を追跡)
const tempSettings = reactive<GlobalSettings>(copySettingsFromStore());

// 利用可能なMCPツールリスト (これはストアから直接取得し、変更しない)
const availableMcpTools = computed<CanonicalToolDefinition[]>(() => settingsStore.availableMcpTools);

const titleGenerationSettings = computed({
  get: () => ({
    vendor: tempSettings.titleGenerationVendor,
    model: tempSettings.titleGenerationModel
  }),
  set: (value) => {
    tempSettings.titleGenerationVendor = value.vendor;
    tempSettings.titleGenerationModel = value.model;
  }
});

// tempSettingsをストアの最新データで同期する関数
function syncTempSettingsFromStore() {
  const freshSettings = copySettingsFromStore();
  
  // Vue3のreactiveオブジェクトを正しく更新するため、各プロパティを個別に設定
  Object.keys(freshSettings).forEach(key => {
    const typedKey = key as keyof GlobalSettings;
    (tempSettings as any)[typedKey] = (freshSettings as any)[typedKey];
  });
  
  // freshSettingsに存在しないキーは削除
  Object.keys(tempSettings).forEach(key => {
    if (!(key in freshSettings)) {
      delete (tempSettings as any)[key];
    }
  });
}

// ダイアログが表示されるたびに設定を更新
watch(dialogVisible, (newValue) => {
  if (newValue) {
    // ダイアログが開かれたとき、最新の設定をストアから tempSettings に同期
    syncTempSettingsFromStore();
    // 変更キーをリセット
    changedApiKeys.value = {};
  }
});

// Helper function to prepare settings for comparison
function prepareSettingsForComparison(settings: any) {
  const settingsCopy = { ...settings };
  delete settingsCopy.apiKeys;
  delete settingsCopy.availableMcpTools;
  return settingsCopy;
}

// 未保存の変更があるかチェック
const hasUnsavedChanges = computed(() => {
    // Store の現在の状態と一時設定を比較
    const originalSettings = deepClone(settingsStore.$state);
    const currentTempSettings = deepClone(tempSettings);

    // APIキー以外の設定変更をチェック (ディープ比較)
    const settingsToCompareOriginal = prepareSettingsForComparison(originalSettings);
    const settingsToCompareTemp = prepareSettingsForComparison(currentTempSettings);

    const otherSettingsChanged = JSON.stringify(settingsToCompareOriginal) !== JSON.stringify(settingsToCompareTemp);
    // APIキーの変更をチェック
    const apiKeysChanged = Object.keys(changedApiKeys.value).length > 0;

    return otherSettingsChanged || apiKeysChanged;
});

const updateFromModelInfo = (modelInfo: any) => {
  // Directly update maxTokens from the model info
  if (modelInfo?.maxTokens) {
    tempSettings.defaultMaxTokens = modelInfo.maxTokens;
  }
};

const updateOpenRouterModels = (newModels: any[]) => {
  tempSettings.openrouterModels = [...newModels];
};

const updateTitleGenerationSettings = (newSettings: { vendor: string; model: string }) => {
  tempSettings.titleGenerationVendor = newSettings.vendor;
  tempSettings.titleGenerationModel = newSettings.model;
};

// ダイアログのアクション
const onCancel = () => {
  if (hasUnsavedChanges.value) {
    // PrimeVueの確認ダイアログを使用
    confirm.require({
      message: 'You have unsaved changes. Are you sure you want to close?',
      header: 'Confirm',
      icon: 'pi pi-exclamation-triangle',
      accept: () => {
        dialogVisible.value = false;
      }
    });
  } else {
    dialogVisible.value = false;
  }
};

const onDialogHide = () => {
  // リセット処理
  currentSection.value = sections[0].id; // 最初のセクションに戻す
  changedApiKeys.value = {}; // APIキー変更もリセット
};

// Helper function to prepare settings for saving
function prepareSettingsForSave() {
  const settingsToSave: Partial<GlobalSettings> & { changedApiKeys?: Record<string, string> } = {
    ...deepClone(tempSettings),
    changedApiKeys: changedApiKeys.value
  };
  // 保存対象外のプロパティを削除
  delete (settingsToSave as any).availableMcpTools;
  delete (settingsToSave as any).apiKeys;
  return settingsToSave;
}

const onSave = async () => {
  try {
    isSaving.value = true;

    const settingsToSave = prepareSettingsForSave();
    await settingsStore.saveSettings(settingsToSave);

    // 保存成功後、tempSettingsを最新のストアの状態で更新
    syncTempSettingsFromStore();

    dialogVisible.value = false; // 保存成功したらダイアログを閉じる

  } catch (error) {
    console.error('Failed to save settings:', error);
    // TODO: エラー通知の実装 (PrimeVue Toast など)
  } finally {
    isSaving.value = false;
  }
};

</script>

<style scoped>
.settings-container {
  display: flex;
  flex-direction: column;
  height: 600px;
  overflow: hidden;
}

.settings-sections {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.settings-navigation {
  width: 200px;
  border-right: 1px solid var(--surface-border);
  background-color: var(--surface-section);
}

.settings-tabs {
  list-style: none;
  padding: 0;
  margin: 0;
}

.settings-tabs li {
  padding: 12px 16px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-left: 3px solid transparent;
}

.settings-tabs li:hover {
  background-color: var(--surface-hover);
}

.settings-tabs li.active {
  background-color: var(--surface-hover);
  border-left-color: var(--primary-color);
  font-weight: 600;
}

.settings-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.settings-header {
  padding: 20px 20px 0;
  background-color: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
}

.settings-header h3 {
  margin-top: 0;
  margin-bottom: 8px;
}

.settings-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.content-no-header {
  padding-top: 0;
}

.content-no-header h3,
.content-no-header .description {
  display: none;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.dialog-buttons {
  display: flex;
  gap: 8px;
}

.unsaved-changes-message {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--yellow-700);
  font-size: 0.875rem;
}

:deep(.p-button-highlighted) {
  background: var(--primary-600);
  border-color: var(--primary-600);
}

:deep(.p-button-highlighted:hover) {
  background: var(--primary-700) !important;
  border-color: var(--primary-700) !important;
}

.description {
  color: var(--text-color-secondary);
  margin-bottom: 24px;
}
</style> 