<template>
  <div class="openrouter-models-settings">
    <h3>OpenRouter Models</h3>
    <p class="description">Configure custom models available through OpenRouter.</p>
    
    <div class="models-container">
      <div v-if="localModels.length === 0" class="no-models">
        <p>No custom models configured yet.</p>
      </div>
      
      <TransitionGroup name="model-list" tag="div" class="models-list">
        <div v-for="(model, index) in localModels" :key="model.id" class="model-item">
          <div class="model-header">
            <div class="model-title">
              <span class="model-name">{{ model.name }}</span>
              <span class="model-id">({{ model.id }})</span>
            </div>
            <div class="model-actions">
              <PrimeButton
                icon="pi pi-pencil"
                class="p-button-text p-button-sm"
                @click="editModel(index)"
              />
              <PrimeButton
                icon="pi pi-trash"
                class="p-button-text p-button-sm p-button-danger"
                @click="removeModel(index)"
              />
            </div>
          </div>
          
          <div class="model-details">
            <div class="detail-item">
              <span class="detail-label">Context Window:</span>
              <span class="detail-value">{{ model.contextWindow.toLocaleString() }} tokens</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Max Output:</span>
              <span class="detail-value">{{ model.maxTokens.toLocaleString() }} tokens</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Multimodal:</span>
              <span class="detail-value">{{ model.multimodal ? 'Yes' : 'No' }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Function Calling:</span>
              <span class="detail-value">{{ model.supportFunctionCalling ? 'Yes' : 'No' }}</span>
            </div>
          </div>
        </div>
      </TransitionGroup>
      
      <div class="add-model">
        <PrimeButton
          label="Add Model"
          icon="pi pi-plus"
          @click="addModel"
          class="p-button-outlined"
        />
      </div>
    </div>
    
    <PrimeDialog
      v-model:visible="modelDialogVisible"
      :modal="true"
      :draggable="false"
      :header="editingIndex === -1 ? 'Add Model' : 'Edit Model'"
      :style="{ width: '700px' }"
      class="model-dialog"
    >
      <div class="dialog-content">
        <div class="form-field">
          <label>Model ID</label>
          <div class="id-input-container">
            <PrimeInputText
              v-model="editingModel.id"
              placeholder="Enter model ID"
              class="w-full"
            />
            <PrimeButton
              icon="pi pi-refresh"
              class="p-button-text fetch-button"
              @click="fetchModelInfo(editingModel.id)"
              :loading="isLoading"
              :disabled="!editingModel.id"
            />
          </div>
          <small class="error-message" v-if="errorMessage">{{ errorMessage }}</small>
        </div>
        
        <div class="form-field">
          <label>Model Name</label>
          <PrimeInputText
            v-model="editingModel.name"
            placeholder="Enter model name"
            class="w-full"
          />
        </div>
        
        <div class="numeric-fields">
          <div class="form-field">
            <label>Context Window (tokens)</label>
            <PrimeInputNumber
              v-model="editingModel.contextWindow"
              :min="1"
              placeholder="Enter context window size"
              class="w-full"
            />
          </div>
          
          <div class="form-field">
            <label>Max Output Tokens</label>
            <PrimeInputNumber
              v-model="editingModel.maxTokens"
              :min="1"
              placeholder="Enter max output tokens"
              class="w-full"
            />
          </div>
        </div>
        
        <div class="form-field">
          <label class="checkbox-label">
            <PrimeCheckbox
              v-model="editingModel.multimodal"
              :binary="true"
            />
            <span>Supports Multimodal Input</span>
          </label>
        </div>

        <div class="form-field">
          <label class="checkbox-label">
            <PrimeCheckbox
              v-model="editingModel.supportFunctionCalling"
              :binary="true"
            />
            <span>Supports Function Calling (Web Search)</span>
          </label>
        </div>
      </div>
      
      <template #footer>
        <PrimeButton
          label="Cancel"
          icon="pi pi-times"
          @click="closeModelDialog"
          class="p-button-text"
        />
        <PrimeButton
          label="Save"
          icon="pi pi-check"
          @click="saveModel"
          :disabled="!isModelValid"
        />
      </template>
    </PrimeDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { Model } from '@/types/models';
import { openRouterService } from '@/services/api/openrouter-service';
import type { OpenRouterModel } from '@/types/openrouter';

const props = defineProps<{
  modelValue: Model[]
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: Model[]): void
}>();

