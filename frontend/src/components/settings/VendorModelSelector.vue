<template>
  <div class="vendor-model-selector">    
    <div class="selector-container">
      <div class="parameter-item">
        <div class="parameter-header">
          <label>Default Vendor</label>
        </div>
        <div class="parameter-control">
          <PrimeDropdown
            v-model="selectedVendor"
            :options="vendorOptions"
            optionLabel="name"
            optionValue="id"
            placeholder="Select a vendor"
            class="w-full"
          />
        </div>
        <small class="parameter-description">
          Select the default AI vendor to use for new conversations.
        </small>
      </div>
      
      <div class="parameter-item">
        <div class="parameter-header">
          <label>Default Model</label>
        </div>
        <div class="parameter-control">
          <PrimeDropdown
            v-model="selectedModel"
            :options="availableModels"
            optionLabel="name"
            optionValue="id"
            placeholder="Select a model"
            class="w-full"
            :disabled="!selectedVendor"
          />
        </div>
        <small class="parameter-description">
          Select the default model to use for new conversations.
        </small>
      </div>

      <!-- Default Temperature Setting -->
      <div class="parameter-item" :class="{ 'disabled': selectedModelInfo?.unsupportsTemperature }">
        <div class="parameter-header">
          <label>Default Temperature for All Models</label>
          <span class="parameter-value">{{ temperature.toFixed(2) }}</span>
        </div>
        <div class="slider-container">
          <PrimeSlider
            v-model="temperature"
            :min="0"
            :max="1"
            :step="0.1"
            class="w-full"
            :disabled="selectedModelInfo?.unsupportsTemperature"
          />
          <div class="slider-labels">
            <span>Precise</span>
            <span>Balanced</span>
            <span>Creative</span>
          </div>
        </div>
        <small class="parameter-description" :class="{ 'text-disabled': selectedModelInfo?.unsupportsTemperature }">
          {{ selectedModelInfo?.unsupportsTemperature
            ? 'This model does not support temperature adjustments.'
            : 'Controls randomness in the model\'s responses. Lower values make the output more focused and deterministic, while higher values make it more creative and diverse.'
          }}
        </small>
      </div>
    </div>
    
    <div v-if="selectedModelInfo" class="model-info">
      <h4>Selected Model Information</h4>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">Context Window:</span>
          <span class="info-value">{{ selectedModelInfo.contextWindow.toLocaleString() }} tokens</span>
        </div>
        <div class="info-item">
          <span class="info-label">Max Output Tokens:</span>
          <span class="info-value">{{ selectedModelInfo.maxTokens.toLocaleString() }} tokens</span>
        </div>
        <div class="info-item">
          <span class="info-label">Multimodal Support:</span>
          <span class="info-value">{{ selectedModelInfo.multimodal ? 'Yes' : 'No' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Reasoning Support:</span>
          <span class="info-value">{{ selectedModelInfo.supportsReasoning ? 'Yes' : 'No' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { MODELS } from '@/constants/models';
import { useSettingsStore } from '@/store/settings';

const props = defineProps<{
  vendor: string;
  model: string;
  temperature: number;
}>();

const emit = defineEmits<{
  (e: 'update:vendor', value: string): void;
  (e: 'update:model', value: string): void;
  (e: 'update:temperature', value: number): void;
  (e: 'model-info', modelInfo: any): void;
}>();

const settingsStore = useSettingsStore();

// ベンダーオプションの生成
const vendorOptions = computed(() => {
  return Object.keys(MODELS).map(id => ({
    id,
    name: id.charAt(0).toUpperCase() + id.slice(1)
  }));
});

// 選択中のベンダー
const selectedVendor = computed({
  get: () => props.vendor,
  set: (value) => {
    emit('update:vendor', value);
  }
});

// 利用可能なモデルのリスト
const availableModels = computed(() => {
  if (selectedVendor.value === 'openrouter') {
    return settingsStore.openrouterModels;
  }
  return Object.values(MODELS[selectedVendor.value] || {});
});

// 選択中のモデル
const selectedModel = computed({
  get: () => props.model,
  set: (value) => {
    emit('update:model', value);
  }
});

// 選択中のモデル情報
const selectedModelInfo = computed(() => {
  if (!selectedModel.value) return null;
  
  if (selectedVendor.value === 'openrouter') {
    return settingsStore.openrouterModels.find(m => m.id === selectedModel.value);
  }
  
  const vendorModels = MODELS[selectedVendor.value] || {};
  return Object.values(vendorModels).find(m => m.id === selectedModel.value);
});

// Temperature computed using props and model support
const temperature = computed({
  get: () => props.temperature,
  set: (value: number) => {
    if (!selectedModelInfo.value?.unsupportsTemperature) {
      emit('update:temperature', value);
    }
  }
});

// ベンダー変更時の処理
watch(selectedVendor, (newVendor, oldVendor) => {
  // ベンダーが実際に変更された場合のみモデルをリセット
  if (oldVendor && newVendor !== oldVendor) {
    const models = availableModels.value;
    if (models.length > 0 && !models.some(m => m.id === selectedModel.value)) {
      emit('update:model', models[0].id);
    }
  }
});

// Emit model info when it changes
watch(selectedModelInfo, (newModelInfo) => {
  if (newModelInfo) {
    emit('model-info', newModelInfo);
  }
}, { immediate: true });
</script>

<style scoped>
.vendor-model-selector {
  padding: 16px;
}

.description {
  color: var(--text-color-secondary);
  margin-bottom: 24px;
}

.selector-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 24px;
}

.selector-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selector-item label {
  font-weight: 600;
  color: var(--text-color);
}

.model-info {
  background: var(--surface-card);
  border-radius: 6px;
  padding: 16px;
  margin-top: 24px;
}

.model-info h4 {
  margin: 0 0 16px 0;
  color: var(--text-color);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.info-value {
  font-weight: 600;
  color: var(--text-color);
}

/* Default Temperature styling */
.parameter-item {
  background: var(--surface-card);
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 4px;
}

.parameter-item.disabled {
  opacity: 0.7;
}

.parameter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.parameter-header label {
  font-weight: 600;
  color: var(--text-color);
}

.parameter-value {
  font-family: monospace;
  color: var(--primary-color);
  font-weight: 600;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
}

.parameter-description {
  margin-top: 8px;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.text-disabled {
  opacity: 0.6;
}

.parameter-control {
  margin-bottom: 8px;
}
</style> 