<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Facts</div>
      <v-spacer />
      <v-btn
        v-if="selectedItems.length"
        color="error"
        variant="tonal"
        prepend-icon="mdi-delete"
        class="mr-3"
        @click="bulkDeleteConfirm"
      >
        Delete ({{ selectedItems.length }})
      </v-btn>
      <v-btn
        v-if="selectedItems.length"
        color="indigo"
        variant="tonal"
        prepend-icon="mdi-tag-multiple"
        class="mr-3"
        @click="openBulkCategoryDialog"
      >
        Change Category ({{ selectedItems.length }})
      </v-btn>
      <v-btn
        v-if="selectedItems.length"
        color="deep-purple"
        variant="tonal"
        prepend-icon="mdi-forum"
        class="mr-3"
        @click="discussSelected"
      >
        Discuss ({{ selectedItems.length }})
      </v-btn>
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
        v-model="filterCategory"
        :items="categoryOptions"
        label="Category"
        variant="outlined"
        density="compact"
        hide-details
        clearable
        style="max-width: 200px;"
        prepend-inner-icon="mdi-tag-outline"
        @update:model-value="loadFacts"
      />
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

    <!-- Facts grouped by category -->
    <div v-if="!filterCategory && groupedFacts.length > 1">
      <div class="d-flex align-center mb-2">
        <v-checkbox
          :model-value="allSelected"
          :indeterminate="someSelected && !allSelected"
          density="compact"
          hide-details
          class="flex-grow-0 mr-2"
          @update:model-value="toggleSelectAll"
        />
        <span class="text-caption text-medium-emphasis">Select all ({{ facts.length }})</span>
      </div>
      <div v-for="group in groupedFacts" :key="group.category" class="mb-6">
        <div class="text-subtitle-1 font-weight-bold mb-2 d-flex align-center">
          <v-checkbox
            :model-value="isCategoryAllSelected(group.category)"
            :indeterminate="isCategorySomeSelected(group.category) && !isCategoryAllSelected(group.category)"
            density="compact"
            hide-details
            class="flex-grow-0 mr-1"
            @update:model-value="toggleSelectCategory(group.category, $event)"
          />
          <v-icon size="18" class="mr-2">mdi-tag</v-icon>
          {{ group.category || 'Uncategorized' }}
          <v-chip size="x-small" variant="tonal" class="ml-2">{{ group.items.length }}</v-chip>
        </div>
        <draggable
          :list="group.items"
          item-key="id"
          handle=".drag-handle"
          animation="200"
          ghost-class="drag-ghost"
          @end="onDragEnd(group.category)"
        >
          <template #item="{ element: fact }">
            <v-card variant="outlined" class="mb-1" :color="isSelected(fact) ? 'primary' : undefined">
              <v-card-text class="pa-2 d-flex align-center ga-2">
                <v-checkbox
                  :model-value="isSelected(fact)"
                  density="compact"
                  hide-details
                  class="flex-grow-0"
                  @update:model-value="toggleSelect(fact)"
                />
                <div class="drag-handle">
                  <v-icon size="18" color="grey">mdi-drag-vertical</v-icon>
                </div>
                <v-chip :color="fact.type === 'fact' ? 'teal' : 'orange'" size="small" variant="tonal">
                  <v-icon start size="14">{{ fact.type === 'fact' ? 'mdi-check-decagram' : 'mdi-help-circle-outline' }}</v-icon>
                  {{ fact.type }}
                </v-chip>
                <div class="flex-grow-1 text-truncate" style="min-width: 0; max-width: 500px;">{{ fact.content }}</div>
                <v-chip v-if="isGlobalFact(fact)" size="x-small" variant="tonal" color="teal">
                  <v-icon start size="12">mdi-earth</v-icon> Global
                </v-chip>
                <template v-else>
                  <v-chip v-for="aid in (fact.agent_ids && fact.agent_ids.length ? fact.agent_ids : [fact.agent_id])" :key="aid" size="x-small" variant="tonal" color="blue" class="mr-1">{{ agentName(aid) }}</v-chip>
                </template>
                <v-icon v-if="fact.verified" color="green" size="18">mdi-check-circle</v-icon>
                <v-chip size="x-small" variant="tonal">{{ (fact.confidence * 100).toFixed(0) }}%</v-chip>
                <span class="text-caption text-grey">{{ formatDate(fact.created_at) }}</span>
                <v-btn v-if="fact.type === 'hypothesis' && !fact.verified" icon size="small" variant="text" color="green" @click.stop="verifyFact(fact)"><v-icon>mdi-check-circle</v-icon></v-btn>
                <v-btn icon size="small" variant="text" @click.stop="editFact(fact)"><v-icon>mdi-pencil</v-icon></v-btn>
                <v-btn icon size="small" variant="text" color="error" @click.stop="deleteFact(fact.id)"><v-icon>mdi-delete</v-icon></v-btn>
              </v-card-text>
            </v-card>
          </template>
        </draggable>
      </div>
    </div>

    <!-- Flat list -->
    <div v-else>
      <div class="d-flex align-center mb-2">
        <v-checkbox
          :model-value="allSelected"
          :indeterminate="someSelected && !allSelected"
          density="compact"
          hide-details
          class="flex-grow-0 mr-2"
          @update:model-value="toggleSelectAll"
        />
        <span class="text-caption text-medium-emphasis">Select all ({{ facts.length }})</span>
      </div>
      <draggable
        :list="facts"
        item-key="id"
        handle=".drag-handle"
        animation="200"
        ghost-class="drag-ghost"
        @end="onDragEndFlat"
      >
        <template #item="{ element: fact }">
          <v-card variant="outlined" class="mb-1" :color="isSelected(fact) ? 'primary' : undefined">
            <v-card-text class="pa-2 d-flex align-center ga-2">
              <v-checkbox
                :model-value="isSelected(fact)"
                density="compact"
                hide-details
                class="flex-grow-0"
                @update:model-value="toggleSelect(fact)"
              />
              <div class="drag-handle">
                <v-icon size="18" color="grey">mdi-drag-vertical</v-icon>
              </div>
              <v-chip :color="fact.type === 'fact' ? 'teal' : 'orange'" size="small" variant="tonal">
                <v-icon start size="14">{{ fact.type === 'fact' ? 'mdi-check-decagram' : 'mdi-help-circle-outline' }}</v-icon>
                {{ fact.type }}
              </v-chip>
              <div class="flex-grow-1 text-truncate" style="min-width: 0; max-width: 500px;">{{ fact.content }}</div>
              <v-chip v-if="isGlobalFact(fact)" size="x-small" variant="tonal" color="teal">
                <v-icon start size="12">mdi-earth</v-icon> Global
              </v-chip>
              <template v-else>
                <v-chip v-for="aid in (fact.agent_ids && fact.agent_ids.length ? fact.agent_ids : [fact.agent_id])" :key="aid" size="x-small" variant="tonal" color="blue" class="mr-1">{{ agentName(aid) }}</v-chip>
              </template>
              <v-chip v-if="fact.category" size="x-small" variant="tonal" color="indigo">{{ fact.category }}</v-chip>
              <v-icon v-if="fact.verified" color="green" size="18">mdi-check-circle</v-icon>
              <v-chip size="x-small" variant="tonal">{{ (fact.confidence * 100).toFixed(0) }}%</v-chip>
              <span class="text-caption text-grey">{{ formatDate(fact.created_at) }}</span>
              <v-btn v-if="fact.type === 'hypothesis' && !fact.verified" icon size="small" variant="text" color="green" @click.stop="verifyFact(fact)"><v-icon>mdi-check-circle</v-icon></v-btn>
              <v-btn icon size="small" variant="text" @click.stop="editFact(fact)"><v-icon>mdi-pencil</v-icon></v-btn>
              <v-btn icon size="small" variant="text" color="error" @click.stop="deleteFact(fact.id)"><v-icon>mdi-delete</v-icon></v-btn>
            </v-card-text>
          </v-card>
        </template>
      </draggable>
    </div>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">{{ deleteFactIds.length > 1 ? `Delete ${deleteFactIds.length} Facts` : 'Delete Fact' }}</v-card-title>
        <v-card-text>
          {{ deleteFactIds.length > 1 ? `Are you sure you want to delete ${deleteFactIds.length} facts? This action cannot be undone.` : 'Are you sure you want to delete this fact? This action cannot be undone.' }}
          <div class="text-body-2 mt-4 mb-1">
            Type <strong class="text-error" style="cursor: pointer; border-bottom: 1px dashed currentColor" @click="deleteConfirmText = 'DELETE'">DELETE</strong> to confirm
          </div>
          <v-text-field
            v-model="deleteConfirmText"
            placeholder="DELETE"
            variant="outlined"
            density="compact"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :disabled="deleteConfirmText !== 'DELETE'" @click="doDeleteFact">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bulk Category Change Dialog -->
    <v-dialog v-model="bulkCategoryDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6">Change Category ({{ selectedItems.length }})</v-card-title>
        <v-card-text>
          <v-combobox
            v-model="bulkCategoryValue"
            :items="categoryOptions"
            label="New Category"
            variant="outlined"
            density="compact"
            clearable
            prepend-inner-icon="mdi-tag-outline"
            hint="Leave empty to remove category"
            persistent-hint
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="bulkCategoryDialog = false">Cancel</v-btn>
          <v-btn color="indigo" :loading="bulkCategorySaving" @click="doBulkCategoryChange">Apply</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Create/Edit Fact Dialog -->
    <v-dialog v-model="formDialog" max-width="600">
      <v-card>
        <v-card-title>{{ editingFact ? 'Edit Fact' : 'New Fact' }}</v-card-title>
        <v-card-text>
          <!-- Global toggle -->
          <v-switch
            v-model="formGlobal"
            label="Global (all agents)"
            color="teal"
            density="compact"
            class="mb-2"
            :disabled="!!editingFact"
            hide-details
          />
          <!-- Multi-agent selector (hidden when global) -->
          <v-select
            v-if="!formGlobal"
            v-model="formData.agent_ids"
            :items="agentOptions"
            item-title="name"
            item-value="id"
            label="Agents"
            variant="outlined"
            density="compact"
            class="mb-3"
            prepend-inner-icon="mdi-robot"
            multiple
            chips
            closable-chips
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
            v-model="formData.category"
            :items="categoryOptions"
            label="Category"
            variant="outlined"
            density="compact"
            clearable
            prepend-inner-icon="mdi-tag-outline"
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
import draggable from 'vuedraggable'
import api from '../api'
import { useAgentsStore } from '../stores/agents'
import { useChatStore } from '../stores/chat'

