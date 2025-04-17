<template>
    <div class="title-generation-settings">
        <div class="settings-container">
            <div class="settings-item">
                <div class="settings-header">
                    <label>Vendor</label>
                </div>
                <PrimeDropdown v-model="vendor" :options="Object.keys(MODELS)" class="w-full"
                    placeholder="Select Vendor" />
            </div>

            <div class="settings-item">
                <div class="settings-header">
                    <label>Model</label>
                </div>
                <PrimeDropdown v-model="model" :options="availableModels" optionLabel="name" optionValue="id"
                    class="w-full" placeholder="Select Model" />
                <small class="settings-description">
                    Select a cost-effective model for generating chat titles. This model will be used exclusively for
                    title generation.
                </small>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { MODELS } from '@/constants/models';
import { useSettingsStore } from '@/store/settings';

const props = defineProps<{
    modelValue: {
        vendor: string;
        model: string;
    }
}>();

const emit = defineEmits<{
    (e: 'update:modelValue', value: { vendor: string; model: string }): void;
}>();

const settingsStore = useSettingsStore();

const vendor = computed({
    get: () => {
        console.log('Getting vendor:', props.modelValue.vendor);
        return props.modelValue.vendor;
    },
    set: (value) => {
        console.log('Setting vendor:', value);
        const newModel = Object.values(MODELS[value] || {})[0]?.id || '';
        emit('update:modelValue', {
            vendor: value,
            model: newModel
        });
    }
});

const model = computed({
    get: () => {
        console.log('Getting model:', props.modelValue.model);
        return props.modelValue.model;
    },
    set: (value) => {
        console.log('Setting model:', value);
        emit('update:modelValue', {
            vendor: vendor.value,
            model: value
        });
    }
});

const availableModels = computed(() => {
    if (vendor.value === 'openrouter') {
        return settingsStore.openrouterModels;
    }
    return Object.values(MODELS[vendor.value] || {});
});

// Add watcher to debug props changes
watch(() => props.modelValue, (newValue) => {
    console.log('Props modelValue changed:', newValue);
}, { deep: true });
</script>

<style scoped>
.title-generation-settings {
    padding: 16px;
}

.description {
    color: var(--text-color-secondary);
    margin-bottom: 24px;
}

.settings-container {
    display: flex;
    flex-direction: column;
    gap: 24px;
}

.settings-item {
    background: var(--surface-card);
    border-radius: 6px;
    padding: 16px;
}

.settings-header {
    margin-bottom: 12px;
}

.settings-header label {
    font-weight: 600;
    color: var(--text-color);
}

.settings-description {
    display: block;
    margin-top: 8px;
    color: var(--text-color-secondary);
    font-size: 0.875rem;
    line-height: 1.4;
}
</style>