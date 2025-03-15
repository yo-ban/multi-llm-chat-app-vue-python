<template>
  <div v-if="!showPersonasManagement">
    <div class="sidebar-menu" :style="{ maxHeight: sidebarHeight }">
      <h3>Conversations</h3>

      <div class="new-chat-container">
        <button class="new-chat-button" @click="createNewConversation">
          <font-awesome-icon icon="plus" />
          <span>New Chat</span>
        </button>
        <VTooltip placement="top" popper-class="tooltip-content">
          <template #popper>
            import Conversation
          </template>
          <button class="import-chat-button" @click="importConversation" title="Import Conversation">
            <font-awesome-icon icon="upload" />
          </button>
        </VTooltip>
        <VTooltip placement="top" popper-class="tooltip-content">
          <template #popper>
            Create Folder
          </template>
          <button class="create-folder-button" @click="openCreateFolderDialog" title="Create Folder">
            <font-awesome-icon icon="folder-plus" />
          </button>
        </VTooltip>
      </div>
      
      <div 
        class="conversation-list"
        @dragover.prevent="handleRootDragOver"
        @drop.prevent="handleRootDrop"
        :class="{ 'drop-target': isDraggingOver && dragOverTarget === 'root' }"
      >
        <div v-for="folder in folders" :key="folder.id" class="folder-container">
          <div 
            class="folder-header" 
            @click="toggleFolder(folder.id)"
            @dragover.prevent="handleFolderDragOver(folder.id, $event)"
            @drop.prevent="handleFolderDrop(folder.id, $event)"
            :class="{ 'drop-target': isDraggingOver && dragOverTarget === folder.id }"
          >
            <font-awesome-icon :icon="folder.isExpanded ? 'folder-open' : 'folder'" class="folder-icon" />
            <div 
              v-if="editingFolderId !== folder.id" 
              class="folder-name"
              @dblclick.stop="startEditFolderName(folder)"
            >
              {{ folder.name }}
            </div>
            <div v-else class="folder-name-edit">
              <input
                ref="folderNameInput"
                v-model="editedFolderName"
                @keyup.enter="saveFolderName(folder.id)"
                @blur="saveFolderName(folder.id)"
                @keyup.esc="cancelFolderEdit()"
                class="folder-name-input"
                @click.stop
              />
            </div>
            <div class="folder-actions">
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Rename
                </template>
                <button @click.stop="startEditFolderName(folder)" class="folder-action-button">
                  <font-awesome-icon icon="edit" />
                </button>
              </VTooltip>
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Delete
                </template>
                <button @click.stop="confirmDeleteFolder(folder.id)" class="folder-action-button">
                  <font-awesome-icon icon="trash" />
                </button>
              </VTooltip>
            </div>
          </div>
          
          <div v-if="folder.isExpanded" class="folder-conversations">
            <div
              v-for="conversation in getConversationsInFolder(folder.id)"
              :key="conversation.conversationId"
              class="conversation-item folder-conversation-item"
              :class="{ 
                active: conversation.conversationId === currentConversationId,
                'being-dragged': draggedConversationId === conversation.conversationId
              }"
              @click="selectConversation(conversation.conversationId)"
              draggable="true"
              @dragstart="handleDragStart(conversation, $event)"
              @dragend="handleDragEnd"
            >
              <div class="conversation-title-container">
                <img :src="getPersonaIcon(conversation.personaId)" alt="Persona Icon" class="persona-icon" />
                <div
                  v-if="editingConversationId !== conversation.conversationId"
                  class="conversation-title"
                  @dblclick="startEditConversationTitle(conversation)"
                >
                  <VTooltip placement="top" popper-class="tooltip-content">
                    <template #popper>
                      {{ conversation.title }} 
                    </template>
                    <span>{{ conversation.title }}</span>
                  </VTooltip>
                </div>
                <div v-else class="conversation-title-edit">
                  <input
                    ref="conversationTitleInput"
                    v-model="editedConversationTitle"
                    @keyup.enter="saveConversationTitle(conversation.conversationId)"
                    @blur="saveConversationTitle(conversation.conversationId)"
                    @keyup.esc="cancelEdit(conversation.title)"
                    class="conversation-title-input"
                  />
                </div>
              </div>
              <div class="conversation-actions" v-if="conversation.conversationId === currentConversationId">
                <div class="action-buttons">
                  <VTooltip placement="bottom" popper-class="tooltip-content">
                    <template #popper>
                      Rename
                    </template>
                    <button @click.stop="startEditConversationTitle(conversation)" class="action-button edit-button">
                      <font-awesome-icon icon="edit" />
                    </button>
                  </VTooltip>
                  <VTooltip placement="bottom" popper-class="tooltip-content">
                    <template #popper>
                      Duplicate
                    </template>
                    <button @click.stop="duplicateConversation(conversation)" class="action-button duplicate-button">
                      <font-awesome-icon icon="copy" />
                    </button>
                  </VTooltip>
                  <VTooltip placement="bottom" popper-class="tooltip-content">
                    <template #popper>
                      Generate Title
                    </template>
                    <button @click.stop="reGenerateChatTitle(conversation.conversationId)" class="action-button generate-button">
                      <font-awesome-icon icon="refresh" />
                    </button>
                  </VTooltip>
                </div>
                <VTooltip placement="bottom" popper-class="tooltip-content">
                  <template #popper>
                    Delete
                  </template>
                  <button @click.stop="confirmDeleteConversation(conversation.conversationId)" class="action-button delete-button">
                    <font-awesome-icon icon="trash" />
                  </button>
                </VTooltip>
              </div>
            </div>
          </div>
        </div>

        <div
          v-for="conversation in rootConversations"
          :key="conversation.conversationId"
          class="conversation-item"
          :class="{ 
            active: conversation.conversationId === currentConversationId,
            'being-dragged': draggedConversationId === conversation.conversationId
          }"
          @click="selectConversation(conversation.conversationId)"
          draggable="true"
          @dragstart="handleDragStart(conversation, $event)"
          @dragend="handleDragEnd"
        >
          <div class="conversation-title-container">
            <img :src="getPersonaIcon(conversation.personaId)" alt="Persona Icon" class="persona-icon" />
            <div
              v-if="editingConversationId !== conversation.conversationId"
              class="conversation-title"
              @dblclick="startEditConversationTitle(conversation)"
            >
              <VTooltip placement="top" popper-class="tooltip-content">
                <template #popper>
                  {{ conversation.title }} 
                </template>
                <span>{{ conversation.title }}</span>
              </VTooltip>
            </div>
            <div v-else class="conversation-title-edit">
              <input
                ref="conversationTitleInput"
                v-model="editedConversationTitle"
                @keyup.enter="saveConversationTitle(conversation.conversationId)"
                @blur="saveConversationTitle(conversation.conversationId)"
                @keyup.esc="cancelEdit(conversation.title)"
                class="conversation-title-input"
              />
            </div>
          </div>
          <div class="conversation-actions" v-if="conversation.conversationId === currentConversationId">
            <div class="action-buttons">
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Rename
                </template>
                <button @click.stop="startEditConversationTitle(conversation)" class="action-button edit-button">
                  <font-awesome-icon icon="edit" />
                </button>
              </VTooltip>
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Duplicate
                </template>
                <button @click.stop="duplicateConversation(conversation)" class="action-button duplicate-button">
                  <font-awesome-icon icon="copy" />
                </button>
              </VTooltip>
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Generate Title
                </template>
                <button @click.stop="reGenerateChatTitle(conversation.conversationId)" class="action-button generate-button">
                  <font-awesome-icon icon="refresh" />
                </button>
              </VTooltip>
            </div>
            <VTooltip placement="bottom" popper-class="tooltip-content">
              <template #popper>
                Delete
              </template>
              <button @click.stop="confirmDeleteConversation(conversation.conversationId)" class="action-button delete-button">
                <font-awesome-icon icon="trash" />
              </button>
            </VTooltip>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else>
    <h3>My Assistant Roles</h3>
    <div class="sidebar-menu" :style="{ maxHeight: sidebarHeight }">
      <div class="new-persona-container">
        <button class="add-persona-button" @click="openAddPersonaDialog">
          <font-awesome-icon icon="plus" />
          Add New Role
        </button>
        <VTooltip placement="top" popper-class="tooltip-content">
          <template #popper>
            Import Role
          </template>
          <button class="import-persona-button" @click="importPersona" title="Import Persona">
            <font-awesome-icon icon="upload" />
          </button>
        </VTooltip>
      </div>
      <div class="persona-list">
        <div class="persona-grid">
          <div v-for="persona in userDefinedPersonas" :key="persona.id" class="persona-card" >
            <VTooltip placement="top" popper-class="tooltip-content">
              <template #popper>
                {{ persona.name }}
              </template>
              <img :src="persona.image" :alt="persona.name" class="persona-image" @click="editPersona(persona)" />
            </VTooltip>
            <VTooltip placement="top" popper-class="tooltip-content">
              <template #popper>
                {{ persona.name }}
              </template>
              <div class="persona-name">{{ persona.name }}</div>
            </VTooltip>
            <div class="persona-actions">
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Edit
                </template>
                <PrimeButton icon="pi pi-pencil" class="p-button-rounded p-button-text" @click="editPersona(persona)" />
              </VTooltip>
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Duplicate
                </template>
                <PrimeButton icon="pi pi-copy" class="p-button-rounded p-button-text" @click="duplicatePersona(persona)" />
              </VTooltip>
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Delete
                </template>
                <PrimeButton icon="pi pi-trash" class="p-button-rounded p-button-text" @click="confirmDeletePersona(persona.id)" />
              </VTooltip>
              <VTooltip placement="bottom" popper-class="tooltip-content">
                <template #popper>
                  Export
                </template>
                <PrimeButton icon="pi pi-download" class="p-button-rounded p-button-text" @click="exportPersona(persona)" />
              </VTooltip>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <PersonaDialog
    v-model:visible="addPersonaDialog"
    :is-edit="false"
    @save="saveNewPersona"
  />
  <PersonaDialog
    v-model:visible="editPersonaDialog"
    :is-edit="true"
    :persona="selectedPersona"
    @save="saveEditedPersona"
  />
  <PrimeConfirmDialog />
  <PrimeDialog v-model:visible="createFolderDialog" header="Create Folder" :style="{ width: '300px' }">
    <div class="folder-dialog-content">
      <PrimeInputText v-model="newFolderName" placeholder="Folder Name" class="w-full" autofocus />
    </div>
    <template #footer>
      <PrimeButton label="Cancel" @click="closeCreateFolderDialog" class="p-button-text" />
      <PrimeButton label="Create" @click="createFolder" :disabled="!newFolderName.trim()" />
    </template>
  </PrimeDialog>
  <PrimeDialog v-model:visible="moveToFolderDialog" header="Move to Folder" :style="{ width: '300px' }">
    <div class="folder-dialog-content">
      <PrimeDropdown 
        v-model="selectedFolderId" 
        :options="folderOptions" 
        optionLabel="name" 
        optionValue="id" 
        placeholder="Select Folder"
        class="w-full"
      />
    </div>
    <template #footer>
      <PrimeButton label="Cancel" @click="closeMoveToFolderDialog" class="p-button-text" />
      <PrimeButton label="Move" @click="moveConversationToFolder" />
    </template>
  </PrimeDialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { useConversationStore } from '@/store/conversation';
