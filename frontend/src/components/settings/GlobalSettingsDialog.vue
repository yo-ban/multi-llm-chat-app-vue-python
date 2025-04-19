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
            <APIKeysSettings
              v-if="currentSection === 'api-keys'"
              :modelValue="tempSettings.apiKeys" 
              @update:changedKeys="updateChangedKeys"
              @reset="resetApiKeys"
              class="content-no-header"
            />
            
            <VendorModelSelector
              v-if="currentSection === 'vendor-model'"
              v-model:vendor="tempSettings.defaultVendor"
              v-model:model="tempSettings.defaultModel"
              v-model:temperature="tempSettings.defaultTemperature"
              @model-info="updateFromModelInfo"
              class="content-no-header"
            />
            
            <TitleGenerationSettings
              v-if="currentSection === 'title-generation'"
              v-model="titleGenerationSettings"
              @update:modelValue="updateTitleGenerationSettings"
              class="content-no-header"
            />
            
            <OpenRouterModelsSettings
              v-if="currentSection === 'openrouter'"
              v-model="tempSettings.openrouterModels"
              @update:model-value="updateOpenRouterModels"
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
import { ref, computed, watch } from 'vue';
import { useSettingsStore } from '@/store/settings';
import { useConfirm } from 'primevue/useconfirm';
import type { GlobalSettings } from '@/types/settings';
import APIKeysSettings from './APIKeysSettings.vue';
import VendorModelSelector from './VendorModelSelector.vue';
import ModelParametersSettings from './ModelParametersSettings.vue';
import OpenRouterModelsSettings from './OpenRouterModelsSettings.vue';
import TitleGenerationSettings from './TitleGenerationSettings.vue';

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

// 一時的な設定を保持
const tempSettings = ref<GlobalSettings>({
  apiKeys: { ...settingsStore.apiKeys },
  defaultTemperature: settingsStore.defaultTemperature,
  defaultMaxTokens: settingsStore.defaultMaxTokens,
  defaultVendor: settingsStore.defaultVendor,
  defaultModel: settingsStore.defaultModel,
  defaultReasoningEffort: settingsStore.defaultReasoningEffort,
  defaultWebSearch: settingsStore.defaultWebSearch,
  openrouterModels: [...settingsStore.openrouterModels],
  titleGenerationVendor: settingsStore.titleGenerationVendor,
  titleGenerationModel: settingsStore.titleGenerationModel
});

const titleGenerationSettings = computed({
  get: () => ({
    vendor: tempSettings.value.titleGenerationVendor,
    model: tempSettings.value.titleGenerationModel
  }),
  set: (value) => {
    console.log('Updating title generation settings:', value);
    tempSettings.value.titleGenerationVendor = value.vendor;
    tempSettings.value.titleGenerationModel = value.model;
  }
});

// Add watcher for title generation settings
watch(
  [
    () => tempSettings.value.titleGenerationVendor,
    () => tempSettings.value.titleGenerationModel
  ],
  ([newVendor, newModel]) => {
    console.log('Title generation settings changed:', { vendor: newVendor, model: newModel });
  }
);

// ダイアログが表示されるたびに設定を更新
watch(dialogVisible, (newValue) => {
  if (newValue) {
    // ダイアログが開かれたとき、最新の設定を反映
    tempSettings.value = {
      apiKeys: { ...settingsStore.apiKeys },
      defaultTemperature: settingsStore.defaultTemperature,
      defaultMaxTokens: settingsStore.defaultMaxTokens,
      defaultVendor: settingsStore.defaultVendor,
      defaultModel: settingsStore.defaultModel,
      defaultReasoningEffort: settingsStore.defaultReasoningEffort,
      defaultWebSearch: settingsStore.defaultWebSearch,
      openrouterModels: [...settingsStore.openrouterModels],
      titleGenerationVendor: settingsStore.titleGenerationVendor,
      titleGenerationModel: settingsStore.titleGenerationModel
    };
    // 変更キーをリセット
    changedApiKeys.value = {}; 
  }
});

