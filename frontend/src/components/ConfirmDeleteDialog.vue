<template>
  <v-dialog v-model="visible" max-width="450" persistent>
    <v-card>
      <v-card-title class="text-error">
        <v-icon class="mr-2" color="error">mdi-alert</v-icon>
        {{ title }}
      </v-card-title>
      <v-card-text>
        <p class="mb-4">{{ message }}</p>
        <v-text-field
          v-model="confirmText"
          label="Type DELETE to confirm"
          placeholder="DELETE"
          variant="outlined"
          density="compact"
          :error="confirmText.length > 0 && confirmText !== 'DELETE'"
          hint="This action cannot be undone"
          persistent-hint
          @keyup.enter="tryConfirm"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="cancel">Cancel</v-btn>
        <v-btn
          color="error"
          :disabled="confirmText !== 'DELETE'"
          :loading="loading"
          @click="tryConfirm"
        >
          Delete
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'Confirm Delete' },
  message: { type: String, default: 'Are you sure you want to delete this item?' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const confirmText = ref('')

const visible = ref(props.modelValue)

watch(() => props.modelValue, (v) => {
  visible.value = v
  if (v) confirmText.value = ''
})
watch(visible, (v) => emit('update:modelValue', v))

const cancel = () => {
  visible.value = false
  confirmText.value = ''
}

const tryConfirm = () => {
  if (confirmText.value === 'DELETE') {
    emit('confirm')
  }
}
</script>