import type { Conversation, ConversationFolder } from '@/types/conversation';
import { useChatStore } from '@/store/chat';
import { storeToRefs } from 'pinia';
import { llmService } from '@/services/domain/llm-service';
import { PERSONAS } from '@/constants/personas';
import { useToast } from 'primevue/usetoast';
import { usePersonaStore } from '@/store/persona';
import { v4 as uuidv4 } from 'uuid';
import type { UserDefinedPersona } from '@/types/personas';
import PersonaDialog from '@/components/PersonaDialog.vue';
import { useConfirm } from 'primevue/useconfirm';
import PrimeDialog from 'primevue/dialog';
import PrimeInputText from 'primevue/inputtext';
import PrimeDropdown from 'primevue/dropdown';

const confirm = useConfirm();
const toast = useToast();
const chatStore = useChatStore();
const conversationStore = useConversationStore();
const personaStore = usePersonaStore();
const isDropdownOpen = ref(false);

const { conversationList, currentConversationId, folders } = storeToRefs(conversationStore);
const { selectConversation, updateConversationTitle, deleteConversation } = conversationStore;

// ペルソナ管理関連の変数
const showPersonasManagement = computed(() => personaStore.showPersonasManagement);
const userDefinedPersonas = computed(() => personaStore.userDefinedPersonas);