const showSnackbar = inject('showSnackbar')
const agentsStore = useAgentsStore()
const chatStore = useChatStore()

// State
const facts = ref([])
const loading = ref(false)
const errorMsg = ref(null)
const filterType = ref('all')
const filterAgent = ref(null)
const filterCategory = ref(null)
const searchQuery = ref('')

const formDialog = ref(false)
const editingFact = ref(null)
const saving = ref(false)
const formGlobal = ref(true)
const formData = ref({
  agent_ids: [], type: 'fact', content: '', source: 'user',
  verified: false, confidence: 0.8, category: '', tags: [],
})

const deleteDialog = ref(false)
const deleteFactIds = ref([])
const deleteConfirmText = ref('')
const selectedItems = ref([])
const bulkCategoryDialog = ref(false)
const bulkCategoryValue = ref(null)
const bulkCategorySaving = ref(false)

const allSelected = computed(() => facts.value.length > 0 && selectedItems.value.length === facts.value.length)
const someSelected = computed(() => selectedItems.value.length > 0)

const agents = ref([])
const agentOptions = computed(() => agents.value)

const categoryOptions = computed(() => {
  const cats = [...new Set(facts.value.map(f => f.category).filter(Boolean))]
  return cats.sort()
})

const groupedFacts = computed(() => {
  const groups = {}
  for (const f of facts.value) {
    const cat = f.category || ''
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(f)
  }
  return Object.entries(groups)
    .sort(([a], [b]) => { if (!a) return 1; if (!b) return -1; return a.localeCompare(b) })
    .map(([cat, items]) => ({ category: cat, items }))
})