// 未保存の変更があるかチェック (APIキーの変更も考慮)
const hasUnsavedChanges = computed(() => {
    // Check other settings change
    const otherSettingsChanged = JSON.stringify({
      // apiKeys を除外して比較
      defaultTemperature: settingsStore.defaultTemperature,
      defaultMaxTokens: settingsStore.defaultMaxTokens,
      defaultVendor: settingsStore.defaultVendor,
      defaultModel: settingsStore.defaultModel,
      defaultReasoningEffort: settingsStore.defaultReasoningEffort,
      defaultWebSearch: settingsStore.defaultWebSearch,
      openrouterModels: settingsStore.openrouterModels,
      titleGenerationVendor: settingsStore.titleGenerationVendor,
      titleGenerationModel: settingsStore.titleGenerationModel
    }) !== JSON.stringify({
      defaultTemperature: tempSettings.value.defaultTemperature,
      defaultMaxTokens: tempSettings.value.defaultMaxTokens,
      defaultVendor: tempSettings.value.defaultVendor,
      defaultModel: tempSettings.value.defaultModel,
      defaultReasoningEffort: tempSettings.value.defaultReasoningEffort,
      defaultWebSearch: tempSettings.value.defaultWebSearch,
      openrouterModels: tempSettings.value.openrouterModels,
      titleGenerationVendor: tempSettings.value.titleGenerationVendor,
      titleGenerationModel: tempSettings.value.titleGenerationModel
    });

    // Check if API keys changed using our local state
    const apiKeysChanged = Object.keys(changedApiKeys.value).length > 0;

    return otherSettingsChanged || apiKeysChanged;
});

const updateFromModelInfo = (modelInfo: any) => {
  // Directly update maxTokens from the model info
  if (modelInfo && modelInfo.maxTokens) {
    tempSettings.value.defaultMaxTokens = modelInfo.maxTokens;
    console.log('Updated maxTokens to', modelInfo.maxTokens, 'based on model info');
  }
};

const updateOpenRouterModels = (newModels: any[]) => {
  tempSettings.value.openrouterModels = [...newModels];
};

const updateTitleGenerationSettings = (newSettings: { vendor: string; model: string }) => {
  tempSettings.value.titleGenerationVendor = newSettings.vendor;
  tempSettings.value.titleGenerationModel = newSettings.model;
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
  tempSettings.value = {
    apiKeys: { ...settingsStore.apiKeys },
    defaultTemperature: settingsStore.defaultTemperature,
    defaultMaxTokens: settingsStore.defaultMaxTokens,
    defaultVendor: settingsStore.defaultVendor,
    defaultModel: settingsStore.defaultModel,
    defaultReasoningEffort: settingsStore.defaultReasoningEffort,
    defaultWebSearch: settingsStore.defaultWebSearch,
    openrouterModels: [...settingsStore.openrouterModels],
    titleGenerationVendor: settingsStore.titleGenerationVendor,
    titleGenerationModel: settingsStore.titleGenerationModel
  };
  currentSection.value = 'api-keys';
  // 変更キーをリセット
  changedApiKeys.value = {};
};

const onSave = async () => {
  try {
    isSaving.value = true;

    // ストアのアクションに渡すデータを作成
    const settingsToSave = {
      ...tempSettings.value, // 他の設定項目 (apiKeys: boolean を含むが、これは無視される)
      changedApiKeys: changedApiKeys.value // 変更された実際のキー情報
    };

    // ストアの saveSettings アクションを呼び出し
    console.log('Saving settings:', settingsToSave);
    await settingsStore.saveSettings(settingsToSave); 

    // Close the dialog (emit is removed as store is the source of truth)
    dialogVisible.value = false;

  } catch (error) {
    console.error('Failed to save settings:', error);
    // TODO: エラー通知の実装
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