const addPersonaDialog = ref(false);
const editPersonaDialog = ref(false);
const selectedPersona = ref<UserDefinedPersona | undefined>(undefined);

// 会話編集関連
const editingConversationId = ref('');
const editedConversationTitle = ref('');
const conversationTitleInput = ref<any | null>(null);

// フォルダ編集関連
const editingFolderId = ref('');
const editedFolderName = ref('');
const folderNameInput = ref<any | null>(null);

// フォルダダイアログ関連
const createFolderDialog = ref(false);
const newFolderName = ref('');
const moveToFolderDialog = ref(false);
const selectedFolderId = ref<string | null>(null);
const currentMovingConversationId = ref('');

const sidebarHeight = ref('100vh');

// ドラッグアンドドロップ関連
const draggedConversationId = ref('');
const isDraggingOver = ref(false);
const dragOverTarget = ref<string | 'root'>('root');
let folderExpandTimeout: number | null = null;

// ドラッグ開始処理
function handleDragStart(conversation: Conversation, event: DragEvent) {
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', conversation.conversationId);
    draggedConversationId.value = conversation.conversationId;
    
    // Set a timeout to add a class that will apply opacity transition
    setTimeout(() => {
      const element = event.target as HTMLElement;
      if (element) {
        element.classList.add('dragging');
      }
    }, 0);
  }
}

