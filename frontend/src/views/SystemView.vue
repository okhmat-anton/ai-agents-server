<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">System</div>
      <v-spacer />
      <v-chip
        v-if="!enabled"
        color="error"
        variant="flat"
        prepend-icon="mdi-lock"
        class="mr-3"
      >
        Disabled — enable in Settings
      </v-chip>
      <v-btn-toggle v-model="activeTab" mandatory density="compact" variant="outlined">
        <v-btn value="info" prepend-icon="mdi-information">Info</v-btn>
        <v-btn value="processes" prepend-icon="mdi-format-list-bulleted">Processes</v-btn>
      </v-btn-toggle>
    </div>

    <v-alert v-if="!enabled" type="warning" variant="tonal" class="mb-4">
      System access is disabled.
      <v-btn to="/settings" variant="text" color="warning" size="small" class="ml-2">Go to Settings</v-btn>
    </v-alert>

    <template v-if="enabled">
      <!-- System Info Tab -->
      <template v-if="activeTab === 'info'">
        <v-row class="mb-4">
          <!-- Platform -->
          <v-col cols="12" md="6">
            <v-card>
              <v-card-title><v-icon class="mr-2">mdi-laptop</v-icon>Platform</v-card-title>
              <v-card-text>
                <v-table density="compact">
                  <tbody>
                    <tr v-for="(val, key) in platformInfo" :key="key">
                      <td class="font-weight-medium" style="width:40%">{{ key }}</td>
                      <td>{{ val }}</td>
                    </tr>
                  </tbody>
                </v-table>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- CPU -->
          <v-col cols="12" md="6">
            <v-card>
              <v-card-title><v-icon class="mr-2">mdi-chip</v-icon>CPU</v-card-title>
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <div class="text-h3 font-weight-bold mr-3">{{ sysInfo.cpu_percent || 0 }}%</div>
                  <div>
                    <div>{{ sysInfo.cpu_count_logical || '?' }} cores (logical)</div>
                    <div v-if="sysInfo.cpu_freq_mhz">{{ sysInfo.cpu_freq_mhz }} MHz</div>
                  </div>
                </div>
                <v-progress-linear
                  :model-value="sysInfo.cpu_percent || 0"
                  :color="sysInfo.cpu_percent > 80 ? 'error' : sysInfo.cpu_percent > 50 ? 'warning' : 'success'"
                  height="8"
                  rounded
                />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row class="mb-4">
          <!-- Memory -->
          <v-col cols="12" md="6">
            <v-card>
              <v-card-title><v-icon class="mr-2">mdi-memory</v-icon>Memory</v-card-title>
              <v-card-text>
                <div class="d-flex align-center mb-3">
                  <div class="text-h3 font-weight-bold mr-3">{{ sysInfo.memory_percent || 0 }}%</div>
                  <div>
                    <div>{{ formatBytes(sysInfo.memory_used) }} / {{ formatBytes(sysInfo.memory_total) }}</div>
                    <div class="text-caption">Available: {{ formatBytes(sysInfo.memory_available) }}</div>
                  </div>
                </div>
                <v-progress-linear
                  :model-value="sysInfo.memory_percent || 0"
                  :color="sysInfo.memory_percent > 85 ? 'error' : sysInfo.memory_percent > 60 ? 'warning' : 'success'"
                  height="8"
                  rounded
                />
                <div v-if="sysInfo.swap_total" class="mt-3">
                  <div class="text-body-2">Swap: {{ formatBytes(sysInfo.swap_used) }} / {{ formatBytes(sysInfo.swap_total) }} ({{ sysInfo.swap_percent }}%)</div>
                  <v-progress-linear
                    :model-value="sysInfo.swap_percent || 0"
                    color="info"
                    height="4"
                    rounded
                    class="mt-1"
                  />
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Network -->
          <v-col cols="12" md="6">
            <v-card>
              <v-card-title><v-icon class="mr-2">mdi-network</v-icon>Network</v-card-title>
              <v-card-text>
                <v-table v-if="sysInfo.network" density="compact">
                  <tbody>
                    <tr><td class="font-weight-medium">Sent</td><td>{{ formatBytes(sysInfo.network.bytes_sent) }}</td></tr>
                    <tr><td class="font-weight-medium">Received</td><td>{{ formatBytes(sysInfo.network.bytes_recv) }}</td></tr>
                    <tr><td class="font-weight-medium">Packets Sent</td><td>{{ sysInfo.network.packets_sent?.toLocaleString() }}</td></tr>
                    <tr><td class="font-weight-medium">Packets Received</td><td>{{ sysInfo.network.packets_recv?.toLocaleString() }}</td></tr>
                  </tbody>
                </v-table>
                <div v-if="sysInfo.boot_time" class="mt-3 text-body-2">
                  <v-icon size="small" class="mr-1">mdi-clock-outline</v-icon>
                  Boot: {{ new Date(sysInfo.boot_time).toLocaleString() }}
                  <span class="text-medium-emphasis">({{ formatUptime(sysInfo.uptime_seconds) }})</span>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Disks -->
        <v-card v-if="sysInfo.disks?.length" class="mb-4">
          <v-card-title><v-icon class="mr-2">mdi-harddisk</v-icon>Disks</v-card-title>
          <v-card-text>
            <v-row>
              <v-col v-for="disk in sysInfo.disks" :key="disk.mountpoint" cols="12" md="4">
                <div class="text-body-2 font-weight-medium mb-1">{{ disk.mountpoint }}</div>
                <div class="text-caption text-medium-emphasis mb-1">{{ disk.device }} ({{ disk.fstype }})</div>
                <v-progress-linear
                  :model-value="disk.percent"
                  :color="disk.percent > 90 ? 'error' : disk.percent > 75 ? 'warning' : 'success'"
                  height="6"
                  rounded
                />
                <div class="text-caption mt-1">
                  {{ formatBytes(disk.used) }} / {{ formatBytes(disk.total) }}
                  ({{ formatBytes(disk.free) }} free)
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <div class="text-right">
          <v-btn variant="outlined" prepend-icon="mdi-refresh" :loading="loadingInfo" @click="loadSystemInfo">
            Refresh
          </v-btn>
        </div>
      </template>

      <!-- Processes Tab -->
      <template v-if="activeTab === 'processes'">
        <v-card class="mb-4">
          <v-card-text class="pa-3 d-flex align-center ga-2">
            <v-text-field
              v-model="processFilter"
              density="compact"
              variant="outlined"
              hide-details
              placeholder="Filter by name or command..."
              prepend-inner-icon="mdi-magnify"
              style="max-width: 350px"
              clearable
              @update:model-value="loadProcesses"
            />
            <v-spacer />
            <v-btn
              variant="outlined"
              prepend-icon="mdi-refresh"
              size="small"
              :loading="loadingProcs"
              @click="loadProcesses"
            >
              Refresh
            </v-btn>
            <v-switch
              v-model="autoRefresh"
              label="Auto-refresh"
              density="compact"
              hide-details
              color="primary"
              class="ml-2"
            />
          </v-card-text>
        </v-card>

        <v-card>
          <v-data-table
            :headers="procHeaders"
            :items="processes"
            :loading="loadingProcs"
            density="compact"
            items-per-page="50"
            hover
          >
            <template #item.pid="{ item }">
              <code>{{ item.pid }}</code>
            </template>

            <template #item.cpu_percent="{ item }">
              <v-chip
                :color="item.cpu_percent > 50 ? 'error' : item.cpu_percent > 20 ? 'warning' : 'default'"
                size="x-small"
                variant="flat"
              >
                {{ item.cpu_percent }}%
              </v-chip>
            </template>

            <template #item.memory_percent="{ item }">
              <v-chip
                :color="item.memory_percent > 10 ? 'error' : item.memory_percent > 5 ? 'warning' : 'default'"
                size="x-small"
                variant="flat"
              >
                {{ item.memory_percent }}%
              </v-chip>
            </template>

            <template #item.command="{ item }">
              <span class="text-caption" style="max-width: 350px; display: inline-block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                {{ item.command }}
              </span>
            </template>

            <template #item.actions="{ item }">
              <v-btn
                icon="mdi-information"
                size="x-small"
                variant="text"
                @click="showProcessDetail(item)"
              />
              <v-btn
                icon="mdi-stop"
                size="x-small"
                variant="text"
                color="warning"
                @click="killProcess(item.pid, 15)"
                title="SIGTERM"
              />
              <v-btn
                icon="mdi-close-circle"
                size="x-small"
                variant="text"
                color="error"
                @click="killProcess(item.pid, 9)"
                title="SIGKILL"
              />
            </template>
          </v-data-table>
        </v-card>
      </template>
    </template>

    <!-- Process detail dialog -->
    <v-dialog v-model="detailDialog" max-width="700" scrollable>
      <v-card v-if="procDetail">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-application</v-icon>
          {{ procDetail.name }} (PID {{ procDetail.pid }})
          <v-spacer />
          <v-btn icon="mdi-close" size="small" variant="text" @click="detailDialog = false" />
        </v-card-title>
        <v-divider />
        <v-card-text>
          <v-table density="compact">
            <tbody>
              <tr><td class="font-weight-medium">PID</td><td>{{ procDetail.pid }}</td></tr>
              <tr><td class="font-weight-medium">Parent PID</td><td>{{ procDetail.ppid }}</td></tr>
              <tr><td class="font-weight-medium">User</td><td>{{ procDetail.username }}</td></tr>
              <tr><td class="font-weight-medium">Status</td><td>{{ procDetail.status }}</td></tr>
              <tr><td class="font-weight-medium">CPU %</td><td>{{ procDetail.cpu_percent }}%</td></tr>
              <tr><td class="font-weight-medium">Memory (RSS)</td><td>{{ formatBytes(procDetail.memory_rss) }}</td></tr>
              <tr><td class="font-weight-medium">Memory (VMS)</td><td>{{ formatBytes(procDetail.memory_vms) }}</td></tr>
              <tr><td class="font-weight-medium">Threads</td><td>{{ procDetail.num_threads }}</td></tr>
              <tr><td class="font-weight-medium">Nice</td><td>{{ procDetail.nice }}</td></tr>
              <tr><td class="font-weight-medium">CWD</td><td class="text-caption">{{ procDetail.cwd }}</td></tr>
              <tr><td class="font-weight-medium">Created</td><td>{{ procDetail.created ? new Date(procDetail.created).toLocaleString() : '—' }}</td></tr>
              <tr><td class="font-weight-medium">Command</td><td class="text-caption" style="word-break: break-all">{{ procDetail.command }}</td></tr>
            </tbody>
          </v-table>

          <div v-if="procDetail.connections?.length" class="mt-4">
            <div class="text-subtitle-2 mb-2">Connections ({{ procDetail.connections.length }})</div>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Local</th><th>Remote</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(c, i) in procDetail.connections" :key="i">
                  <td class="text-caption">{{ c.local }}</td>
                  <td class="text-caption">{{ c.remote || '—' }}</td>
                  <td>{{ c.status }}</td>
                </tr>
              </tbody>
            </v-table>
          </div>

          <div v-if="procDetail.open_files?.length" class="mt-4">
            <div class="text-subtitle-2 mb-2">Open Files ({{ procDetail.open_files.length }})</div>
            <div v-for="f in procDetail.open_files.slice(0, 30)" :key="f" class="text-caption">{{ f }}</div>
            <div v-if="procDetail.open_files.length > 30" class="text-caption text-medium-emphasis">
              ... and {{ procDetail.open_files.length - 30 }} more
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn color="warning" variant="tonal" prepend-icon="mdi-stop" @click="killProcess(procDetail.pid, 15); detailDialog = false">
            SIGTERM
          </v-btn>
          <v-btn color="error" variant="tonal" prepend-icon="mdi-close-circle" @click="killProcess(procDetail.pid, 9); detailDialog = false">
            SIGKILL
          </v-btn>
          <v-spacer />
          <v-btn @click="detailDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, inject } from 'vue'
