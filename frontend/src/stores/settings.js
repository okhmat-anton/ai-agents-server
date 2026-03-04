import { defineStore } from 'pinia'
import api from '../api'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    models: [],
    apiKeys: [],
    loading: false,
  }),

  actions: {
    async fetchModels() {
      const { data } = await api.get('/settings/models')
      this.models = data
    },

    async createModel(payload) {
      const { data } = await api.post('/settings/models', payload)
      this.models.unshift(data)
      return data
    },

    async updateModel(id, payload) {
      const { data } = await api.put(`/settings/models/${id}`, payload)
      const idx = this.models.findIndex((m) => m.id === id)
      if (idx >= 0) this.models[idx] = data
      return data
    },

    async deleteModel(id) {
      await api.delete(`/settings/models/${id}`)
      this.models = this.models.filter((m) => m.id !== id)
    },

    async testModel(id) {
      const { data } = await api.post(`/settings/models/${id}/test`)
      return data
    },

    async listAvailableModels(id) {
      const { data } = await api.get(`/settings/models/${id}/available`)
      return data.models
    },

    async fetchApiKeys() {
      const { data } = await api.get('/settings/api-keys')
      this.apiKeys = data
    },

    async createApiKey(payload) {
      const { data } = await api.post('/settings/api-keys', payload)
      return data
    },

    async deleteApiKey(id) {
      await api.delete(`/settings/api-keys/${id}`)
      this.apiKeys = this.apiKeys.filter((k) => k.id !== id)
    },

    async changePassword(oldPassword, newPassword) {
      await api.put('/settings/password', { old_password: oldPassword, new_password: newPassword })
    },
  },
})
