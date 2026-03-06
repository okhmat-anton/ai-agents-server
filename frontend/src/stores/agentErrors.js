import { defineStore } from 'pinia'
import api from '../api'

export const useAgentErrorsStore = defineStore('agentErrors', {
  state: () => ({
    errors: [],
    stats: null,
    loading: false,
  }),

  actions: {
    async fetchErrors(params = {}) {
      this.loading = true
      try {
        const { data } = await api.get('/agent-errors', { params })
        this.errors = data
      } finally {
        this.loading = false
      }
    },

    async fetchAgentErrors(agentId, params = {}) {
      this.loading = true
      try {
        const { data } = await api.get(`/agents/${agentId}/errors`, { params })
        this.errors = data
      } finally {
        this.loading = false
      }
    },

    async fetchStats() {
      const { data } = await api.get('/agent-errors/stats')
      this.stats = data
      return data
    },

    async resolveError(agentId, errorId, resolution = '') {
      const { data } = await api.patch(`/agents/${agentId}/errors/${errorId}/resolve`, { resolution })
      const idx = this.errors.findIndex(e => e.id === errorId)
      if (idx !== -1) this.errors[idx] = data
      return data
    },

    async clearAgentErrors(agentId) {
      await api.delete(`/agents/${agentId}/errors`)
      this.errors = this.errors.filter(e => e.agent_id !== agentId)
    },
  },
})
