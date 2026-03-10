<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">
        <v-icon class="mr-2" size="32">mdi-backup-restore</v-icon>
        Backups
      </div>
      <v-spacer />
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        :loading="creating"
        @click="createBackup"
      >
        Create Backup
      </v-btn>
    </div>

    <!-- Settings Card -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-cog</v-icon>
        Auto-Backup Settings
      </v-card-title>
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" sm="4">
            <v-switch
              v-model="settings.auto_backup_enabled"
              label="Enable auto-backup"
              color="primary"
              hide-details
              @update:model-value="saveSettings"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-select
              v-model="settings.backup_interval_hours"
              :items="intervalOptions"
              item-title="label"
              item-value="value"
              label="Backup interval"
              variant="outlined"
              density="compact"
              hide-details
              :disabled="!settings.auto_backup_enabled"
              @update:model-value="saveSettings"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-select
              v-model="settings.max_backups"
              :items="maxOptions"
              item-title="label"
              item-value="value"
              label="Maximum backups"
              variant="outlined"
              density="compact"
              hide-details
              @update:model-value="saveSettings"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Backup List -->
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2">mdi-archive</v-icon>
        Backups ({{ backups.length }})
        <v-spacer />
        <v-btn icon size="small" variant="text" @click="loadBackups" :loading="loading">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="headers"
          :items="backups"
          :loading="loading"
          item-value="filename"
          class="elevation-0"
          density="comfortable"
          :items-per-page="20"
          no-data-text="No backups yet. Create your first backup."
        >
          <template #item.created_at="{ item }">
            {{ formatDate(item.created_at) }}
          </template>
          <template #item.size_bytes="{ item }">
            {{ formatSize(item.size_bytes) }}
          </template>
          <template #item.documents_count="{ item }">
            {{ item.documents_count.toLocaleString() }}
          </template>
          <template #item.collections="{ item }">
            {{ item.collections?.length || 0 }} collections
          </template>
          <template #item.actions="{ item }">
            <v-btn icon size="small" variant="text" @click="downloadBackup(item)" title="Download">
              <v-icon>mdi-download</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" color="warning" @click="confirmRestore(item)" title="Restore">
              <v-icon>mdi-restore</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" color="error" @click="confirmDelete(item)" title="Delete">
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Restore Confirmation Dialog -->
    <v-dialog v-model="restoreDialog" max-width="500">
      <v-card>
        <v-card-title class="text-warning">
          <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
          Restore Backup
        </v-card-title>
        <v-card-text>
          <p class="mb-3">This will <strong>replace all current data</strong> with data from:</p>
          <p class="text-subtitle-1 font-weight-bold mb-3">{{ selectedBackup?.filename }}</p>
          <p class="text-error mb-3">This action cannot be undone!</p>
          <v-text-field
            v-model="confirmText"
            label="Type DELETE to confirm"
            variant="outlined"
            density="compact"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="restoreDialog = false">Cancel</v-btn>
          <v-btn
            color="warning"
            :disabled="confirmText !== 'DELETE'"
            :loading="restoring"
            @click="doRestore"
          >
            Restore
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error">
          <v-icon color="error" class="mr-2">mdi-delete-alert</v-icon>
          Delete Backup
        </v-card-title>
        <v-card-text>
          <p>Are you sure you want to delete <strong>{{ selectedBackup?.filename }}</strong>?</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="deleting" @click="doDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" :color="snackColor" :timeout="3000">
      {{ snackText }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const backups = ref([])
const loading = ref(false)
const creating = ref(false)
const restoring = ref(false)
const deleting = ref(false)

const settings = ref({
  auto_backup_enabled: false,
  backup_interval_hours: 24,
  max_backups: 10,
})

const restoreDialog = ref(false)
const deleteDialog = ref(false)
const selectedBackup = ref(null)
const confirmText = ref('')

const snackbar = ref(false)
const snackText = ref('')
const snackColor = ref('success')

const headers = [
  { title: 'Date', key: 'created_at', sortable: true },
  { title: 'Size', key: 'size_bytes', sortable: true },
  { title: 'Documents', key: 'documents_count', sortable: true },
  { title: 'Collections', key: 'collections', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]

const intervalOptions = [
  { label: 'Every 1 hour', value: 1 },
  { label: 'Every 3 hours', value: 3 },
  { label: 'Every 6 hours', value: 6 },
  { label: 'Every 12 hours', value: 12 },
  { label: 'Every 24 hours', value: 24 },
  { label: 'Every 48 hours', value: 48 },
  { label: 'Every 72 hours', value: 72 },
  { label: 'Every week', value: 168 },
]

const maxOptions = [
  { label: '3 backups', value: 3 },
  { label: '5 backups', value: 5 },
  { label: '10 backups', value: 10 },
  { label: '20 backups', value: 20 },
  { label: '50 backups', value: 50 },
]

function showSnack(text, color = 'success') {
  snackText.value = text
  snackColor.value = color
  snackbar.value = true
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
}

async function loadBackups() {
  loading.value = true
  try {
    const { data } = await api.get('/backups')
    backups.value = data
  } catch (e) {
    showSnack('Failed to load backups', 'error')
  } finally {
    loading.value = false
  }
}

async function loadSettings() {
  try {
    const { data } = await api.get('/backups/settings/current')
    settings.value = data
  } catch (e) {
    console.error('Failed to load backup settings', e)
  }
}

async function saveSettings() {
  try {
    const { data } = await api.put('/backups/settings/current', settings.value)
    settings.value = data
    showSnack('Settings saved')
  } catch (e) {
    showSnack('Failed to save settings', 'error')
  }
}

async function createBackup() {
  creating.value = true
  try {
    await api.post('/backups', { note: '' })
    showSnack('Backup created successfully')
    await loadBackups()
  } catch (e) {
    showSnack('Failed to create backup', 'error')
  } finally {
    creating.value = false
  }
}

async function downloadBackup(item) {
  try {
    const response = await api.get(`/backups/${item.filename}/download`, {
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = item.filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (e) {
    showSnack('Failed to download backup', 'error')
  }
}

function confirmRestore(item) {
  selectedBackup.value = item
  confirmText.value = ''
  restoreDialog.value = true
}

async function doRestore() {
  if (!selectedBackup.value || confirmText.value !== 'DELETE') return
  restoring.value = true
  try {
    await api.post(`/backups/${selectedBackup.value.filename}/restore`)
    showSnack('Backup restored successfully. Page will reload.', 'success')
    restoreDialog.value = false
    setTimeout(() => window.location.reload(), 2000)
  } catch (e) {
    showSnack('Restore failed: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    restoring.value = false
  }
}

function confirmDelete(item) {
  selectedBackup.value = item
  deleteDialog.value = true
}

async function doDelete() {
  if (!selectedBackup.value) return
  deleting.value = true
  try {
    await api.delete(`/backups/${selectedBackup.value.filename}`)
    showSnack('Backup deleted')
    deleteDialog.value = false
    await loadBackups()
  } catch (e) {
    showSnack('Failed to delete backup', 'error')
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadBackups()
  loadSettings()
})
</script>
