<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Video Analysis</div>
      <v-spacer />
      <v-text-field
        v-model="videoUrl"
        density="compact"
        variant="outlined"
        placeholder="Paste video URL..."
        prepend-inner-icon="mdi-link"
        hide-details
        clearable
        class="mr-3"
        style="max-width: 400px"
        @keydown.enter="addVideo"
      />
      <v-btn color="primary" prepend-icon="mdi-plus" :loading="adding" :disabled="!videoUrl?.trim()" @click="addVideo">
        Add Video
      </v-btn>
    </div>

    <!-- Error alert -->
    <v-alert v-if="errorMsg" type="error" closable class="mb-4" @click:close="errorMsg = null">
      {{ errorMsg }}
    </v-alert>

    <!-- Filters -->
    <div class="d-flex align-center ga-3 mb-4 flex-wrap">
      <v-chip-group v-model="filterPlatform" selected-class="text-primary" @update:model-value="loadHistory">
        <v-chip value="" variant="tonal" size="small">All</v-chip>
        <v-chip v-for="p in platforms" :key="p.value" :value="p.value" :color="p.color" variant="tonal" size="small">
          <v-icon start size="14">{{ p.icon }}</v-icon>
          {{ p.label }}
        </v-chip>
      </v-chip-group>
      <v-spacer />
      <v-select
        v-model="filterCategory"
        :items="categoryOptions"
        label="Category"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        style="max-width: 200px;"
        prepend-inner-icon="mdi-tag-outline"
        @update:model-value="loadHistory"
      />
      <v-select
        v-model="selectedAgentId"
        :items="agents"
        item-title="name"
        item-value="id"
        label="Agent"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        style="max-width: 220px;"
        prepend-inner-icon="mdi-robot"
      />
    </div>

    <!-- Videos grouped by category -->
    <div v-if="filterCategory === null && groupedHistory.length > 1">
      <div v-for="group in groupedHistory" :key="group.category" class="mb-6">
        <div class="text-subtitle-1 font-weight-bold mb-2 d-flex align-center">
          <v-icon size="18" class="mr-2">mdi-tag</v-icon>
          {{ group.category || 'Uncategorized' }}
          <v-chip size="x-small" variant="tonal" class="ml-2">{{ group.items.length }}</v-chip>
        </div>
        <v-card>
          <v-card-text class="pa-0">
            <v-data-table
              :headers="headers"
              :items="group.items"
              :loading="loadingHistory"
              hover
              density="compact"
              @click:row="(_, { item }) => openVideo(item)"
            >
              <template #item.platform="{ item }">
                <v-chip :color="platformColor(item.platform)" size="small" variant="tonal">
                  {{ item.platform }}
                </v-chip>
              </template>
              <template #item.url="{ item }">
                <div class="d-flex align-center">
                  <div>
                    <span class="font-weight-medium text-truncate d-block" style="max-width: 400px;">{{ item.url }}</span>
                    <div v-if="item.transcript" class="text-caption text-grey text-truncate" style="max-width: 400px;">
                      {{ item.transcript.substring(0, 80) }}…
                    </div>
                  </div>
                </div>
              </template>
              <template #item.status="{ item }">
                <v-chip :color="item.transcript ? 'success' : (item.error ? 'error' : 'warning')" size="small" variant="tonal">
                  {{ item.transcript ? 'ready' : (item.error ? 'error' : 'pending') }}
                </v-chip>
              </template>
              <template #item.category="{ item }">
                <v-chip v-if="item.category" size="small" variant="tonal" color="indigo">{{ item.category }}</v-chip>
              </template>
              <template #item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>
              <template #item.actions="{ item }">
                <v-btn v-if="!item.transcript && !item.error" icon size="small" variant="text" color="primary" :loading="fetchingId === item.id" @click.stop="fetchTranscriptForItem(item)">
                  <v-icon>mdi-text-recognition</v-icon>
                </v-btn>
                <v-btn icon size="small" variant="text" color="error" @click.stop="confirmDeleteVideo(item.id)">
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </div>
    </div>

    <!-- Flat table when no grouping -->
    <v-card v-else>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="headers"
          :items="filteredHistory"
          :loading="loadingHistory"
          hover
          @click:row="(_, { item }) => openVideo(item)"
        >
          <template #item.platform="{ item }">
            <v-chip :color="platformColor(item.platform)" size="small" variant="tonal">
              {{ item.platform }}
            </v-chip>
          </template>

          <template #item.url="{ item }">
            <div class="d-flex align-center">
              <div>
                <span class="font-weight-medium text-truncate d-block" style="max-width: 400px;">{{ item.url }}</span>
                <div v-if="item.transcript" class="text-caption text-grey text-truncate" style="max-width: 400px;">
                  {{ item.transcript.substring(0, 80) }}…
                </div>
              </div>
            </div>
          </template>

          <template #item.status="{ item }">
            <v-chip
              :color="item.transcript ? 'success' : (item.error ? 'error' : 'warning')"
              size="small"
              variant="tonal"
            >
              {{ item.transcript ? 'ready' : (item.error ? 'error' : 'pending') }}
            </v-chip>
          </template>

          <template #item.category="{ item }">
            <v-chip v-if="item.category" size="small" variant="tonal" color="indigo">{{ item.category }}</v-chip>
          </template>

          <template #item.created_at="{ item }">
            {{ formatDate(item.created_at) }}
          </template>

          <template #item.actions="{ item }">
            <v-btn
              v-if="!item.transcript && !item.error"
              icon
              size="small"
              variant="text"
              color="primary"
              :loading="fetchingId === item.id"
              @click.stop="fetchTranscriptForItem(item)"
            >
              <v-icon>mdi-text-recognition</v-icon>
              <v-tooltip activator="parent" location="top">Get Transcript</v-tooltip>
            </v-btn>
            <v-btn icon size="small" variant="text" color="error" @click.stop="confirmDeleteVideo(item.id)">
              <v-icon>mdi-delete</v-icon>
              <v-tooltip activator="parent" location="top">Delete</v-tooltip>
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Delete Video</v-card-title>
        <v-card-text>
          Are you sure you want to delete this video? This action cannot be undone.
          <v-text-field
            v-model="deleteConfirmText"
            label="Type DELETE to confirm"
            variant="outlined"
            density="compact"
            class="mt-4"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :disabled="deleteConfirmText !== 'DELETE'" @click="doDeleteVideo">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Video Detail Dialog -->
    <v-dialog v-model="detailDialog" max-width="900" scrollable>
      <v-card v-if="currentVideo">
        <v-card-title class="d-flex align-center pa-4">
          <v-chip :color="platformColor(currentVideo.platform)" size="small" class="mr-3">
            {{ currentVideo.platform }}
          </v-chip>
          <span class="text-body-1 text-truncate flex-grow-1" style="max-width: 600px;">{{ currentVideo.url }}</span>
          <v-spacer />
          <v-btn
            v-if="!transcript"
            color="primary"
            size="small"
            variant="tonal"
            :loading="fetching"
            prepend-icon="mdi-text-recognition"
            class="mr-2"
            @click="fetchTranscriptForCurrent"
          >
            Get Transcript
          </v-btn>
          <v-chip v-if="currentVideo.language" size="x-small" variant="tonal" class="mr-2">{{ currentVideo.language }}</v-chip>
          <v-btn icon size="small" variant="text" @click="detailDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-divider />

        <!-- Category -->
        <div class="d-flex align-center ga-2 px-4 py-2" style="background: rgba(255,255,255,0.02);">
          <v-combobox
            :model-value="currentVideo.category"
            :items="categoryOptions"
            label="Category"
            variant="outlined"
            density="compact"
            hide-details
            clearable
            style="max-width: 250px;"
            prepend-inner-icon="mdi-tag-outline"
            @update:model-value="updateVideoCategory($event)"
          />
          <v-spacer />
        </div>

        <!-- Action toolbar (only when transcript is available) -->
        <div v-if="transcript" class="d-flex align-center flex-wrap ga-2 px-4 py-2" style="background: rgba(255,255,255,0.02);">
          <v-btn variant="tonal" color="primary" size="small" prepend-icon="mdi-chat-plus-outline" @click="startChatWithTranscript">
            Start Chat
          </v-btn>
          <v-btn variant="tonal" color="orange" size="small" prepend-icon="mdi-lightbulb-on-outline" :loading="extractingFacts" :disabled="!selectedAgentId" @click="extractFacts">
            Extract Facts
          </v-btn>
          <v-btn variant="tonal" color="teal" size="small" prepend-icon="mdi-text-box-check-outline" :loading="summarizing" @click="getSummary">
            Summary
          </v-btn>
          <v-btn variant="tonal" color="deep-purple" size="small" prepend-icon="mdi-brain" :loading="savingMemory" :disabled="!selectedAgentId" @click="saveToMemory">
            Save to Memory
          </v-btn>
        </div>

        <v-divider v-if="transcript" />

        <v-card-text style="max-height: 65vh; overflow-y: auto;">
          <!-- Summary result -->
          <v-alert v-if="summaryText" type="info" variant="tonal" class="mb-3" closable @click:close="summaryText = null">
            <div class="text-subtitle-2 mb-1 font-weight-bold">Summary</div>
            <div style="white-space: pre-wrap;">{{ summaryText }}</div>
          </v-alert>

          <!-- Facts result -->
          <v-alert v-if="factsResult" type="success" variant="tonal" class="mb-3" closable @click:close="factsResult = null">
            <div class="text-subtitle-2 mb-1 font-weight-bold">Extracted Facts</div>
            <div style="white-space: pre-wrap;">{{ factsResult }}</div>
          </v-alert>

          <!-- Memory result -->
          <v-alert v-if="memoryResult" color="deep-purple" variant="tonal" class="mb-3" closable @click:close="memoryResult = null">
            <v-icon class="mr-1">mdi-brain</v-icon>
            {{ memoryResult }}
          </v-alert>

          <!-- Transcript text -->
          <div v-if="transcript" class="transcript-box pa-4 rounded-lg" style="
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            white-space: pre-wrap;
            font-size: 13px;
            line-height: 1.7;
          ">{{ transcript }}</div>

          <div v-else-if="!fetching" class="text-center text-grey py-8">
            <v-icon size="48" class="mb-2" color="grey-darken-1">mdi-text-recognition</v-icon>
            <div>No transcript yet. Click <strong>Get Transcript</strong> to fetch it via ScrapeCreators API.</div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import api from '../api'
