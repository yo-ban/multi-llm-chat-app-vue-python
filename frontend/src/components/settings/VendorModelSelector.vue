<template>
  <div class="vendor-model-selector">    
    <div class="selector-container">
      <div class="selector-item">
        <label>Default Vendor</label>
        <PrimeDropdown
          v-model="selectedVendor"
          :options="vendorOptions"
          optionLabel="name"
          optionValue="id"
          placeholder="Select a vendor"
          class="w-full"
        />
      </div>
      
      <div class="selector-item">
        <label>Default Model</label>
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
}>();

const emit = defineEmits<{
  (e: 'update:vendor', value: string): void;
  (e: 'update:model', value: string): void;
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
</style> 