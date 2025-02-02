<template>
  <div class="message" :class="[role, { 'error-message': role === 'error', 'editing': isEditing }]" @mouseenter="hovering = true" @mouseleave="hovering = false">
    <div class="message-header">
      <div class="avatar" :class="role">
        <img :src="personaIcon" alt="Avatar" class="avatar-image" />
      </div>
      <div class="role">{{ personaRole }}</div>
    </div>
    <div class="message-body">
      <div class="message-content" :class="{ 'editing': isEditing }">
        <div v-if="images && images.length > 0" class="message-images" v-memo="[images]">
          <div v-for="(image, index) in images" :key="index" class="message-image-wrapper">
            <PrimeImage :src="image" alt="Message Image" class="message-image" preview>
              <template #indicatoricon>
                <i class="pi pi-search"></i>
              </template>
              <template #image>
                <img :src="image" alt="thumbnail" class="thumbnail-image" />
              </template>              
              <template #preview="slotProps">
                <img :src="image" alt="preview" :style="{ ...slotProps.style, maxHeight: '80vh', maxWidth: '80vw' }" @click="slotProps.onClick" />
              </template>
            </PrimeImage>
            <button @click="deleteImage(index)" class="delete-image-button">
              <font-awesome-icon icon="times" />
            </button>
          </div>
        </div>
        <div v-if="!isEditing" class="text message-content" v-html="formattedText" v-triple-click="toggleEditMode" v-memo="[formattedText]"></div>
        <div v-else class="edit-container">
          <textarea v-model="editedText" class="edit-textarea" ref="editTextarea" @blur="saveEditedMessage()" @keyup.esc="cancelEdit()"></textarea>
        </div>
      </div>
      <div class="message-actions-container">
        <div class="message-actions" :class="{ 'visible': hovering && !streaming }">
          <button @click="toggleEditMode" class="action-button" v-if="role !== 'error' && !streaming">
            <font-awesome-icon :icon="isEditing ? 'save' : 'edit'" />
          </button>
          <button v-if="isEditing" @click="cancelEdit" class="action-button">
            <font-awesome-icon icon="times" />
          </button>
          <button @click="$emit('resend-message', id)" class="action-button" v-if="role === 'user' && !isEditing && !streaming">
            <font-awesome-icon icon="redo" />
          </button>
          <button @click="confirmDeleteMessage" class="action-button" v-if="!isEditing && !streaming">
            <font-awesome-icon icon="trash" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';

import hljs from '@/utils/highlight';
import '@/assets/styles/code-theme.css';
import { PERSONAS } from '@/constants/personas';
import { usePersonaStore } from '@/store/persona';
import { useConfirm } from 'primevue/useconfirm';

const confirm = useConfirm();

const props = defineProps({
  role: {
    type: String,
    required: true,
  },
  text: {
    type: String,
    required: true,
  },
  id: {
    type: String,
    required: true,
  },
  images: {
    type: Array as () => string[],
    default: () => [],
  },
  streaming: {
    type: Boolean,
    default: false,
  },
  streamedText: {
    type: String,
    default: '',
  },
  personaId: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['save-edited-message', 'delete-message', 'delete-image', 'resend-message']);

const vTripleClick = {
  mounted(el: HTMLElement, binding: any) {
    let timer: NodeJS.Timeout | null = null;
    let counter = 0;

    el.addEventListener('click', () => {
      counter++;
      if (counter === 1) {
        timer = setTimeout(() => {
          counter = 0;
        }, 350);
      } else if (counter === 3 && !props.streaming) {
        if (timer) {
          clearTimeout(timer);
        }
        counter = 0;
        binding.value();
      }
    });
  },
};

const md: MarkdownIt = new MarkdownIt({
  breaks: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const code = hljs.highlight(str, { language: lang }).value;
        return `<pre class="hljs"><div class="code-header"><span class="language">${lang}</span><button class="copy-button">Copy</button></div><code>${code}</code></pre>`;
      } catch (error) {
        console.error('Error highlighting code:', error);
      }
    }
    return `<pre class="hljs"><div class="code-header"><span class="language">Code</span><button class="copy-button">Copy</button></div><code>${md.utils.escapeHtml(str)}</code></pre>`;
  },
});

const personaStore = usePersonaStore();
const isEditing = ref(false);
const editedText = ref('');
const hovering = ref(false);
const editTextarea = ref<HTMLTextAreaElement | null>(null);

const displayText = computed(() => {
  if (props.role === 'assistant') {
    return props.streaming ? props.streamedText : props.text;
  } else {
    return props.text;
  }
});

const formattedText = computed(() => {
  const rawText = displayText.value;
  let html;
  if (props.role === 'user') {
    const processedText = rawText.replace(/\n/g, '  \n');
    html = md.render(processedText);
  } else {
    html = md.render(rawText);
  }
  return DOMPurify.sanitize(html);
});

const personaIcon = computed(() => {
  if (props.role === 'user') {
    return new URL('../assets/images/user.svg', import.meta.url).href;
  } else if (props.role === 'assistant') {
    const persona = PERSONAS.find(p => p.id === props.personaId) || personaStore.userDefinedPersonas.find(p => p.id === props.personaId);
    return persona ? persona.image.startsWith('data:') ? persona.image : new URL(`../assets/images/${persona.image}`, import.meta.url).href : new URL('../assets/images/chat.svg', import.meta.url).href;
  } else {
    return new URL('../assets/images/warning.svg', import.meta.url).href;
  }
});

const personaRole = computed(() => {
  if (props.role === 'user') {
    return 'You';
  } else if (props.role === 'assistant') {
    const persona = PERSONAS.find(p => p.id === props.personaId) || personaStore.userDefinedPersonas.find(p => p.id === props.personaId);
    return persona ? persona.name : 'Assistant';
  } else {
    return 'Error';
  }
});

