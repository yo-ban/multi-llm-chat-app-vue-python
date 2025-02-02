<template>
  <div class="model-configuration">
    <div class="settings-section">
      <h3 class="settings-section-header">OpenRouter Models</h3>
      <div v-for="(model, index) in modelsList" :key="model.id" class="openrouter-model-item">
        <div class="model-info">
          <span class="model-name">{{ model.name }}</span>
          <span class="model-id">({{ model.id }})</span>
        </div>
        <div class="model-actions">
          <PrimeButton icon="pi pi-pencil" @click="editModel(index)" class="p-button-text" />
          <PrimeButton icon="pi pi-trash" @click="deleteModel(index)" class="p-button-text p-button-danger" />
        </div>
      </div>
      <div class="add-model-button">
        <PrimeButton label="Add Model" icon="pi pi-plus" @click="showAddDialog = true" />
      </div>
    </div>

    <PrimeDialog 
      v-model:visible="showAddDialog" 
      :header="editingIndex === null ? 'Add OpenRouter Model' : 'Edit OpenRouter Model'"
      modal 
      class="model-dialog"
    >
      <div class="model-form">
        <div class="form-field">
          <label for="model-id">Model ID</label>
          <PrimeInputText id="model-id" v-model="tempModel.id" class="w-full" />
        </div>
        <div class="form-field">
          <label for="model-name">Display Name</label>
          <PrimeInputText id="model-name" v-model="tempModel.name" class="w-full" />
        </div>
        <div class="form-field">
          <label for="context-window">Context Window</label>
          <PrimeInputNumber 
            id="context-window" 
            v-model="tempModel.contextWindow" 
            :min="1000" 
            :max="1000000" 
            class="w-full" 
          />
        </div>
        <div class="form-field">
          <label for="max-tokens">Max Tokens</label>
          <PrimeInputNumber 
            id="max-tokens" 
            v-model="tempModel.maxTokens" 
            :min="100" 
            :max="100000" 
            class="w-full" 
          />
        </div>
        <div class="form-field">
          <div class="flex align-items-center">
            <PrimeCheckbox 
              id="multimodal" 
              v-model="tempModel.multimodal" 
              :binary="true" 
            />
            <label for="multimodal" class="ml-2">Supports Images</label>
          </div>
        </div>
      </div>
      <template #footer>
        <PrimeButton 
          label="Cancel" 
          icon="pi pi-times" 
          @click="cancelEdit" 
          class="p-button-text" 
        />
        <PrimeButton 
          label="Save" 
          icon="pi pi-check" 
          @click="saveModel" 
          :disabled="!isValidModel" 
        />
      </template>
    </PrimeDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { ModelConfiguration } from '@/types/models';

const props = defineProps<{
  modelsList: ModelConfiguration[];
}>();

const emit = defineEmits<{
  (e: 'update:modelsList', models: ModelConfiguration[]): void;
}>();

const showAddDialog = ref(false);
const editingIndex = ref<number | null>(null);
const tempModel = ref<ModelConfiguration>({
  id: '',
  name: '',
  contextWindow: 8192,
  maxTokens: 4096,
  multimodal: false,
});

const isValidModel = computed(() => {
  return (
    tempModel.value.id.trim() !== '' &&
    tempModel.value.name.trim() !== '' &&
    tempModel.value.contextWindow > 0 &&
    tempModel.value.maxTokens > 0
  );
});

function editModel(index: number) {
  editingIndex.value = index;
  const model = props.modelsList[index];
  tempModel.value = { ...model };
  showAddDialog.value = true;
}

function deleteModel(index: number) {
  const newModels = [...props.modelsList];
  newModels.splice(index, 1);
  emit('update:modelsList', newModels);
}

function saveModel() {
  if (!isValidModel.value) return;

  const newModels = [...props.modelsList];
  if (editingIndex.value !== null) {
    newModels[editingIndex.value] = { ...tempModel.value };
  } else {
    newModels.push({ ...tempModel.value });
  }
  
  emit('update:modelsList', newModels);
  cancelEdit();
}

function cancelEdit() {
  showAddDialog.value = false;
  editingIndex.value = null;
  tempModel.value = {
    id: '',
    name: '',
    contextWindow: 8192,
    maxTokens: 4096,
    multimodal: false,
  };
}
</script>

<style scoped>
.model-configuration {
  padding: 1rem;
}

.openrouter-model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.model-name {
  font-weight: 600;
}

.model-id {
  color: var(--text-color-secondary);
}

.model-actions {
  display: flex;
  gap: 0.5rem;
}

.add-model-button {
  margin-top: 1rem;
}

.model-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field label {
  font-weight: 500;
}

:deep(.p-dialog-content) {
  min-width: 400px;
}
</style> 