import { useChatStore } from '../stores/chat'
import { useAgentsStore } from '../stores/agents'

const showSnackbar = inject('showSnackbar')
const chatStore = useChatStore()
const agentsStore = useAgentsStore()

// State
const videoUrl = ref('')
const adding = ref(false)
const fetching = ref(false)
const fetchingId = ref(null)
const currentVideo = ref(null)
const transcript = ref('')
const errorMsg = ref(null)
const detailDialog = ref(false)
const filterPlatform = ref('')

const selectedAgentId = ref(null)
const extractingFacts = ref(false)
const summarizing = ref(false)
const savingMemory = ref(false)
const summaryText = ref(null)
const factsResult = ref(null)
const memoryResult = ref(null)

const history = ref([])
const loadingHistory = ref(false)
const agents = ref([])
const deleteDialog = ref(false)
const deleteVideoId = ref(null)
const deleteConfirmText = ref('')
const filterCategory = ref(null)

const platforms = [
  { value: 'youtube', label: 'YouTube', color: 'red', icon: 'mdi-youtube' },
  { value: 'tiktok', label: 'TikTok', color: 'pink', icon: 'mdi-music-note' },
  { value: 'instagram', label: 'Instagram', color: 'purple', icon: 'mdi-instagram' },
  { value: 'facebook', label: 'Facebook', color: 'blue', icon: 'mdi-facebook' },
  { value: 'twitter', label: 'X/Twitter', color: 'cyan', icon: 'mdi-twitter' },
]

