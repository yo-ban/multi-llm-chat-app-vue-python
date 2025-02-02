<template>
  <div class="file-management">
    <div class="file-list">
      <div v-for="(fileContent, fileName) in currentConversationFiles" :key="fileName" class="file-item">
        <div class="file-info">
          <font-awesome-icon :icon="getFileIcon(fileName.toString())" class="file-icon" />
          <div class="file-details">
            <span class="file-name">{{ fileName }}</span>
            <span class="file-size">{{ getFileSize(fileContent) }}</span>
          </div>
        </div>
        <div class="file-actions">
          <button @click="previewFile(fileName.toString(), fileContent)" class="preview-button">
            <font-awesome-icon icon="eye" />
          </button>
          <button @click="deleteFile(fileName.toString())" class="delete-button">
            <font-awesome-icon icon="trash" />
          </button>
        </div>
      </div>
    </div>
    <div class="upload-section" @dragover.prevent @drop.prevent="handleFileDrop">
      <label for="file-upload" class="upload-button">
        <font-awesome-icon icon="upload" />
        Upload Files
      </label>
      <input id="file-upload" type="file" @change="uploadFile" multiple accept=".pdf,.txt,.md,.html,.js,.ts,.py,.java,.c,.cpp,.cs,.rb,.go,.swift,.kotlin,.php,.rs,.scala,.sql,.json,.xml" />
      <span class="upload-text">or drag and drop files here (Max 20MB each)</span>
    </div>
    <PrimeDialog v-model:visible="previewVisible" modal header="File Preview" :style="{ width: '80vw' }">
      <pre>{{ previewContent }}</pre>
    </PrimeDialog>
  </div>
  <PrimeToast />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useConversationStore } from '@/store/conversation';
import { extractTextFromFile } from '@/utils/file-utils';
import { useToast } from 'primevue/usetoast';

const conversationStore = useConversationStore();
const MAX_FILE_SIZE = 20 * 1024 * 1024;
const toast = useToast();
const previewVisible = ref(false);
const previewContent = ref('');

const currentConversationFiles = computed(() => {
  const currentConversation = conversationStore.conversationList.find(
    (c) => c.conversationId === conversationStore.currentConversationId
  );
  return currentConversation ? currentConversation.files || {} : {};
});

function getFileIcon(fileName: string) {
  const extension = fileName.split('.').pop()?.toLowerCase();
  switch (extension) {
    case 'pdf':
      return 'file-pdf';
    case 'txt':
    case 'md':
      return 'file-alt';
    default:
      return 'file';
  }
}

function getFileSize(fileContent: string) {
  const bytes = new Blob([fileContent]).size;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  if (bytes === 0) return '0 Bytes';
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${parseFloat((bytes / Math.pow(1024, i)).toFixed(2))} ${sizes[i]}`;
}

async function deleteFile(fileName: string) {
  await conversationStore.deleteConversationFile(conversationStore.currentConversationId!, fileName);
}

function previewFile(fileName: string, fileContent: string) {
  previewContent.value = fileContent;
  previewVisible.value = true;
}

async function uploadFile(event: Event) {
  const files = (event.target as HTMLInputElement).files;
  if (files) {
    try {
      await processFiles(files);
      (event.target as HTMLInputElement).value = "";
    } catch (error) {
      const errorMessage = (error as Error).message;
      toast.add({ severity: 'error', summary: 'Error', detail: errorMessage, life: 10000 });
    }
  }
}

async function handleFileDrop(event: DragEvent) {
  event.preventDefault();
  const files = event.dataTransfer?.files;
  if (files) {
    try {
      await processFiles(files);
      event.dataTransfer.clearData();
    } catch (error) {
      const errorMessage = (error as Error).message;
      toast.add({ severity: 'error', summary: 'Error', detail: errorMessage, life: 10000 });
    }
  }
}

async function processFiles(files: FileList) {
  const fileContents: { [key: string]: string } = {};

  for (const file of Array.from(files)) {
    if (file.size > MAX_FILE_SIZE) {
      throw new Error(`You may not upload files larger than 20mb.\nFilename: ${file.name}`);
    }
    try {
      const fileContent = await extractTextFromFile(file);
      fileContents[file.name] = fileContent;
    } catch (error) {
      console.error(`Error extracting text from file ${file.name}:`, error);
      throw new Error(`Error extracting text from file. \nFilename: ${file.name}\nError: ${error}`);
    }
  }

  await conversationStore.updateConversationFiles(conversationStore.currentConversationId!, {
    ...currentConversationFiles.value,
    ...fileContents,
  });
}
</script>

<style scoped>
.file-management {
  padding: 20px;
}

.file-list {
  margin-bottom: 20px;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #e0e0e0;
  transition: background-color 0.3s;
}

.file-item:hover {
  background-color: #f5f5f5;
}

.file-info {
  display: flex;
  align-items: center;
}

.file-icon {
  margin-right: 15px;
  font-size: 24px;
  color: #757575;
}

.file-details {
  display: flex;
  flex-direction: column;
}

.file-name {
  font-size: 16px;
  color: #333;
}

.file-size {
  font-size: 12px;
  color: #757575;
}

.file-actions {
  display: flex;
  align-items: center;
}



.preview-button,
.delete-button {
  background-color: transparent;
  border: none;
  color: #757575;
  cursor: pointer;
  font-size: 18px;
  transition: color 0.3s;
  margin-left: 10px;
}

.delete-button {
  color: #f35e54;
}

.preview-button:hover {
  color: #333;
}

.delete-button:hover {
  color: #db382c;
}

.upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  border: 2px dashed #ccc;
  border-radius: 4px;
  transition: border-color 0.3s;
}

.upload-section:hover {
  border-color: #999;
}

.upload-button {
  display: inline-flex;
  align-items: center;
  padding: 12px 24px;
  background-color: #2196f3;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

.upload-button:hover {
  background-color: #1976d2;
}

.upload-button svg {
  margin-right: 10px;
}

.upload-text {
  margin-top: 10px;
  font-size: 14px;
  color: #757575;
}

input[type="file"] {
  display: none;
}
</style>
