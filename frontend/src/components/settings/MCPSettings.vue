<template>
  <div class="mcp-settings">
    <!-- Server Configuration Section -->
    <div class="mcp-section">
      <h4>Configured Servers</h4>
      <p class="section-description">
        Manage your MCP server configurations. Changes here affect which servers the application tries to connect to.
      </p>
      <div v-if="serverNames.length === 0" class="no-items-message">
        No MCP servers configured yet. Click "Add Server" to begin.
      </div>
      <div v-else class="item-list server-list">
        <div v-for="serverName in serverNames" :key="serverName" class="item-card server-card">
          <div class="item-header">
            <span class="item-name">{{ serverName }}</span>
            <span class="item-type-badge">{{ localMcpServersConfig[serverName]?.type }}</span>
            <div class="item-actions">
              <PrimeButton icon="pi pi-pencil" class="p-button-text p-button-sm p-button-secondary"
                @click="openEditServerDialog(serverName)" v-tooltip.top="'Edit Server'" />
              <PrimeButton icon="pi pi-trash" class="p-button-text p-button-sm p-button-danger"
                @click="confirmDeleteServer(serverName)" v-tooltip.top="'Delete Server'" />
            </div>
          </div>
          <div class="item-details">
            <span v-if="localMcpServersConfig[serverName]?.type === 'stdio'">
              Command: `{{ formatCommand(localMcpServersConfig[serverName]) }}`
            </span>
            <span v-if="localMcpServersConfig[serverName]?.type === 'http'">
              URL: {{ (localMcpServersConfig[serverName] as HttpServerConfig)?.url }}
            </span>
          </div>
          <div class="item-toggle">
            <label :for="'server-toggle-' + serverName">Enable Server:</label>
            <PrimeInputSwitch :inputId="'server-toggle-' + serverName" :modelValue="!isServerDisabled(serverName)"
              @update:modelValue="toggleServerEnabled(serverName, $event)" />
          </div>
        </div>
      </div>
      <div class="add-item-button">
        <PrimeButton label="Add Server" icon="pi pi-plus" class="p-button-outlined p-button-sm"
          @click="openAddServerDialog" />
      </div>
    </div>

    <!-- Tool Enable/Disable Section -->
    <div class="mcp-section">
      <h4>Available Tools</h4>
      <p class="section-description">
        Enable or disable specific tools provided by the connected MCP servers. Disabled tools will not be presented to
        the AI.
      </p>
      <div v-if="groupedAvailableTools.length === 0" class="no-items-message">
        No tools available from connected servers, or no servers are configured/enabled.
      </div>
      <div v-else>
        <PrimeAccordion :multiple="true" > <!-- :activeIndex="defaultOpenAccordionTabs" -->
          <PrimeAccordionTab v-for="group in groupedAvailableTools" :key="group.serverName" :header="group.serverName">
            <div class="item-list tool-list">
              <div v-for="tool in group.tools" :key="tool.name" class="item-card tool-card">
                <div class="item-header tool-header">
                  <span class="item-name tool-name">{{ getToolShortName(tool.name) }}</span>
                  <div class="item-toggle tool-toggle">
                    <label :for="'tool-toggle-' + tool.name">Enable Tool:</label>
                    <PrimeInputSwitch :inputId="'tool-toggle-' + tool.name" :modelValue="!isToolDisabled(tool.name)"
                      @update:modelValue="toggleToolEnabled(tool.name, $event)" />
                  </div>
                </div>
                <div class="item-details tool-description">
                  {{ tool.description || 'No description available.' }}
                </div>
              </div>
            </div>
          </PrimeAccordionTab>
        </PrimeAccordion>
      </div>
    </div>

    <!-- Server Edit/Add Dialog -->
    <PrimeDialog v-model:visible="isServerDialogVisible"
      :header="editingServerName ? 'Edit MCP Server' : 'Add MCP Server'" modal :style="{ width: '600px' }"
      @hide="resetServerDialog">
      <div class="p-fluid server-dialog-content">
        <div class="field">
          <label for="server-name">Server Name *</label>
          <PrimeInputText id="server-name" v-model.trim="currentServerEditData.name" :disabled="!!editingServerName"
            placeholder="Unique identifier (e.g., filesystem-local)" :class="{ 'p-invalid': serverNameError }" />
          <small v-if="serverNameError" class="p-error">{{ serverNameError }}</small>
        </div>

        <div class="field">
          <label for="server-type">Server Type *</label>
          <PrimeDropdown id="server-type" v-model="currentServerEditData.type" :options="serverTypes"
            placeholder="Select Type" />
        </div>

        <!-- Stdio Fields -->
        <div v-if="currentServerEditData.type === 'stdio'">
          <div class="field">
            <label for="stdio-command">Command *</label>
            <PrimeInputText id="stdio-command" v-model="currentStdioConfig.command" placeholder="e.g., npx or python" />
          </div>
          <div class="field">
            <label for="stdio-args">Arguments (one per line)</label>
            <PrimeTextarea id="stdio-args" v-model="currentServerEditData.argsString" rows="3"
              placeholder="e.g., -y&#10;@modelcontextprotocol/server-filesystem&#10;/path/to/serve" />
          </div>
          <div class="field">
            <label for="stdio-env">Environment Variables (JSON)</label>
            <PrimeTextarea id="stdio-env" v-model="currentServerEditData.envString" rows="3"
              placeholder='e.g., {"VAR_NAME": "value"}' :class="{ 'p-invalid': envJsonError }" />
            <small v-if="envJsonError" class="p-error">{{ envJsonError }}</small>
          </div>
        </div>

        <!-- Http Fields -->
        <div v-if="currentServerEditData.type === 'http'">
          <div class="field">
            <label for="http-url">Server URL *</label>
            <PrimeInputText id="http-url" v-model="currentHttpConfig.url" placeholder="e.g., http://localhost:8000" />
          </div>
          <!-- Add fields for authentication etc. if needed -->
        </div>
      </div>
      <template #footer>
        <PrimeButton label="Cancel" icon="pi pi-times" class="p-button-text" @click="isServerDialogVisible = false" />
        <PrimeButton label="Save Server" icon="pi pi-check" @click="saveServer" :disabled="!isServerDataValid" />
      </template>
    </PrimeDialog>

    <PrimeConfirmDialog />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive, nextTick } from 'vue';
