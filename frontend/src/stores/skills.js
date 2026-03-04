import { defineStore } from 'pinia'
import api from '../api'

export const useSkillsStore = defineStore('skills', {
  state: () => ({
    skills: [],
    loading: false,
  }),

  actions: {
    async fetchSkills(params = {}) {
      this.loading = true
      try {
        const { data } = await api.get('/skills', { params })
        this.skills = data
      } finally {
        this.loading = false
      }
    },

    async fetchSkill(id) {
      const { data } = await api.get(`/skills/${id}`)
      return data
    },

    async createSkill(payload) {
      const { data } = await api.post('/skills', payload)
      this.skills.unshift(data)
      return data
    },

    async updateSkill(id, payload) {
      const { data } = await api.put(`/skills/${id}`, payload)
      const idx = this.skills.findIndex((s) => s.id === id)
      if (idx >= 0) this.skills[idx] = data
      return data
    },

    async deleteSkill(id) {
      await api.delete(`/skills/${id}?force=true`)
      this.skills = this.skills.filter((s) => s.id !== id)
    },

    async shareSkill(id) {
      const { data } = await api.post(`/skills/${id}/share`)
      const idx = this.skills.findIndex((s) => s.id === id)
      if (idx >= 0) this.skills[idx] = data
      return data
    },

    async unshareSkill(id) {
      const { data } = await api.post(`/skills/${id}/unshare`)
      const idx = this.skills.findIndex((s) => s.id === id)
      if (idx >= 0) this.skills[idx] = data
      return data
    },

    async duplicateSkill(id) {
      const { data } = await api.post(`/skills/${id}/duplicate`)
      this.skills.unshift(data)
      return data
    },
  },
})
