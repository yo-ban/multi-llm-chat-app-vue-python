<template>
  <div class="image-uploader">
    <label for="file-input" :class="{ 'disabled': disabled }">
      <font-awesome-icon icon="paperclip" />
    </label>
    <input
      id="file-input"
      type="file"
      @change="onImageUpload"
      accept="image/*"
      :disabled="disabled"
      ref="fileInput"
      multiple
    />
  </div>
</template>

<script setup lang="ts">
import { ref, defineProps, defineEmits } from 'vue';

defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['image-uploaded']);

const fileInput = ref<HTMLInputElement | null>(null);

const onImageUpload = (event: Event) => {
  const files = (event.target as HTMLInputElement).files;
  if (files) {
    const uploadedImages: string[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const reader = new FileReader();
      reader.onload = () => {
        uploadedImages.push(reader.result as string);
        if (uploadedImages.length === files.length) {
          emit('image-uploaded', uploadedImages);
        }
      };
      reader.readAsDataURL(file);
    }
  }
};
</script>

<style scoped>
.image-uploader {
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
</style>