import type { PropType } from 'vue';
import PrimeInputSwitch from 'primevue/inputswitch';
import PrimeAccordion from 'primevue/accordion';
import PrimeAccordionTab from 'primevue/accordiontab';
import PrimeDialog from 'primevue/dialog';
import PrimeDropdown from 'primevue/dropdown';
import PrimeInputText from 'primevue/inputtext';
import PrimeTextarea from 'primevue/textarea';
import PrimeConfirmDialog from 'primevue/confirmdialog'; // Import ConfirmDialog
import { useConfirm } from "primevue/useconfirm"; // Import useConfirm

// Import MCP types
import type {
  McpServersConfig,
  ServerConfig,
  StdioServerConfig,
  HttpServerConfig,
  CanonicalToolDefinition
} from '@/types/mcp';

// Props definition using defineProps
const props = defineProps({
  mcpServersConfig: {
    type: Object as PropType<McpServersConfig>,
    required: true
  },
  disabledMcpServers: {
    type: Array as PropType<string[]>,
    required: true
  },
  disabledMcpTools: {
    type: Array as PropType<string[]>,
    required: true
  },
  availableMcpTools: {
    type: Array as PropType<CanonicalToolDefinition[]>,
    required: true
  }
});

// Emits definition using defineEmits
const emit = defineEmits<{
  'update:mcpServersConfig': [value: McpServersConfig],
  'update:disabledMcpServers': [value: string[]],
  'update:disabledMcpTools': [value: string[]]
}>();

const confirm = useConfirm(); // Initialize useConfirm

