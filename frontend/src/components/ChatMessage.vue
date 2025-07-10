<template>
  <div class="message" :class="[role, { 'error-message': role === 'error', 'editing': isEditing }]" @mouseenter="hovering = true" @mouseleave="hovering = false">
    <div class="message-header">
      <div class="avatar" :class="role">
        <img :src="personaIcon" alt="Avatar" class="avatar-image" />
      </div>
      <div class="role">{{ personaRole }}</div>
    </div>
    <div class="message-body">
      <div class="message-content" :class="{ 'editing': isEditing, 'streaming': props.streaming && role === 'assistant' }">
        <div v-if="images && images.length > 0" class="message-images">
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
        <div class="message-actions" :class="{ 'visible': hovering && !is_processing }">
          <VTooltip placement="bottom" popper-class="tooltip-content">
            <template #popper>
              Edit message
            </template>
            <button @click="toggleEditMode" class="action-button" v-if="role !== 'error' && !is_processing">
              <font-awesome-icon :icon="isEditing ? 'save' : 'edit'" />
            </button>
          </VTooltip>
          <VTooltip placement="bottom" popper-class="tooltip-content">
            <template #popper>
              Cancel edit
            </template>
            <button v-if="isEditing" @click="cancelEdit" class="action-button">
              <font-awesome-icon icon="times" />
            </button>
          </VTooltip>
          <VTooltip placement="bottom" popper-class="tooltip-content">
            <template #popper>
              Copy message to clipboard
            </template>
            <button @click="copyMessage" class="action-button" v-if="role === 'assistant' && !isEditing && !is_processing">
              <font-awesome-icon icon="copy" />
            </button>
          </VTooltip>
          <VTooltip placement="bottom" popper-class="tooltip-content">
            <template #popper>
              Create branch from here
            </template>
            <button @click="createBranchFromHere" class="action-button" v-if="!isEditing && !is_processing">
              <font-awesome-icon icon="code-branch" />
            </button>
          </VTooltip>
          <VTooltip placement="bottom" popper-class="tooltip-content">
            <template #popper>
              Resend message
            </template>
            <button @click="$emit('resend-message', id)" class="action-button" v-if="role === 'user' && !isEditing && !is_processing">
              <font-awesome-icon icon="redo" />
            </button>
          </VTooltip>
          <VTooltip placement="bottom" popper-class="tooltip-content">
            <template #popper>
              Delete message
            </template>
            <button @click="confirmDeleteMessage" class="action-button" v-if="!isEditing && !is_processing">
              <font-awesome-icon icon="trash" />
            </button>
          </VTooltip>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch, inject } from 'vue';
import type { DirectiveBinding } from 'vue';
import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';

import { PERSONAS } from '@/constants/personas';
import { usePersonaStore } from '@/store/persona';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import { useConversationStore } from '@/store/conversation';

// プラグインから関数をインジェクト
const highlightCode = inject('highlightCode') as (str: string, lang: string) => string;
const setupCopyButtonHandler = inject('setupCopyButtonHandler') as () => () => void;

const confirm = useConfirm();
const toast = useToast();

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
  is_processing: {
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
  mounted(el: HTMLElement, binding: DirectiveBinding<() => void>) {
    let timer: NodeJS.Timeout | null = null;
    let counter = 0;

    const handleClick = () => {
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
    };

    el.addEventListener('click', handleClick);
    
    // Store the handler on the element for cleanup
    (el as HTMLElement & { _tripleClickHandler?: () => void })._tripleClickHandler = handleClick;
  },
  
  unmounted(el: HTMLElement) {
    const extendedEl = el as HTMLElement & { _tripleClickHandler?: () => void };
    if (extendedEl._tripleClickHandler) {
      el.removeEventListener('click', extendedEl._tripleClickHandler);
      delete extendedEl._tripleClickHandler;
    }
  },
};

