<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">Tasks</div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" to="/tasks/new">New Task</v-btn>
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
        <v-data-table :headers="headers" :items="store.tasks" :loading="store.loading" hover>
          <template #item.status="{ item }">
            <v-chip :color="statusColor(item.status)" size="small" variant="tonal">{{ item.status }}</v-chip>
          </template>
          <template #item.priority="{ item }">
            <v-chip :color="priorityColor(item.priority)" size="x-small" variant="flat">{{ item.priority }}</v-chip>
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
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useTasksStore } from '../stores/tasks'
import ConfirmDeleteDialog from '../components/ConfirmDeleteDialog.vue'

const store = useTasksStore()
const filterStatus = ref('all')
const filterPriority = ref('all')
const deleteDialog = ref(false)
const deleteTarget = ref(null)

const headers = [
  { title: 'Title', key: 'title' },
  { title: 'Status', key: 'status', width: 120 },
  { title: 'Priority', key: 'priority', width: 100 },
  { title: 'Type', key: 'type', width: 100 },
  { title: 'Created', key: 'created_at', width: 120 },
  { title: 'Actions', key: 'actions', sortable: false, width: 160 },
]

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