// --- Local Reactive State ---
// Use computed properties with setters for v-model binding to props
const localMcpServersConfig = computed({
  get: () => props.mcpServersConfig,
  set: (value) => emit('update:mcpServersConfig', value)
});
const localDisabledMcpServers = computed({
  get: () => props.disabledMcpServers,
  set: (value) => emit('update:disabledMcpServers', value)
});
const localDisabledMcpTools = computed({
  get: () => props.disabledMcpTools,
  set: (value) => emit('update:disabledMcpTools', value)
});

// Server Dialog State
const isServerDialogVisible = ref(false);
const editingServerName = ref<string | null>(null); // null for adding, string for editing
const currentServerEditData = reactive({
  name: '',
  type: 'stdio' as 'stdio' | 'http',
  argsString: '', // For easier textarea binding
  envString: '{}', // For easier textarea binding and JSON validation
  config: {} as Partial<StdioServerConfig | HttpServerConfig> // Holds specific config
});
const serverNameError = ref('');
const envJsonError = ref('');


// --- Computed Properties ---
const serverNames = computed(() => Object.keys(localMcpServersConfig.value).sort());
const serverTypes = ref(['stdio', 'http']);

// Group available tools by server name
const groupedAvailableTools = computed(() => {
  const groups: Record<string, { serverName: string; tools: CanonicalToolDefinition[] }> = {};
  const mcpPrefix = "mcp-"; // Assuming this prefix convention

  props.availableMcpTools.forEach(tool => {
    if (tool.name.startsWith(mcpPrefix)) {
      // Extract server name (handle hyphens in server name)
      const nameWithoutPrefix = tool.name.substring(mcpPrefix.length);
      let serverName = '';
      let toolShortName = nameWithoutPrefix; // Default if no server found

      // Find the longest matching server key
      let bestMatch = '';
      for (const configuredServerName in localMcpServersConfig.value) {
        if (nameWithoutPrefix.startsWith(configuredServerName + '-')) {
          if (configuredServerName.length > bestMatch.length) {
            bestMatch = configuredServerName;
          }
        }
      }

      if (bestMatch) {
        serverName = bestMatch;
      } else {
        // Fallback if no configured server matches prefix (should ideally not happen)
        serverName = 'Unknown Server';
        console.warn(`Could not determine server for tool: ${tool.name}`);
      }


      if (!groups[serverName]) {
        groups[serverName] = { serverName: serverName, tools: [] };
      }
      groups[serverName].tools.push(tool);
    } else {
      // Handle tools without the expected prefix if necessary
      if (!groups['Built-in Tools']) {
        groups['Built-in Tools'] = { serverName: 'Built-in Tools', tools: [] };
      }
      groups['Built-in Tools'].tools.push(tool);
    }
  });

  // Sort groups so that Built-in Tools are always first
  return Object.values(groups).sort((a, b) => {
    if (a.serverName === 'Built-in Tools') {
      return -1;
    }
    if (b.serverName === 'Built-in Tools') {
      return 1;
    }
    return a.serverName.localeCompare(b.serverName);
  });
});

// Default open accordion tabs (all)
// const defaultOpenAccordionTabs = computed(() => {
//   return groupedAvailableTools.value.map((_, index) => index);
// });

// Check if server data in dialog is valid for saving
const isServerDataValid = computed(() => {
  const data = currentServerEditData;
  if (!data.name || serverNameError.value) return false;
  if (data.type === 'stdio') {
    const config = data.config as Partial<StdioServerConfig>;
    return !!config.command && !envJsonError.value;
  }
  if (data.type === 'http') {
    const config = data.config as Partial<HttpServerConfig>;
    return !!config.url;
  }
  return false;
});

// Stdio 設定への安全なアクセス用 computed
const currentStdioConfig = computed(() => {
  if (currentServerEditData.type === 'stdio') {
    // ここで Partial<StdioServerConfig> にキャスト
    return currentServerEditData.config as Partial<StdioServerConfig>;
  }
  return {}; // stdio でない場合は空オブジェクトを返す (テンプレートでのエラーを防ぐ)
});

// Http 設定への安全なアクセス用 computed
const currentHttpConfig = computed(() => {
  if (currentServerEditData.type === 'http') {
    // ここで Partial<HttpServerConfig> にキャスト
    return currentServerEditData.config as Partial<HttpServerConfig>;
  }
  return {}; // http でない場合は空オブジェクト
});

