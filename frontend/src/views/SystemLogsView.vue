<template>
  <div>
    <div class="text-h4 font-weight-bold mb-6">System Logs</div>

    <v-card>
      <v-card-text class="pb-0">
        <v-row>
          <v-col cols="auto">
            <v-select v-model="level" :items="['all','debug','info','warning','error','critical']" label="Level" density="compact" style="min-width: 140px" />
          </v-col>
          <v-col cols="auto">
            <v-select v-model="source" :items="['all','system','auth','api','scheduler','engine']" label="Source" density="compact" style="min-width: 140px" />
          </v-col>
          <v-col>
            <v-text-field v-model="search" label="Search" density="compact" prepend-inner-icon="mdi-magnify" clearable />
          </v-col>
          <v-col cols="auto">
            <v-btn icon="mdi-refresh" @click="loadLogs" />
          </v-col>
        </v-row>
      </v-card-text>

      <v-card-text>
        <v-list density="compact" class="log-list" style="max-height: 600px; overflow-y: auto; font-family: monospace; font-size: 13px;">
          <v-list-item v-for="log in logs" :key="log.id" class="py-0 px-2">
            <div class="d-flex align-center" style="min-height: 28px;">
              <v-chip :color="logColor(log.level)" size="x-small" variant="flat" style="min-width: 56px; justify-content: center;" class="mr-2">
                {{ log.level }}
              </v-chip>
              <v-chip size="x-small" variant="outlined" class="mr-2" style="min-width: 64px; justify-content: center;">
                {{ log.source }}
              </v-chip>
              <span class="text-caption text-grey mr-3">{{ new Date(log.created_at).toLocaleTimeString() }}</span>
              <span class="text-body-2">{{ log.message }}</span>
            </div>
          </v-list-item>
          <v-list-item v-if="!logs.length">
            <div class="text-center text-grey pa-6 w-100">No logs found</div>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import api from '../api'

const logs = ref([])
const level = ref('all')
const source = ref('all')
const search = ref('')

const logColor = (l) => ({ debug: 'grey', info: 'info', warning: 'warning', error: 'error', critical: 'error' }[l] || 'grey')

const loadLogs = async () => {
  const params = { limit: 200 }
  if (level.value !== 'all') params.level = level.value
  if (source.value !== 'all') params.source = source.value
  if (search.value) params.search = search.value
  const { data } = await api.get('/system/logs', { params })
  logs.value = data
}

watch([level, source, search], loadLogs)
onMounted(loadLogs)
</script>
