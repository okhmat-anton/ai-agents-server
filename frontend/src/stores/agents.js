import { defineStore } from 'pinia'
import api from '../api'

export const useAgentsStore = defineStore('agents', {
  state: () => ({
    agents: [],
    currentAgent: null,
    loading: false,
  }),

  actions: {
    async fetchAgents(params = {}) {
      this.loading = true
      try {
        const { data } = await api.get('/agents', { params })
        this.agents = data
      } finally {
        this.loading = false
      }
    },

    async fetchAgent(id) {
      const { data } = await api.get(`/agents/${id}`)
      this.currentAgent = data
      return data
    },

    async createAgent(payload) {
      const { data } = await api.post('/agents', payload)
      return data
    },

    async updateAgent(id, payload) {
      const { data } = await api.put(`/agents/${id}`, payload)
      return data
    },

    async deleteAgent(id) {
      await api.delete(`/agents/${id}`)
      this.agents = this.agents.filter((a) => a.id !== id)
    },

    async startAgent(id) {
      const { data } = await api.post(`/agents/${id}/start`)
      this._updateLocal(data)
      return data
    },

    async stopAgent(id) {
      const { data } = await api.post(`/agents/${id}/stop`)
      this._updateLocal(data)
      return data
    },

    async duplicateAgent(id) {
      const { data } = await api.post(`/agents/${id}/duplicate`)
      this.agents.unshift(data)
      return data
    },

    async fetchStats(id) {
      const { data } = await api.get(`/agents/${id}/stats`)
      return data
    },

    _updateLocal(agent) {
      const idx = this.agents.findIndex((a) => a.id === agent.id)
      if (idx >= 0) this.agents[idx] = agent
    },
  },
})