// --- Methods ---

// Helper to format command for display
const formatCommand = (config: ServerConfig | undefined): string => {
  if (config?.type === 'stdio') {
    return `${config.command} ${config.args?.join(' ') ?? ''}`;
  }
  return '';
};

// Server Enable/Disable
const isServerDisabled = (serverName: string): boolean => {
  return localDisabledMcpServers.value.includes(serverName);
};
const toggleServerEnabled = (serverName: string, isEnabled: boolean) => {
  const currentDisabled = new Set(localDisabledMcpServers.value);
  if (isEnabled) {
    currentDisabled.delete(serverName);
  } else {
    currentDisabled.add(serverName);
  }
  // Emit update using computed setter
  localDisabledMcpServers.value = Array.from(currentDisabled);
};

// Tool Enable/Disable
const isToolDisabled = (toolName: string): boolean => {
  return localDisabledMcpTools.value.includes(toolName);
};
const toggleToolEnabled = (toolName: string, isEnabled: boolean) => {
  const currentDisabled = new Set(localDisabledMcpTools.value);
  if (isEnabled) {
    currentDisabled.delete(toolName);
  } else {
    currentDisabled.add(toolName);
  }
  // Emit update using computed setter
  localDisabledMcpTools.value = Array.from(currentDisabled);
};

// Get short name for tool (remove server prefix)
const getToolShortName = (fullToolName: string): string => {
  const mcpPrefix = "mcp-";
  if (fullToolName.startsWith(mcpPrefix)) {
    const nameWithoutPrefix = fullToolName.substring(mcpPrefix.length);
    // Find the longest matching server key
    let bestMatch = '';
    for (const configuredServerName in localMcpServersConfig.value) {
      if (nameWithoutPrefix.startsWith(configuredServerName + '-')) {
        if (configuredServerName.length > bestMatch.length) {
          bestMatch = configuredServerName;
        }
      }
    }
    if (bestMatch) {
      return nameWithoutPrefix.substring(bestMatch.length + 1);
    }
  }
  return fullToolName; // Fallback
};

// Server Dialog Logic
const resetServerDialog = () => {
  editingServerName.value = null;
  currentServerEditData.name = '';
  currentServerEditData.type = 'stdio';
  currentServerEditData.argsString = '';
  currentServerEditData.envString = '{}';
  currentServerEditData.config = { type: 'stdio', command: '', args: [], env: {} }; // Reset config for stdio default
  serverNameError.value = '';
  envJsonError.value = '';
};

const openAddServerDialog = () => {
  resetServerDialog();
  isServerDialogVisible.value = true;
};

const openEditServerDialog = (serverName: string) => {
  resetServerDialog(); // Start fresh
  const serverToEdit = localMcpServersConfig.value[serverName];
  if (!serverToEdit) return;

  editingServerName.value = serverName;
  currentServerEditData.name = serverName;
  currentServerEditData.type = serverToEdit.type;

  // Deep copy config and handle specific fields for editing
  if (serverToEdit.type === 'stdio') {
    const stdioConfig = serverToEdit as StdioServerConfig;
    currentServerEditData.config = JSON.parse(JSON.stringify(stdioConfig));
    currentServerEditData.argsString = stdioConfig.args?.join('\n') ?? '';
    currentServerEditData.envString = stdioConfig.env ? JSON.stringify(stdioConfig.env, null, 2) : '{}';
  } else if (serverToEdit.type === 'http') {
    currentServerEditData.config = JSON.parse(JSON.stringify(serverToEdit as HttpServerConfig));
    // argsString/envString are not relevant for http type
    currentServerEditData.argsString = '';
    currentServerEditData.envString = '{}';
  }

  isServerDialogVisible.value = true;
};

const confirmDeleteServer = (serverName: string) => {
  confirm.require({
    message: `Are you sure you want to delete the server "${serverName}"? This will also remove it from the disabled list if present.`,
    header: 'Confirm Deletion',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Delete',
    rejectLabel: 'Cancel',
    accept: () => {
      deleteServer(serverName);
    },
    reject: () => {
      // Optional: Do something on rejection
    }
  });
};


