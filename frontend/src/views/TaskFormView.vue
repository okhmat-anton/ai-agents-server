<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="$router.back()" />
      <div class="text-h4 font-weight-bold ml-2">{{ isEdit ? 'Edit Task' : 'New Task' }}</div>
    </div>

    <v-card>
      <v-card-text>
        <v-form @submit.prevent="handleSubmit">
          <v-text-field v-model="form.title" label="Title" required />
          <v-textarea v-model="form.description" label="Description / Prompt" rows="4" />
          <v-row>
            <v-col cols="4">
              <v-select v-model="form.type" :items="['one_time','recurring','cron']" label="Type" />
            </v-col>
            <v-col cols="4">
              <v-select v-model="form.priority" :items="['low','normal','high','critical']" label="Priority" />
            </v-col>
            <v-col cols="4">
              <v-text-field v-model.number="form.timeout" label="Timeout (sec)" type="number" />
            </v-col>
          </v-row>
          <v-text-field v-if="form.type !== 'one_time'" v-model="form.schedule" label="Cron Expression" hint="e.g. */5 * * * *" />
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
import { useTasksStore } from '../stores/tasks'
import api from '../api'

const route = useRoute()
const router = useRouter()
const store = useTasksStore()
const saving = ref(false)
const isEdit = computed(() => !!route.params.id)
const agentId = computed(() => route.query.agent_id || null)

const form = ref({
  title: '', description: '', type: 'one_time', priority: 'normal', schedule: null, max_retries: 3, timeout: 300,
})

onMounted(async () => {
  if (isEdit.value) {
    const { data } = await api.get(`/tasks/${route.params.id}`)
    Object.keys(form.value).forEach((k) => { if (data[k] !== undefined) form.value[k] = data[k] })
  }
})

const handleSubmit = async () => {
  saving.value = true
  try {
    if (isEdit.value) {
      await store.updateTask(route.params.id, form.value)
    } else {
      await store.createTask(form.value, agentId.value)
    }
    router.back()
  } finally {
    saving.value = false
  }
}
</script>
