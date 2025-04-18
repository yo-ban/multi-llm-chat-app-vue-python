<template>
  <div class="api-keys-settings">
    <div class="api-keys-list">
      <div v-for="(isSet, vendor) in modelValue" :key="vendor" class="api-key-item">
        <div class="vendor-header">
          <div class="vendor-info">
            <span class="vendor-name">{{ formatVendorName(vendor) }}</span>
            <span :class="['key-status', isSet ? 'key-configured' : 'key-not-configured']">
              <i :class="isSet ? 'pi pi-check-circle' : 'pi pi-times-circle'"></i>
              {{ isSet ? 'Configured' : 'Not configured' }}
            </span>
          </div>
          <div class="key-actions">
            <PrimeButton
              v-if="isSet"
              icon="pi pi-refresh"
              class="p-button-text p-button-sm p-button-secondary"
              @click="onInputFocus(vendor)"
              tooltip="Update key"
              tooltipOptions="{ position: 'top' }"
            />
            <PrimeButton
              v-if="localApiKeysInput[vendor]"
              icon="pi pi-times"
              class="p-button-text p-button-sm p-button-danger"
              @click="clearApiKey(vendor)"
              tooltip="Remove key"
              tooltipOptions="{ position: 'top' }"
            />
          </div>
        </div>
        
        <div class="key-input">
          <span class="p-input-icon-right">
            <i v-if="isValidating[vendor]" class="pi pi-spin pi-spinner" />
            <PrimeInputText
              v-model="localApiKeysInput[vendor]"
              :type="getInputType(vendor)"
              :placeholder="getPlaceholder(vendor)"
              class="w-full"
              @input="onApiKeyInput(vendor)"
              @focus="onInputFocus(vendor)"
              :class="{ 'key-field-configured': isSet && localApiKeysInput[vendor] === maskedPlaceholder }"
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
import { ref, watch, computed } from 'vue';

const props = defineProps<{
  modelValue: { [key: string]: boolean } // isSet の Map を受け取る
}>();

// カスタムイベントを定義
const emit = defineEmits<{
  'update:changedKeys': [{ [key: string]: string }]
  'reset': [] // リセットイベントを追加
}>();

// ローカルでユーザーの入力を保持する状態 (実際のキーまたはプレースホルダー)
const localApiKeysInput = ref<{ [key: string]: string }>({});
// 変更されたキーのみを保持する状態 (実際のキーまたは空文字)
const changedKeys = ref<{ [key: string]: string }>({});
// マスク用プレースホルダー
const maskedPlaceholder = '********';

const isKeyVisible = ref<{ [key: string]: boolean }>({});
const isValidating = ref<{ [key: string]: boolean }>({});
const validationErrors = ref<{ [key: string]: string }>({});

// 入力フィールドのタイプを決定
const getInputType = (vendor: string | number) => {
    const key = String(vendor);
    // キーが表示可能状態 or プレースホルダーでない場合 は 'text'
    if (isKeyVisible.value[key] || localApiKeysInput.value[key] !== maskedPlaceholder) {
        return 'text';
    }
    // それ以外（マスク状態）は 'password'
    return 'password';
};

// プレースホルダーを決定
const getPlaceholder = (vendor: string | number) => {
    const key = String(vendor);
    // 設定済み（プレースホルダー表示中）かつキー非表示状態なら空
    if (localApiKeysInput.value[key] === maskedPlaceholder && !isKeyVisible.value[key]) {
        return `${formatVendorName(vendor)} API Key is configured`;
    }
    // 未設定またはキー表示状態なら具体的なプレースホルダー
    return `Enter ${formatVendorName(vendor)} API Key`;
};

// フォーカス時にプレースホルダーを実際の入力値に切り替え
const onInputFocus = (vendor: string | number) => {
    const key = String(vendor);
    if (localApiKeysInput.value[key] === maskedPlaceholder) {
        localApiKeysInput.value[key] = ''; // 入力のためにクリア
    }
};

// 現在有効な変更キーを計算
const actualChangedKeys = computed(() => {
  const keys: { [key: string]: string } = {};
  for (const vendor in changedKeys.value) {
    if (changedKeys.value[vendor] !== maskedPlaceholder) {
      keys[vendor] = changedKeys.value[vendor];
    }
  }
  return keys;
});

// 変更を監視して親コンポーネントに通知
watch(
  actualChangedKeys,
  (newChangedKeys) => {
    emit('update:changedKeys', newChangedKeys);
  },
  { deep: true }
);

// APIキー入力ハンドラ
const onApiKeyInput = (vendor: string | number) => {
  const key = String(vendor);
  const currentValue = localApiKeysInput.value[key];

  // ユーザーが手動でプレースホルダーと同じ文字列を入力することは想定しない
  // もし入力値が空になったら変更リストにも空を反映 (クリアボタンと同様)
  if (currentValue === '') {
      changedKeys.value[key] = '';
  } else if (currentValue && currentValue !== maskedPlaceholder) {
      changedKeys.value[key] = currentValue;
  } else {
      // プレースホルダーが表示されている場合（通常フォーカスが外れた時）は変更リストから削除
      delete changedKeys.value[key];
  }
};

// APIキークリア処理
const clearApiKey = (vendor: string | number) => {
  const key = String(vendor);
  localApiKeysInput.value[key] = ''; // ローカル入力をクリア
  changedKeys.value[key] = ''; // 変更リストに空文字を設定（削除シグナル）
  isKeyVisible.value[key] = false; // マスク状態に戻す
  validationErrors.value[key] = '';
};

// ベンダー名のフォーマット
const formatVendorName = (vendor: string | number) => {
  const str = String(vendor);
  return str.charAt(0).toUpperCase() + str.slice(1);
};

// props.modelValue (isSet Map) が変更されたらローカル入力を初期化
watch(
  () => props.modelValue,
  (isConfiguredMap) => {
    const initialInputState: { [key: string]: string } = {};
    for (const vendor in isConfiguredMap) {
      initialInputState[vendor] = isConfiguredMap[vendor] ? maskedPlaceholder : '';
    }
    localApiKeysInput.value = initialInputState;
    // Props変更時には変更リストをリセット
    changedKeys.value = {}; 
  },
  { deep: true, immediate: true }
);

// リセットを処理するイベントリスナーを追加
watch(
  () => props,
  () => {
    // 親コンポーネントから'reset'イベントをリッスン
    const onReset = () => {
      changedKeys.value = {};
    };
    
    // 親から'reset'イベントが来たときにローカルの変更をリセット
    onReset();
  }
);
</script>

<style scoped>
.api-keys-settings {
  /* padding: 16px; パディングを親コンポーネントで管理 */
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
  border-left: 3px solid var(--surface-border);
  transition: all 0.2s ease;
}

.api-key-item:hover {
  border-left-color: var(--primary-300);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.vendor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.vendor-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vendor-name {
  font-weight: 600;
  color: var(--text-color);
  font-size: 1rem;
}

.key-actions {
  display: flex;
  gap: 4px;
}

.key-input {
  margin-top: 8px;
  margin-bottom: 8px;
}

.validation-error {
  color: var(--red-500);
  display: block;
  margin-top: 4px;
  font-size: 0.875rem;
}

.key-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
}

.key-configured {
  color: var(--green-500);
}

.key-not-configured {
  color: var(--text-color-secondary);
}

.key-field-configured {
  background-color: var(--surface-hover);
  border-color: var(--surface-border);
  color: var(--text-color-secondary);
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