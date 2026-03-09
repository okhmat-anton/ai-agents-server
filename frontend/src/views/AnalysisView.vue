<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Analysis</div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        New Topic
      </v-btn>
    </div>

    <!-- Error alert -->
    <v-alert v-if="errorMsg" type="error" closable class="mb-4" @click:close="errorMsg = null">
      {{ errorMsg }}
    </v-alert>

    <!-- Filters -->
    <div class="d-flex align-center ga-3 mb-4 flex-wrap">
      <v-chip-group v-model="filterStatus" selected-class="text-primary" @update:model-value="loadTopics">
        <v-chip value="" variant="tonal" size="small">All</v-chip>
        <v-chip v-for="s in statuses" :key="s.value" :value="s.value" :color="s.color" variant="tonal" size="small">
          <v-icon start size="14">{{ s.icon }}</v-icon>
          {{ s.label }}
        </v-chip>
      </v-chip-group>
      <v-spacer />
      <v-text-field
        v-model="searchQuery"
        density="compact"
        variant="outlined"
        placeholder="Search topics..."
        prepend-inner-icon="mdi-magnify"
        hide-details
        clearable
        style="max-width: 280px;"
        @update:model-value="debouncedLoad"
      />
    </div>

    <!-- Topics Table -->
    <v-card>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="headers"
          :items="topics"
          :loading="loading"
          hover
          @click:row="(_, { item }) => openDetail(item)"
        >
          <template #item.status="{ item }">
            <v-chip :color="statusColor(item.status)" size="small" variant="tonal">
              {{ item.status }}
            </v-chip>
          </template>

          <template #item.title="{ item }">
            <div>
              <span class="font-weight-medium">{{ item.title }}</span>
              <div v-if="item.description" class="text-caption text-grey text-truncate" style="max-width: 400px;">
                {{ item.description }}
              </div>
            </div>
          </template>

          <template #item.agent_id="{ item }">
            <v-chip v-if="item.agent_id" size="small" variant="tonal" color="blue">
              {{ agentName(item.agent_id) }}
            </v-chip>
            <v-chip v-else size="small" variant="tonal" color="grey">Global</v-chip>
          </template>

          <template #item.fact_ids="{ item }">
            <v-chip size="small" variant="tonal" color="teal">
              {{ item.fact_ids?.length || 0 }} facts
            </v-chip>
          </template>

          <template #item.created_at="{ item }">
            {{ formatDate(item.created_at) }}
          </template>

          <template #item.actions="{ item }">
            <v-btn icon size="small" variant="text" @click.stop="editTopic(item)">
              <v-icon>mdi-pencil</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" color="error" @click.stop="deleteTopic(item.id)">
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Topic Detail Dialog -->
    <v-dialog v-model="detailDialog" max-width="900" scrollable>
      <v-card v-if="currentTopic">
        <v-card-title class="d-flex align-center pa-4">
          <v-chip :color="statusColor(currentTopic.status)" size="small" class="mr-3">
            {{ currentTopic.status }}
          </v-chip>
          <span class="text-h6 flex-grow-1">{{ currentTopic.title }}</span>
          <v-spacer />
          <v-btn icon size="small" variant="text" @click="detailDialog = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-divider />
        <v-card-text style="max-height: 65vh; overflow-y: auto;">
          <!-- Description -->
          <div v-if="currentTopic.description" class="mb-4 pa-3 rounded-lg" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);">
            {{ currentTopic.description }}
          </div>

          <!-- Metadata -->
          <div class="d-flex align-center ga-2 mb-4 flex-wrap">
            <v-chip v-if="currentTopic.agent_id" size="small" variant="tonal" color="blue">
              <v-icon start size="14">mdi-robot</v-icon>
              {{ agentName(currentTopic.agent_id) }}
            </v-chip>
            <v-chip v-else size="small" variant="tonal" color="grey">Global</v-chip>
            <v-chip v-for="tag in currentTopic.tags" :key="tag" size="small" variant="tonal" color="blue-grey">{{ tag }}</v-chip>
            <v-chip size="x-small" variant="tonal">{{ currentTopic.created_by }}</v-chip>
            <v-chip size="x-small" variant="tonal">{{ formatDate(currentTopic.created_at) }}</v-chip>
          </div>

          <v-divider class="mb-4" />

          <!-- Connected Facts -->
          <div class="d-flex align-center mb-3">
            <div class="text-subtitle-1 font-weight-bold">
              <v-icon class="mr-1" size="20">mdi-check-decagram</v-icon>
              Connected Facts ({{ connectedFacts.length }})
            </div>
            <v-spacer />
            <v-btn size="small" variant="tonal" color="teal" prepend-icon="mdi-link-plus" @click="openConnectFactDialog">
              Connect Fact
            </v-btn>
          </div>

          <div v-if="connectedFacts.length">
            <v-card v-for="f in connectedFacts" :key="f.id" variant="outlined" class="mb-2 pa-3">
              <div class="d-flex align-start">
                <v-icon :color="f.type === 'fact' ? 'teal' : 'orange'" size="18" class="mr-2 mt-1">
                  {{ f.type === 'fact' ? 'mdi-check-decagram' : 'mdi-help-circle-outline' }}
                </v-icon>
                <div class="flex-grow-1">
                  <div class="text-body-2">{{ f.content }}</div>
                  <div class="d-flex ga-1 mt-1">
                    <v-chip :color="f.type === 'fact' ? 'teal' : 'orange'" size="x-small" variant="flat">{{ f.type }}</v-chip>
                    <v-chip v-if="f.agent_id" size="x-small" variant="tonal" color="blue">{{ agentName(f.agent_id) }}</v-chip>
                    <v-chip size="x-small" variant="tonal">conf: {{ (f.confidence * 100).toFixed(0) }}%</v-chip>
                  </div>
                </div>
                <v-btn icon size="x-small" variant="text" color="error" @click="disconnectFact(f.id)">
                  <v-icon>mdi-link-off</v-icon>
                  <v-tooltip activator="parent" location="top">Disconnect</v-tooltip>
                </v-btn>
              </div>
            </v-card>
          </div>
          <div v-else class="text-center text-grey pa-4">
            <v-icon size="40" class="mb-2">mdi-link-variant-off</v-icon>
            <div>No facts connected yet</div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Create/Edit Topic Dialog -->
    <v-dialog v-model="formDialog" max-width="600">
      <v-card>
        <v-card-title>{{ editingTopic ? 'Edit Topic' : 'New Analysis Topic' }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="formData.title"
            label="Title"
            variant="outlined"
            density="compact"
            class="mb-3"
          />
          <v-textarea
            v-model="formData.description"
            label="Description"
            variant="outlined"
            density="compact"
            rows="4"
            class="mb-3"
          />
          <v-select
            v-model="formData.status"
            :items="statuses.map(s => s.value)"
            label="Status"
            variant="outlined"
            density="compact"
            class="mb-3"
          />
          <v-select
            v-model="formData.agent_id"
            :items="agentOptions"
            item-title="name"
            item-value="id"
            label="Agent (optional)"
            variant="outlined"
            density="compact"
            clearable
            prepend-inner-icon="mdi-robot"
            class="mb-3"
          />
          <v-combobox
            v-model="formData.tags"
            label="Tags"
            variant="outlined"
            density="compact"
            chips
            multiple
            closable-chips
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="formDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveTopic">{{ editingTopic ? 'Update' : 'Create' }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Connect Fact Dialog -->
    <v-dialog v-model="connectFactDialog" max-width="700" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          Connect Fact
          <v-spacer />
          <v-text-field
            v-model="factSearchQuery"
            density="compact"
            variant="outlined"
            placeholder="Search facts..."
            prepend-inner-icon="mdi-magnify"
            hide-details
            clearable
            style="max-width: 260px;"
            @update:model-value="debouncedLoadAvailableFacts"
          />
        </v-card-title>
        <v-divider />
        <v-card-text style="max-height: 50vh; overflow-y: auto;">
          <div v-if="availableFactsLoading" class="text-center pa-4">
            <v-progress-circular indeterminate size="24" />
          </div>
          <div v-else-if="availableFacts.length">
            <v-card
              v-for="f in availableFacts"
              :key="f.id"
              variant="outlined"
              class="mb-2 pa-3"
              :class="{ 'border-opacity-50': isFactConnected(f.id) }"
              @click="connectFact(f.id)"
              style="cursor: pointer;"
            >
              <div class="d-flex align-center">
                <v-icon :color="f.type === 'fact' ? 'teal' : 'orange'" size="18" class="mr-2">
                  {{ f.type === 'fact' ? 'mdi-check-decagram' : 'mdi-help-circle-outline' }}
                </v-icon>
                <div class="flex-grow-1">
                  <div class="text-body-2">{{ f.content }}</div>
                  <div class="d-flex ga-1 mt-1">
                    <v-chip v-if="f.agent_id" size="x-small" variant="tonal" color="blue">{{ agentName(f.agent_id) }}</v-chip>
                    <v-chip size="x-small" variant="tonal">{{ f.source }}</v-chip>
                  </div>
                </div>
                <v-icon v-if="isFactConnected(f.id)" color="success" size="20">mdi-check-circle</v-icon>
                <v-icon v-else color="grey" size="20">mdi-link-plus</v-icon>
              </div>
            </v-card>
          </div>
          <div v-else class="text-center text-grey pa-4">No facts found</div>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import api from '../api'
import { useAgentsStore } from '../stores/agents'

const showSnackbar = inject('showSnackbar')
const agentsStore = useAgentsStore()

// State
const topics = ref([])
const loading = ref(false)
const errorMsg = ref(null)
const filterStatus = ref('')
const searchQuery = ref('')

const detailDialog = ref(false)
const currentTopic = ref(null)
const connectedFacts = ref([])

const formDialog = ref(false)
const editingTopic = ref(null)
const saving = ref(false)
const formData = ref({ title: '', description: '', status: 'active', agent_id: null, tags: [] })

const connectFactDialog = ref(false)
const availableFacts = ref([])
const availableFactsLoading = ref(false)
const factSearchQuery = ref('')

const agents = ref([])

const statuses = [
  { value: 'draft', label: 'Draft', color: 'grey', icon: 'mdi-pencil-outline' },
  { value: 'active', label: 'Active', color: 'blue', icon: 'mdi-play-circle-outline' },
  { value: 'completed', label: 'Completed', color: 'success', icon: 'mdi-check-circle-outline' },
  { value: 'archived', label: 'Archived', color: 'brown', icon: 'mdi-archive-outline' },
]

const headers = [
  { title: 'Status', key: 'status', width: 120 },
  { title: 'Title', key: 'title' },
  { title: 'Agent', key: 'agent_id', width: 150 },
  { title: 'Facts', key: 'fact_ids', width: 100 },
  { title: 'Created', key: 'created_at', width: 140 },
  { title: 'Actions', key: 'actions', sortable: false, width: 100 },
]

const agentOptions = computed(() => agents.value)

onMounted(async () => {
  await Promise.all([loadTopics(), loadAgents()])
})

async function loadAgents() {
  try {
    await agentsStore.fetchAgents()
    agents.value = agentsStore.agents
  } catch (e) {
    console.error('Failed to load agents:', e)
  }
}

async function loadTopics() {
  loading.value = true
  try {
    const params = { limit: 200 }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await api.get('/analysis-topics', { params })
    topics.value = data.items || []
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to load topics'
  } finally {
    loading.value = false
  }
}

let _debounce = null
function debouncedLoad() {
  clearTimeout(_debounce)
  _debounce = setTimeout(() => loadTopics(), 400)
}

function openCreateDialog() {
  editingTopic.value = null
  formData.value = { title: '', description: '', status: 'active', agent_id: null, tags: [] }
  formDialog.value = true
}

function editTopic(item) {
  editingTopic.value = item
  formData.value = {
    title: item.title,
    description: item.description,
    status: item.status,
    agent_id: item.agent_id,
    tags: [...(item.tags || [])],
  }
  formDialog.value = true
}

async function saveTopic() {
  saving.value = true
  try {
    if (editingTopic.value) {
      await api.patch(`/analysis-topics/${editingTopic.value.id}`, {
        title: formData.value.title,
        description: formData.value.description,
        status: formData.value.status,
        tags: formData.value.tags,
      })
      showSnackbar?.('Topic updated', 'success')
    } else {
      const payload = { ...formData.value }
      if (payload.agent_id) {
        await api.post(`/agents/${payload.agent_id}/analysis-topics`, payload)
      } else {
        await api.post('/analysis-topics', payload)
      }
      showSnackbar?.('Topic created', 'success')
    }
    formDialog.value = false
    await loadTopics()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to save topic'
  } finally {
    saving.value = false
  }
}

async function deleteTopic(id) {
  try {
    await api.delete(`/analysis-topics/${id}`)
    topics.value = topics.value.filter(t => t.id !== id)
    showSnackbar?.('Topic deleted', 'success')
  } catch (e) {
    showSnackbar?.('Failed to delete', 'error')
  }
}

async function openDetail(item) {
  currentTopic.value = item
  connectedFacts.value = []
  detailDialog.value = true
  await loadConnectedFacts(item.id)
}

async function loadConnectedFacts(topicId) {
  try {
    const { data } = await api.get(`/analysis-topics/${topicId}/facts`)
    connectedFacts.value = data.items || []
  } catch (e) {
    console.error('Failed to load connected facts:', e)
  }
}

function openConnectFactDialog() {
  factSearchQuery.value = ''
  availableFacts.value = []
  connectFactDialog.value = true
  loadAvailableFacts()
}

async function loadAvailableFacts() {
  availableFactsLoading.value = true
  try {
    const params = { limit: 100 }
    if (factSearchQuery.value) params.search = factSearchQuery.value
    const { data } = await api.get('/facts', { params })
    availableFacts.value = data.items || []
  } catch (e) {
    console.error('Failed to load facts:', e)
  } finally {
    availableFactsLoading.value = false
  }
}

let _factDebounce = null
function debouncedLoadAvailableFacts() {
  clearTimeout(_factDebounce)
  _factDebounce = setTimeout(() => loadAvailableFacts(), 400)
}

function isFactConnected(factId) {
  return currentTopic.value?.fact_ids?.includes(factId)
}

async function connectFact(factId) {
  if (isFactConnected(factId)) return
  try {
    const { data } = await api.post(`/analysis-topics/${currentTopic.value.id}/facts/${factId}`)
    currentTopic.value = data
    await loadConnectedFacts(currentTopic.value.id)
    showSnackbar?.('Fact connected', 'success')
  } catch (e) {
    showSnackbar?.('Failed to connect fact', 'error')
  }
}

async function disconnectFact(factId) {
  try {
    const { data } = await api.delete(`/analysis-topics/${currentTopic.value.id}/facts/${factId}`)
    currentTopic.value = data
    await loadConnectedFacts(currentTopic.value.id)
    showSnackbar?.('Fact disconnected', 'success')
  } catch (e) {
    showSnackbar?.('Failed to disconnect fact', 'error')
  }
}

function agentName(agentId) {
  const a = agents.value.find(a => a.id === agentId)
  return a?.name || agentId?.substring(0, 8)
}

function statusColor(s) {
  return { draft: 'grey', active: 'blue', completed: 'success', archived: 'brown' }[s] || 'grey'
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