// ドラッグ終了処理
function handleDragEnd() {
  draggedConversationId.value = '';
  isDraggingOver.value = false;
  dragOverTarget.value = 'root';
  
  // Clear any pending folder expand timeout
  if (folderExpandTimeout !== null) {
    clearTimeout(folderExpandTimeout);
    folderExpandTimeout = null;
  }
  
  // Remove dragging class from all elements
  document.querySelectorAll('.dragging').forEach(el => {
    el.classList.remove('dragging');
  });
}

// フォルダへのドラッグオーバー処理
function handleFolderDragOver(folderId: string, event: DragEvent) {
  // Stop propagation to prevent the root dragover handler from also being triggered
  event.stopPropagation();
  
  if (draggedConversationId.value) {
    isDraggingOver.value = true;
    dragOverTarget.value = folderId;
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
    
    // Find the folder
    const folder = folders.value.find(f => f.id === folderId);
    
    // If the folder is not expanded, set a timeout to expand it after hovering
    if (folder && !folder.isExpanded) {
      // Clear any existing timeout for other folders
      if (folderExpandTimeout !== null) {
        clearTimeout(folderExpandTimeout);
      }
      
      // Set a new timeout to expand this folder after 800ms of hovering
      folderExpandTimeout = window.setTimeout(() => {
        conversationStore.toggleFolderExpanded(folderId);
        folderExpandTimeout = null;
      }, 800);
    }
  }
}

// ルートへのドラッグオーバー処理
function handleRootDragOver(event: DragEvent) {
  // Clear any pending folder expand timeout when dragging over root
  if (folderExpandTimeout !== null) {
    clearTimeout(folderExpandTimeout);
    folderExpandTimeout = null;
  }
  
  if (draggedConversationId.value) {
    isDraggingOver.value = true;
    dragOverTarget.value = 'root';
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
  }
}

// フォルダへのドロップ処理
async function handleFolderDrop(folderId: string, event: DragEvent) {
  // Stop propagation to prevent the root drop handler from also being triggered
  event.stopPropagation();
  
  // Clear any pending folder expand timeout
  if (folderExpandTimeout !== null) {
    clearTimeout(folderExpandTimeout);
    folderExpandTimeout = null;
  }
  
  if (event.dataTransfer) {
    const conversationId = event.dataTransfer.getData('text/plain');
    if (conversationId) {
      try {
        // Find conversation to check if it's already in this folder
        const conversation = conversationList.value.find(c => c.conversationId === conversationId);
        if (conversation && conversation.folderId !== folderId) {
          await conversationStore.moveConversationToFolder(conversationId, folderId);
          toast.add({
            severity: 'success',
            summary: 'Conversation Moved',
            detail: 'Conversation has been moved to the folder',
            life: 3000
          });
        }
      } catch (error) {
        console.error('Error moving conversation:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to move conversation',
          life: 3000
        });
      }
    }
  }
  isDraggingOver.value = false;
  dragOverTarget.value = 'root';
}

