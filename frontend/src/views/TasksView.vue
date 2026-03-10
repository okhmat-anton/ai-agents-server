<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Tasks</div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="taskDialog = true">New Task</v-btn>
    </div>

    <v-card>
      <v-card-text>
        <v-row class="mb-3">
          <v-col cols="3">
            <v-select v-model="filterStatus" :items="['all','pending','running','completed','failed','cancelled']" label="Status" density="compact" />
          </v-col>
          <v-col cols="3">
            <v-select v-model="filterPriority" :items="['all','low','normal','high','critical']" label="Priority" density="compact" />
          </v-col>
        </v-row>

        <!-- Tag filter -->
        <div v-if="allTags.length" class="d-flex align-center ga-1 mb-3 flex-wrap">
          <v-icon size="18" class="mr-1 text-grey">mdi-tag-multiple</v-icon>
          <v-chip
            v-for="tag in allTags" :key="tag"
            :color="selectedTags.includes(tag) ? 'cyan' : 'default'"
            :variant="selectedTags.includes(tag) ? 'flat' : 'outlined'"
            size="small" @click="toggleTag(tag)"
          >{{ tag }}</v-chip>
          <v-btn v-if="selectedTags.length" variant="text" size="x-small" color="grey" @click="selectedTags = []">Clear</v-btn>
        </div>

        <v-data-table :headers="headers" :items="tagFilteredTasks" :loading="store.loading" hover>
          <template #item.status="{ item }">
            <v-chip :color="statusColor(item.status)" size="small" variant="tonal">{{ item.status }}</v-chip>
            <v-chip v-if="item.is_user_task" size="x-small" variant="flat" color="amber" class="ml-1">
              <v-icon size="10" class="mr-1">mdi-account</v-icon>User
            </v-chip>
          </template>
          <template #item.agent_name="{ item }">
            <router-link v-if="item.agent_id" :to="`/agents/${item.agent_id}/detail`" class="text-decoration-none">
              <v-chip size="small" variant="tonal" color="primary">{{ item.agent_name || 'Agent' }}</v-chip>
            </router-link>
            <span v-else class="text-grey">—</span>
          </template>
          <template #item.priority="{ item }">
            <v-chip :color="priorityColor(item.priority)" size="x-small" variant="flat">{{ item.priority }}</v-chip>
          </template>
          <template #item.tags="{ item }">
            <div class="d-flex ga-1 flex-wrap"><v-chip v-for="t in (item.tags || [])" :key="t" size="x-small" variant="tonal" color="cyan">{{ t }}</v-chip></div>
          </template>
          <template #item.created_at="{ item }">{{ new Date(item.created_at).toLocaleDateString() }}</template>
          <template #item.actions="{ item }">
            <v-btn v-if="item.status === 'pending'" icon="mdi-play" size="small" variant="text" color="success" @click="run(item)" />
            <v-btn v-if="item.status === 'running'" icon="mdi-cancel" size="small" variant="text" color="warning" @click="cancel(item)" />
            <v-btn icon="mdi-pencil" size="small" variant="text" @click="$router.push(`/tasks/${item.id}`)" />
            <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="handleDelete(item)" />
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <ConfirmDeleteDialog
      v-model="deleteDialog"
      title="Delete Task"
      :message="`Are you sure you want to delete &quot;${deleteTarget?.title}&quot;?`"
      @confirm="confirmDelete"
    />

    <TaskFormDialog v-model="taskDialog" @saved="load" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, inject } from 'vue'
import { useTasksStore } from '../stores/tasks'
import ConfirmDeleteDialog from '../components/ConfirmDeleteDialog.vue'
import TaskFormDialog from '../components/TaskFormDialog.vue'

const dataRefreshSignal = inject('dataRefreshSignal', reactive({ type: '', timestamp: 0 }))
watch(() => dataRefreshSignal.timestamp, () => {
  if (dataRefreshSignal.type === 'tasks') load()
})

const store = useTasksStore()
const filterStatus = ref('all')
const filterPriority = ref('all')
const deleteDialog = ref(false)
const deleteTarget = ref(null)
const taskDialog = ref(false)

const selectedTags = ref([])

const headers = [
  { title: 'Title', key: 'title' },
  { title: 'Agent', key: 'agent_name', width: 150 },
  { title: 'Status', key: 'status', width: 120 },
  { title: 'Tags', key: 'tags', width: 160, sortable: false },
  { title: 'Priority', key: 'priority', width: 100 },
  { title: 'Type', key: 'type', width: 100 },
  { title: 'Created', key: 'created_at', width: 120 },
  { title: 'Actions', key: 'actions', sortable: false, width: 160 },
]

const allTags = computed(() => {
  const tags = new Set()
  store.tasks.forEach(i => (i.tags || []).forEach(t => tags.add(t)))
  return [...tags].sort()
})

const tagFilteredTasks = computed(() => {
  if (!selectedTags.value.length) return store.tasks
  return store.tasks.filter(i => (i.tags || []).some(t => selectedTags.value.includes(t)))
})

function toggleTag(tag) {
  const idx = selectedTags.value.indexOf(tag)
  if (idx >= 0) selectedTags.value.splice(idx, 1)
  else selectedTags.value.push(tag)
}

const statusColor = (s) => ({ pending: 'info', running: 'success', completed: 'success', failed: 'error', cancelled: 'grey', paused: 'warning' }[s] || 'grey')
const priorityColor = (p) => ({ low: 'grey', normal: 'info', high: 'warning', critical: 'error' }[p] || 'grey')

const load = () => {
  const params = {}
  if (filterStatus.value !== 'all') params.status = filterStatus.value
  if (filterPriority.value !== 'all') params.priority = filterPriority.value
  store.fetchTasks(params)
}

watch([filterStatus, filterPriority], load)
onMounted(load)

const run = (t) => store.runTask(t.id).then(load)
const cancel = (t) => store.cancelTask(t.id).then(load)
const handleDelete = (t) => {
  deleteTarget.value = t
  deleteDialog.value = true
}
const confirmDelete = async () => {
  await store.deleteTask(deleteTarget.value.id)
  deleteDialog.value = false
  load()
}
</script>