const headers = [
  { title: 'Platform', key: 'platform', width: 120 },
  { title: 'URL', key: 'url' },
  { title: 'Category', key: 'category', width: 140 },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Added', key: 'created_at', width: 140 },
  { title: 'Actions', key: 'actions', sortable: false, width: 120 },
]

const filteredHistory = computed(() => {
  if (!filterPlatform.value) return history.value
  return history.value.filter(v => v.platform === filterPlatform.value)
})

const categoryOptions = computed(() => {
  const cats = [...new Set(history.value.map(v => v.category).filter(Boolean))]
  return cats.sort()
})

const groupedHistory = computed(() => {
  const items = filteredHistory.value
  const groups = {}
  for (const v of items) {
    const cat = v.category || ''
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(v)
  }
  return Object.entries(groups)
    .sort(([a], [b]) => {
      if (!a) return 1
      if (!b) return -1
      return a.localeCompare(b)
    })
    .map(([cat, items]) => ({ category: cat, items }))
})

onMounted(async () => {
  await Promise.all([loadHistory(), loadAgents()])
})

async function loadAgents() {
  try {
    await agentsStore.fetchAgents()
    agents.value = agentsStore.agents
    if (agents.value.length && !selectedAgentId.value) {
      selectedAgentId.value = agents.value[0].id
    }
  } catch (e) {
    console.error('Failed to load agents:', e)
  }
}