// ルートへのドロップ処理
async function handleRootDrop(event: DragEvent) {
  if (event.dataTransfer) {
    const conversationId = event.dataTransfer.getData('text/plain');
    if (conversationId) {
      try {
        // Find conversation to check if it's already in root
        const conversation = conversationList.value.find(c => c.conversationId === conversationId);
        if (conversation && conversation.folderId !== null) {
          await conversationStore.moveConversationToFolder(conversationId, null);
          toast.add({
            severity: 'success',
            summary: 'Conversation Moved',
            detail: 'Conversation has been moved to root',
            life: 3000
          });
        }
      } catch (error) {
        console.error('Error moving conversation:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to move conversation',
          life: 3000
        });
      }
    }
  }
  isDraggingOver.value = false;
  dragOverTarget.value = 'root';
}

// ペルソナ関連の関数
const openAddPersonaDialog = () => {
  addPersonaDialog.value = true;
};

const closeAddPersonaDialog = () => {
  addPersonaDialog.value = false;
};

const saveNewPersona = (persona: UserDefinedPersona) => {
  personaStore.addPersona({ ...persona, id: `persona-${uuidv4()}` });
  closeAddPersonaDialog();
};

const editPersona = (persona: UserDefinedPersona) => {
  selectedPersona.value = persona;
  editPersonaDialog.value = true;
};

const closeEditPersonaDialog = () => {
  selectedPersona.value = undefined;
  editPersonaDialog.value = false;
};

const saveEditedPersona = (persona: UserDefinedPersona) => {
  personaStore.updatePersona(persona.id, persona);
  closeEditPersonaDialog();
};

const importPersona = () => {
  personaStore.importPersona();
};

const exportPersona = (persona: UserDefinedPersona) => {
  personaStore.exportPersona(persona);
};

const confirmDeletePersona = (personaId: string) => {
  confirm.require({
    message: 'Are you sure you want to delete this role?',
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      personaStore.deletePersona(personaId);
    },
  });
};

// ルートの会話（フォルダに属さない会話）を取得
const rootConversations = computed(() => {
  const rootConvs = conversationStore.getRootConversations;
  return [...rootConvs].sort((a, b) => {
    return new Date(b.updatedAt ?? '').getTime() - new Date(a.updatedAt ?? '').getTime();
  });
});

// フォルダ内の会話を取得する関数
const getConversationsInFolder = (folderId: string) => {
  const folderConvs = conversationStore.getConversationsInFolder(folderId);
  return [...folderConvs].sort((a, b) => {
    return new Date(b.updatedAt ?? '').getTime() - new Date(a.updatedAt ?? '').getTime();
  });
};

// 「フォルダに移動」ドロップダウン用のオプション
const folderOptions = computed(() => {
  return [
    { name: 'Root (No folder)', id: null as string | null },
    ...folders.value.map(folder => ({ name: folder.name, id: folder.id }))
  ];
});

const updateSidebarHeight = () => {
  sidebarHeight.value = `${window.innerHeight-75}px`;
};

onMounted(() => {
  updateSidebarHeight();
  window.addEventListener('resize', updateSidebarHeight);
  personaStore.loadUserDefinedPersonas();
});

onUnmounted(() => {
  window.removeEventListener('resize', updateSidebarHeight);
});

function openCreateFolderDialog() {
  newFolderName.value = '';
  createFolderDialog.value = true;
}

function closeCreateFolderDialog() {
  createFolderDialog.value = false;
}

async function createFolder() {
  if (newFolderName.value.trim()) {
    await conversationStore.createFolder(newFolderName.value.trim());
    closeCreateFolderDialog();
    toast.add({
      severity: 'success',
      summary: 'Folder Created',
      detail: 'New folder has been created',
      life: 3000
    });
  }
}

function toggleFolder(folderId: string) {
  conversationStore.toggleFolderExpanded(folderId);
}

