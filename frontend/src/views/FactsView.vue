<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Facts</div>
      <v-spacer />
      <v-btn color="teal" prepend-icon="mdi-plus" @click="openCreateDialog">
        Add Fact
      </v-btn>
    </div>

    <!-- Error alert -->
    <v-alert v-if="errorMsg" type="error" closable class="mb-4" @click:close="errorMsg = null">
      {{ errorMsg }}
    </v-alert>

    <!-- Filters -->
    <div class="d-flex align-center ga-3 mb-4 flex-wrap">
      <v-btn-toggle v-model="filterType" density="compact" variant="outlined" mandatory @update:model-value="loadFacts">
        <v-btn value="all" size="small">All</v-btn>
        <v-btn value="fact" size="small">
          <v-icon size="16" class="mr-1">mdi-check-decagram</v-icon> Facts
        </v-btn>
        <v-btn value="hypothesis" size="small">
          <v-icon size="16" class="mr-1">mdi-help-circle-outline</v-icon> Hypotheses
        </v-btn>
      </v-btn-toggle>
      <v-spacer />
      <v-select
        v-model="filterAgent"
        :items="agentOptions"
        item-title="name"
        item-value="id"
        label="Agent"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        style="max-width: 220px;"
        prepend-inner-icon="mdi-robot"
        @update:model-value="loadFacts"
      />
      <v-text-field
        v-model="searchQuery"
        density="compact"
        variant="outlined"
        placeholder="Search facts..."
        prepend-inner-icon="mdi-magnify"
        hide-details
        clearable
        style="max-width: 280px;"
        @update:model-value="debouncedLoad"
      />
    </div>

    <!-- Facts Table -->
    <v-card>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="headers"
          :items="facts"
          :loading="loading"
          hover
        >
          <template #item.type="{ item }">
            <v-chip :color="item.type === 'fact' ? 'teal' : 'orange'" size="small" variant="tonal">
              <v-icon start size="14">{{ item.type === 'fact' ? 'mdi-check-decagram' : 'mdi-help-circle-outline' }}</v-icon>
              {{ item.type }}
            </v-chip>
          </template>

          <template #item.content="{ item }">
            <div class="text-truncate" style="max-width: 500px;">{{ item.content }}</div>
          </template>

          <template #item.agent_id="{ item }">
            <v-chip size="small" variant="tonal" color="blue">
              {{ agentName(item.agent_id) }}
            </v-chip>
          </template>

          <template #item.verified="{ item }">
            <v-icon v-if="item.verified" color="green" size="20">mdi-check-circle</v-icon>
            <v-icon v-else color="grey" size="20">mdi-minus-circle-outline</v-icon>
          </template>

          <template #item.confidence="{ item }">
            <v-chip size="small" variant="tonal">{{ (item.confidence * 100).toFixed(0) }}%</v-chip>
          </template>

          <template #item.created_at="{ item }">
            {{ formatDate(item.created_at) }}
          </template>

          <template #item.actions="{ item }">
            <v-btn
              v-if="item.type === 'hypothesis' && !item.verified"
              icon size="small" variant="text" color="green"
              @click.stop="verifyFact(item)"
            >
              <v-icon>mdi-check-circle</v-icon>
              <v-tooltip activator="parent" location="top">Verify</v-tooltip>
            </v-btn>
            <v-btn icon size="small" variant="text" @click.stop="editFact(item)">
              <v-icon>mdi-pencil</v-icon>
            </v-btn>
            <v-btn icon size="small" variant="text" color="error" @click.stop="deleteFact(item.id)">
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Create/Edit Fact Dialog -->
    <v-dialog v-model="formDialog" max-width="600">
      <v-card>
        <v-card-title>{{ editingFact ? 'Edit Fact' : 'New Fact' }}</v-card-title>
        <v-card-text>
          <v-select
            v-model="formData.agent_id"
            :items="agentOptions"
            item-title="name"
            item-value="id"
            label="Agent"
            variant="outlined"
            density="compact"
            class="mb-3"
            prepend-inner-icon="mdi-robot"
            :disabled="!!editingFact"
          />
          <v-select
            v-model="formData.type"
            :items="['fact', 'hypothesis']"
            label="Type"
            variant="outlined"
            density="compact"
            class="mb-3"
          />
          <v-textarea
            v-model="formData.content"
            label="Content"
            variant="outlined"
            density="compact"
            rows="4"
            class="mb-3"
          />
          <v-text-field
            v-model="formData.source"
            label="Source"
            variant="outlined"
            density="compact"
            class="mb-3"
          />
          <v-slider
            v-model="formData.confidence"
            label="Confidence"
            min="0"
            max="1"
            step="0.05"
            thumb-label
            class="mb-3"
          />
          <v-checkbox
            v-model="formData.verified"
            label="Verified"
            density="compact"
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
          <v-btn color="teal" :loading="saving" @click="saveFact">{{ editingFact ? 'Update' : 'Create' }}</v-btn>
        </v-card-actions>
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
const facts = ref([])
const loading = ref(false)
const errorMsg = ref(null)
const filterType = ref('all')
const filterAgent = ref(null)
const searchQuery = ref('')

