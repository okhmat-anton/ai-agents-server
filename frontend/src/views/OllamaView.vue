<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Ollama</div>
      <v-spacer />
      <v-chip
        :color="status.running ? 'success' : 'error'"
        variant="tonal"
        class="mr-3"
        size="large"
      >
        <v-icon start :icon="status.running ? 'mdi-check-circle' : 'mdi-close-circle'" />
        {{ status.running ? 'Running' : 'Stopped' }}
      </v-chip>
      <v-btn
        v-if="!status.running"
        color="success"
        :loading="starting"
        @click="startOllama"
        prepend-icon="mdi-play"
      >
        Start Ollama
      </v-btn>
      <v-btn
        v-if="status.running"
        color="error"
        variant="tonal"
        :loading="stopping"
        @click="stopOllama"
        prepend-icon="mdi-stop"
      >
        Stop Ollama
      </v-btn>
      <v-btn
        color="primary"
        variant="tonal"
        :loading="refreshing"
        @click="refresh"
        prepend-icon="mdi-refresh"
        class="ml-2"
      >
        Refresh
      </v-btn>
    </div>

    <!-- Pull New Model -->
    <v-card class="mb-6">
      <v-card-title>
        <v-icon class="mr-2">mdi-download</v-icon>
        Pull Model
      </v-card-title>
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="6">
            <v-text-field
              v-model="pullModelName"
              label="Model name"
              placeholder="e.g. llama3:8b, qwen2.5-coder:14b, gemma2:9b"
              variant="outlined"
              density="compact"
              hide-details
              :disabled="!status.running || pulling"
              @keyup.enter="pullModel"
            />
          </v-col>
          <v-col cols="auto">
            <v-btn
              color="primary"
              :loading="pulling"
              :disabled="!pullModelName || !status.running"
              @click="pullModel"
              prepend-icon="mdi-download"
            >
              Pull
            </v-btn>
          </v-col>
        </v-row>
        <v-alert
          v-if="pullResult"
          :type="pullResult.type"
          class="mt-3"
          closable
          @click:close="pullResult = null"
        >
          {{ pullResult.message }}
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Running Models (in memory) -->
    <v-card class="mb-6" v-if="runningModels.length">
      <v-card-title>
        <v-icon class="mr-2" color="success">mdi-lightning-bolt</v-icon>
        Running in Memory
      </v-card-title>
      <v-card-text>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Model</th>
              <th>RAM / VRAM</th>
              <th>Expires</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in runningModels" :key="m.name">
              <td class="font-weight-medium">{{ m.name }}</td>
              <td>{{ m.size_hr }} / {{ m.size_vram_hr }}</td>
              <td>{{ formatDate(m.expires_at) }}</td>
              <td class="text-right">
                <v-btn
                  size="small"
                  color="primary"
                  variant="tonal"
                  class="mr-1"
                  @click="openChat(m.name)"
                  prepend-icon="mdi-chat"
                >
                  Chat
                </v-btn>
                <v-btn
                  size="small"
                  color="warning"
                  variant="tonal"
                  :loading="unloadingModel === m.name"
                  @click="unloadModel(m.name)"
                  prepend-icon="mdi-eject"
                >
                  Unload
                </v-btn>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

    <!-- Local Models -->
    <v-card>
      <v-card-title>
        <v-icon class="mr-2">mdi-database</v-icon>
        Local Models
        <v-chip class="ml-2" size="small" variant="tonal">{{ models.length }}</v-chip>
      </v-card-title>
      <v-card-text>
        <v-alert v-if="!status.running" type="warning" variant="tonal" class="mb-4">
          Ollama is not running. Start it to see local models.
        </v-alert>

        <div v-if="loading" class="d-flex justify-center pa-8">
          <v-progress-circular indeterminate color="primary" />
        </div>

        <v-table v-else-if="models.length" density="comfortable">
          <thead>
            <tr>
              <th>Model</th>
              <th>Size</th>
              <th>Parameters</th>
              <th>Quantization</th>
              <th>Family</th>
              <th>Modified</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in models" :key="m.name">
              <td>
                <span class="font-weight-medium">{{ m.name }}</span>
                <div class="text-caption text-grey">{{ m.digest }}</div>
              </td>
              <td>{{ m.size_hr }}</td>
              <td>{{ m.parameter_size || '—' }}</td>
              <td>{{ m.quantization || '—' }}</td>
              <td>{{ m.family || '—' }}</td>
              <td>{{ formatDate(m.modified_at) }}</td>
              <td class="text-right" style="white-space: nowrap">
                <v-btn
                  v-if="!isModelRunning(m.name)"
                  size="small"
                  color="success"
                  variant="tonal"
                  class="mr-1"
                  :loading="loadingModel === m.name"
                  @click="loadModel(m.name)"
                  prepend-icon="mdi-play"
                >
                  Run
                </v-btn>
                <v-btn
                  v-else
                  size="small"
                  color="warning"
                  variant="tonal"
                  class="mr-1"
                  :loading="unloadingModel === m.name"
                  @click="unloadModel(m.name)"
                  prepend-icon="mdi-eject"
                >
                  Unload
                </v-btn>
                <v-btn
                  icon="mdi-information-outline"
                  size="small"
                  variant="text"
                  @click="showDetail(m)"
                />
                <v-btn
                  icon="mdi-delete-outline"
                  size="small"
                  variant="text"
                  color="error"
                  @click="confirmDelete(m)"
                />
              </td>
            </tr>
          </tbody>
        </v-table>

        <div v-else class="text-center text-grey pa-8">
          No local models found. Pull one to get started.
        </div>
      </v-card-text>
    </v-card>

    <!-- Model Detail Dialog -->
    <v-dialog v-model="detailDialog" max-width="700">
      <v-card v-if="detailModel">
        <v-card-title>
          <v-icon class="mr-2">mdi-brain</v-icon>
          {{ detailModel.name }}
        </v-card-title>
        <v-card-text>
          <div v-if="detailLoading" class="d-flex justify-center pa-6">
            <v-progress-circular indeterminate color="primary" />
          </div>
          <div v-else-if="modelDetail">
            <div v-if="modelDetail.parameters" class="mb-4">
              <div class="text-subtitle-2 font-weight-bold mb-1">Parameters</div>
              <pre class="pa-3 bg-grey-lighten-4 rounded text-body-2" style="white-space: pre-wrap">{{ modelDetail.parameters }}</pre>
            </div>
            <div v-if="modelDetail.template" class="mb-4">
              <div class="text-subtitle-2 font-weight-bold mb-1">Template</div>
              <pre class="pa-3 bg-grey-lighten-4 rounded text-body-2" style="white-space: pre-wrap; max-height: 200px; overflow-y: auto">{{ modelDetail.template }}</pre>
            </div>
            <div v-if="modelDetail.system" class="mb-4">
              <div class="text-subtitle-2 font-weight-bold mb-1">System Prompt</div>
              <pre class="pa-3 bg-grey-lighten-4 rounded text-body-2" style="white-space: pre-wrap; max-height: 200px; overflow-y: auto">{{ modelDetail.system }}</pre>
            </div>
            <div v-if="modelDetail.license">
              <div class="text-subtitle-2 font-weight-bold mb-1">License</div>
              <pre class="pa-3 bg-grey-lighten-4 rounded text-body-2" style="white-space: pre-wrap; max-height: 150px; overflow-y: auto">{{ modelDetail.license }}</pre>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="detailDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Chat Dialog -->
    <v-dialog v-model="chatDialog" max-width="800" persistent>
      <v-card height="600" class="d-flex flex-column">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-chat</v-icon>
          Chat — {{ chatModel }}
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="closeChat" />
        </v-card-title>
        <v-divider />

        <!-- Messages -->
        <v-card-text ref="chatContainer" class="flex-grow-1 overflow-y-auto pa-4" style="min-height: 0">
          <div v-if="!chatMessages.length" class="text-center text-grey pa-8">
            Send a message to start chatting with <strong>{{ chatModel }}</strong>
          </div>
          <div v-for="(msg, i) in chatMessages" :key="i" class="mb-3">
            <div :class="msg.role === 'user' ? 'text-right' : ''">
              <v-chip
                :color="msg.role === 'user' ? 'primary' : 'grey-lighten-3'"
                :text-color="msg.role === 'user' ? 'white' : ''"
                variant="flat"
                size="small"
                class="mb-1"
              >
                {{ msg.role === 'user' ? 'You' : chatModel }}
                <span v-if="msg.stats" class="ml-2 text-caption">
                  {{ msg.stats }}
                </span>
              </v-chip>
              <div
                class="pa-3 rounded-lg text-body-2"
                :class="msg.role === 'user' ? 'bg-primary-lighten-5 ml-auto' : 'bg-grey-lighten-4'"
                style="max-width: 85%; display: inline-block; white-space: pre-wrap; word-break: break-word; text-align: left"
              >
                {{ msg.content }}
              </div>
            </div>
          </div>
          <div v-if="chatSending" class="mb-3">
            <v-chip color="grey-lighten-3" variant="flat" size="small" class="mb-1">{{ chatModel }}</v-chip>
            <div class="pa-3 rounded-lg bg-grey-lighten-4" style="max-width: 85%; display: inline-block">
              <v-progress-linear indeterminate color="primary" height="2" />
              <span class="text-caption text-grey mt-1">Thinking...</span>
            </div>
          </div>
        </v-card-text>

        <v-divider />

        <!-- Input -->
        <v-card-actions class="pa-3">
          <v-text-field
            v-model="chatInput"
            placeholder="Type a message..."
            variant="outlined"
            density="compact"
            hide-details
            :disabled="chatSending"
            @keyup.enter="sendChat"
            class="mr-2"
          />
          <v-btn
            color="primary"
            :loading="chatSending"
            :disabled="!chatInput.trim()"
            @click="sendChat"
            icon="mdi-send"
          />
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation -->
    <v-dialog v-model="deleteDialog" max-width="450">
      <v-card>
        <v-card-title class="text-error">
          <v-icon class="mr-2" color="error">mdi-alert</v-icon>
          Delete Model
        </v-card-title>
        <v-card-text>
          Are you sure you want to delete <strong>{{ deleteTarget?.name }}</strong>?
          This will free {{ deleteTarget?.size_hr }} of disk space.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteModel">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

