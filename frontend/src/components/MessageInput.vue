<template>
  <div class="input-container" @dragover.prevent="handleDragOver" @dragleave.prevent="handleDragLeave" @drop.prevent="handleDrop">
    <div v-if="dragActive" class="drag-overlay">
      Drop image to upload
    </div>
    <div class="input-wrapper" :class="{ 'disabled': !isApiKeySet }">
      <textarea
        v-model="newMessage"
        @keydown="onKeyDown"
        @paste="onPaste"
        :placeholder="isApiKeySet ? 'Type a message (Shift + Enter to break line)' : 'Please set up API key in settings to start chatting'"
        :disabled="!!errorMessage || !isApiKeySet"
        rows="1"
        ref="textareaRef"
      ></textarea>
      <VTooltip v-if="!isStreaming" placement="top" popper-class="tooltip-content">
        <template #popper>
          <template v-if="isMultimodalModel">
            Upload images<br>
            (Max 20mb each)
          </template>
          <template v-else>
            This model does not support image input
          </template>
        </template>
        <FileUploader
          @file-uploaded="onFileUpload"
          @image-uploaded="onImageUpload"
          :disabled="isStreaming || !!errorMessage || !isMultimodalModel"
          :accepted-file-types="acceptedFileTypeImages"
          :use-image-icon="true"
          ref="fileUploaderRef"
        />
      </VTooltip>
      <div v-if="uploadedImages.length > 0" class="image-preview">
        <div v-for="(image, index) in uploadedImages" :key="index" class="image-wrapper">
          <img :src="image" alt="Uploaded Image" />
          <button @click="removeImage(index)" class="remove-image-button">
            <font-awesome-icon icon="times" />
          </button>
        </div>
      </div>
    </div>
    <button
      @click="sendMessage"
      :disabled="isStreaming || !!errorMessage || !isApiKeySet"
      :class="{ 'disabled': isStreaming || !!errorMessage || !isApiKeySet }"
    >
      <font-awesome-icon icon="paper-plane" v-if="!isStreaming" />
      <div v-if="isStreaming" class="stop-button" @click.stop="cancelStreaming">
        <div class="stop-icon"></div>
      </div>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch, computed } from 'vue';
import type { APISettings } from '@/types/api';
import FileUploader from '@/components/FileUploader.vue';
import { useConversationStore } from '@/store/conversation';
import { useSettingsStore } from '@/store/settings';
import { MODELS } from '@/constants/models';
import type { Conversation } from '@/types/conversation';
const props = defineProps({
  isStreaming: {
    type: Boolean,
    required: true,
  },
  errorMessage: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(['send-message', 'cancel-streaming', 'image-dropped']);

const newMessage = ref('');
const uploadedImages = ref<string[]>([]);
const scrollTop = ref(0);

const textareaRef = ref<HTMLTextAreaElement | null>(null);
const fileUploaderRef = ref<InstanceType<typeof FileUploader> | null>(null);

// png, jpg, jpeg
const acceptedFileTypeImages = ref('.png, .jpeg, .jpg');

const conversationStore = useConversationStore();

const settingsStore = useSettingsStore();

const isApiKeySet = computed(() => {
  const vendor = currentConversationSettings.value.vendor;
  return !!settingsStore.apiKeys[vendor];
});

const currentConversation = computed<Conversation | undefined>(() => {
  return conversationStore.conversationList.find(
    conversation => conversation.conversationId === conversationStore.currentConversationId
  );
});

const currentConversationSettings = computed<APISettings>(() => {
  return currentConversation.value ? currentConversation.value.settings: {
    vendor: settingsStore.defaultVendor,
    model: settingsStore.defaultModel,
    maxTokens: 4096,
    temperature: 0.5,
  };
});

// Helper functions
function getModelByVendorAndId(vendor: string, modelId: string) {
  if (vendor === 'openrouter') {
    return settingsStore.openrouterModels.find(m => m.id === modelId);
  }
  return Object.values(MODELS[vendor] || {}).find((m) => m.id === modelId);
}

function readFileAsDataURL(file: File | Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function validateImage(dataURL: string): Promise<boolean> {
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => resolve(image.width > 0 && image.height > 0);
    image.onerror = () => resolve(false);
    image.src = dataURL;
  });
}

const isMultimodalModel = computed(() => {
  const { vendor, model } = currentConversationSettings.value;
  const currentModel = getModelByVendorAndId(vendor, model);
  return currentModel ? currentModel.multimodal : false;
});

const dragActive = ref(false);

const sendMessage = () => {
  if (!isApiKeySet.value) return;
  
  const hasMessage = !!newMessage.value;
  const hasImages = uploadedImages.value.length > 0;
  
  if (!hasMessage && !hasImages) return;
  
  const messageToSend = hasMessage ? newMessage.value : "Please describe this image(s).";
  emit('send-message', messageToSend, uploadedImages.value);
  
  // Clear inputs
  newMessage.value = '';
  uploadedImages.value = [];
};

const cancelStreaming = () => {
  emit('cancel-streaming');
};

const onKeyDown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey && !props.isStreaming) {
    event.preventDefault();
    sendMessage();
  }
};

