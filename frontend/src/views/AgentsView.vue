<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Agents</div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" to="/agents/new">New Agent</v-btn>
    </div>

    <v-card>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="headers"
          :items="store.agents"
          :loading="store.loading"
          hover
          @click:row="(_, { item }) => $router.push(`/agents/${item.id}/detail`)"
        >
          <template #item.status="{ item }">
            <v-chip :color="statusColor(item.status)" size="small" variant="tonal">{{ item.status }}</v-chip>
          </template>
          <template #item.models="{ item }">
            <div v-if="item.agent_models && item.agent_models.length" class="d-flex flex-wrap ga-1">
              <v-chip v-for="am in item.agent_models" :key="am.id" size="x-small" variant="tonal" color="primary">
                {{ am.model_display_name || am.model_name }}
              </v-chip>
            </div>
            <span v-else class="text-grey">—</span>
          </template>
          <template #item.created_at="{ item }">
            {{ new Date(item.created_at).toLocaleDateString() }}
          </template>
          <template #item.actions="{ item }">
            <v-btn icon="mdi-play" size="small" variant="text" color="success" @click.stop="handleStart(item)" v-if="item.status !== 'running'" />
            <v-btn icon="mdi-stop" size="small" variant="text" color="error" @click.stop="handleStop(item)" v-else />
            <v-btn icon="mdi-pencil" size="small" variant="text" @click.stop="$router.push(`/agents/${item.id}`)" />
            <v-btn icon="mdi-content-copy" size="small" variant="text" @click.stop="handleDuplicate(item)" />
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click.stop="handleDelete(item)" />
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Delete confirm -->
    <ConfirmDeleteDialog
      v-model="deleteDialog"
      title="Delete Agent"
      :message="`Are you sure you want to delete &quot;${deleteTarget?.name}&quot;?`"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import { useAgentsStore } from '../stores/agents'
import ConfirmDeleteDialog from '../components/ConfirmDeleteDialog.vue'

const store = useAgentsStore()
const showSnackbar = inject('showSnackbar')
const deleteDialog = ref(false)
const deleteTarget = ref(null)

const headers = [
  { title: 'Name', key: 'name' },
  { title: 'Status', key: 'status', width: 120 },
  { title: 'Model', key: 'models', sortable: false },
  { title: 'Created', key: 'created_at', width: 120 },
  { title: 'Actions', key: 'actions', sortable: false, width: 200 },
]

const statusColor = (s) => ({ idle: 'grey', running: 'success', paused: 'warning', error: 'error', stopped: 'grey' }[s] || 'grey')

const handleStart = async (agent) => {
  await store.startAgent(agent.id)
  showSnackbar(`${agent.name} started`)
}

const handleStop = async (agent) => {
  await store.stopAgent(agent.id)
  showSnackbar(`${agent.name} stopped`)
}

const handleDuplicate = async (agent) => {
  await store.duplicateAgent(agent.id)
  showSnackbar(`${agent.name} duplicated`)
}

const handleDelete = (agent) => {
  deleteTarget.value = agent
  deleteDialog.value = true
}

const confirmDelete = async () => {
  await store.deleteAgent(deleteTarget.value.id)
  deleteDialog.value = false
  showSnackbar('Agent deleted')
}

onMounted(() => store.fetchAgents())
</script>