function toggleEditMode() {
  if (isEditing.value) {
    saveEditedMessage();
  } else {
    isEditing.value = true;
    editedText.value = props.text;
  }
}

async function saveEditedMessage() {
  if (editedText.value && editedText.value.trim().length > 0) {
    emit('save-edited-message', props.id, editedText.value.trim());
  }
  isEditing.value = false;
}

function cancelEdit() {
  isEditing.value = false;
  editedText.value = props.text;
}

const scrollTop = ref(0);

function adjustTextareaHeight(event: Event) {
  const textarea = event.target as HTMLTextAreaElement;
  scrollTop.value = textarea.scrollTop;
  console.log(textarea.scrollTop)
  textarea.style.height = 'auto';
  textarea.style.height = `${textarea.scrollHeight}px`;
  textarea.scrollTop = scrollTop.value;
  console.log(textarea.scrollTop)

}

function focusEditTextarea() {
  nextTick(() => {
    if (editTextarea.value) {
      editTextarea.value.style.height = `${editTextarea.value.scrollHeight}px`;
      editTextarea.value.focus();
    }
  });
}

const confirmDeleteMessage = () => {
  confirm.require({
    message: 'Are you sure you want to delete this message?',
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      emit('delete-message', props.id);
    },
  });
};

function handleCopyButtonClick(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (target.classList.contains('copy-button')) {
    const codeElement = target.parentElement?.nextElementSibling;
    if (codeElement) {
      const code = codeElement.textContent || '';
      navigator.clipboard.writeText(code).then(() => {
        target.textContent = 'Copied!';
        setTimeout(() => {
          target.textContent = 'Copy';
        }, 10000);
      });
    }
  }
}

function deleteImage(index: number) {
  emit('delete-image', props.id, index);
}

onMounted(() => {
  window.addEventListener('click', handleCopyButtonClick);
});

onBeforeUnmount(() => {
  window.removeEventListener('click', handleCopyButtonClick);
});

watch(isEditing, (newVal) => {
  if (newVal) {
    nextTick(() => {
      focusEditTextarea();
    });
  }
});

watch(editedText, () => {
  nextTick(() => {
    adjustTextareaHeight({ target: editTextarea.value } as Event);
  });
});

</script>

<style scoped>
.message {
  margin-bottom: 15px;
  display: flex;
}

:deep(li) > code,
:deep(p) > code {
  background-color: #fafafa;
  color: #b71c1c;
  border-radius: 3px;
  font-family: 'Fira Code', monospace;
  padding: 0.2em 0.4em;
  font-size: 0.9em;
}

.message-body {
  flex: 1;
  max-width: 100%;
}

.message-content {
  max-width: 100%;
  padding: 5px;
  border-radius: 5px;
  margin-bottom: 0px;
  position: relative;
  overflow: hidden;
}

.message-content:not(.editing) {
  display: inline-block;
}

.message:hover .message-actions {
  display: flex;
}

.message-images {
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: flex-start;
}

.message-image-wrapper {
  position: relative;
  display: inline-block;
}

.message-image {
  max-height: 300px;
  border-radius: 10px;
}

.delete-image-button {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 12px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.1s;
}

.message-image-wrapper:hover .delete-image-button {
  opacity: 1;
}

.message.editing {
  border-radius: 10px;
  background-color: #f1f1f1;
}

.edit-container {
  width: 100%;
}

.edit-textarea {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 5px;
  resize: none;
  background-color: #fff8e1;
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
  overflow-y: hidden;
  box-sizing: border-box;
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.1);
}

.user .edit-textarea {
  color: #70584f;
}

.assistant .edit-textarea {
  color: #3b2b26;
}

.edit-textarea:focus {
  background-color: #fff3e0;
  outline: none;
}

.edit-textarea:focus-visible {
  outline: 2px solid #8a775c;
}
.message-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-right: 10px;
  flex-shrink: 0;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #e8f5e9;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 5px;
  overflow: hidden;
}

.avatar .avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center; /* 追加 */
}

.avatar.user {
  background-color: #e8f5e9;
  color: #1b5e20;
}

.role {
  font-size: 12px;
  font-weight: bold;
  text-align: center;
  width: 60px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.avatar.assistant {
  background-color: #e3f2fd;
  color: #0d47a1;
}

.avatar.error {
  background-color: #ffebee;
  color: #b71c1c;
}

.thumbnail-image {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  cursor: pointer;
}

.user .message-content {
  background-color: #e8f5e9;
  color: #1b5e20;
}
.assistant .message-content {
  background-color: #e3f2fd;
  color: #0d47a1;
}
.error-message .message-content {
  background-color: #ffebee;
  color: #b71c1c;
}

.message-actions-container {
  height: 20px;
}

.message-actions {
  display: none;
  justify-content: flex-start;
  opacity: 0;
  transition: opacity 0.2s;
}

.message-actions.visible {
  display: flex;
  opacity: 1;
}

.message:hover .message-actions {
  display: flex;
}

.action-button {
  background: none;
  border: none;
  cursor: pointer;
  color: #1a73e86e;
  font-size: 14px;
  margin-right: 5px;
  align-items: left;
}

.action-button :hover {
  color: #1a73e8d2;
}

img {
  max-width: 100%;
  border-radius: 10px;
}
.text :deep(p) {
  margin-block-start: 0.1em;
  margin-block-end: 0.5em;
}
.text :deep(p:last-child) {
  margin-block-end: 0.1em;
}
.text :deep(ol) {
  margin-block-start: 0.2em;
}
.text :deep(ol:last-child) {
  margin-block-end: 0.2em;
}

</style>