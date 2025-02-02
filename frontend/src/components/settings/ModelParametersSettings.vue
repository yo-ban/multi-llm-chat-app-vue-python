<template>
  <div class="model-parameters-settings">
    <h3>Model Parameters</h3>
    <p class="description">Configure default parameters for model generation.</p>
    
    <div class="parameters-container">
      <div class="parameter-item" :class="{ 'disabled': selectedModel?.unsupportsTemperature }">
        <div class="parameter-header">
          <label>Temperature</label>
          <span class="parameter-value">{{ temperature.toFixed(2) }}</span>
        </div>
        <div class="slider-container">
          <PrimeSlider
            v-model="temperature"
            :min="0"
            :max="1"
            :step="0.1"
            class="w-full"
            :disabled="selectedModel?.unsupportsTemperature"
          />
          <div class="slider-labels">
            <span>Precise</span>
            <span>Balanced</span>
            <span>Creative</span>
          </div>
        </div>
        <small class="parameter-description" :class="{ 'text-disabled': selectedModel?.unsupportsTemperature }">
          {{ !selectedModel?.unsupportsTemperature 
            ? 'Controls randomness in the model\'s responses. Lower values make the output more focused and deterministic, while higher values make it more creative and diverse.'
            : 'This model does not support temperature adjustments.' }}
        </small>
      </div>
      
      <div class="parameter-item">
        <div class="parameter-header">
          <label>Max Tokens</label>
          <span class="parameter-value">{{ maxTokens.toLocaleString() }}</span>
        </div>
        <div class="slider-container">
          <PrimeSlider
            v-model="maxTokens"
            :min="1"
            :max="modelMaxTokens"
            :step="1"
            class="w-full"
          />
          <div class="slider-labels">
            <span>1</span>
            <span>{{ Math.floor(modelMaxTokens / 2).toLocaleString() }}</span>
            <span>{{ modelMaxTokens.toLocaleString() }}</span>
          </div>
        </div>
        <small class="parameter-description">
          Maximum number of tokens to generate in the response. One token is roughly 4 characters of English text.
        </small>
      </div>

      <div class="parameter-item">
        <div class="parameter-header">
          <label>Default Reasoning Effort</label>
          <span class="parameter-value">{{ reasoningEffort }}</span>
        </div>
        <div class="dropdown-container">
          <PrimeDropdown
            v-model="reasoningEffort"
            :options="reasoningEffortOptions"
            optionLabel="label"
            optionValue="value"
            class="w-full"
          />
        </div>
        <small class="parameter-description">
          Default reasoning effort level for models that support reasoning capabilities. This setting will be used as the initial value for new chats when using reasoning-capable models.
        </small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { MODELS } from '@/constants/models';
import { useSettingsStore } from '@/store/settings';

const props = defineProps<{
  temperature: number;
  maxTokens: number;
  selectedVendor: string;
  selectedModel: string;
  defaultReasoningEffort?: string;
}>();

const emit = defineEmits<{
  (e: 'update:temperature', value: number): void;
  (e: 'update:maxTokens', value: number): void;
  (e: 'update:defaultReasoningEffort', value: string): void;
}>();

const settingsStore = useSettingsStore();

const reasoningEffortOptions = [
  { label: 'Low', value: 'low' },
  { label: 'Medium', value: 'medium' },
  { label: 'High', value: 'high' }
];

// Temperature setting
const temperature = computed({
  get: () => props.temperature,
  set: (value) => {
    if (!selectedModel.value?.unsupportsTemperature) {
      emit('update:temperature', value);
    }
  }
});

// Add selectedModel computed property
const selectedModel = computed(() => {
  if (props.selectedVendor === 'openrouter') {
    return settingsStore.openrouterModels.find(m => m.id === props.selectedModel);
  }
  const vendorModels = MODELS[props.selectedVendor] || {};
  return Object.values(vendorModels).find(m => m.id === props.selectedModel);
});

// Maximum tokens for the selected model
const modelMaxTokens = computed(() => {
  if (props.selectedVendor === 'openrouter') {
    const model = settingsStore.openrouterModels.find(m => m.id === props.selectedModel);
    return model?.maxTokens || 4096;
  }
  
  const vendorModels = MODELS[props.selectedVendor] || {};
  const model = Object.values(vendorModels).find(m => m.id === props.selectedModel);
  return model?.maxTokens || 4096;
});

// Max tokens setting
const maxTokens = computed({
  get: () => Math.min(props.maxTokens, modelMaxTokens.value),
  set: (value) => emit('update:maxTokens', value)
});

// Reasoning effort setting
const reasoningEffort = computed({
  get: () => props.defaultReasoningEffort || 'medium',
  set: (value) => emit('update:defaultReasoningEffort', value)
});

// Adjust max tokens when model changes
watch(
  [() => props.selectedVendor, () => props.selectedModel],
  () => {
    if (props.maxTokens > modelMaxTokens.value) {
      emit('update:maxTokens', modelMaxTokens.value);
    }
  }
);
</script>

<style scoped>
.model-parameters-settings {
  padding: 16px;
}

.description {
  color: var(--text-color-secondary);
  margin-bottom: 24px;
}

.parameters-container {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.parameter-item {
  background: var(--surface-card);
  border-radius: 6px;
  padding: 16px;
}

.parameter-item.disabled {
  opacity: 0.7;
}

.parameter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
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

.slider-container {
  margin-bottom: 12px;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.parameter-description {
  color: var(--text-color-secondary);
  display: block;
  margin-top: 8px;
  font-size: 0.875rem;
  line-height: 1.4;
}

.text-disabled {
  color: var(--text-color-disabled, var(--text-color-secondary));
}

:deep(.p-slider) {
  background: var(--surface-border);
}

:deep(.p-slider .p-slider-handle) {
  background: var(--primary-color);
  border: 2px solid var(--surface-border);
  transition: background-color 0.2s, border-color 0.2s, transform 0.2s;
}

:deep(.p-slider:not(.p-disabled) .p-slider-handle:hover) {
  background: var(--primary-600);
  border-color: var(--primary-600);
  transform: scale(1.1);
}

:deep(.p-slider-range) {
  background: var(--primary-color);
}

:deep(.p-slider.p-disabled) {
  opacity: 0.7;
}

.dropdown-container {
  width: 100%;
  margin-bottom: 8px;
}
</style> 