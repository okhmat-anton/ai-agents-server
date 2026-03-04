<template>
  <div>
    <div class="text-h4 font-weight-bold mb-6">Dashboard</div>

    <!-- Stats Cards -->
    <v-row>
      <v-col v-for="stat in statsCards" :key="stat.title" cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="d-flex align-center">
            <v-avatar :color="stat.color" size="48" class="mr-4">
              <v-icon color="white">{{ stat.icon }}</v-icon>
            </v-avatar>
            <div>
              <div class="text-h5 font-weight-bold">{{ stat.value }}</div>
              <div class="text-body-2 text-grey">{{ stat.title }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- System Health -->
    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-heart-pulse</v-icon>
            System Health
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="(val, key) in health" :key="key">
                <template #prepend>
                  <v-icon :color="val === 'ok' ? 'success' : val === 'error' ? 'error' : 'warning'" size="small">
                    {{ val === 'ok' ? 'mdi-check-circle' : val === 'error' ? 'mdi-close-circle' : 'mdi-alert-circle' }}
                  </v-icon>
                </template>
                <v-list-item-title>{{ key }}</v-list-item-title>
                <template #append>
                  <v-chip :color="val === 'ok' ? 'success' : 'warning'" size="small" variant="tonal">{{ val }}</v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-robot</v-icon>
            Active Agents
          </v-card-title>
          <v-card-text>
            <v-list v-if="agents.length" density="compact">
              <v-list-item v-for="agent in agents" :key="agent.id" :to="`/agents/${agent.id}/detail`">
                <v-list-item-title>{{ agent.name }}</v-list-item-title>
                <template #append>
                  <v-chip :color="statusColor(agent.status)" size="small" variant="tonal">{{ agent.status }}</v-chip>
                </template>
              </v-list-item>
            </v-list>
            <div v-else class="text-center text-grey pa-4">No agents yet</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const stats = ref({})
const health = ref({})
const agents = ref([])

const statsCards = computed(() => [
  { title: 'Agents', value: stats.value.total_agents || 0, icon: 'mdi-robot', color: 'primary' },
  { title: 'Running', value: stats.value.running_agents || 0, icon: 'mdi-play-circle', color: 'success' },
  { title: 'Tasks', value: stats.value.total_tasks || 0, icon: 'mdi-clipboard-list', color: 'secondary' },
  { title: 'Skills', value: stats.value.total_skills || 0, icon: 'mdi-puzzle', color: 'accent' },
])

const statusColor = (s) => ({ idle: 'grey', running: 'success', paused: 'warning', error: 'error', stopped: 'grey' }[s] || 'grey')

onMounted(async () => {
  try {
    const [sRes, hRes, aRes] = await Promise.all([
      api.get('/system/stats'),
      api.get('/system/health'),
      api.get('/agents', { params: { limit: 10 } }),
    ])
    stats.value = sRes.data
    const { status, uptime_seconds, ...healthData } = hRes.data
    health.value = healthData
    agents.value = aRes.data
  } catch { /* ignore on first load */ }
})
</script>
