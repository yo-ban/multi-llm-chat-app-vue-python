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
import { fileService } from '@/services/api/file-service';
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

// Helper function to read file as data URL
function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Helper function to validate file size
function validateFileSize(file: File): boolean {
  if (file.size > MAX_FILE_SIZE) {
    toast.add({ 
      severity: 'error', 
      summary: 'Error', 
      detail: `You may not upload files larger than 20mb.\nFilename: ${file.name}`, 
      life: 10000 
    });
    return false;
  }
  return true;
}

// Helper function to process non-image file
async function processTextFile(file: File): Promise<{ filename: string; content: string } | null> {
  try {
    const content = await fileService.extractTextFromFile(file);
    return { filename: file.name, content };
  } catch (error) {
    toast.add({ 
      severity: 'error', 
      summary: 'Error', 
      detail: `Error extracting text from file. \nFilename: ${file.name}\nError: ${error}`, 
      life: 10000 
    });
    return null;
  }
}

const onFileUpload = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const files = input.files;
  if (!files || files.length === 0) return;

  const uploadedFiles = Array.from(files);
  
  // Validate all files first
  for (const file of uploadedFiles) {
    if (!validateFileSize(file)) {
      return;
    }
  }

  // Separate images and text files
  const imageFiles = uploadedFiles.filter(f => f.type.startsWith('image/'));
  const textFiles = uploadedFiles.filter(f => !f.type.startsWith('image/'));

  // Process image files
  if (imageFiles.length > 0) {
    const imagePromises = imageFiles.map(file => readFileAsDataURL(file));
    try {
      const uploadedImages = await Promise.all(imagePromises);
      emit('image-uploaded', uploadedImages);
    } catch (error) {
      toast.add({ 
        severity: 'error', 
        summary: 'Error', 
        detail: 'Failed to process image files', 
        life: 10000 
      });
    }
  }

  // Process text files
  if (textFiles.length > 0) {
    const textPromises = textFiles.map(file => processTextFile(file));
    const results = await Promise.all(textPromises);
    
    const fileContents: { [key: string]: string } = {};
    results.forEach(result => {
      if (result) {
        fileContents[result.filename] = result.content;
      }
    });

    if (Object.keys(fileContents).length > 0) {
      emit('file-uploaded', fileContents);
    }
  }

  // Clear input
  if (fileInput.value) {
    fileInput.value.value = '';
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
