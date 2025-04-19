<template>
  <div id="app" :class="{ 'sidebar-hidden': isSidebarHidden }">
    <div class="sidebar-wrapper" :class="{ 'resizing': isResizing, 'no-transition': isResponsiveTransition }" :style="sidebarWidthStyle">
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
      <transition name="sidebar-fade" mode="out-in">
        <div class="sidebar-right" v-if="!isSidebarHidden">
          <SidebarMenu />
          <div 
            class="resize-handle" 
            @mousedown="startResize" 
            title="ドラッグしてサイドバーの幅を調整"
          ></div>
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
  // defaultBudgetTokens: settingsStore.defaultBudgetTokens,
  defaultWebSearch: settingsStore.defaultWebSearch,
  openrouterModels: settingsStore.openrouterModels,
  titleGenerationVendor: settingsStore.titleGenerationVendor,
  titleGenerationModel: settingsStore.titleGenerationModel,
});



const isSidebarHidden = ref(false);
const isSidebarManuallyHidden = ref(false);
const isSettingsDialogVisible = ref(false);
const sidebarWidth = ref(400); // デフォルトのサイドバー幅
const minSidebarWidth = ref(250); // 最小サイドバー幅
const maxSidebarWidth = ref(700); // 最大サイドバー幅
const isResizing = ref(false);
const isResponsiveTransition = ref(false); // レスポンシブ切り替え時のトランジションフラグ
const startMouseX = ref(0);
const startWidth = ref(0);
let lastResizeTime = 0;
const resizeThrottle = 16; // 約60FPS相当


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
    isResponsiveTransition.value = true; // レスポンシブによる切り替えなのでフラグを設定
    isSidebarHidden.value = window.innerWidth <= 768;
    
    // 少し遅延して、フラグをリセット
    setTimeout(() => {
      isResponsiveTransition.value = false;
    }, 100);
  }
};

const toggleSidebar = () => {
  isResponsiveTransition.value = false; // 手動切り替えなのでフラグをリセット
  isSidebarHidden.value = !isSidebarHidden.value;
  isSidebarManuallyHidden.value = isSidebarHidden.value;
};

const closeDrawerOnMobile = () => {
  if (window.innerWidth <= 768 && !isSidebarHidden.value) {
    isSidebarHidden.value = true;
    isSidebarManuallyHidden.value = true;
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
  // tempSettings.defaultBudgetTokens = settingsStore.defaultBudgetTokens;
  tempSettings.defaultWebSearch = settingsStore.defaultWebSearch;
  tempSettings.titleGenerationVendor = settingsStore.titleGenerationVendor;
  tempSettings.titleGenerationModel = settingsStore.titleGenerationModel;
  isSettingsDialogVisible.value = true;
};

const onSettingsSave = (settings: GlobalSettings) => {
  // 設定が保存された後の処理
  // 必要に応じて、他のコンポーネントに通知したり、状態を更新したりする
  console.log('Settings saved:', settings);
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

const sidebarWidthStyle = computed(() => {
  if (isSidebarHidden.value) {
    return { width: '50px' };
  }
  return { width: `${sidebarWidth.value}px` };
});

/**
 * リサイズ開始時の処理
 */
const startResize = (e: MouseEvent) => {
  isResizing.value = true;
  // リサイズ開始時のマウス位置とサイドバー幅を記録
  startMouseX.value = e.clientX;
  startWidth.value = sidebarWidth.value;
  
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
  document.body.style.cursor = 'ew-resize';
  document.body.style.userSelect = 'none';
  e.preventDefault();
};

/**
 * リサイズ中の処理
 */
const handleResize = (e: MouseEvent) => {
  if (!isResizing.value) return;
  
  // 前回の要求がまだ処理中の場合は、新しいフレームでのみ処理
  const now = Date.now();
  if (now - lastResizeTime < resizeThrottle) return;
  lastResizeTime = now;
  
  // マウスの移動距離を計算し、即座にサイドバーの幅を更新
  const deltaX = e.clientX - startMouseX.value;
  const newWidth = startWidth.value + deltaX;
  
  // 最小値と最大値の範囲内に収める
  sidebarWidth.value = Math.max(minSidebarWidth.value, Math.min(maxSidebarWidth.value, newWidth));
};

/**
 * リサイズ終了時の処理
 */
const stopResize = () => {
  isResizing.value = false;
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
  
};

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
  min-width: 50px;
  overflow: hidden;
  transition: width 0.2s ease-out;
  will-change: width; /* GPU高速化のヒント */
}

/* リサイズ中はトランジションを無効にする */
.sidebar-wrapper.resizing,
.sidebar-wrapper.no-transition {
  transition: none !important;
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
  transition: color 0.3s, background-color 0.3s;
  border-radius: 10%;
}

.sidebar-item:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.animate-icon-open {
  transform: rotate(90deg);
  transition: transform 0.2s ease;
}

.animate-icon-close {
  transform: rotate(0deg);
  transition: transform 0.2s ease;
}

.sidebar-right {
  flex: 1;
  background-color: #34495e;
  padding: 15px;
  color: white;
  z-index: 100;
  position: relative;
  overflow-y: auto;
  overflow-x: hidden;
  white-space: nowrap;
  will-change: transform, opacity; /* GPU高速化のヒント */
}

.sidebar-right h1 {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 20px;
}

/* リサイズハンドル */
.resize-handle {
  position: absolute;
  top: 0;
  right: 0;
  width: 8px; /* 幅を太くして掴みやすくする */
  height: 100%;
  background: transparent;
  cursor: ew-resize;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resize-handle::after {
  content: '';
  width: 2px;
  height: 100%;
  background: rgba(255, 255, 255, 0.1);
  transition: background 0.2s ease;
}

.resize-handle:hover::after,
.resize-handle:active::after {
  background: rgba(255, 255, 255, 0.3);
}

/* 改善したアニメーション - 軽量化 */
.sidebar-fade-enter-active,
.sidebar-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease-out;
}

.sidebar-fade-enter-from,
.sidebar-fade-leave-to {
  opacity: 0;
  transform: translateX(-15px);
}

#app.sidebar-hidden .sidebar-wrapper {
  width: 50px !important;
  transition: width 0.2s ease-out;
}

.chat-view-wrapper {
  flex: 1;
  display: flex;
  transition: width 0.2s ease-out;
  will-change: width; /* GPU高速化のヒント */
}

/* リサイズ中はチャット表示部分のトランジションも無効にする */
.resizing ~ .chat-view-wrapper {
  transition: none !important;
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
    z-index: 1000;
  }

  #app.sidebar-hidden .sidebar-wrapper {
    transform: none;
    width: 50px !important;
  }

  .sidebar-right {
    position: absolute;
    left: 50px;
    right: 0;
    top: 0;
    bottom: 0;
    z-index: 900;
  }

  .chat-view-wrapper {
    margin-left: 50px;
    width: calc(100% - 50px) !important;
  }
}
</style>