// コードブロックを安全に処理するための特殊なDOMPurify設定
const purifyConfig = {
  ALLOWED_TAGS: ['pre', 'code', 'div', 'span', 'button', 'p', 'a', 'ul', 'ol', 'li', 'strong', 'em', 'blockquote', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'br', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
  ADD_ATTR: ['class', 'style', 'data-code', 'data-lang'],
  KEEP_CONTENT: true
};

// カスタムプラグインで、コードブロックを特殊処理
const safeCodePlugin = (md: MarkdownIt) => {
  // カスタムレンダラーでフェンスドコードブロックを処理
  md.renderer.rules.fence = (tokens, idx) => {
    const token = tokens[idx];
    const content = token.content;
    const lang = token.info || '';

    // ハイライト適用
    const codeHtml = highlightCode(content, lang);
    
    // 特殊なdata属性でマークして、後で適切に処理できるようにする
    return `<div class="code-block-wrapper" data-code="${encodeURIComponent(content)}" data-lang="${lang}">${codeHtml}</div>`;
  };
};

const md = new MarkdownIt({
  breaks: true,
  html: false // HTMLタグをエスケープ
});

// カスタムプラグインを追加
md.use(safeCodePlugin);

const personaStore = usePersonaStore();
const isEditing = ref(false);
const editedText = ref('');
const hovering = ref(false);
const editTextarea = ref<HTMLTextAreaElement | null>(null);

// Helper functions
function showToast(severity: 'success' | 'error' | 'info' | 'warn', summary: string, detail: string, life: number = 3000) {
  toast.add({ severity, summary, detail, life, closable: severity === 'error' });
}

function showConfirmDialog(message: string, onAccept: () => void) {
  confirm.require({
    message,
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: onAccept,
  });
}

function getPersonaById(personaId: string | undefined) {
  if (!personaId) return null;
  return PERSONAS.find(p => p.id === personaId) || 
         personaStore.userDefinedPersonas.find(p => p.id === personaId);
}

function getPersonaImageUrl(persona: any) {
  if (!persona) return new URL('../assets/images/chat.svg', import.meta.url).href;
  return persona.image.startsWith('data:') 
    ? persona.image 
    : new URL(`../assets/images/${persona.image}`, import.meta.url).href;
}

// Typing animation state
const typingState = {
  smoothText: ref(''),
  targetText: ref(''),
  interval: ref<number | null>(null),
  baseSpeed: 20, // Base typing speed (milliseconds)
  lastPunctuationTime: ref(0)
};

// スムーズ表示のためにタイピングエフェクトを実装
function updateSmoothText() {
  if (typingState.targetText.value.length > typingState.smoothText.value.length) {
    const currentLength = typingState.smoothText.value.length;
    const targetLength = typingState.targetText.value.length;
    const remaining = targetLength - currentLength;
    
    // 追加する文字数の計算 (テキスト長さと状況に応じて調整)
    let charsToAdd = 1;
    
    // 通常テキストの場合は残りの量に応じて適応
    charsToAdd = Math.max(1, Math.floor(remaining / 100));
    
    // 残りテキストが少なくなると遅くする
    if (remaining < 20) {
      charsToAdd = 1;
    }
    
    // 文の終わりの句読点で少し一時停止する
    const nextChar = typingState.targetText.value.charAt(currentLength);
    const isPunctuation = ['.', '!', '?', '。', '！', '？'].includes(nextChar);
    const now = Date.now();
    
    if (isPunctuation && (now - typingState.lastPunctuationTime.value > 1000)) {
      typingState.lastPunctuationTime.value = now;
      // 句読点を追加して一時停止
      typingState.smoothText.value = typingState.targetText.value.substring(0, currentLength + 1);
      return;
    }
    
    // 実際にテキストを追加
    typingState.smoothText.value = typingState.targetText.value.substring(0, currentLength + charsToAdd);

    // 状況に応じて速度を調整
    adjustTypingSpeed();
  } else {
    // 目標のテキストに到達したら停止
    if (typingState.interval.value) {
      clearInterval(typingState.interval.value);
      typingState.interval.value = null;
    }
  }
}

// 状況に応じてタイピング速度を調整
function adjustTypingSpeed() {
  let newSpeed = typingState.baseSpeed;

  // 文が長くなるほど若干速くする
  const textLengthFactor = 1 - Math.min(0.5, typingState.smoothText.value.length / 5000);
  newSpeed = Math.max(10, Math.floor(newSpeed * textLengthFactor));
  
  // 速度が変わったらインターバルを再設定
  if (typingState.interval.value) {
    clearInterval(typingState.interval.value);
    typingState.interval.value = window.setInterval(updateSmoothText, newSpeed);
  }
}

// 新しいテキストを受け取ったときの処理
watch(() => props.streamedText, (newText) => {
  if (props.streaming && newText) {
    // 前回のテキストから新しいテキストへの変更を処理
    typingState.targetText.value = newText;
    
    // 初回表示または大幅なテキスト追加の場合
    if (!typingState.smoothText.value) {
      // 初回表示時は少し先に表示してからアニメーション
      const initialDisplayLength = Math.min(100, Math.floor(newText.length * 0.3));
      typingState.smoothText.value = newText.substring(0, initialDisplayLength);
    } else if (newText.length < typingState.smoothText.value.length) {
      // テキストが減った場合（まれなケース）
      typingState.smoothText.value = newText;
    } else if (newText.length - typingState.smoothText.value.length > 500) {
      // 大量テキストが一度に来た場合、前のテキストは保持して新しい部分のみ一部先行表示
      
      // すでに表示しているテキストが新しいテキストに含まれているか確認
      if (newText.startsWith(typingState.smoothText.value)) {
        // 既存テキストを保持し、追加分の一部を先行表示
        const additionalText = newText.substring(typingState.smoothText.value.length);
        const additionalDisplayLength = Math.floor(additionalText.length * 0.3);
        typingState.smoothText.value = newText.substring(0, typingState.smoothText.value.length + additionalDisplayLength);
      } else {
        // 既存テキストが新テキストと一致しない場合（まれなケース）は新テキストの一部を表示
        const displayLength = Math.floor(newText.length * 0.3);
        typingState.smoothText.value = newText.substring(0, displayLength);
      }
    }
        
    // インターバルがまだ設定されていなければ設定
    if (!typingState.interval.value) {
      typingState.interval.value = window.setInterval(updateSmoothText, typingState.baseSpeed);
    }
  } else {
    // ストリーミングが終了したら、すぐに完全なテキストを表示
    typingState.smoothText.value = newText || '';
    if (typingState.interval.value) {
      clearInterval(typingState.interval.value);
      typingState.interval.value = null;
    }
  }
}, { immediate: true });

// コンポーネントがアンマウントされたときにインターバルをクリア
onBeforeUnmount(() => {
  if (typingState.interval.value) {
    clearInterval(typingState.interval.value);
    typingState.interval.value = null;
  }
});

const displayText = computed(() => {
  if (props.role === 'assistant') {
    return props.streaming ? typingState.smoothText.value : props.text;
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
  
  // DOMPurifyでサニタイズ
  html = DOMPurify.sanitize(html, purifyConfig);
  
  return html;
});

const personaIcon = computed(() => {
  if (props.role === 'user') {
    return new URL('../assets/images/user.svg', import.meta.url).href;
  } else if (props.role === 'assistant') {
    const persona = getPersonaById(props.personaId);
    return getPersonaImageUrl(persona);
  } else {
    return new URL('../assets/images/warning.svg', import.meta.url).href;
  }
});

const personaRole = computed(() => {
  if (props.role === 'user') {
    return 'You';
  } else if (props.role === 'assistant') {
    const persona = getPersonaById(props.personaId);
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
  textarea.style.height = 'auto';
  textarea.style.height = `${textarea.scrollHeight}px`;
  textarea.scrollTop = scrollTop.value;
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
  showConfirmDialog(
    'Are you sure you want to delete this message?',
    () => emit('delete-message', props.id)
  );
};

function deleteImage(index: number) {
  emit('delete-image', props.id, index);
}

function copyMessage() {
  const messageText = props.text;
  navigator.clipboard.writeText(messageText).then(() => {
    showToast('info', 'Copied', 'Message copied to clipboard', 1500);
  }).catch(err => {
    console.error('Failed to copy message:', err);
    showToast('error', 'Error', 'Failed to copy message');
  });
}

function createBranchFromHere() {
  const { currentConversationId } = useConversationStore();
  if (!currentConversationId) {
    showToast('error', 'Error', 'No active conversation');
    return;
  }
  
  useConversationStore().createBranchFromMessage(props.id)
    .then(() => {
      showToast('success', 'Branch Created', 'New conversation branch has been created');
    })
    .catch((error) => {
      console.error('Error creating branch:', error);
      showToast('error', 'Error', 'Failed to create conversation branch');
    });
}

onMounted(() => {
  // コピーボタンのイベントハンドラを設定
  const removeHandler = setupCopyButtonHandler();
  
  // コンポーネント破棄時にイベントリスナーを削除するように保存
  onBeforeUnmount(() => {
    removeHandler();
  });
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

/* タイピングエフェクトの最後に表示するカーソルのアニメーション */
@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.assistant .message-content.streaming::after {
  display: inline-block;
  width: 0.5em;
  animation: cursor-blink 0.8s infinite;
  color: #0d47a1;
  vertical-align: baseline;
  font-weight: normal;
  margin-left: 1px;
}
</style>