const onFileUpload = async (fileContents: { [key: string]: string }) => {
  const conversation = currentConversation.value;
  if (!conversation) return;

  const updatedFiles = {
    ...conversation.files,
    ...fileContents,
  };

  await conversationStore.updateConversationFiles(
    conversation.conversationId, 
    updatedFiles
  );
};

const onImageUpload = (images: string[]) => {
  uploadedImages.value = [...uploadedImages.value, ...images];
  
  // 画像のアップロード処理が完了した後、ファイル入力要素をクリアする
  const fileUploader = fileUploaderRef.value;
  if (fileUploader && fileUploader.fileInput) {
    fileUploader.fileInput.value = '';
  }
};

const removeImage = (index: number) => {
  uploadedImages.value.splice(index, 1);
};

// Process images from various sources (paste, drop)
async function processImageFiles(files: (File | Blob)[]) {
  if (!isMultimodalModel.value) return;
  
  const validImages: string[] = [];
  
  for (const file of files) {
    if (file.type.startsWith('image/')) {
      try {
        const dataURL = await readFileAsDataURL(file);
        if (await validateImage(dataURL)) {
          validImages.push(dataURL);
        }
      } catch (error) {
        console.warn('Invalid image:', error);
      }
    }
  }
  
  if (validImages.length > 0) {
    onImageUpload(validImages);
  }
}

const onPaste = async (event: ClipboardEvent) => {
  const items = event.clipboardData?.items;
  if (!items) return;

  const files: File[] = [];
  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/') && isMultimodalModel.value) {
      const blob = item.getAsFile();
      if (blob) files.push(blob);
    }
  }
  
  if (files.length > 0) {
    await processImageFiles(files);
  }
};

// Constants
const MAX_TEXTAREA_HEIGHT_RATIO = 0.7;

const adjustTextareaHeight = () => {
  const textarea = textareaRef.value;
  if (!textarea) return;
  
  scrollTop.value = textarea.scrollTop;
  textarea.style.height = 'auto';
  textarea.style.height = textarea.scrollHeight + 'px';

  const maxHeight = window.innerHeight * MAX_TEXTAREA_HEIGHT_RATIO;

  if (textarea.scrollHeight > maxHeight) {
    textarea.style.height = maxHeight + 'px';
    textarea.style.overflowY = 'auto';
  } else {
    textarea.style.overflowY = 'hidden';
  }
  textarea.scrollTop = scrollTop.value;
};

onMounted(() => {
  nextTick(() => {
    adjustTextareaHeight();
  });
});

watch(newMessage, () => {
  nextTick(() => {
    adjustTextareaHeight();
  });
});

const handleDragOver = (event: DragEvent) => {
  if (!isMultimodalModel.value) return;
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy';
  }
  dragActive.value = true;
};

const handleDragLeave = () => {
  if (!isMultimodalModel.value) return;
  dragActive.value = false;
};

const handleDrop = async (event: DragEvent) => {
  if (!isMultimodalModel.value) return;
  dragActive.value = false;
  
  const files = event.dataTransfer?.files;
  if (files && files.length > 0) {
    await processImageFiles(Array.from(files));
  }
};
</script>

<style scoped>
.input-container {
  position: relative;
  display: flex;
  align-items: center;
  padding: 8px 15px;
  background-color: #fffdfa;
  box-shadow: 0px -2px 10px rgba(0, 0, 0, 0.1);
  z-index: 10;
}
.input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 10px;
  background-color: #fffefc;
  border-radius: 12px;
  margin-right: 10px;
  overflow: hidden;
  transition: background-color 0.3s ease;
}

.input-wrapper.disabled {
  background-color: #f5f5f5;
  opacity: 0.8;
  cursor: not-allowed;
}

.input-wrapper.disabled textarea {
  cursor: not-allowed;
  color: #666;
}

textarea {
  flex: 1;
  padding: 0 10px;
  font-size: inherit;
  border: none;
  outline: none;
  resize: none;
  background-color: transparent;
  border-radius: 12px;
  font-family: inherit;
  font-weight: inherit;
  line-height: 1.5;
  overflow: hidden;
}

.image-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.image-wrapper {
  position: relative;
}

.image-wrapper img {
  max-height: 100px;
  max-width: 100px;
  border-radius: 5px;
}

.remove-image-button {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #d85950;
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 12px;
  cursor: pointer;
}

button {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 44px;
  height: 44px;
  background-color: #1a73e8;
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
  position: relative;
}
button:hover {
  background-color: #1765cc;
}
button:disabled,
button.disabled {
  background-color: #c5c5c5;
  cursor: default;
}
button:disabled:hover,
button.disabled:hover {
  background-color: #c5c5c5;
}

.stop-button {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 12px;
  background-color: rgba(211, 47, 47, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  animation: pulse 1.5s infinite;
}

.stop-icon {
  width: 18px;
  height: 18px;
  background-color: white;
  border-radius: 4px;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(211, 47, 47, 0.4);
  }
  70% {
    transform: scale(1.02);
    box-shadow: 0 0 0 6px rgba(211, 47, 47, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(211, 47, 47, 0);
  }
}

.drag-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.11);
  color: #fff;
  font-size: 1.2em;
  font-weight: bold;
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 20;
  pointer-events: none;
}
</style>