<template>
  <div v-if="agent">
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" @click="$router.push('/agents')" />
      <div class="text-h4 font-weight-bold ml-2">{{ agent.name }}</div>
      <v-chip :color="statusColor(agent.status)" class="ml-3" variant="tonal">{{ agent.status }}</v-chip>
      <v-spacer />
      <v-btn v-if="agent.status !== 'running'" color="success" prepend-icon="mdi-play" @click="start" class="mr-2">Start</v-btn>
      <v-btn v-else color="error" prepend-icon="mdi-stop" @click="stop" class="mr-2">Stop</v-btn>
      <v-btn prepend-icon="mdi-pencil" :to="`/agents/${agent.id}`">Edit</v-btn>
    </div>

    <!-- Stats -->
    <v-row class="mb-4">
      <v-col v-for="s in statItems" :key="s.label" cols="6" md="2">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h5 font-weight-bold">{{ s.value }}</div>
            <div class="text-caption text-grey">{{ s.label }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Tabs -->
    <v-card>
      <v-tabs v-model="tab">
        <v-tab value="info">Info</v-tab>
        <v-tab value="tasks">Tasks</v-tab>
        <v-tab value="logs">Logs</v-tab>
        <v-tab value="skills">Skills</v-tab>
        <v-tab value="memory">Memory</v-tab>
      </v-tabs>
      <v-card-text>
        <!-- Info Tab -->
        <div v-if="tab === 'info'">
          <v-list>
            <v-list-item><strong>Model:</strong>&nbsp;{{ agent.model_name }}</v-list-item>
            <v-list-item><strong>Temperature:</strong>&nbsp;{{ agent.temperature }}</v-list-item>
            <v-list-item><strong>Context:</strong>&nbsp;{{ agent.num_ctx }}</v-list-item>
            <v-list-item v-if="agent.description"><strong>Description:</strong>&nbsp;{{ agent.description }}</v-list-item>
          </v-list>
          <div v-if="agent.system_prompt" class="mt-4">
            <div class="text-subtitle-2 mb-1">System Prompt</div>
            <v-sheet rounded class="pa-3 bg-grey-darken-4" style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">{{ agent.system_prompt }}</v-sheet>
          </div>
        </div>

        <!-- Tasks Tab -->
        <div v-if="tab === 'tasks'">
          <v-btn color="primary" size="small" prepend-icon="mdi-plus" @click="createAgentTask" class="mb-3">New Task</v-btn>
          <v-data-table :headers="taskHeaders" :items="tasks" density="compact" hover>
            <template #item.status="{ item }">
              <v-chip :color="taskStatusColor(item.status)" size="x-small" variant="tonal">{{ item.status }}</v-chip>
            </template>
          </v-data-table>
        </div>

        <!-- Logs Tab -->
        <div v-if="tab === 'logs'">
          <v-select v-model="logLevel" :items="['all','debug','info','warning','error','critical']" label="Level" density="compact" style="max-width: 200px" class="mb-3" />
          <v-list density="compact" class="log-list" style="max-height: 500px; overflow-y: auto;">
            <v-list-item v-for="log in logs" :key="log.id" class="py-0">
              <div class="d-flex">
                <v-chip :color="logColor(log.level)" size="x-small" variant="flat" class="mr-2" style="min-width: 60px;">{{ log.level }}</v-chip>
                <span class="text-caption text-grey mr-2">{{ new Date(log.created_at).toLocaleTimeString() }}</span>
                <span class="text-body-2">{{ log.message }}</span>
              </div>
            </v-list-item>
          </v-list>
        </div>

        <!-- Skills Tab -->
        <div v-if="tab === 'skills'">
          <v-list v-if="agentSkills.length">
            <v-list-item v-for="s in agentSkills" :key="s.skill_id">
              <v-list-item-title>{{ s.skill?.display_name || s.skill_id }}</v-list-item-title>
              <v-list-item-subtitle>{{ s.skill?.description }}</v-list-item-subtitle>
              <template #append>
                <v-chip :color="s.is_enabled ? 'success' : 'grey'" size="small">{{ s.is_enabled ? 'ON' : 'OFF' }}</v-chip>
              </template>
            </v-list-item>
          </v-list>
          <div v-else class="text-center text-grey pa-6">No skills attached</div>
        </div>

        <!-- Memory Tab -->
        <div v-if="tab === 'memory'">
          <v-data-table :headers="memHeaders" :items="memories" density="compact" hover>
            <template #item.type="{ item }">
              <v-chip size="x-small" variant="tonal">{{ item.type }}</v-chip>
            </template>
            <template #item.importance="{ item }">
              <v-progress-linear :model-value="item.importance * 100" :color="item.importance > 0.7 ? 'success' : 'grey'" height="6" rounded />
            </template>
            <template #item.tags="{ item }">
              <v-chip v-for="t in (item.tags || []).slice(0, 3)" :key="t" size="x-small" class="mr-1">{{ t }}</v-chip>
            </template>
          </v-data-table>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { useAgentsStore } from '../stores/agents'

const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()
const tab = ref('info')
const agent = ref(null)
const stats = ref({})
const tasks = ref([])
const logs = ref([])
const agentSkills = ref([])
const memories = ref([])
const logLevel = ref('all')

const id = computed(() => route.params.id)

const statusColor = (s) => ({ idle: 'grey', running: 'success', paused: 'warning', error: 'error', stopped: 'grey' }[s] || 'grey')
const taskStatusColor = (s) => ({ pending: 'info', running: 'success', completed: 'success', failed: 'error', cancelled: 'grey' }[s] || 'grey')
const logColor = (l) => ({ debug: 'grey', info: 'info', warning: 'warning', error: 'error', critical: 'error' }[l] || 'grey')

const statItems = computed(() => [
  { label: 'Tasks', value: stats.value.total_tasks || 0 },
  { label: 'Completed', value: stats.value.completed_tasks || 0 },
  { label: 'Failed', value: stats.value.failed_tasks || 0 },
  { label: 'Logs', value: stats.value.total_logs || 0 },
  { label: 'Memories', value: stats.value.total_memories || 0 },
  { label: 'Skills', value: stats.value.total_skills || 0 },
])

const taskHeaders = [
  { title: 'Title', key: 'title' },
  { title: 'Status', key: 'status', width: 100 },
  { title: 'Priority', key: 'priority', width: 100 },
  { title: 'Created', key: 'created_at', width: 150 },
]

const memHeaders = [
  { title: 'Title', key: 'title' },
  { title: 'Type', key: 'type', width: 100 },
  { title: 'Importance', key: 'importance', width: 120 },
  { title: 'Tags', key: 'tags', width: 200 },
  { title: 'Source', key: 'source', width: 80 },
]

const loadData = async () => {
  agent.value = await agentsStore.fetchAgent(id.value)
  stats.value = await agentsStore.fetchStats(id.value)
}

const loadTasks = async () => {
  const { data } = await api.get(`/agents/${id.value}/tasks`)
  tasks.value = data
}

const loadLogs = async () => {
  const params = logLevel.value !== 'all' ? { level: logLevel.value } : {}
  const { data } = await api.get(`/agents/${id.value}/logs`, { params: { ...params, limit: 100 } })
  logs.value = data
}

const loadSkills = async () => {
  const { data } = await api.get(`/agents/${id.value}/skills`)
  agentSkills.value = data
}

const loadMemories = async () => {
  const { data } = await api.get(`/agents/${id.value}/memory`, { params: { limit: 100 } })
  memories.value = data
}

watch(tab, (val) => {
  if (val === 'tasks') loadTasks()
  if (val === 'logs') loadLogs()
  if (val === 'skills') loadSkills()
  if (val === 'memory') loadMemories()
})

watch(logLevel, () => { if (tab.value === 'logs') loadLogs() })

const start = async () => { await agentsStore.startAgent(id.value); await loadData() }
const stop = async () => { await agentsStore.stopAgent(id.value); await loadData() }
const createAgentTask = () => router.push(`/tasks/new?agent_id=${id.value}`)

onMounted(loadData)
</script>
