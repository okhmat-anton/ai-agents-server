<template>
  <v-container fluid>
    <div class="d-flex align-center mb-4">
      <v-icon class="mr-2">mdi-alert-circle-outline</v-icon>
      <h1 class="text-h5">Agent Errors</h1>
      <v-spacer />
      <v-btn
        v-if="stats"
        variant="tonal"
        color="error"
        size="small"
        class="mr-2"
      >
        {{ stats.unresolved }} unresolved / {{ stats.total }} total
      </v-btn>
    </div>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row dense>
          <v-col cols="3">
            <v-select
              v-model="filters.agent_id"
              :items="agentOptions"
              item-title="name"
              item-value="id"
              label="Agent"
              density="compact"
              clearable
            />
          </v-col>
          <v-col cols="2">
            <v-select
              v-model="filters.error_type"
              :items="errorTypes"
              label="Error Type"
              density="compact"
              clearable
            />
          </v-col>
          <v-col cols="2">
            <v-select
              v-model="filters.source"
              :items="['autonomous', 'chat', 'skill']"
              label="Source"
              density="compact"
              clearable
            />
          </v-col>
          <v-col cols="2">
            <v-select
              v-model="filters.resolved"
              :items="[{title:'All',value:null},{title:'Unresolved',value:false},{title:'Resolved',value:true}]"
              item-title="title"
              item-value="value"
              label="Status"
              density="compact"
            />
          </v-col>
          <v-col cols="3" class="d-flex align-center">
            <v-btn color="primary" variant="tonal" size="small" @click="loadErrors" :loading="loading">
              <v-icon start>mdi-refresh</v-icon> Refresh
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Stats Cards -->
    <v-row v-if="stats" class="mb-4" dense>
      <v-col v-for="(count, type) in stats.by_type" :key="type" cols="auto">
        <v-card variant="tonal" :color="errorTypeColor(type)" class="px-4 py-2">
          <div class="text-caption">{{ type }}</div>
          <div class="text-h6">{{ count }}</div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Errors Table -->
    <v-card>
      <v-card-text class="pa-0">
        <v-alert v-if="!loading && !errors.length" type="success" variant="tonal" class="ma-4">
          No errors found matching the current filters.
        </v-alert>

        <v-table v-else density="compact" hover>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Type</th>
              <th>Source</th>
              <th>Message</th>
              <th>Context</th>
              <th>Status</th>
              <th>Time</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="err in errors" :key="err.id" :class="{ 'text-grey': err.resolved }">
              <td>
                <router-link
                  v-if="agentMap[err.agent_id]"
                  :to="`/agents/${err.agent_id}/detail`"
                  class="text-decoration-none"
                >
                  {{ agentMap[err.agent_id] }}
                </router-link>
                <span v-else class="text-grey">{{ err.agent_id.slice(0, 8) }}</span>
              </td>
              <td>
                <v-chip :color="errorTypeColor(err.error_type)" size="x-small" variant="flat">
                  {{ err.error_type }}
                </v-chip>
              </td>
              <td>
                <v-chip size="x-small" variant="outlined">{{ err.source }}</v-chip>
              </td>
              <td style="max-width: 350px;">
                <v-tooltip :text="err.message" location="bottom" max-width="500">
                  <template #activator="{ props }">
                    <span v-bind="props" class="text-truncate d-inline-block" style="max-width: 350px;">
                      {{ err.message }}
                    </span>
                  </template>
                </v-tooltip>
              </td>
              <td>
                <v-chip v-if="err.context && err.context.skill_name" size="x-small" color="info" variant="tonal">
                  {{ err.context.skill_name }}
                </v-chip>
                <v-chip v-if="err.context && err.context.project_slug" size="x-small" color="purple" variant="tonal" class="ml-1">
                  {{ err.context.project_slug }}
                </v-chip>
                <v-chip v-if="err.context && err.context.cycle" size="x-small" variant="tonal" class="ml-1">
                  cycle {{ err.context.cycle }}
                </v-chip>
              </td>
              <td>
                <v-chip :color="err.resolved ? 'success' : 'warning'" size="x-small" variant="flat">
                  {{ err.resolved ? 'Resolved' : 'Open' }}
                </v-chip>
              </td>
              <td class="text-caption text-grey text-no-wrap">
                {{ new Date(err.created_at).toLocaleString() }}
              </td>
              <td>
                <v-btn
                  v-if="!err.resolved"
                  icon
                  size="x-small"
                  @click="resolveError(err)"
                  title="Mark as resolved"
                >
                  <v-icon>mdi-check-circle-outline</v-icon>
                </v-btn>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import api from '../api'
import { useAgentsStore } from '../stores/agents'

const agentsStore = useAgentsStore()

const loading = ref(false)
const errors = ref([])
const stats = ref(null)
const filters = reactive({
  agent_id: null,
  error_type: null,
  source: null,
  resolved: null,
})

const errorTypes = ['skill_not_found', 'skill_exec_error', 'llm_error', 'unknown']

const agentOptions = computed(() =>
  (agentsStore.agents || []).map(a => ({ id: a.id, name: a.name }))
)

const agentMap = computed(() => {
  const m = {}
  for (const a of agentsStore.agents || []) m[a.id] = a.name
  return m
})

const errorTypeColor = (t) =>
  ({ skill_not_found: 'warning', skill_exec_error: 'error', llm_error: 'deep-purple', unknown: 'grey' }[t] || 'grey')

async function loadErrors() {
  loading.value = true
  try {
    const params = {}
    if (filters.agent_id) params.agent_id = filters.agent_id
    if (filters.error_type) params.error_type = filters.error_type
    if (filters.source) params.source = filters.source
    if (filters.resolved !== null) params.resolved = filters.resolved
    const { data } = await api.get('/agent-errors', { params })
    errors.value = data
  } catch (e) {
    console.error('Failed to load errors', e)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const { data } = await api.get('/agent-errors/stats')
    stats.value = data
  } catch (e) {
    console.error('Failed to load stats', e)
  }
}

async function resolveError(err) {
  try {
    const { data } = await api.patch(`/agents/${err.agent_id}/errors/${err.id}/resolve`, { resolution: '' })
    const idx = errors.value.findIndex(e => e.id === err.id)
    if (idx !== -1) errors.value[idx] = data
    loadStats()
  } catch (e) {
    console.error('Failed to resolve error', e)
  }
}

watch(filters, () => loadErrors(), { deep: true })

onMounted(async () => {
  await agentsStore.fetchAgents()
  await Promise.all([loadErrors(), loadStats()])
})
</script>
