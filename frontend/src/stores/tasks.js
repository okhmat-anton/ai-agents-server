import { defineStore } from 'pinia'
import api from '../api'

export const useTasksStore = defineStore('tasks', {
  state: () => ({
    tasks: [],
    loading: false,
  }),

  actions: {
    async fetchTasks(params = {}) {
      this.loading = true
      try {
        const { data } = await api.get('/tasks', { params })
        this.tasks = data
      } finally {
        this.loading = false
      }
    },

    async fetchAgentTasks(agentId, params = {}) {
      this.loading = true
      try {
        const { data } = await api.get(`/agents/${agentId}/tasks`, { params })
        this.tasks = data
      } finally {
        this.loading = false
      }
    },

    async createTask(payload, agentId = null) {
      const url = agentId ? `/agents/${agentId}/tasks` : '/tasks'
      const { data } = await api.post(url, payload)
      return data
    },

    async updateTask(id, payload) {
      const { data } = await api.put(`/tasks/${id}`, payload)
      return data
    },

    async deleteTask(id) {
      await api.delete(`/tasks/${id}`)
      this.tasks = this.tasks.filter((t) => t.id !== id)
    },

    async runTask(id) {
      const { data } = await api.post(`/tasks/${id}/run`)
      return data
    },

    async cancelTask(id) {
      const { data } = await api.post(`/tasks/${id}/cancel`)
      return data
    },
  },
})