// State
const status = ref({ running: false, base_url: '', models_count: 0 })
const models = ref([])
const runningModels = ref([])
const loading = ref(false)
const refreshing = ref(false)
const starting = ref(false)
const stopping = ref(false)

// Pull model
const pullModelName = ref('')
const pulling = ref(false)
const pullResult = ref(null)

// Detail dialog
const detailDialog = ref(false)
const detailModel = ref(null)
const detailLoading = ref(false)
const modelDetail = ref(null)

// Delete dialog
const deleteDialog = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Load / unload model
const loadingModel = ref(null)
const unloadingModel = ref(null)

// Chat
const chatDialog = ref(false)
const chatModel = ref('')
const chatMessages = ref([])
const chatInput = ref('')
const chatSending = ref(false)
const chatContainer = ref(null)

// Helpers
const formatDate = (iso) => {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch { return iso }
}

const isModelRunning = (name) => {
  return runningModels.value.some(m => m.name === name)
}

// Methods
const fetchStatus = async () => {
  try {
    const { data } = await api.get('/ollama/status')
    status.value = data
  } catch {
    status.value = { running: false, base_url: '', models_count: 0 }
  }
}

const fetchModels = async () => {
  if (!status.value.running) { models.value = []; return }
  loading.value = true
  try {
    const { data } = await api.get('/ollama/models')
    models.value = data
  } catch {
    models.value = []
  } finally {
    loading.value = false
  }
}

