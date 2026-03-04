<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="$router.back()" />
      <div class="text-h4 font-weight-bold ml-2">{{ isEdit ? 'Edit Agent' : 'New Agent' }}</div>
    </div>

    <v-card>
      <v-card-text>
        <v-form @submit.prevent="handleSubmit">
          <v-row>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.name" label="Name" required />
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="form.model_id"
                :items="models"
                item-title="name"
                item-value="id"
                label="Provider"
                required
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-text-field v-model="form.model_name" label="Model Name" hint="e.g. qwen2.5-coder:14b" />
            </v-col>
            <v-col cols="12">
              <v-textarea v-model="form.description" label="Description" rows="2" />
            </v-col>
            <v-col cols="12">
              <v-textarea v-model="form.system_prompt" label="System Prompt" rows="4" />
            </v-col>
          </v-row>

          <v-expansion-panels class="mt-4">
            <v-expansion-panel title="Generation Parameters">
              <v-expansion-panel-text>
                <v-row>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.temperature" label="Temperature" type="number" step="0.1" min="0" max="2" />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.top_p" label="Top P" type="number" step="0.05" min="0" max="1" />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.top_k" label="Top K" type="number" min="1" />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.max_tokens" label="Max Tokens" type="number" min="1" />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.num_ctx" label="Context Window" type="number" />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.repeat_penalty" label="Repeat Penalty" type="number" step="0.05" />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.num_thread" label="CPU Threads" type="number" min="1" />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field v-model.number="form.num_gpu" label="GPU Layers" type="number" min="0" />
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <div class="d-flex mt-6">
            <v-btn color="primary" type="submit" :loading="saving" size="large">
              {{ isEdit ? 'Update' : 'Create' }}
            </v-btn>
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
import { useAgentsStore } from '../stores/agents'
import { useSettingsStore } from '../stores/settings'

const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()
const settingsStore = useSettingsStore()
const saving = ref(false)

const isEdit = computed(() => !!route.params.id)
const models = computed(() => settingsStore.models)

const form = ref({
  name: '',
  description: '',
  model_id: null,
  model_name: 'qwen2.5-coder:14b',
  system_prompt: '',
  temperature: 0.7,
  top_p: 0.9,
  top_k: 40,
  max_tokens: 2048,
  num_ctx: 32768,
  repeat_penalty: 1.1,
  num_thread: 8,
  num_gpu: 1,
})

onMounted(async () => {
  await settingsStore.fetchModels()
  if (isEdit.value) {
    const agent = await agentsStore.fetchAgent(route.params.id)
    Object.keys(form.value).forEach((key) => {
      if (agent[key] !== undefined) form.value[key] = agent[key]
    })
  } else if (models.value.length) {
    form.value.model_id = models.value[0].id
  }
})

const handleSubmit = async () => {
  saving.value = true
  try {
    if (isEdit.value) {
      await agentsStore.updateAgent(route.params.id, form.value)
    } else {
      await agentsStore.createAgent(form.value)
    }
    router.push('/agents')
  } finally {
    saving.value = false
  }
}
</script>