// ローカルモデルリスト
const localModels = ref<Model[]>([...props.modelValue]);

// 編集用の一時データ
const editingModel = ref<Model>({
  id: '',
  name: '',
  contextWindow: 4096,
  maxTokens: 4096,
  multimodal: false,
  supportFunctionCalling: false
});

const modelDialogVisible = ref(false);
const editingIndex = ref(-1);

// モデル情報の自動補完
const isLoading = ref(false);
const errorMessage = ref('');

async function fetchModelInfo(modelId: string) {
  try {
    isLoading.value = true;
    errorMessage.value = '';
    const models = await openRouterService.fetchModels();
    const model = models.find((m: OpenRouterModel) => m.id === modelId);
    
    if (model) {
      const customModel = openRouterService.convertToCustomModel(model);
      editingModel.value = {
        ...editingModel.value,
        name: customModel.name,
        contextWindow: customModel.contextWindow,
        maxTokens: customModel.maxTokens,
        multimodal: customModel.multimodal,
        supportFunctionCalling: customModel.supportFunctionCalling
      };
    } else {
      errorMessage.value = 'Model not found in OpenRouter API';
    }
  } catch (error) {
    console.error('Error fetching model info:', error);
    errorMessage.value = 'Failed to fetch model information';
  } finally {
    isLoading.value = false;
  }
}

// モデルの追加
const addModel = () => {
  editingIndex.value = -1;
  editingModel.value = {
    id: '',
    name: '',
    contextWindow: 4096,
    maxTokens: 4096,
    multimodal: false,
    supportFunctionCalling: false
  };
  modelDialogVisible.value = true;
};

// モデルの編集
const editModel = (index: number) => {
  editingIndex.value = index;
  editingModel.value = { ...localModels.value[index] };
  modelDialogVisible.value = true;
};

// モデルの削除
const removeModel = (index: number) => {
  localModels.value = localModels.value.filter((_, i) => i !== index);
  emit('update:modelValue', localModels.value);
};

// モデルの保存
const saveModel = () => {
  if (editingIndex.value === -1) {
    localModels.value.push({ ...editingModel.value });
  } else {
    localModels.value[editingIndex.value] = { ...editingModel.value };
  }
  emit('update:modelValue', localModels.value);
  closeModelDialog();
};

// ダイアログを閉じる
const closeModelDialog = () => {
  modelDialogVisible.value = false;
  editingIndex.value = -1;
};

// モデルのバリデーション
const isModelValid = computed(() => {
  return (
    editingModel.value.id.trim() !== '' &&
    editingModel.value.name.trim() !== '' &&
    editingModel.value.contextWindow > 0 &&
    editingModel.value.maxTokens > 0
  );
});
</script>

<style scoped>
.openrouter-models-settings {
  padding: 16px;
}

.description {
  color: var(--text-color-secondary);
  margin-bottom: 24px;
}

.no-models {
  text-align: center;
  padding: 32px;
  background: var(--surface-ground);
  border-radius: 6px;
  color: var(--text-color-secondary);
}

.models-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 24px;
}

.model-item {
  background: var(--surface-card);
  border-radius: 6px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.model-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.model-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-weight: 600;
  color: var(--text-color);
}

.model-id {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.model-actions {
  display: flex;
  gap: 4px;
}

.model-details {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.detail-value {
  font-weight: 500;
  color: var(--text-color);
}

.add-model {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 0;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 数値入力フィールドを横並びにする */
.numeric-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 8px 0;
}

/* 入力フィールドのラベルスタイルを調整 */
.form-field label {
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

/* 入力フィールドのコンテナスタイルを調整 */
.id-input-container {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.fetch-button {
  flex-shrink: 0;
  margin-top: 1px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

/* トランジションアニメーション */
.model-list-move,
.model-list-enter-active,
.model-list-leave-active {
  transition: all 0.3s ease;
}

.model-list-enter-from,
.model-list-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.model-list-leave-active {
  position: absolute;
}

.error-message {
  color: var(--red-500);
  margin-top: 4px;
}
</style> 