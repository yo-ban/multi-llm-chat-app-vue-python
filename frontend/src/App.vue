<template>
  <div id="app" :class="{ 'sidebar-hidden': isSidebarHidden }">
    <div class="sidebar-wrapper">
      <div class="sidebar-left">
        <div class="sidebar-item" @click="toggleSidebar">
          <font-awesome-icon
            icon="bars"
            :class="{ 'animate-icon-open': !isSidebarHidden, 'animate-icon-close': isSidebarHidden }"
          />
        </div>
        <VTooltip placement="top" popper-class="tooltip-content">
          <template #popper>
            Convesations
          </template>
          <div class="sidebar-item" @click="togglePersonasManagement(false)">
            <font-awesome-icon icon="comment-alt" />
          </div>
        </VTooltip>
        <VTooltip placement="top" popper-class="tooltip-content">
          <template #popper>
            My Assistant Roles
          </template>
          <div class="sidebar-item" @click="togglePersonasManagement(true)">
            <font-awesome-icon icon="user-circle" />
          </div>
        </VTooltip>
        <VTooltip placement="top" popper-class="tooltip-content">
          <template #popper>
            Global Settings
          </template>
          <div class="sidebar-item" @click="openSettingsDialog">
            <font-awesome-icon icon="cog" />
          </div>
        </VTooltip>
      </div>
      <transition name="sidebar">
        <div class="sidebar-right" v-if="!isSidebarHidden">
          <SidebarMenu />
        </div>
      </transition>
    </div>
    <div class="header-background"></div>
    <div class="chat-view-wrapper" @click="closeDrawerOnMobile">
      <ChatView />
    </div>
    <GlobalSettingsDialog
      v-model="isSettingsDialogVisible"
      @save="onSettingsSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, reactive, watch } from 'vue';
import SidebarMenu from './components/SidebarMenu.vue';
import ChatView from './views/ChatView.vue';
import { useConversationStore } from './store/conversation';
import { useSettingsStore } from './store/settings';
import { usePersonaStore } from '@/store/persona';
import { initializeIndexedDB } from './services/indexeddb';
import { MODELS } from '@/constants/models';
import GlobalSettingsDialog from '@/components/settings/GlobalSettingsDialog.vue';
import type { GlobalSettings } from '@/types/settings';

const conversationStore = useConversationStore();
const settingsStore = useSettingsStore();
const personaStore = usePersonaStore();

const tempSettings = reactive<GlobalSettings>({
  apiKeys: { ...settingsStore.apiKeys },
  defaultVendor: settingsStore.defaultVendor,
  defaultModel: settingsStore.defaultModel,
  defaultTemperature: settingsStore.defaultTemperature,
  defaultMaxTokens: settingsStore.defaultMaxTokens,
  defaultReasoningEffort: settingsStore.defaultReasoningEffort,
  defaultWebSearch: settingsStore.defaultWebSearch,
  openrouterModels: settingsStore.openrouterModels,
  titleGenerationVendor: settingsStore.titleGenerationVendor,
  titleGenerationModel: settingsStore.titleGenerationModel,
});

initializeIndexedDB();

// const availableModels = computed(() => {
//   if (tempSettings.defaultVendor === 'openrouter') {
//     return tempSettings.openrouterModels;
//   }
//   return Object.values(MODELS[tempSettings.defaultVendor] || {});
// });

// const selectedModel = computed(() => {
//   return Object.values(MODELS[tempSettings.defaultVendor] || {}).find((m) => m.id === tempSettings.defaultModel) || MODELS.anthropic.CLAUDE_3_5_SONNET;
// });

const isSidebarHidden = ref(false);
const isSidebarManuallyHidden = ref(false);
const isSettingsDialogVisible = ref(false);

// const showApiKey = ref(Object.keys(MODELS).reduce((acc, vendor) => {
//   acc[vendor] = false;
//   return acc;
// }, {} as { [key: string]: boolean }));

// const toggleApiKeyVisibility = (vendor: string) => {
//   showApiKey.value[vendor] = !showApiKey.value[vendor];
// };

const showPersonasManagement = computed({
  get: () => personaStore.showPersonasManagement,
  set: (value) => personaStore.setShowPersonasManagement(value),
});

const togglePersonasManagement = (show: boolean) => {
  if (isSidebarHidden.value || showPersonasManagement.value === show) {
    toggleSidebar()
  }
  showPersonasManagement.value = show;
};

const updateSidebarVisibility = () => {
  if (!isSidebarManuallyHidden.value) {
    isSidebarHidden.value = window.innerWidth <= 768;
  }
};

const toggleSidebar = () => {
  isSidebarHidden.value = !isSidebarHidden.value;
  isSidebarManuallyHidden.value = isSidebarHidden.value;
};

const closeDrawerOnMobile = () => {
  if (window.innerWidth <= 768 && !isSidebarHidden.value) {
    isSidebarHidden.value = true;
  }
};

const openSettingsDialog = () => {
  tempSettings.apiKeys = { ...settingsStore.apiKeys };
  tempSettings.defaultVendor = settingsStore.defaultVendor;
  tempSettings.defaultTemperature = settingsStore.defaultTemperature;
  tempSettings.defaultMaxTokens = settingsStore.defaultMaxTokens;
  tempSettings.defaultModel = settingsStore.defaultModel;
  tempSettings.openrouterModels = settingsStore.openrouterModels;
  tempSettings.defaultReasoningEffort = settingsStore.defaultReasoningEffort;
  tempSettings.defaultWebSearch = settingsStore.defaultWebSearch;
  tempSettings.titleGenerationVendor = settingsStore.titleGenerationVendor;
  tempSettings.titleGenerationModel = settingsStore.titleGenerationModel;
  isSettingsDialogVisible.value = true;
};