const deleteServer = (serverName: string) => {
  const newConfig = { ...localMcpServersConfig.value };
  delete newConfig[serverName];
  localMcpServersConfig.value = newConfig; // Update via computed setter

  // Also remove from disabled list if it exists there
  const currentDisabled = new Set(localDisabledMcpServers.value);
  currentDisabled.delete(serverName);
  localDisabledMcpServers.value = Array.from(currentDisabled);
};

// saveServer メソッド内の修正 (finalConfig を作成する部分)
const saveServer = () => {
  if (!isServerDataValid.value) return;

  const serverName = currentServerEditData.name;
  let finalConfig: ServerConfig;

  if (currentServerEditData.type === 'stdio') {
    // currentStdioConfig computed property を使用
    const args = currentServerEditData.argsString.split('\n').map(s => s.trim()).filter(s => s);
    let env: Record<string, string> | null = null;
    try {
      const parsedEnv = JSON.parse(currentServerEditData.envString || '{}');
      if (typeof parsedEnv === 'object' && parsedEnv !== null && !Array.isArray(parsedEnv)) {
        env = Object.entries(parsedEnv).reduce((acc, [key, value]) => {
          acc[key] = String(value);
          return acc;
        }, {} as Record<string, string>);
      } else { throw new Error("Parsed environment variables is not a valid object."); }
      envJsonError.value = '';
    } catch (e) { return; }

    finalConfig = {
      type: 'stdio',
      command: currentStdioConfig.value.command || '', // computed から取得
      args: args,
      env: env,
    };
  } else { // type === 'http'
    // currentHttpConfig computed property を使用
    finalConfig = {
      type: 'http',
      url: currentHttpConfig.value.url || '', // computed から取得
    };
  }

  const newConfig = { ...localMcpServersConfig.value };
  newConfig[serverName] = finalConfig;
  localMcpServersConfig.value = newConfig;

  isServerDialogVisible.value = false;
};

// --- Watchers ---
// Validate server name (only when adding new)
watch(() => currentServerEditData.name, (newName) => {
  if (!editingServerName.value) { // Only validate when adding
    if (!newName) {
      serverNameError.value = 'Server name is required.';
    } else if (localMcpServersConfig.value[newName]) {
      serverNameError.value = 'Server name already exists.';
    } else if (!/^[a-zA-Z0-9-_]+$/.test(newName)) {
      serverNameError.value = 'Server name can only contain letters, numbers, hyphens, and underscores.';
    }
    else {
      serverNameError.value = '';
    }
  } else {
    serverNameError.value = ''; // Don't validate existing names during edit
  }
});

// Validate Environment Variables JSON in real-time
watch(() => currentServerEditData.envString, (newEnvString) => {
  if (currentServerEditData.type !== 'stdio') {
    envJsonError.value = '';
    return;
  }
  if (!newEnvString || newEnvString.trim() === '{}' || newEnvString.trim() === '') {
    envJsonError.value = ''; // Allow empty or '{}'
    return;
  }
  try {
    const parsed = JSON.parse(newEnvString);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      envJsonError.value = 'Must be a valid JSON object (e.g., {"KEY": "value"}).';
    } else {
      // Optional: Check if all values are strings (or can be stringified)
      // for (const key in parsed) {
      //     if (typeof parsed[key] !== 'string') {
      //         // Potentially warn or auto-convert later during save
      //     }
      // }
      envJsonError.value = ''; // Valid JSON object
    }
  } catch (e) {
    envJsonError.value = 'Invalid JSON format.';
  }
});


// Reset specific config fields when type changes
watch(() => currentServerEditData.type, (newType) => {
  if (newType === 'stdio') {
    // config を Partial<StdioServerConfig> として初期化
    currentServerEditData.config = { type: 'stdio', command: '', args: [], env: {} };
    currentServerEditData.envString = '{}';
    envJsonError.value = '';
  } else { // http
    // config を Partial<HttpServerConfig> として初期化
    currentServerEditData.config = { type: 'http', url: '' };
    currentServerEditData.argsString = '';
    currentServerEditData.envString = '{}';
    envJsonError.value = '';
  }
});


