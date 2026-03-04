<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push('/settings')" />
      <div class="text-h4 font-weight-bold ml-2">LLM Models</div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="showDialog()">Add Model</v-btn>
    </div>

    <v-card>
      <v-data-table :headers="headers" :items="settingsStore.models" hover>
        <template #item.is_active="{ item }">
          <v-chip :color="item.is_active ? 'success' : 'grey'" size="small" variant="tonal">{{ item.is_active ? 'Active' : 'Inactive' }}</v-chip>
        </template>
        <template #item.actions="{ item }">
          <v-btn icon="mdi-connection" size="small" variant="text" color="info" @click="testModel(item)" title="Test connection" />
          <v-btn icon="mdi-format-list-bulleted" size="small" variant="text" @click="listModels(item)" title="List available models" />
          <v-btn icon="mdi-pencil" size="small" variant="text" @click="showDialog(item)" />
          <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="handleDelete(item)" />
        </template>
      </v-data-table>
    </v-card>

    <!-- Dialog -->
    <v-dialog v-model="dialog" max-width="600">
      <v-card>
        <v-card-title>{{ editItem ? 'Edit Model' : 'Add Model' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.name" label="Display Name" hint="e.g. My Ollama Coder" class="mb-2" />
          <v-text-field v-model="form.model_id" label="Model ID" hint="e.g. qwen2.5-coder:14b" class="mb-2" />
          <v-select v-model="form.provider" :items="['ollama','openai_compatible','custom']" label="Provider" class="mb-2" />
          <v-text-field v-model="form.base_url" label="Base URL" class="mb-2" />
          <v-text-field v-model="form.api_key" label="API Key (optional)" class="mb-2" />
          <v-checkbox v-model="form.is_active" label="Active" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" @click="handleSave" :loading="saving">{{ editItem ? 'Update' : 'Create' }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Available models dialog -->
    <v-dialog v-model="availDialog" max-width="500">
      <v-card>
        <v-card-title>Available Models</v-card-title>
        <v-card-text>
          <v-list density="compact">
            <v-list-item v-for="m in availModels" :key="m.name">
              <v-list-item-title>{{ m.name }}</v-list-item-title>
              <template #append v-if="m.size">
                <span class="text-caption text-grey">{{ (m.size / 1e9).toFixed(1) }}GB</span>
              </template>
            </v-list-item>
          </v-list>
          <div v-if="!availModels.length" class="text-center text-grey pa-4">No models found</div>
        </v-card-text>
        <v-card-actions><v-spacer /><v-btn @click="availDialog = false">Close</v-btn></v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { useSettingsStore } from '../stores/settings'

const settingsStore = useSettingsStore()
const showSnackbar = inject('showSnackbar')
const dialog = ref(false)
const editItem = ref(null)
const saving = ref(false)
const availDialog = ref(false)
const availModels = ref([])

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Model ID', key: 'model_id', width: 200 },
  { title: 'Provider', key: 'provider', width: 130 },
  { title: 'Base URL', key: 'base_url' },
  { title: 'Status', key: 'is_active', width: 100 },
  { title: 'Actions', key: 'actions', sortable: false, width: 180 },
]

const defaultForm = () => ({ name: '', model_id: '', provider: 'ollama', base_url: 'http://host.docker.internal:11434', api_key: '', is_active: true })
const form = ref(defaultForm())

const showDialog = (item = null) => {
  editItem.value = item
  form.value = item ? { ...item } : defaultForm()
  dialog.value = true
}

const handleSave = async () => {
  saving.value = true
  try {
    if (editItem.value) {
      await settingsStore.updateModel(editItem.value.id, form.value)
    } else {
      await settingsStore.createModel(form.value)
    }
    dialog.value = false
    showSnackbar('Model saved')
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error', 'error')
  } finally {
    saving.value = false
  }
}

const handleDelete = async (item) => {
  if (!confirm(`Delete model "${item.name}"?`)) return
  await settingsStore.deleteModel(item.id)
  showSnackbar('Model deleted')
}

const testModel = async (item) => {
  try {
    await settingsStore.testModel(item.id)
    showSnackbar('Connection successful')
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Connection failed', 'error')
  }
}

const listModels = async (item) => {
  try {
    availModels.value = await settingsStore.listAvailableModels(item.id)
    availDialog.value = true
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error', 'error')
  }
}

settingsStore.fetchModels()
</script>
