<template>
  <div class="file-uploader">
    <label for="file-input" :class="{ 'disabled': disabled }">
      <font-awesome-icon :icon="icon" />
    </label>
    <input
      id="file-input"
      type="file"
      @change="onFileUpload"
      :disabled="disabled"
      ref="fileInput"
      multiple
      :accept="acceptedFileTypes"
    />
  </div>
  <PrimeToast />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { extractTextFromFile } from '@/utils/file-utils';
import { useToast } from 'primevue/usetoast';

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
  acceptedFileTypes: {
    type: String,
    default: 'image/*,.pdf,.txt,.md,.html,.js,.ts,.py,.java,.c,.cpp,.cs,.rb,.go,.swift,.kotlin,.php,.rs,.scala,.sql,.json,.xml',
  },
  useImageIcon: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(['file-uploaded', 'image-uploaded']);

// アイコンを動的に設定
const icon = computed(() => props.useImageIcon ? 'image' : 'paperclip');

const fileInput = ref<HTMLInputElement | null>(null);
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
const toast = useToast();

const onFileUpload = async (event: Event) => {
  const files = (event.target as HTMLInputElement).files;
  if (files) {
    const uploadedFiles = Array.from(files);
    const uploadedImages: string[] = [];
    const fileContents: { [key: string]: string } = {};
    
    for (const file of uploadedFiles) {
      if (file.size > MAX_FILE_SIZE) {
        toast.add({ severity: 'error', summary: 'Error', detail: `You may not upload files larger than 20mb.\nFilename: ${file.name}`, life: 10000 });
        return;
      }
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = () => {
          uploadedImages.push(reader.result as string);
          if (uploadedImages.length === uploadedFiles.filter(f => f.type.startsWith('image/')).length) {
            emit('image-uploaded', uploadedImages);
          }
        };
        reader.readAsDataURL(file);
      } else {
        try {
          const fileContent = await extractTextFromFile(file);
          fileContents[file.name] = fileContent;
        } catch (error) {
          console.error(`Error extracting text from file ${file.name}:`, error);
          toast.add({ severity: 'error', summary: 'Error', detail: `Error extracting text from file. \nFilename: ${file.name}\nError: ${error}`, life: 10000 });
        }
      }
    }

    if (Object.keys(fileContents).length > 0) {
      emit('file-uploaded', fileContents);
      if (fileInput.value) {
        fileInput.value.value = '';
      }
    }
  }
};

defineExpose({
  fileInput,
});

</script>

<style scoped>
.file-uploader {
  display: inline-block;
  position: relative;
  margin-left: 10px;
}
label {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 24px;
  height: 24px;
  color: #5f6368;
  cursor: pointer;
}
label.disabled {
  color: #c5c5c5;
  pointer-events: none;
}
input[type="file"] {
  display: none;
}

.error-message {
  color: #f44336;
  font-size: 14px;
  text-align: center;
}
</style>