async function loadHistory() {
  loadingHistory.value = true
  try {
    const params = { limit: 200 }
    if (filterPlatform.value) params.platform = filterPlatform.value
    if (filterCategory.value) params.category = filterCategory.value
    const { data } = await api.get('/watched-videos', { params })
    history.value = data.items || []
  } catch (e) {
    console.error('Failed to load history:', e)
  } finally {
    loadingHistory.value = false
  }
}

async function addVideo() {
  if (!videoUrl.value?.trim()) return
  adding.value = true
  errorMsg.value = null
  try {
    const { data } = await api.post('/watched-videos', { url: videoUrl.value.trim() })
    videoUrl.value = ''
    await loadHistory()
    openVideo(data)
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to add video'
  } finally {
    adding.value = false
  }
}

function openVideo(item) {
  currentVideo.value = item
  summaryText.value = null
  factsResult.value = null
  memoryResult.value = null
  errorMsg.value = null
  if (item.transcript) {
    loadFullTranscript(item)
  } else {
    transcript.value = ''
  }
  detailDialog.value = true
}

async function loadFullTranscript(item) {
  try {
    const { data } = await api.get(`/watched-videos/${item.id}/full-transcript`)
    transcript.value = data.transcript || item.transcript || ''
  } catch {
    transcript.value = item.transcript || ''
  }
}

async function fetchTranscriptForCurrent() {
  if (!currentVideo.value) return
  fetching.value = true
  errorMsg.value = null
  try {
    const { data } = await api.post('/watched-videos/fetch', { video_id: currentVideo.value.id })
    currentVideo.value = { ...currentVideo.value, ...data }
    if (data.id) {
      try {
        const { data: full } = await api.get(`/watched-videos/${data.id}/full-transcript`)
        transcript.value = full.transcript || data.transcript || ''
      } catch {
        transcript.value = data.transcript || ''
      }
    } else {
      transcript.value = data.transcript || ''
    }
    await loadHistory()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to fetch transcript'
  } finally {
    fetching.value = false
  }
}

async function fetchTranscriptForItem(item) {
  fetchingId.value = item.id
  errorMsg.value = null
  try {
    const { data } = await api.post('/watched-videos/fetch', { video_id: item.id })
    const idx = history.value.findIndex(v => v.id === item.id)
    if (idx !== -1) {
      history.value[idx] = { ...history.value[idx], transcript: data.transcript, language: data.language }
    }
    if (currentVideo.value?.id === item.id) {
      currentVideo.value = { ...currentVideo.value, ...data }
      try {
        const { data: full } = await api.get(`/watched-videos/${data.id}/full-transcript`)
        transcript.value = full.transcript || data.transcript || ''
      } catch {
        transcript.value = data.transcript || ''
      }
    }
    showSnackbar?.('Transcript fetched', 'success')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to fetch transcript'
  } finally {
    fetchingId.value = null
  }
}

