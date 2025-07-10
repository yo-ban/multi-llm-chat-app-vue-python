<template>
  <PrimeDialog :visible="visible" :modal="true" :closable="false" :header="isEdit ? 'Edit Role' : 'Add New Role'" :style="{ width: '600px' }">
    <div class="p-fluid">
      <div class="p-field">
        <div class="p-inputgroup">
          <div class="persona-image-container">
            <div class="persona-image-wrapper" @click="onImageClick">
              <img v-if="personaData.image" :src="personaData.image" :alt="personaData.name" class="persona-image-preview" />
              <img v-else :src="defaultIcon" alt="Avatar" class="persona-image-preview" />
            </div>
            <input ref="fileInput" type="file" accept="image/*" @change="onImageSelect" style="display: none;" />
          </div>
          <PrimeInputText id="name" v-model="personaData.name" placeholder="Role Name" />
        </div>
      </div>
      <div class="p-field">
        <label for="systemMessage">System Message</label>
        <PrimeTextarea id="systemMessage" v-model="personaData.systemMessage" rows="5" />
      </div>
    </div>
    <template #footer>
      <PrimeButton label="Cancel" icon="pi pi-times" class="p-button-text" @click="closeDialog" />
      <PrimeButton label="Save" icon="pi pi-check" @click="savePersona" />
    </template>
  </PrimeDialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import type { UserDefinedPersona } from '@/types/personas';

const props = defineProps<{
  visible: boolean;
  isEdit: boolean;
  persona?: UserDefinedPersona;
}>();

const defaultIcon = computed(() => {
    return new URL('../assets/images/persona.svg', import.meta.url).href;
});

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'save', persona: UserDefinedPersona): void;
}>();

// Helper function to create default persona data
function createDefaultPersonaData(): UserDefinedPersona {
  return {
    id: '',
    name: '',
    image: '',
    systemMessage: '',
    custom: true,
  };
}

// Helper function to read file as data URL
function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Helper function to load default SVG as base64
async function loadDefaultImageAsBase64(): Promise<string | null> {
  try {
    const response = await fetch(defaultIcon.value);
    const svgText = await response.text();
    const svgBase64 = btoa(svgText);
    return `data:image/svg+xml;base64,${svgBase64}`;
  } catch (error) {
    return null;
  }
}

const personaData = ref<UserDefinedPersona>(createDefaultPersonaData());

const fileInput = ref<HTMLInputElement | null>(null);

const onImageClick = () => {
  fileInput.value?.click();
};

const onImageSelect = async (event: Event) => {
  const files = (event.target as HTMLInputElement).files;
  if (files && files.length > 0) {
    const file = files[0];
    try {
      personaData.value.image = await readFileAsDataURL(file);
    } catch (error) {
      // Failed to read file, image remains unchanged
    }
  }
};

const resetForm = () => {
  personaData.value = createDefaultPersonaData();
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

const closeDialog = () => {
  emit('update:visible', false);
};

const savePersona = async () => {
  if (!personaData.value.image) {
    const defaultImage = await loadDefaultImageAsBase64();
    if (defaultImage) {
      personaData.value.image = defaultImage;
    }
  }
  emit('save', personaData.value);
  resetForm();
};

const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value),
});

watch(
  () => props.persona,
  (newPersona) => {
    if (newPersona) {
      personaData.value = { ...newPersona };
    } else {
      resetForm();
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.p-inputtextarea {
  max-width: 100%;
  min-height: 500px;
  font-size: small;
}

.p-field {
  margin-bottom: 10px;
}

.p-field label {
  font-weight: 600;
  margin-bottom: 10px;
}

.persona-image-preview {
  max-width: 50px;
  max-height: 50px;
  object-fit: contain;
}

.p-dialog-footer {
  padding: 10px 20px;
  display: flex;
  justify-content: flex-end;
}

.p-button {
  margin-left: 10px;
}

.p-inputgroup {
  display: flex;
  align-items: center;
}

.persona-image-container {
  position: relative;
  margin-right: 10px;
}

.persona-image-wrapper {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f0f0;
  transition: background-color 0.3s;
}

.persona-image-wrapper:hover {
  background-color: #e0e0e0;
}

.persona-image-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.persona-image-placeholder {
  font-size: 24px;
  color: #999;
}
</style>