const fetchRunning = async () => {
  if (!status.value.running) { runningModels.value = []; return }
  try {
    const { data } = await api.get('/ollama/running')
    runningModels.value = data
  } catch {
    runningModels.value = []
  }
}

const refresh = async () => {
  refreshing.value = true
  await fetchStatus()
  await Promise.all([fetchModels(), fetchRunning()])
  refreshing.value = false
}

const startOllama = async () => {
  starting.value = true
  try {
    await api.post('/ollama/start')
    await fetchStatus()
    await Promise.all([fetchModels(), fetchRunning()])
  } catch (e) {
    console.error('Failed to start Ollama:', e)
  } finally {
    starting.value = false
  }
}

const stopOllama = async () => {
  stopping.value = true
  try {
    await api.post('/ollama/stop')
    await fetchStatus()
    models.value = []
    runningModels.value = []
  } catch (e) {
    console.error('Failed to stop Ollama:', e)
  } finally {
    stopping.value = false
  }
}

const pullModel = async () => {
  if (!pullModelName.value) return
  pulling.value = true
  pullResult.value = null
  try {
    const { data } = await api.post('/ollama/models/pull', { model: pullModelName.value })
    pullResult.value = { type: 'success', message: data.message }
    pullModelName.value = ''
    await fetchModels()
  } catch (e) {
    pullResult.value = { type: 'error', message: e.response?.data?.detail || 'Pull failed' }
  } finally {
    pulling.value = false
  }
}