function startEditFolderName(folder: ConversationFolder) {
  editingFolderId.value = folder.id;
  editedFolderName.value = folder.name;
  nextTick(() => {
    if (folderNameInput.value) {
      const input = folderNameInput.value[0];
      input.focus();
      input.setSelectionRange(0, input.value.length);
    }
  });
}

function cancelFolderEdit() {
  editingFolderId.value = '';
}

async function saveFolderName(folderId: string) {
  if (editedFolderName.value.trim()) {
    await conversationStore.updateFolderName(folderId, editedFolderName.value.trim());
  }
  editingFolderId.value = '';
}

function confirmDeleteFolder(folderId: string) {
  confirm.require({
    message: 'Are you sure you want to delete this folder? Conversations will be moved to root.',
    header: 'Delete Folder',
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      conversationStore.deleteFolder(folderId).then(() => {
        toast.add({
          severity: 'success',
          summary: 'Folder Deleted',
          detail: 'Folder and its contents have been deleted',
          life: 3000
        });
      });
    }
  });
}

function openMoveToFolderDialog(conversation: Conversation) {
  currentMovingConversationId.value = conversation.conversationId;
  selectedFolderId.value = conversation.folderId ?? null;
  moveToFolderDialog.value = true;
}

function closeMoveToFolderDialog() {
  moveToFolderDialog.value = false;
  currentMovingConversationId.value = '';
}

async function moveConversationToFolder() {
  await conversationStore.moveConversationToFolder(currentMovingConversationId.value, selectedFolderId.value);
  closeMoveToFolderDialog();
  toast.add({
    severity: 'success',
    summary: 'Conversation Moved',
    detail: 'Conversation has been moved to the selected folder',
    life: 3000
  });
}

function createNewConversation() {
  conversationStore.createNewConversation();
  isDropdownOpen.value = false;
}

function importConversation() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (event: Event) => {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) {
      try {
        await conversationStore.importConversation(file);
      } catch (error) {
        console.error('Error importing conversation:', error);
        toast.add({ severity: 'error', summary: 'Error', detail: `Error importing conversation: ${error}`, life: 10000 });
      }
    }
  };
  input.click();
  isDropdownOpen.value = false;
}

function getPersonaIcon(personaId: string | undefined) {
  if (personaId) {
    const persona = PERSONAS.find(p => p.id === personaId) || personaStore.userDefinedPersonas.find(p => p.id === personaId);
    if (persona) {
      return persona ? persona.image.startsWith('data:') ? persona.image : new URL(`../assets/images/${persona.image}`, import.meta.url).href : new URL('../assets/images/chat.svg', import.meta.url).href;
    }
  }
  return new URL('../assets/images/chat.svg', import.meta.url).href;
}

function startEditConversationTitle(conversation: Conversation) {
  editingConversationId.value = conversation.conversationId;
  editedConversationTitle.value = conversation.title;
  nextTick(() => {
    const input = conversationTitleInput.value[0];
    input.focus();
    input.setSelectionRange(0, 0);
    input.scrollLeft = 0;
  });
}

function cancelEdit(originalTitle: string) {
  editingConversationId.value = '';
  editedConversationTitle.value = originalTitle;
}

function saveConversationTitle(conversationId: string) {
  updateConversationTitle(conversationId, editedConversationTitle.value);
  editingConversationId.value = '';
}

const confirmDeleteConversation = (conversationId: string) => {
  confirm.require({
    message: 'Are you sure you want to delete this conversation?',
    header: 'Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      deleteConversation(conversationId);
    },
  });
};

async function reGenerateChatTitle(conversationId: string) {
  if (chatStore.messages.length >= 2) {
    llmService.generateChatTitle(chatStore.messages).then(async (title: string) => {
      await conversationStore.updateConversationTitle(conversationId, title);
    }).catch((error: Error) => {
      console.error('Error generating chat title:', error);
    });
  }
}

function duplicateConversation(conversation: Conversation) {
  conversationStore.duplicateConversation(conversation.conversationId)
    .then(() => {
      toast.add({ 
        severity: 'success', 
        summary: 'Conversation Duplicated', 
        detail: 'The conversation has been duplicated successfully', 
        life: 3000 
      });
    })
    .catch((error) => {
      console.error('Error duplicating conversation:', error);
      toast.add({ 
        severity: 'error', 
        summary: 'Duplication Failed', 
        detail: 'Failed to duplicate the conversation', 
        life: 3000 
      });
    });
}