</script>

<style scoped>
.mcp-settings {
  /* padding: 16px; Inherited from parent potentially */
}

.mcp-section {
  margin-bottom: 24px;
  padding: 16px;
  background-color: var(--surface-section);
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.mcp-section h4 {
  margin-top: 0;
  margin-bottom: 8px;
  font-size: 1.1rem;
  color: var(--text-color);
  border-bottom: 1px solid var(--surface-border);
  padding-bottom: 8px;
}

.section-description {
  color: var(--text-color-secondary);
  margin-bottom: 16px;
  font-size: 0.9rem;
  line-height: 1.3;
}

.no-items-message {
  text-align: center;
  padding: 20px;
  color: var(--text-color-secondary);
  background-color: var(--surface-ground);
  border-radius: 6px;
  border: 1px dashed var(--surface-d);
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-card {
  background: var(--surface-card);
  border-radius: 6px;
  padding: 12px 16px;
  border: 1px solid var(--surface-border);
  transition: box-shadow 0.2s ease-in-out;
}

.item-card:hover {
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08);
}


.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  gap: 10px;
  /* Add gap between header items */
}

.item-name {
  font-weight: 600;
  color: var(--text-color);
  font-size: 1rem;
  flex-grow: 1;
  /* Allow name to take available space */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-name {
  font-family: monospace;
  font-size: 0.95rem;
}

.item-type-badge {
  background-color: var(--primary-color);
  color: var(--primary-color-text);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
  margin-left: 8px;
  /* Add space between name and badge */
  flex-shrink: 0;
  /* Prevent badge from shrinking */
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  /* Prevent actions from shrinking */
}

.item-details {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  margin-bottom: 10px;
  line-height: 1.1;
  word-break: break-all;
  /* Break long commands/URLs */
}

.tool-description {
  margin-bottom: 0;
  /* Remove bottom margin for tool description */
  margin-top: 4px;
  white-space: pre-line;
}


.item-toggle {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  /* Align toggle to the right */
  gap: 8px;
  margin-top: 8px;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.tool-header {
  margin-bottom: 4px;
  /* Reduce margin for tool header */
}

.tool-toggle {
  margin-top: 0;
  /* Remove top margin for tool toggle */
  margin-left: auto;
  /* Push toggle to the right */
  flex-shrink: 0;
}


.add-item-button {
  margin-top: 16px;
  text-align: center;
}

/* Dialog Styles */
.server-dialog-content .field {
  margin-bottom: 1.5rem;
}

.server-dialog-content label {
  font-weight: 600;
  display: block;
  margin-bottom: 0.5rem;
}

.p-error {
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

:deep(.p-accordion .p-accordion-header .p-accordion-header-link) {
  background-color: var(--surface-b);
  border: 1px solid var(--surface-d);
  border-radius: 6px;
  /* Match card radius */
  transition: background-color 0.2s;
}

:deep(.p-accordion .p-accordion-header:not(.p-disabled).p-highlight .p-accordion-header-link) {
  background-color: var(--surface-c);
  border-color: var(--surface-d);
}

:deep(.p-accordion .p-accordion-header:not(.p-disabled) .p-accordion-header-link:focus) {
  box-shadow: 0 0 0 0.2rem var(--primary-200);
  /* Adjust focus ring color */
}


:deep(.p-accordion .p-accordion-content) {
  padding: 1rem;
  border: 1px solid var(--surface-d);
  border-top: 0;
  border-bottom-left-radius: 6px;
  border-bottom-right-radius: 6px;
  background-color: var(--surface-a);
}

.tool-list {
  margin-top: -1rem;
  /* Adjust spacing within accordion */
  margin-bottom: -1rem;
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
}

.tool-card {
  padding: 10px 12px;
  /* Slightly reduced padding */
  margin-bottom: 8px;
  /* Reduced margin */
}
</style>