import api from '../api'
import { useSettingsStore } from '../stores/settings'

const showSnackbar = inject('showSnackbar')
const settingsStore = useSettingsStore()

const enabled = ref(false)
const activeTab = ref('info')

// System info
const sysInfo = ref({})
const loadingInfo = ref(false)

// Processes
const processes = ref([])
const loadingProcs = ref(false)
const processFilter = ref('')
const autoRefresh = ref(false)
let refreshInterval = null

// Detail
const detailDialog = ref(false)
const procDetail = ref(null)

const procHeaders = [
  { title: 'PID', key: 'pid', width: '80px' },
  { title: 'Name', key: 'name', sortable: true },
  { title: 'User', key: 'username', sortable: true, width: '100px' },
  { title: 'CPU %', key: 'cpu_percent', sortable: true, width: '90px' },
  { title: 'Mem %', key: 'memory_percent', sortable: true, width: '90px' },
  { title: 'Status', key: 'status', width: '80px' },
  { title: 'Command', key: 'command' },
  { title: 'Actions', key: 'actions', sortable: false, width: '120px', align: 'end' },
]

const platformInfo = computed(() => {
  if (!sysInfo.value.platform) return {}
  return {
    'System': sysInfo.value.platform,
    'Release': sysInfo.value.platform_release,
    'Architecture': sysInfo.value.architecture,
    'Hostname': sysInfo.value.hostname,
    'Processor': sysInfo.value.processor || '—',
    'Python': sysInfo.value.python_version,
  }
})

