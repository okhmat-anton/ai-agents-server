<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push('/settings')" />
      <div class="text-h4 font-weight-bold ml-2">API Keys</div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="showCreate = true">New Key</v-btn>
    </div>

    <v-card>
      <v-data-table :headers="headers" :items="settingsStore.apiKeys" hover>
        <template #item.key_prefix="{ item }">
          <code>{{ item.key_prefix }}...</code>
        </template>
        <template #item.last_used_at="{ item }">
          {{ item.last_used_at ? new Date(item.last_used_at).toLocaleString() : 'Never' }}
        </template>
        <template #item.created_at="{ item }">
          {{ new Date(item.created_at).toLocaleDateString() }}
        </template>
        <template #item.actions="{ item }">
          <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="handleDelete(item)" />
        </template>
      </v-data-table>
    </v-card>

    <!-- Create dialog -->
    <v-dialog v-model="showCreate" max-width="500">
      <v-card>
        <v-card-title>Create API Key</v-card-title>
        <v-card-text>
          <v-text-field v-model="form.name" label="Name (e.g. VSCode)" class="mb-2" />
          <v-text-field v-model="form.description" label="Description (optional)" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showCreate = false">Cancel</v-btn>
          <v-btn color="primary" @click="handleCreate" :loading="creating">Create</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Show key dialog -->
    <v-dialog v-model="showKey" max-width="600" persistent>
      <v-card>
        <v-card-title class="text-warning">
          <v-icon class="mr-2">mdi-alert</v-icon>
          Save your API Key
        </v-card-title>
        <v-card-text>
          <p class="mb-3">This key will only be shown once. Copy it now!</p>
          <v-text-field :model-value="createdKey" readonly append-inner-icon="mdi-content-copy" @click:append-inner="copyKey" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="showKey = false">I've saved it</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { useSettingsStore } from '../stores/settings'

const settingsStore = useSettingsStore()
const showSnackbar = inject('showSnackbar')
const showCreate = ref(false)
const showKey = ref(false)
const creating = ref(false)
const createdKey = ref('')
const form = ref({ name: '', description: '' })

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Key', key: 'key_prefix', width: 120 },
  { title: 'Description', key: 'description' },
  { title: 'Last Used', key: 'last_used_at', width: 180 },
  { title: 'Created', key: 'created_at', width: 120 },
  { title: '', key: 'actions', sortable: false, width: 60 },
]

const handleCreate = async () => {
  creating.value = true
  try {
    const data = await settingsStore.createApiKey(form.value)
    createdKey.value = data.key
    showCreate.value = false
    showKey.value = true
    settingsStore.fetchApiKeys()
    form.value = { name: '', description: '' }
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error', 'error')
  } finally {
    creating.value = false
  }
}

const handleDelete = async (item) => {
  if (!confirm(`Delete API key "${item.name}"?`)) return
  await settingsStore.deleteApiKey(item.id)
  showSnackbar('API key deleted')
}

const copyKey = () => {
  navigator.clipboard.writeText(createdKey.value)
  showSnackbar('Copied to clipboard')
}

settingsStore.fetchApiKeys()
</script>