function duplicatePersona(persona: UserDefinedPersona) {
  personaStore.duplicatePersona(persona.id)
    .then(() => {
      toast.add({ 
        severity: 'success', 
        summary: 'Role Duplicated', 
        detail: 'The assistant role has been duplicated successfully', 
        life: 3000 
      });
    })
    .catch((error) => {
      console.error('Error duplicating persona:', error);
      toast.add({ 
        severity: 'error', 
        summary: 'Duplication Failed', 
        detail: 'Failed to duplicate the assistant role', 
        life: 3000 
      });
    });
}
</script>

<style scoped>
.sidebar-menu {
  display: flex;
  flex-direction: column;
}

.new-chat-container {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.new-chat-button {
  flex: 1;
  justify-content: center;
  margin-right: 0px;
  width: 100%; 
  white-space: nowrap;
  display: flex;
  align-items: center;
  padding: 10px;
  background-color: #4a5f7d;
  color: white;
  border: 1px solid #253546;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background-color 0.3s, box-shadow 0.3s;
  border-radius: 5px;
  font-size: medium;
  font-weight: 600;
  font-family: inherit;
  height: 40px;
}

.new-chat-button:hover {
  background-color: #5a7190;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
}

.new-chat-button:active {
  background-color: #3d5166;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.new-chat-button svg {
  margin-right: 10px;
}

.import-chat-button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  background-color: #4a5f7d;
  color: white;
  border: 1px solid #253546;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background-color 0.3s, box-shadow 0.3s;
  border-radius: 5px;
  font-size: medium;
  font-weight: 600;
  font-family: inherit;
  width: 35px;
  height: 40px;
}

.import-chat-button:hover {
  background-color: #5a7190;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
}

.import-chat-button:active {
  background-color: #3d5166;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.conversation-item {
  display: flex;
  flex-direction: column;
  padding: 5px 10px;
  color: white;
  cursor: pointer;
  transition: background-color 0.3s;
  border-radius: 5px;
  margin-bottom: 5px;
  position: relative;
}

.conversation-item:hover,
.conversation-item.active {
  background-color: rgba(255, 255, 255, 0.1);
}

.conversation-title-container {
  display: flex;
  align-items: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 5px;
  position: relative;
}

.conversation-title,
.conversation-title-edit {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-left: 0.5em;
  padding: 3px;
  display: flex;
  align-items: center;
  min-height: 32.00px;
  box-sizing: border-box;
  font-weight: 300;
}

.conversation-title svg {
  margin-right: 10px;
  flex-shrink: 0;
}

.conversation-title-input {
  width: 100%;
  padding: 3px;
  border: none;
  background: #324457;
  color: inherit;
  outline: none;
  box-sizing: border-box;
  font-size: inherit;
  font-family: inherit;
  font-weight: 300;
  margin-left: -2px;
  border-radius: 5%;
}

.persona-icon {
  width: 22px;
  height: 22px;
  margin-right: 0px;
  flex-shrink: 0;
  object-fit: cover;
  border-radius: 30%;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.conversation-list::-webkit-scrollbar {
  width: 4px;
}

.conversation-list::-webkit-scrollbar-track {
  background: transparent;
}

.conversation-list::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 20px;
}

.conversation-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.3);
}

.conversation-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0 10px;
}

.action-buttons {
  display: flex;
  align-items: center;
}

.action-button {
  background: none;
  border: none;
  cursor: pointer;
  color: #fff;
  padding: 5px;
  border-radius: 5px;
  transition: background-color 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-left: 5px;
}

.action-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.action-button:focus {
  outline: none;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.4);
}

.edit-button {
  margin-left: 18px;
}
.delete-button {
  margin-left: auto;
}