onMounted(async () => {
  await settingsStore.fetchSystemSettings()
  enabled.value = settingsStore.systemSettings.system_access_enabled?.value === 'true'
  if (enabled.value) {
    loadSystemInfo()
    loadProcesses()
  }
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

watch(autoRefresh, (on) => {
  if (on) {
    refreshInterval = setInterval(loadProcesses, 3000)
  } else {
    if (refreshInterval) clearInterval(refreshInterval)
    refreshInterval = null
  }
})

async function loadSystemInfo() {
  loadingInfo.value = true
  try {
    const { data } = await api.get('/processes/system-info')
    sysInfo.value = data
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error loading system info', 'error')
  } finally {
    loadingInfo.value = false
  }
}

async function loadProcesses() {
  loadingProcs.value = true
  try {
    const params = { sort_by: 'cpu_percent', sort_desc: true, limit: 200 }
    if (processFilter.value) params.filter_name = processFilter.value
    const { data } = await api.get('/processes/list', { params })
    processes.value = data.processes
  } catch (e) {
    if (!autoRefresh.value) {
      showSnackbar(e.response?.data?.detail || 'Error loading processes', 'error')
    }
  } finally {
    loadingProcs.value = false
  }
}

async function killProcess(pid, signal) {
  try {
    const { data } = await api.post('/processes/kill', { pid, signal })
    showSnackbar(data.message)
    setTimeout(loadProcesses, 500)
  } catch (e) {
    showSnackbar(e.response?.data?.detail || `Error killing PID ${pid}`, 'error')
  }
}

async function showProcessDetail(proc) {
  try {
    const { data } = await api.get(`/processes/${proc.pid}`)
    procDetail.value = data
    detailDialog.value = true
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error loading process details', 'error')
  }
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

function formatUptime(seconds) {
  if (!seconds) return ''
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const parts = []
  if (d) parts.push(`${d}d`)
  if (h) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return parts.join(' ')
}
</script>
