<template>
  <v-navigation-drawer
    v-model="chatStore.panelOpen"
    location="right"
    :width="420"
    temporary
    class="chat-panel"
  >
    <!-- Header -->
    <div class="chat-header pa-3 d-flex align-center">
      <v-btn
        v-if="chatStore.currentSession || chatStore.showSessionList"
        icon
        size="small"
        variant="text"
        @click="goBack"
        class="mr-1"
      >
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <v-icon class="mr-2" color="primary">mdi-chat</v-icon>
      <span class="text-subtitle-1 font-weight-medium flex-grow-1">
        {{ headerTitle }}
      </span>
      <v-btn icon size="small" variant="text" @click="chatStore.showSessionList = !chatStore.showSessionList">
        <v-icon>mdi-history</v-icon>
        <v-tooltip activator="parent" location="bottom">Chat History</v-tooltip>
      </v-btn>
      <v-btn icon size="small" variant="text" @click="newChat" class="ml-1">
        <v-icon>mdi-plus</v-icon>
        <v-tooltip activator="parent" location="bottom">New Chat</v-tooltip>
      </v-btn>
      <v-btn icon size="small" variant="text" @click="chatStore.closePanel()" class="ml-1">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </div>
    <v-divider />

    <!-- Session List View -->
    <div v-if="chatStore.showSessionList" class="session-list">
      <div class="pa-3">
        <v-text-field
          v-model="sessionSearch"
          placeholder="Search chats..."
          density="compact"
          variant="outlined"
          prepend-inner-icon="mdi-magnify"
          hide-details
          clearable
        />
      </div>
      <v-list density="compact" class="session-list-items">
        <v-list-item
          v-for="session in filteredSessions"
          :key="session.id"
          :active="chatStore.currentSession?.id === session.id"
          @click="loadSession(session.id)"
          class="session-item"
          rounded="lg"
        >
          <template #prepend>
            <v-icon size="small" :color="session.multi_model ? 'warning' : 'primary'">
              {{ session.multi_model ? 'mdi-brain' : 'mdi-chat-outline' }}
            </v-icon>
          </template>
          <v-list-item-title class="text-body-2">
            {{ session.title }}
          </v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ formatDate(session.updated_at) }} · {{ session.message_count }} msgs
          </v-list-item-subtitle>
          <template #append>
            <v-btn icon size="x-small" variant="text" @click.stop="deleteSession(session.id)">
              <v-icon size="small">mdi-delete-outline</v-icon>
            </v-btn>
          </template>
        </v-list-item>
        <v-list-item v-if="filteredSessions.length === 0" class="text-center">
          <v-list-item-title class="text-body-2 text-medium-emphasis">
            No chats found
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <!-- Setup View (no active session) -->
    <div v-else-if="!chatStore.currentSession" class="setup-view pa-4">
      <div class="text-center mb-6">
        <v-icon size="64" color="primary" class="mb-3">mdi-chat-processing</v-icon>
        <h3 class="text-h6 mb-1">Start a Conversation</h3>
        <p class="text-body-2 text-medium-emphasis">
          Select models or an agent, then send your first message.
        </p>
      </div>

      <!-- Mode Toggle -->
      <v-btn-toggle v-model="setupMode" mandatory variant="outlined" density="compact" class="mb-4 d-flex">
        <v-btn value="single" class="flex-grow-1">
          <v-icon start size="small">mdi-chat</v-icon>
          Single Model
        </v-btn>
        <v-btn value="multi" class="flex-grow-1">
          <v-icon start size="small">mdi-brain</v-icon>
          Multi-Model
        </v-btn>
      </v-btn-toggle>

      <!-- Model Selection -->
      <v-autocomplete
        v-model="selectedModels"
        :items="modelItems"
        item-title="name"
        item-value="id"
        :label="setupMode === 'multi' ? 'Select Models (2+)' : 'Select Model'"
        :multiple="setupMode === 'multi'"
        :chips="setupMode === 'multi'"
        closable-chips
        density="compact"
        variant="outlined"
        hide-details
        class="mb-4"
      >
        <template #item="{ props: itemProps, item }">
          <v-list-item v-bind="itemProps">
            <template #prepend>
              <v-icon size="small" :color="item.raw.type === 'agent' ? 'success' : 'primary'">
                {{ item.raw.type === 'agent' ? 'mdi-robot' : 'mdi-cube-outline' }}
              </v-icon>
            </template>
            <template #subtitle>
              <span class="text-caption">{{ item.raw.provider }}</span>
            </template>
          </v-list-item>
        </template>
      </v-autocomplete>

      <!-- System Prompt -->
      <v-textarea
        v-model="systemPrompt"
        label="System Prompt (optional)"
        variant="outlined"
        density="compact"
        rows="2"
        auto-grow
        hide-details
        class="mb-4"
      />

      <!-- Temperature -->
      <div class="d-flex align-center mb-4">
        <span class="text-body-2 mr-3">Temperature</span>
        <v-slider
          v-model="temperature"
          :min="0"
          :max="2"
          :step="0.1"
          thumb-label
          hide-details
          class="flex-grow-1"
        />
        <span class="text-body-2 ml-2" style="min-width:30px">{{ temperature }}</span>
      </div>

      <!-- Quick input at bottom -->
      <v-textarea
        v-model="quickMessage"
        placeholder="Type a message to start..."
        variant="outlined"
        density="compact"
        rows="2"
        auto-grow
        hide-details
        @keydown.enter.exact.prevent="startChat"
        class="mb-3"
      />
      <v-btn
        block
        color="primary"
        :disabled="!canStart"
        :loading="chatStore.sending"
        @click="startChat"
      >
        <v-icon start>mdi-send</v-icon>
        Start Chat
      </v-btn>
    </div>

    <!-- Chat View (active session) -->
    <template v-else>
      <!-- Session Info Bar -->
      <div class="session-info pa-2 d-flex align-center">
        <v-chip
          v-if="chatStore.currentSession.multi_model"
          size="x-small"
          color="warning"
          class="mr-2"
        >
          <v-icon start size="small">mdi-brain</v-icon>
          Multi-Model
        </v-chip>
        <div class="text-caption text-medium-emphasis text-truncate flex-grow-1">
          {{ modelNamesDisplay }}
        </div>
        <v-btn icon size="x-small" variant="text" @click="showSettings = !showSettings">
          <v-icon size="small">mdi-cog</v-icon>
        </v-btn>
      </div>

      <!-- Inline Session Settings -->
      <v-expand-transition>
        <div v-if="showSettings" class="pa-3 bg-surface-variant">
          <v-text-field
            :model-value="chatStore.currentSession.title"
            @update:model-value="updateTitle"
            label="Chat Title"
            density="compact"
            variant="outlined"
            hide-details
            class="mb-3"
          />
          <v-autocomplete
            :model-value="chatStore.currentSession.model_ids"
            @update:model-value="updateModels"
            :items="modelItems"
            item-title="name"
            item-value="id"
            label="Models"
            :multiple="chatStore.currentSession.multi_model"
            :chips="chatStore.currentSession.multi_model"
            closable-chips
            density="compact"
            variant="outlined"
            hide-details
            class="mb-3"
          />
          <v-switch
            :model-value="chatStore.currentSession.multi_model"
            @update:model-value="toggleMultiModel"
            label="Multi-Model Consultation"
            density="compact"
            color="warning"
            hide-details
          />
        </div>
      </v-expand-transition>
      <v-divider />

      <!-- Messages -->
      <div ref="messagesContainer" class="messages-container">
        <div v-if="chatStore.messages.length === 0" class="text-center pa-8">
          <v-icon size="48" color="grey-lighten-1">mdi-chat-outline</v-icon>
          <p class="text-body-2 text-medium-emphasis mt-2">Send a message to start</p>
        </div>

        <div
          v-for="msg in chatStore.messages"
          :key="msg.id"
          class="message-bubble"
          :class="msg.role"
        >
          <div class="message-header d-flex align-center mb-1">
            <v-icon size="x-small" :color="msg.role === 'user' ? 'primary' : 'success'" class="mr-1">
              {{ msg.role === 'user' ? 'mdi-account' : 'mdi-robot' }}
            </v-icon>
            <span class="text-caption font-weight-medium">
              {{ msg.role === 'user' ? 'You' : (msg.model_name || 'Assistant') }}
            </span>
            <v-spacer />
            <span v-if="msg.duration_ms" class="text-caption text-medium-emphasis">
              {{ (msg.duration_ms / 1000).toFixed(1) }}s
            </span>
          </div>

          <div class="message-content text-body-2" v-html="renderMarkdown(msg.content)"></div>

          <!-- Multi-model details -->
          <v-expand-transition>
            <div v-if="msg.model_responses && expandedResponses[msg.id]" class="mt-2">
              <v-divider class="mb-2" />
              <div v-for="(resp, modelName) in msg.model_responses" :key="modelName" class="mb-2">
                <div class="text-caption font-weight-bold text-warning">{{ modelName }}</div>
                <div class="text-caption" v-html="renderMarkdown(resp)"></div>
              </div>
            </div>
          </v-expand-transition>

          <div v-if="msg.model_responses" class="mt-1">
            <v-btn
              size="x-small"
              variant="text"
              @click="expandedResponses[msg.id] = !expandedResponses[msg.id]"
            >
              <v-icon size="small" start>
                {{ expandedResponses[msg.id] ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
              </v-icon>
              {{ expandedResponses[msg.id] ? 'Hide' : 'Show' }} individual responses
            </v-btn>
          </div>

          <div v-if="msg.total_tokens" class="text-caption text-medium-emphasis mt-1">
            {{ msg.total_tokens }} tokens
          </div>
        </div>

        <!-- Typing indicator -->
        <div v-if="chatStore.sending" class="message-bubble assistant">
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area pa-3">
        <v-divider class="mb-3" />
        <div class="d-flex align-end">
          <v-textarea
            v-model="messageInput"
            placeholder="Type a message..."
            variant="outlined"
            density="compact"
            rows="1"
            max-rows="6"
            auto-grow
            hide-details
            class="flex-grow-1 mr-2"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <v-btn
            icon
            color="primary"
            :disabled="!messageInput?.trim() || chatStore.sending"
            :loading="chatStore.sending"
            @click="sendMessage"
          >
            <v-icon>mdi-send</v-icon>
          </v-btn>
        </div>
      </div>
    </template>
  </v-navigation-drawer>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, reactive } from 'vue'
import { useChatStore } from '../stores/chat'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const chatStore = useChatStore()

// Setup state
const setupMode = ref('single')
const selectedModels = ref([])
const systemPrompt = ref('')
const temperature = ref(0.7)
const quickMessage = ref('')

// Chat state
const messageInput = ref('')
const messagesContainer = ref(null)
const showSettings = ref(false)
const sessionSearch = ref('')
const expandedResponses = reactive({})

// Debounce timer for updates
let titleTimeout = null
let modelTimeout = null

const headerTitle = computed(() => {
  if (chatStore.showSessionList) return 'Chat History'
  if (chatStore.currentSession) return chatStore.currentSession.title
  return 'AI Chat'
})

const modelItems = computed(() => {
  return chatStore.availableModels || []
})

const modelNamesDisplay = computed(() => {
  if (!chatStore.currentSession) return ''
  const ids = chatStore.currentSession.model_ids || []
  return ids.map(id => {
    const m = chatStore.availableModels.find(am => am.id === id)
    return m ? m.name : id
  }).join(', ')
})

const filteredSessions = computed(() => {
  const q = (sessionSearch.value || '').toLowerCase()
  if (!q) return chatStore.sortedSessions
  return chatStore.sortedSessions.filter(s =>
    s.title.toLowerCase().includes(q) ||
    (s.last_message || '').toLowerCase().includes(q)
  )
})

const canStart = computed(() => {
  const hasModel = setupMode.value === 'multi'
    ? selectedModels.value.length >= 2
    : selectedModels.value.length > 0 || (typeof selectedModels.value === 'string' && selectedModels.value)
  return hasModel && quickMessage.value?.trim()
})

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

function renderMarkdown(content) {
  if (!content) return ''
  try {
    return DOMPurify.sanitize(marked.parse(content))
  } catch {
    return content
  }
}

function formatDate(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return 'just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
  return date.toLocaleDateString()
}

function goBack() {
  if (chatStore.showSessionList) {
    chatStore.showSessionList = false
  } else {
    chatStore.newChat()
  }
}

function newChat() {
  chatStore.newChat()
  selectedModels.value = []
  systemPrompt.value = ''
  temperature.value = 0.7
  quickMessage.value = ''
  setupMode.value = 'single'
}

async function startChat() {
  if (!canStart.value) return

  const models = setupMode.value === 'multi'
    ? selectedModels.value
    : (Array.isArray(selectedModels.value) ? selectedModels.value : [selectedModels.value])

  await chatStore.createSession({
    model_ids: models,
    multi_model: setupMode.value === 'multi',
    system_prompt: systemPrompt.value || null,
    temperature: temperature.value,
  })

  const msg = quickMessage.value
  quickMessage.value = ''
  await chatStore.sendMessage(msg)
  scrollToBottom()
}

async function sendMessage() {
  const msg = messageInput.value?.trim()
  if (!msg || chatStore.sending) return
  messageInput.value = ''
  await chatStore.sendMessage(msg)
  scrollToBottom()
}

async function loadSession(sessionId) {
  await chatStore.loadSession(sessionId)
  await nextTick()
  scrollToBottom()
}

async function deleteSession(sessionId) {
  await chatStore.deleteSession(sessionId)
}

function updateTitle(val) {
  clearTimeout(titleTimeout)
  titleTimeout = setTimeout(() => {
    chatStore.updateSession(chatStore.currentSession.id, { title: val })
  }, 600)
}

function updateModels(val) {
  clearTimeout(modelTimeout)
  modelTimeout = setTimeout(() => {
    chatStore.updateSession(chatStore.currentSession.id, { model_ids: Array.isArray(val) ? val : [val] })
  }, 300)
}

function toggleMultiModel(val) {
  chatStore.updateSession(chatStore.currentSession.id, { multi_model: val })
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Auto-scroll on new messages
watch(() => chatStore.messages.length, () => {
  scrollToBottom()
})

// Fetch data on mount
onMounted(async () => {
  await chatStore.fetchAvailableModels()
  await chatStore.fetchSessions()
})

// Refetch models when panel opens
watch(() => chatStore.panelOpen, (open) => {
  if (open) {
    chatStore.fetchAvailableModels()
  }
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
}

.chat-header {
  background: rgb(var(--v-theme-surface));
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  min-height: 48px;
}

.session-list {
  overflow-y: auto;
  flex: 1;
}

.session-list-items {
  max-height: calc(100vh - 140px);
  overflow-y: auto;
}

.session-item {
  margin: 0 8px;
}

.setup-view {
  overflow-y: auto;
  flex: 1;
}

.session-info {
  background: rgb(var(--v-theme-surface-variant));
  min-height: 36px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  min-height: 0;
}

.message-bubble {
  margin-bottom: 12px;
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 95%;
}

.message-bubble.user {
  background: rgba(var(--v-theme-primary), 0.08);
  margin-left: auto;
  border-bottom-right-radius: 4px;
}

.message-bubble.assistant {
  background: rgba(var(--v-theme-surface-variant), 0.6);
  margin-right: auto;
  border-bottom-left-radius: 4px;
}

.message-content {
  line-height: 1.6;
  word-break: break-word;
}

.message-content :deep(pre) {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  padding: 10px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 0.85em;
}

.message-content :deep(code) {
  font-size: 0.9em;
  background: rgba(0, 0, 0, 0.06);
  padding: 1px 4px;
  border-radius: 3px;
}

.message-content :deep(pre code) {
  background: none;
  padding: 0;
}

.message-content :deep(p) {
  margin-bottom: 4px;
}

.message-content :deep(ul), .message-content :deep(ol) {
  padding-left: 20px;
  margin-bottom: 4px;
}

.input-area {
  background: rgb(var(--v-theme-surface));
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

/* Typing indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}
.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(var(--v-theme-on-surface), 0.4);
  animation: typing 1.4s infinite ease-in-out both;
}
.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
</style>