const onSettingsSave = (settings: GlobalSettings) => {
  // 設定が保存された後の処理
  // 必要に応じて、他のコンポーネントに通知したり、状態を更新したりする
};

watch(
  () => tempSettings.defaultVendor,
  (newVendor) => {
    const newModel = Object.values(MODELS[newVendor] || {})[0];
    tempSettings.defaultModel = newModel ? newModel.id : MODELS.anthropic.CLAUDE_3_5_SONNET.id;
  }
);

watch(
  () => tempSettings.defaultModel,
  (newModelId) => {
    const model = Object.values(MODELS[tempSettings.defaultVendor] || {}).find((m) => m.id === newModelId);
    if (model) {
      tempSettings.defaultMaxTokens = Math.min(tempSettings.defaultMaxTokens, model.maxTokens);
    }
  }
);

onMounted(async () => {
  await conversationStore.initializeConversationStore();
  await settingsStore.loadSettings();
  updateSidebarVisibility();
  window.addEventListener('resize', updateSidebarVisibility);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateSidebarVisibility);
});
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300..600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@300..600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');

html, body {
  overflow: hidden;
  height: 100%;
}

body {
  margin: 0;
  padding: 0;
  overflow: hidden;
  font-family: 'Quicksand', 'Noto Sans JP', "Noto Color Emoji", Arial, Helvetica, sans-serif; 
  font-size: 0.9em;
  font-weight: 400;
  font-style: normal;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background-color: transparent;
  border-radius: 10px;
}

::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.3);
}

/* Firefox */
* {
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.2) transparent;
}

.tooltip-content {
  text-align: center;
  font-size: 12px;
  padding: 2px;
}
</style>

<style scoped>
#app {
  display: flex;
  height: 100vh;
  background-color: #fffdfa;
}

.vendor-logo {
  width: 20px;
  height: 20px;
  margin-right: 5px;
}

.sidebar-wrapper {
  display: flex;
  width: 350px;
  overflow: hidden;
  transition: width 0.35s ease;
}

.sidebar-wrapper.sidebar-hidden {
  width: 50px;
}

.sidebar-left {
  width: 50px;
  background-color: #2c3e50;
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 200;
  flex-shrink: 0;
}

.sidebar-item {
  color: white;
  margin-bottom: 20px;
  cursor: pointer;
  position: relative;
  width: 30px;
  height: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: color 0.3s;
  border-radius: 10%;
}

.sidebar-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.animate-icon-open {
  animation: rotate-open 0.4s forwards;
}

.animate-icon-close {
  animation: rotate-close 0.4s forwards;
}

@keyframes rotate-open {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(90deg);
  }
}

@keyframes rotate-close {
  0% {
    transform: rotate(90deg);
  }
  100% {
    transform: rotate(0deg);
  }
}

.sidebar-right {
  flex: 1;
  background-color: #34495e;
  padding: 15px;
  color: white;
  z-index: 100;
  transition: transform 0.35s ease;
  overflow: hidden; 
  white-space: nowrap;
  position: relative;
}

.sidebar-right::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #34495e;
  z-index: 200;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.sidebar-hidden .sidebar-right::before {
  opacity: 1;
}
.sidebar-right h1 {
  font-size:18px;
  font-weight: 500;
  margin-bottom: 20px;
}

.sidebar-enter-active,
.sidebar-leave-active {
  transition: transform 0.35s ease;
}
.sidebar-enter,
.sidebar-leave-to {
  transform: translateX(-100%);
}

.chat-view-wrapper {
  flex: 1;
  display: flex;
}

#app.sidebar-hidden .sidebar-wrapper {
  width: 50px;
}

#app.sidebar-hidden .chat-view-wrapper {
  width: calc(100% - 50px);
}

.header-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 50px;
  background-color: #34495e;
  z-index: 1;
}

.settings-dialog :deep(.p-dialog-content) {
  padding: 20px;
}

.settings-content {
  display: flex;
  flex-direction: column;
}

.settings-section {
  margin-bottom: 10px;
}

.settings-section-header {
  font-size: 20px;
  font-weight: bold;
  margin-bottom: 15px;
}

.settings-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.settings-label {
  flex: 0 0 120px;
  margin-right: 20px;
  font-weight: bold;
}

.settings-control {
  flex: 1;
}

.settings-input {
  width: 100%;
}

.settings-dropdown {
  width: 100%;
}

.input-wrapper {
  position: relative;
}

.input-wrapper .settings-input {
  padding-right: 30px;
}

.input-wrapper i {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
}

.slider-input :deep(.p-inputnumber) {
  width: 60px;
}

.slider-input :deep(.p-inputnumber-input) {
  width: 100%;
  text-align: center;
}

.slider-container {
  display: flex;
  align-items: center;
}

.settings-slider {
  flex: 1;
  margin-right: 20px;
}

.slider-input {
  width: 80px;
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
  padding: 20px;
}

.settings-footer .p-button {
  margin-left: 10px;
}

@media (max-width: 768px) {
  .sidebar-wrapper {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    transform: none;
  }

  .sidebar-wrapper.sidebar-hidden {
    transform: translateX(-100%);
  }

  .sidebar-right {
    position: absolute;
    left: 50px;
    right: 0;
    top: 0;
    bottom: 0;
    overflow: hidden; 
    white-space: nowrap;
  }

  .sidebar-right.sidebar-hidden {
    transform: translateX(-100%);
  }

  .chat-view-wrapper {
    margin-left: 50px;
  }
}
</style>