const formDialog = ref(false)
const editingFact = ref(null)
const saving = ref(false)
const formData = ref({
  agent_id: null, type: 'fact', content: '', source: 'user',
  verified: false, confidence: 0.8, tags: [],
})

const agents = ref([])
const agentOptions = computed(() => agents.value)

const headers = [
  { title: 'Type', key: 'type', width: 130 },
  { title: 'Content', key: 'content' },
  { title: 'Agent', key: 'agent_id', width: 150 },
  { title: 'Verified', key: 'verified', width: 90 },
  { title: 'Confidence', key: 'confidence', width: 110 },
  { title: 'Created', key: 'created_at', width: 140 },
  { title: 'Actions', key: 'actions', sortable: false, width: 140 },
]

onMounted(async () => {
  await Promise.all([loadFacts(), loadAgents()])
})

async function loadAgents() {
  try {
    await agentsStore.fetchAgents()
    agents.value = agentsStore.agents
    if (agents.value.length && !formData.value.agent_id) {
      formData.value.agent_id = agents.value[0].id
    }
  } catch (e) {
    console.error('Failed to load agents:', e)
  }
}

async function loadFacts() {
  loading.value = true
  try {
    const params = { limit: 200 }
    if (filterType.value && filterType.value !== 'all') params.type = filterType.value
    if (filterAgent.value) params.agent_id = filterAgent.value
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await api.get('/facts', { params })
    facts.value = data.items || []
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to load facts'
  } finally {
    loading.value = false
  }
}

let _debounce = null
function debouncedLoad() {
  clearTimeout(_debounce)
  _debounce = setTimeout(() => loadFacts(), 400)
}

function openCreateDialog() {
  editingFact.value = null
  formData.value = {
    agent_id: agents.value.length ? agents.value[0].id : null,
    type: 'fact', content: '', source: 'user',
    verified: false, confidence: 0.8, tags: [],
  }
  formDialog.value = true
}

function editFact(item) {
  editingFact.value = item
  formData.value = {
    agent_id: item.agent_id,
    type: item.type,
    content: item.content,
    source: item.source,
    verified: item.verified,
    confidence: item.confidence,
    tags: [...(item.tags || [])],
  }
  formDialog.value = true
}

async function saveFact() {
  saving.value = true
  try {
    if (editingFact.value) {
      await api.patch(`/facts/${editingFact.value.id}`, {
        type: formData.value.type,
        content: formData.value.content,
        source: formData.value.source,
        verified: formData.value.verified,
        confidence: formData.value.confidence,
        tags: formData.value.tags,
      })
      showSnackbar?.('Fact updated', 'success')
    } else {
      if (!formData.value.agent_id) {
        errorMsg.value = 'Please select an agent'
        saving.value = false
        return
      }
      await api.post('/facts', formData.value)
      showSnackbar?.('Fact created', 'success')
    }
    formDialog.value = false
    await loadFacts()
  } catch (e) {
    errorMsg.value = e.response?.data?.detail || 'Failed to save fact'
  } finally {
    saving.value = false
  }
}

async function verifyFact(item) {
  try {
    await api.patch(`/facts/${item.id}`, { verified: true, type: 'fact' })
    showSnackbar?.('Fact verified', 'success')
    await loadFacts()
  } catch (e) {
    showSnackbar?.('Failed to verify', 'error')
  }
}

async function deleteFact(id) {
  try {
    await api.delete(`/facts/${id}`)
    facts.value = facts.value.filter(f => f.id !== id)
    showSnackbar?.('Fact deleted', 'success')
  } catch (e) {
    showSnackbar?.('Failed to delete', 'error')
  }
}

function agentName(agentId) {
  const a = agents.value.find(a => a.id === agentId)
  return a?.name || agentId?.substring(0, 8)
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>
