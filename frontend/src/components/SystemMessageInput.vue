<template>
  <div class="system-message-input">
    <h2>Assistant Roles</h2>
    <div class="persona-options">
      <div
        v-for="persona in allPersonas"
        :key="persona.id"
        class="persona-option"
        :class="{ selected: selectedPersona === persona.id }"
        @click="selectPersona(persona.id)"
      >
        <img :src="getPersonaImage(persona.image)" :alt="persona.name" class="persona-image" />
        <div class="persona-name">{{ persona.name }}</div>
      </div>
    </div>
    <div class="persona-message">
      <textarea
        v-if="selectedPersona === 'custom'"
        v-model="customSystemMessage"
        class="custom-persona-textarea"
        placeholder="Enter custom system message"
      ></textarea>
      <div v-else class="preset-persona-message">
        {{ getPersonaSystemMessage(selectedPersona) }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { PERSONAS, DEFAULT_PERSONA, CUSTOM_PERSONA  } from '@/constants/personas';
import { usePersonaStore } from '@/store/persona';

const props = defineProps({
  value: {
    type: String,
    required: true,
  },
  isCustomSelected: {
    type: Boolean,
    default: false,
  },
  personaId: {
    type: String,
    default: '',
  },
});

const emit = defineEmits(['update:system-message', 'update:is-custom-selected', 'update:persona-id']);

const personaStore = usePersonaStore();

const allPersonas = computed(() => {
  const customPersonaIndex = PERSONAS.findIndex(p => p.id === CUSTOM_PERSONA.id);
  if (customPersonaIndex !== -1) {
    const personas = [...PERSONAS];
    personas.splice(customPersonaIndex, 1);
    return [...personas, ...personaStore.userDefinedPersonas, CUSTOM_PERSONA];
  } else {
    return [...PERSONAS, ...personaStore.userDefinedPersonas];
  }
});

const selectedPersona = ref(props.isCustomSelected ? 'custom' : DEFAULT_PERSONA.id);
const customSystemMessage = ref(props.isCustomSelected ? props.value : '');

watch(
  () => props.value,
  (newValue) => {
    if (props.isCustomSelected) {
      customSystemMessage.value = newValue;
    }
  }
);

watch(
  () => props.isCustomSelected,
  (newValue) => {
    if (newValue) {
      selectedPersona.value = 'custom';
    }
  }
);

function getPersonaImage(imagePath: string) {
  if (imagePath.startsWith('data:')) {
    return imagePath;
  } else {
    return new URL(`../assets/images/${imagePath}`, import.meta.url).href;
  }
}

function selectPersona(personaId: string) {
  selectedPersona.value = personaId;
  const persona = allPersonas.value.find(p => p.id === personaId);
  emit('update:persona-id', personaId);
  if (personaId === 'custom') {
    emit('update:system-message', customSystemMessage.value);
    emit('update:is-custom-selected', true);
  } else if (persona) {
    emit('update:system-message', persona.systemMessage);
    emit('update:is-custom-selected', false);
  }
}

function getPersonaSystemMessage(personaId: string) {
  const persona = allPersonas.value.find(p => p.id === personaId);
  return persona ? persona.systemMessage : DEFAULT_PERSONA.systemMessage;
}

watch(customSystemMessage, (newValue) => {
  if (selectedPersona.value === 'custom') {
    emit('update:system-message', newValue);
  }
});
</script>

<style scoped>
.system-message-input {
  padding: 24px;
  background-color: #f7fafc;
  border-radius: 8px;
  margin-top: 40px;
  margin-bottom: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

h2 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #2d3748;
}

.persona-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.persona-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  padding: 16px;
  border-radius: 8px;
  background-color: #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.persona-option:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.persona-option.selected {
  background-color: #e2e8f0;
}

.persona-image {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 30%;
  margin-bottom: 12px;
}

.persona-name {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  color: #2d3748;
}

.custom-persona {
  margin-top: 24px;
}

.persona-message {
  margin-top: 24px;
}

.custom-persona-textarea {
  width: 100%;
  min-height: 250px;
  padding: 12px;
  resize: vertical;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 14px;
  color: #2d3748;
  transition: border-color 0.2s;
}

.custom-persona-textarea:focus {
  outline: none;
  border-color: #4299e1;
}

.preset-persona-message {
  padding: 12px;
  background-color: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 14px;
  color: #2d3748;
  white-space: pre-wrap;
}
</style>