const headers = [
  { title: 'Type', key: 'type', width: 130 },
  { title: 'Content', key: 'content' },
  { title: 'Agent', key: 'agent_id', width: 200 },
  { title: 'Category', key: 'category', width: 140 },
  { title: 'Links', key: 'links', width: 80, sortable: false },
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
    if (filterCategory.value) params.category = filterCategory.value
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
  formGlobal.value = true
  formData.value = {
    agent_ids: [],
    type: 'fact', content: '', source: 'user',
    verified: false, confidence: 0.8, category: '', tags: [],
  }
  formDialog.value = true
}

function editFact(item) {
  editingFact.value = item
  const agentIds = item.agent_ids || []
  formGlobal.value = isGlobalFact(item)
  formData.value = {
    agent_ids: [...agentIds],
    type: item.type,
    content: item.content,
    source: item.source,
    verified: item.verified,
    confidence: item.confidence,
    category: item.category || '',
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
        category: formData.value.category || null,
        tags: formData.value.tags,
        agent_ids: formGlobal.value ? [] : formData.value.agent_ids,
      })
      showSnackbar?.('Fact updated', 'success')
    } else {
      const payload = {
        ...formData.value,
        agent_ids: formGlobal.value ? [] : formData.value.agent_ids,
      }
      if (!formGlobal.value && (!payload.agent_ids || !payload.agent_ids.length)) {
        errorMsg.value = 'Please select at least one agent or set as Global'
        saving.value = false
        return
      }
      await api.post('/facts', payload)
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
  deleteFactIds.value = [id]
  deleteConfirmText.value = ''
  deleteDialog.value = true
}

function bulkDeleteConfirm() {
  if (!selectedItems.value.length) return
  deleteFactIds.value = selectedItems.value.map(f => f.id)
  deleteConfirmText.value = ''
  deleteDialog.value = true
}

