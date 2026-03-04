import { defineStore } from 'pinia'
import api from '../api'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    currentSession: null,
    messages: [],
    availableModels: [],
    loading: false,
    sending: false,
    panelOpen: localStorage.getItem('chat_panel_open') === 'true',
    showSessionList: false,
  }),

  getters: {
    sortedSessions: (state) => {
      return [...state.sessions].sort((a, b) =>
        new Date(b.updated_at) - new Date(a.updated_at)
      )
    },
    currentModels: (state) => {
      if (!state.currentSession) return []
      return state.currentSession.model_ids || []
    },
    isMultiModel: (state) => {
      return state.currentSession?.multi_model || false
    },
  },

  actions: {
    togglePanel() {
      this.panelOpen = !this.panelOpen
      localStorage.setItem('chat_panel_open', this.panelOpen)
    },
    openPanel() {
      this.panelOpen = true
      localStorage.setItem('chat_panel_open', 'true')
    },
    closePanel() {
      this.panelOpen = false
      localStorage.setItem('chat_panel_open', 'false')
    },

    async fetchAvailableModels() {
      try {
        const { data } = await api.get('/chat/available-models')
        this.availableModels = data
      } catch (e) {
        console.error('Failed to fetch available models:', e)
      }
    },

    async fetchSessions() {
      this.loading = true
      try {
        const { data } = await api.get('/chat/sessions')
        this.sessions = data
      } catch (e) {
        console.error('Failed to fetch sessions:', e)
      } finally {
        this.loading = false
      }
    },

    async createSession(params = {}) {
      try {
        const { data } = await api.post('/chat/sessions', {
          title: params.title || 'New Chat',
          model_ids: params.model_ids || [],
          agent_id: params.agent_id || null,
          multi_model: params.multi_model || false,
          system_prompt: params.system_prompt || null,
          temperature: params.temperature ?? 0.7,
        })
        this.sessions.unshift(data)
        this.currentSession = data
        this.messages = []
        return data
      } catch (e) {
        console.error('Failed to create session:', e)
        throw e
      }
    },

    async loadSession(sessionId) {
      this.loading = true
      try {
        const { data } = await api.get(`/chat/sessions/${sessionId}`)
        this.currentSession = data
        this.messages = data.messages || []
        this.showSessionList = false
      } catch (e) {
        console.error('Failed to load session:', e)
      } finally {
        this.loading = false
      }
    },

    async updateSession(sessionId, params) {
      try {
        const { data } = await api.put(`/chat/sessions/${sessionId}`, params)
        const idx = this.sessions.findIndex(s => s.id === sessionId)
        if (idx >= 0) this.sessions[idx] = data
        if (this.currentSession?.id === sessionId) {
          this.currentSession = { ...this.currentSession, ...data }
        }
        return data
      } catch (e) {
        console.error('Failed to update session:', e)
        throw e
      }
    },

    async deleteSession(sessionId) {
      try {
        await api.delete(`/chat/sessions/${sessionId}`)
        this.sessions = this.sessions.filter(s => s.id !== sessionId)
        if (this.currentSession?.id === sessionId) {
          this.currentSession = null
          this.messages = []
        }
      } catch (e) {
        console.error('Failed to delete session:', e)
        throw e
      }
    },

    async sendMessage(content, modelIds = null) {
      if (!this.currentSession) return
      this.sending = true

      // Optimistic: add user message
      const userMsg = {
        id: 'temp-' + Date.now(),
        role: 'user',
        content,
        model_name: null,
        model_responses: null,
        total_tokens: 0,
        duration_ms: 0,
        created_at: new Date().toISOString(),
      }
      this.messages.push(userMsg)

      try {
        const { data } = await api.post(
          `/chat/sessions/${this.currentSession.id}/messages`,
          { content, model_ids: modelIds },
          { timeout: 120000 }
        )
        this.messages.push(data)

        // Update session in list
        const idx = this.sessions.findIndex(s => s.id === this.currentSession.id)
        if (idx >= 0) {
          this.sessions[idx].last_message = data.content?.substring(0, 100)
          this.sessions[idx].message_count = this.messages.length
          this.sessions[idx].updated_at = new Date().toISOString()
        }

        return data
      } catch (e) {
        // Add error message
        this.messages.push({
          id: 'error-' + Date.now(),
          role: 'assistant',
          content: `**Error:** ${e.response?.data?.detail || e.message}`,
          model_name: 'system',
          total_tokens: 0,
          duration_ms: 0,
          created_at: new Date().toISOString(),
        })
        throw e
      } finally {
        this.sending = false
      }
    },

    async autoTitle(sessionId) {
      try {
        const { data } = await api.post(`/chat/sessions/${sessionId}/auto-title`)
        const idx = this.sessions.findIndex(s => s.id === sessionId)
        if (idx >= 0) this.sessions[idx].title = data.title
        if (this.currentSession?.id === sessionId) {
          this.currentSession.title = data.title
        }
      } catch (e) {
        console.error('Failed to auto-title:', e)
      }
    },

    newChat() {
      this.currentSession = null
      this.messages = []
      this.showSessionList = false
    },
  },
})
