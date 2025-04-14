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
        
        <div class="settings-content">
          <APIKeysSettings
            v-if="currentSection === 'api-keys'"
            v-model="tempSettings.apiKeys"
            @update:model-value="updateAPIKeys"
          />
          
          <VendorModelSelector
            v-if="currentSection === 'vendor-model'"
            v-model:vendor="tempSettings.defaultVendor"
            v-model:model="tempSettings.defaultModel"
            @update:vendor="updateVendorModel"
          />
          
          <ModelParametersSettings
            v-if="currentSection === 'parameters'"
            v-model:temperature="tempSettings.defaultTemperature"
            v-model:maxTokens="tempSettings.defaultMaxTokens"
            v-model:defaultReasoningEffort="tempSettings.defaultReasoningEffort"
            :selectedVendor="tempSettings.defaultVendor"
            :selectedModel="tempSettings.defaultModel"
          />
          
          <TitleGenerationSettings
            v-if="currentSection === 'title-generation'"
            v-model="titleGenerationSettings"
            @update:modelValue="updateTitleGenerationSettings"
          />
          
          <OpenRouterModelsSettings
            v-if="currentSection === 'openrouter'"
            v-model="tempSettings.openrouterModels"
            @update:model-value="updateOpenRouterModels"
          />
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

const sections = [
  { id: 'api-keys', label: 'API Keys' },
  { id: 'vendor-model', label: 'Default Model' },
  { id: 'parameters', label: 'Parameters' },
  { id: 'title-generation', label: 'Title Generation' },
  { id: 'openrouter', label: 'OpenRouter Models' },
];

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
  }
});

// 設定が変更されたかどうかを追跡
const hasUnsavedChanges = computed(() => {
  return (
    JSON.stringify({
      apiKeys: settingsStore.apiKeys,
      defaultTemperature: settingsStore.defaultTemperature,
      defaultMaxTokens: settingsStore.defaultMaxTokens,
      defaultVendor: settingsStore.defaultVendor,
      defaultModel: settingsStore.defaultModel,
      defaultReasoningEffort: settingsStore.defaultReasoningEffort,
      defaultWebSearch: settingsStore.defaultWebSearch,
      openrouterModels: settingsStore.openrouterModels,
      titleGenerationVendor: settingsStore.titleGenerationVendor,
      titleGenerationModel: settingsStore.titleGenerationModel
    }) !== JSON.stringify(tempSettings.value)
  );
});

// 各セクションの更新ハンドラー
const updateAPIKeys = (newApiKeys: { [key: string]: string }) => {
  tempSettings.value.apiKeys = { ...newApiKeys };
};

const updateVendorModel = () => {
  // ベンダーが変更された場合、対応するモデルのmaxTokensに合わせて更新
  const selectedModel = settingsStore.getModelById(tempSettings.value.defaultModel);
  if (selectedModel) {
    tempSettings.value.defaultMaxTokens = Math.min(
      tempSettings.value.defaultMaxTokens,
      selectedModel.maxTokens
    );
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
};

const onSave = async () => {
  try {
    isSaving.value = true;

    // Call the store's save action
    await settingsStore.saveSettings(tempSettings.value);

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

.settings-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
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
</style> 