async function doDeleteFact() {
  const ids = deleteFactIds.value
  deleteDialog.value = false
  try {
    if (ids.length === 1) {
      await api.delete(`/facts/${ids[0]}`)
      facts.value = facts.value.filter(f => f.id !== ids[0])
    } else {
      await api.post('/facts/bulk-delete', { ids })
      const idSet = new Set(ids)
      facts.value = facts.value.filter(f => !idSet.has(f.id))
      selectedItems.value = []
    }
    showSnackbar?.(`${ids.length > 1 ? ids.length + ' facts' : 'Fact'} deleted`, 'success')
  } catch (e) {
    showSnackbar?.('Failed to delete', 'error')
  }
}

function isSelected(fact) {
  return selectedItems.value.some(f => f.id === fact.id)
}

function toggleSelect(fact) {
  const idx = selectedItems.value.findIndex(f => f.id === fact.id)
  if (idx !== -1) {
    selectedItems.value.splice(idx, 1)
  } else {
    selectedItems.value.push(fact)
  }
}

function toggleSelectAll(val) {
  if (val) {
    selectedItems.value = [...facts.value]
  } else {
    selectedItems.value = []
  }
}

function isCategoryAllSelected(category) {
  const group = groupedFacts.value.find(g => g.category === category)
  if (!group || !group.items.length) return false
  return group.items.every(f => selectedItems.value.some(s => s.id === f.id))
}

function isCategorySomeSelected(category) {
  const group = groupedFacts.value.find(g => g.category === category)
  if (!group) return false
  return group.items.some(f => selectedItems.value.some(s => s.id === f.id))
}

function toggleSelectCategory(category, val) {
  const group = groupedFacts.value.find(g => g.category === category)
  if (!group) return
  if (val) {
    // Add all items from this category that are not already selected
    const existingIds = new Set(selectedItems.value.map(f => f.id))
    for (const f of group.items) {
      if (!existingIds.has(f.id)) selectedItems.value.push(f)
    }
  } else {
    // Remove all items from this category
    const catIds = new Set(group.items.map(f => f.id))
    selectedItems.value = selectedItems.value.filter(f => !catIds.has(f.id))
  }
}

function openBulkCategoryDialog() {
  if (!selectedItems.value.length) return
  bulkCategoryValue.value = null
  bulkCategoryDialog.value = true
}

async function doBulkCategoryChange() {
  bulkCategorySaving.value = true
  try {
    const ids = selectedItems.value.map(f => f.id)
    await api.post('/facts/bulk-category', { ids, category: bulkCategoryValue.value || null })
    showSnackbar?.(`Category updated for ${ids.length} facts`, 'success')
    bulkCategoryDialog.value = false
    selectedItems.value = []
    await loadFacts()
  } catch (e) {
    showSnackbar?.('Failed to update category', 'error')
  } finally {
    bulkCategorySaving.value = false
  }
}

function agentName(agentId) {
  const a = agents.value.find(a => a.id === agentId)
  return a?.name || agentId?.substring(0, 8)
}

function isGlobalFact(item) {
  return (!item.agent_ids || item.agent_ids.length === 0) && item.agent_id === '__global__'
}

function linkedCount(item) {
  return (item.linked_video_ids?.length || 0) + (item.linked_analysis_ids?.length || 0) + (item.linked_idea_ids?.length || 0)
}

function formatDate(dt) {
  if (!dt) return ''
  return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function onDragEnd(category) {
  const group = groupedFacts.value.find(g => g.category === (category || ''))
  if (!group) return
  const ids = group.items.map(f => f.id)
  try {
    await api.post('/facts/reorder', { ids })
    await loadFacts()
  } catch (e) {
    showSnackbar?.('Failed to reorder', 'error')
  }
}

async function onDragEndFlat() {
  const ids = facts.value.map(f => f.id)
  try {
    await api.post('/facts/reorder', { ids })
    await loadFacts()
  } catch (e) {
    showSnackbar?.('Failed to reorder', 'error')
  }
}

async function discussSelected() {
  if (!selectedItems.value.length) return
  try {
    const lines = selectedItems.value.map(f => {
      const label = f.type === 'hypothesis' ? 'Hypothesis' : 'Fact'
      return `### ${label}: ${f.content.substring(0, 300)}`
    }).join('\n\n')
    const session = await chatStore.createSession({ title: `Discuss ${selectedItems.value.length} fact(s)` })
    chatStore.openPanel()
    await chatStore.sendMessage(`Please analyze and discuss these facts:\n\n${lines}`)
    selectedItems.value = []
    showSnackbar?.('Chat session created', 'success')
  } catch (e) {
    showSnackbar?.('Failed to create discussion', 'error')
  }
}
</script>

<style scoped>
.drag-handle {
  cursor: grab;
  opacity: 0.4;
  transition: opacity 0.2s;
}
.drag-handle:hover {
  opacity: 1;
}
.drag-handle:active {
  cursor: grabbing;
}
.drag-ghost {
  opacity: 0.3;
  background: rgba(var(--v-theme-primary), 0.1);
}
</style>
