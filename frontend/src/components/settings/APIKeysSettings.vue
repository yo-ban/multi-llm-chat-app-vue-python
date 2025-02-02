<template>
  <div class="api-keys-settings">
    <h3>API Keys Configuration</h3>
    <p class="description">Configure API keys for each vendor. These keys are stored locally and never sent to our servers.</p>
    
    <div class="api-keys-list">
      <div v-for="(key, vendor) in localApiKeys" :key="vendor" class="api-key-item">
        <div class="vendor-header">
          <span class="vendor-name">{{ formatVendorName(vendor) }}</span>
          <div class="key-actions">
            <PrimeButton
              v-if="key"
              icon="pi pi-eye"
              class="p-button-text p-button-sm"
              @click="toggleKeyVisibility(vendor)"
              :class="{ 'p-button-info': isKeyVisible[vendor] }"
            />
            <PrimeButton
              v-if="key"
              icon="pi pi-times"
              class="p-button-text p-button-sm p-button-danger"
              @click="clearApiKey(vendor)"
            />
          </div>
        </div>
        
        <div class="key-input">
          <span class="p-input-icon-right">
            <i v-if="isValidating[vendor]" class="pi pi-spin pi-spinner" />
            <PrimeInputText
              v-model="localApiKeys[vendor]"
              :type="isKeyVisible[vendor] ? 'text' : 'password'"
              :placeholder="`Enter ${formatVendorName(vendor)} API Key`"
              class="w-full"
              @input="onApiKeyInput(vendor)"
            />
          </span>
        </div>
        
        <small v-if="validationErrors[vendor]" class="validation-error">
          {{ validationErrors[vendor] }}
        </small>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import debounce from 'lodash/debounce';

const props = defineProps<{
  modelValue: { [key: string]: string }
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: { [key: string]: string }): void
}>();

const localApiKeys = ref<{ [key: string]: string }>({ ...props.modelValue });
const isKeyVisible = ref<{ [key: string]: boolean }>({});
const isValidating = ref<{ [key: string]: boolean }>({});
const validationErrors = ref<{ [key: string]: string }>({});

// API キーの表示/非表示を切り替え
const toggleKeyVisibility = (vendor: string | number) => {
  const key = String(vendor);
  isKeyVisible.value[key] = !isKeyVisible.value[key];
};

// API キーをクリア
const clearApiKey = (vendor: string | number) => {
  const key = String(vendor);
  localApiKeys.value[key] = '';
  validationErrors.value[key] = '';
  emit('update:modelValue', { ...localApiKeys.value });
};

// ベンダー名のフォーマット
const formatVendorName = (vendor: string | number) => {
  const str = String(vendor);
  return str.charAt(0).toUpperCase() + str.slice(1);
};

// API キーの検証
const validateApiKey = async (vendor: string | number, key: string) => {
  const vendorKey = String(vendor);
  if (!key) {
    validationErrors.value[vendorKey] = '';
    return;
  }

  isValidating.value[vendorKey] = true;
  try {
    // TODO: 各ベンダーのAPI Key検証ロジックを実装
    // 例: OpenAIの場合は /v1/models を叩いてみる等
    await new Promise(resolve => setTimeout(resolve, 500)); // 仮の遅延
    validationErrors.value[vendorKey] = '';
  } catch (error) {
    validationErrors.value[vendorKey] = 'Invalid API key';
  } finally {
    isValidating.value[vendorKey] = false;
  }
};

// 入力値の変更を遅延処理
const debouncedValidation = debounce(validateApiKey, 500);

const onApiKeyInput = (vendor: string | number) => {
  const key = String(vendor);
  const value = localApiKeys.value[key];
  emit('update:modelValue', { ...localApiKeys.value });
  debouncedValidation(key, value);
};

// props の変更を監視
watch(
  () => props.modelValue,
  (newValue) => {
    localApiKeys.value = { ...newValue };
  },
  { deep: true }
);
</script>

<style scoped>
.api-keys-settings {
  padding: 16px;
}

.description {
  color: var(--text-color-secondary);
  margin-bottom: 24px;
}

.api-keys-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.api-key-item {
  background: var(--surface-card);
  border-radius: 6px;
  padding: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.vendor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.vendor-name {
  font-weight: 600;
  color: var(--text-color);
}

.key-actions {
  display: flex;
  gap: 4px;
}

.key-input {
  margin-top: 8px;
}

.validation-error {
  color: var(--red-500);
  display: block;
  margin-top: 4px;
}

:deep(.p-inputtext) {
  width: 100%;
}

:deep(.p-button-sm) {
  padding: 0.4rem;
}

:deep(.p-button-sm .p-button-icon) {
  font-size: 0.875rem;
}
</style> 