function startChatWithTranscript() {
  if (!transcript.value) return
  const prefix = `Video transcript from ${currentVideo.value?.url || 'video'}:\n\n`
  chatStore.pendingInput = prefix + transcript.value
  chatStore.openPanel()
  detailDialog.value = false
}

async function extractFacts() {
  if (!transcript.value || !selectedAgentId.value) return
  extractingFacts.value = true
  factsResult.value = null
  try {
    const { data } = await api.post(`/agents/${selectedAgentId.value}/facts`, {
      type: 'fact',
      content: `[Video: ${currentVideo.value?.url}]\n\n${transcript.value.substring(0, 8000)}`,
      source: 'video',
      verified: false,
      confidence: 0.7,
      tags: ['video', currentVideo.value?.platform || 'unknown'],
    })
    factsResult.value = `Fact saved (id: ${data.id}). Source: video transcript.`
    showSnackbar?.('Fact extracted and saved', 'success')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to extract facts'
  } finally {
    extractingFacts.value = false
  }
}

async function getSummary() {
  if (!transcript.value) return
  summarizing.value = true
  summaryText.value = null
  try {
    const { data: session } = await api.post('/chat/sessions', {
      title: `Summary: ${currentVideo.value?.url?.substring(0, 60) || 'video'}`,
      chat_type: 'user',
    })
    const { data } = await api.post(`/chat/sessions/${session.id}/messages`, {
      content: `Please provide a concise summary of the following video transcript. Focus on the key points, main topics, and conclusions.\n\n---\n\n${transcript.value.substring(0, 12000)}`,
    }, { timeout: 300000 })
    const assistantMsg = data.find?.(m => m.role === 'assistant') || data
    summaryText.value = assistantMsg.content || assistantMsg.text || JSON.stringify(assistantMsg)
    showSnackbar?.('Summary generated', 'success')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to generate summary'
  } finally {
    summarizing.value = false
  }
}

async function saveToMemory() {
  if (!transcript.value || !selectedAgentId.value) return
  savingMemory.value = true
  memoryResult.value = null
  try {
    const { data } = await api.post(`/agents/${selectedAgentId.value}/memory`, {
      title: `Video transcript: ${currentVideo.value?.url?.substring(0, 80) || 'video'}`,
      content: transcript.value.substring(0, 50000),
      type: 'fact',
      importance: 0.7,
      tags: ['video', currentVideo.value?.platform || 'unknown'],
      category: 'knowledge',
    })
    memoryResult.value = `Saved to ChromaDB memory (id: ${data.id})`
    showSnackbar?.('Saved to memory', 'success')
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to save to memory'
  } finally {
    savingMemory.value = false
  }
}

function confirmDeleteVideo(id) {
  deleteVideoId.value = id
  deleteConfirmText.value = ''
  deleteDialog.value = true
}

async function updateVideoCategory(val) {
  if (!currentVideo.value) return
  const category = val || null
  try {
    await api.patch(`/watched-videos/${currentVideo.value.id}`, { category })
    currentVideo.value = { ...currentVideo.value, category }
    const idx = history.value.findIndex(v => v.id === currentVideo.value.id)
    if (idx !== -1) history.value[idx] = { ...history.value[idx], category }
    showSnackbar?.('Category updated', 'success')
  } catch (e) {
    showSnackbar?.('Failed to update category', 'error')
  }
}

async function doDeleteVideo() {
  const id = deleteVideoId.value
  deleteDialog.value = false
  try {
    await api.delete(`/watched-videos/${id}`)
    history.value = history.value.filter(v => v.id !== id)
    if (currentVideo.value?.id === id) {
      currentVideo.value = null
      transcript.value = ''
      detailDialog.value = false
    }
    showSnackbar?.('Video deleted', 'success')
  } catch (e) {
    showSnackbar?.('Failed to delete', 'error')
  }
}

function platformColor(p) {
  return { youtube: 'red', tiktok: 'pink', instagram: 'purple', facebook: 'blue', twitter: 'cyan', threads: 'grey', linkedin: 'indigo', reddit: 'deep-orange', twitch: 'purple', kick: 'green' }[p] || 'grey'
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