/* Personas */
.new-persona-container {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.add-persona-button {
  flex: 1;
  justify-content: center;
  margin-right: 0px;
  width: 100%; 
  white-space: nowrap;
  display: flex;
  align-items: center;
  padding: 10px;
  background-color: #4a5f7d;
  color: white;
  border: 1px solid #253546;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background-color 0.3s, box-shadow 0.3s;
  border-radius: 5px;
  font-size: medium;
  font-weight: 600;
  font-family: inherit;
  height: 40px;
}

.add-persona-button:hover {
  background-color: #5a7190;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
}

.add-persona-button:active {
  background-color: #3d5166;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.add-persona-button svg {
  margin-right: 10px;
}

.persona-list {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  grid-gap: 5px;
  margin-bottom: 10px;
}

.persona-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  /* background-color: #4a5f7d; */
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
  border: 1px solid #304358;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  border-radius: 5px;
  transition: background-color 0.3s, box-shadow 0.3s;
}

.persona-card:hover {
  background-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
}

.persona-image {
  cursor: pointer;
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 50%;
  margin-bottom: 10px;
}

.persona-name {
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  margin-bottom: 5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}

.persona-actions {
  display: flex;
  justify-content: space-around;
  width: 100%;
}

.p-button-rounded {
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.p-button-text {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  transition: color 0.3s;
}

.p-button-text:hover {
  color: #c8d0e0;
}

.import-persona-button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  background-color: #4a5f7d;
  color: white;
  border: 1px solid #253546;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background-color 0.3s, box-shadow 0.3s;
  border-radius: 5px;
  font-size: medium;
  font-weight: 600;
  font-family: inherit;
  width: 35px;
  height: 40px;
}

.import-persona-button:hover {
  background-color: #5a7190;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
}

.import-persona-button:active {
  background-color: #3d5166;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.create-folder-button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  background-color: #4a5f7d;
  color: white;
  border: 1px solid #253546;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background-color 0.3s, box-shadow 0.3s;
  border-radius: 5px;
  font-size: medium;
  font-weight: 600;
  font-family: inherit;
  width: 35px;
  height: 40px;
}

.create-folder-button:hover {
  background-color: #5a7190;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
}

.create-folder-button:active {
  background-color: #3d5166;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.folder-container {
  margin-bottom: 10px;
}

.folder-header {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.folder-header:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.folder-icon {
  margin-right: 8px;
  color: #e6e6e6;
}

.folder-name {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-name-edit {
  flex: 1;
}

.folder-name-input {
  width: 100%;
  padding: 3px;
  border: none;
  background: #324457;
  color: inherit;
  outline: none;
  box-sizing: border-box;
  font-size: inherit;
  font-family: inherit;
  font-weight: 500;
  border-radius: 5%;
}

.folder-actions {
  display: flex;
  visibility: hidden;
}

.folder-header:hover .folder-actions {
  visibility: visible;
}

.folder-action-button {
  background: none;
  border: none;
  cursor: pointer;
  color: #fff;
  padding: 5px;
  border-radius: 5px;
  transition: background-color 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  margin-left: 5px;
}

.folder-action-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.folder-conversations {
  margin-left: 15px;
  padding-left: 10px;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
}

.folder-conversation-item {
  margin-top: 5px;
}

.folder-dialog-content {
  margin: 20px 0;
}

.move-button {
  color: #a8c5ff;
}

/* Drag and Drop styles */
.being-dragged {
  opacity: 0.5;
}

.dragging {
  opacity: 0.5;
}

.drop-target {
  background-color: rgba(74, 144, 226, 0.2);
  border: 2px dashed #4a90e2;
  border-radius: 5px;
  transition: all 0.2s ease;
}

.folder-header.drop-target {
  padding: 8px 10px;
  background-color: rgba(74, 144, 226, 0.25);
  border: 2px dashed #4a90e2;
  border-radius: 5px;
  transition: all 0.2s ease;
  box-shadow: 0 0 5px rgba(74, 144, 226, 0.3);
}

.conversation-list.drop-target {
  padding: 4px;
  background-color: rgba(74, 144, 226, 0.05);
  border: 1px dashed rgba(74, 144, 226, 0.4);
  border-radius: 5px;
  transition: all 0.2s ease;
}

.conversation-item {
  cursor: grab;
}

.conversation-item:active {
  cursor: grabbing;
}

.drag-helper {
  font-size: 12px;
  color: #a8c5ff;
  margin-bottom: 8px;
  padding: 4px 8px;
  background-color: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drag-helper svg {
  margin-right: 5px;
}
</style>