const showDetail = async (m) => {
  detailModel.value = m
  detailDialog.value = true
  detailLoading.value = true
  modelDetail.value = null
  try {
    const { data } = await api.get(`/ollama/models/${encodeURIComponent(m.name)}/detail`)
    modelDetail.value = data
  } catch {
    modelDetail.value = { parameters: 'Failed to load details' }
  } finally {
    detailLoading.value = false
  }
}

const confirmDelete = (m) => {
  deleteTarget.value = m
  deleteDialog.value = true
}

const deleteModel = async () => {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`/ollama/models/${encodeURIComponent(deleteTarget.value.name)}`)
    models.value = models.value.filter(m => m.name !== deleteTarget.value.name)
    deleteDialog.value = false
  } catch (e) {
    console.error('Failed to delete model:', e)
  } finally {
    deleting.value = false
  }
}

const loadModel = async (name) => {
  loadingModel.value = name
  try {
    await api.post(`/ollama/models/${encodeURIComponent(name)}/load`)
    await fetchRunning()
  } catch (e) {
    console.error('Failed to load model:', e)
  } finally {
    loadingModel.value = null
  }
}

const unloadModel = async (name) => {
  unloadingModel.value = name
  try {
    await api.post(`/ollama/models/${encodeURIComponent(name)}/unload`)
    await fetchRunning()
  } catch (e) {
    console.error('Failed to unload model:', e)
  } finally {
    unloadingModel.value = null
  }
}

const openChat = (name) => {
  chatModel.value = name
  chatMessages.value = []
  chatInput.value = ''
  chatDialog.value = true
}

const closeChat = () => {
  chatDialog.value = false
  chatMessages.value = []
}

const scrollToBottom = () => {
  setTimeout(() => {
    const el = chatContainer.value?.$el || chatContainer.value
    if (el) el.scrollTop = el.scrollHeight
  }, 50)
}

const sendChat = async () => {
  const text = chatInput.value.trim()
  if (!text || chatSending.value) return

  chatMessages.value.push({ role: 'user', content: text })
  chatInput.value = ''
  chatSending.value = true
  scrollToBottom()

  try {
    const { data } = await api.post('/ollama/chat', {
      model: chatModel.value,
      message: text,
    })
    const durationSec = data.total_duration ? (data.total_duration / 1e9).toFixed(1) + 's' : ''
    const tokensPerSec = data.eval_duration && data.eval_count
      ? (data.eval_count / (data.eval_duration / 1e9)).toFixed(1) + ' tok/s'
      : ''
    const stats = [durationSec, tokensPerSec].filter(Boolean).join(' · ')
    chatMessages.value.push({ role: 'assistant', content: data.content, stats })
  } catch (e) {
    chatMessages.value.push({ role: 'assistant', content: '❌ ' + (e.response?.data?.detail || 'Request failed'), stats: '' })
  } finally {
    chatSending.value = false
    scrollToBottom()
  }
}

onMounted(() => refresh())
</script>
