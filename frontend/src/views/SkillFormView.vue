<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="$router.back()" />
      <div class="text-h4 font-weight-bold ml-2">{{ isEdit ? 'Edit Skill' : 'New Skill' }}</div>
    </div>

    <v-card>
      <v-card-text>
        <v-form @submit.prevent="handleSubmit">
          <v-row>
            <v-col cols="6"><v-text-field v-model="form.name" label="Name (snake_case)" /></v-col>
            <v-col cols="6"><v-text-field v-model="form.display_name" label="Display Name" /></v-col>
          </v-row>
          <v-textarea v-model="form.description" label="Description" rows="2" />
          <v-row>
            <v-col cols="4">
              <v-select v-model="form.category" :items="['general','web','files','code','data','custom']" label="Category" />
            </v-col>
            <v-col cols="4">
              <v-text-field v-model="form.version" label="Version" />
            </v-col>
            <v-col cols="4">
              <v-switch v-model="form.is_shared" label="Shared" color="primary" />
            </v-col>
          </v-row>
          <v-textarea v-model="form.code" label="Python Code" rows="12" style="font-family: monospace;" />
          <div class="d-flex mt-4">
            <v-btn type="submit" color="primary" :loading="saving">{{ isEdit ? 'Update' : 'Create' }}</v-btn>
            <v-btn class="ml-3" variant="outlined" @click="$router.back()">Cancel</v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const saving = ref(false)
const isEdit = computed(() => !!route.params.id)

const form = ref({
  name: '', display_name: '', description: '', category: 'general', version: '1.0.0', code: '', is_shared: false,
  input_schema: {}, output_schema: {},
})

onMounted(async () => {
  if (isEdit.value) {
    const { data } = await api.get(`/skills/${route.params.id}`)
    Object.keys(form.value).forEach((k) => { if (data[k] !== undefined) form.value[k] = data[k] })
  }
})

const handleSubmit = async () => {
  saving.value = true
  try {
    if (isEdit.value) {
      await api.put(`/skills/${route.params.id}`, form.value)
    } else {
      await api.post('/skills', form.value)
    }
    router.push('/skills')
  } finally {
    saving.value = false
  }
}
</script>
