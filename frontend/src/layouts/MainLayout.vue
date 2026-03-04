<template>
  <v-layout>
    <!-- Navigation Drawer -->
    <v-navigation-drawer v-model="drawer" :rail="rail" permanent>
      <v-list-item
        prepend-icon="mdi-robot-happy"
        title="AI Agents"
        subtitle="Server"
        nav
        @click="rail = !rail"
      />
      <v-divider />
      <v-list density="compact" nav>
        <v-list-item
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :prepend-icon="item.icon"
          :title="item.title"
          :value="item.path"
          rounded="xl"
        />
      </v-list>
      <template #append>
        <v-list density="compact" nav>
          <v-list-item
            prepend-icon="mdi-logout"
            title="Logout"
            @click="handleLogout"
            rounded="xl"
          />
        </v-list>
      </template>
    </v-navigation-drawer>

    <!-- Main Content -->
    <v-main>
      <v-container fluid class="pa-6">
        <router-view />
      </v-container>

      <!-- Chat FAB -->
      <v-btn
        icon
        color="primary"
        size="large"
        class="chat-fab"
        elevation="8"
        @click="chatStore.togglePanel()"
      >
        <v-icon>{{ chatStore.panelOpen ? 'mdi-close' : 'mdi-chat' }}</v-icon>
        <v-tooltip activator="parent" location="left">AI Chat</v-tooltip>
      </v-btn>
    </v-main>

    <!-- Right Chat Panel -->
    <ChatPanel />
  </v-layout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import ChatPanel from '../components/ChatPanel.vue'

const router = useRouter()
const auth = useAuthStore()
const chatStore = useChatStore()
const drawer = ref(true)
const rail = ref(false)

const navItems = [
  { path: '/', icon: 'mdi-view-dashboard', title: 'Dashboard' },
  { path: '/agents', icon: 'mdi-robot', title: 'Agents' },
  { path: '/tasks', icon: 'mdi-clipboard-list', title: 'Tasks' },
  { path: '/skills', icon: 'mdi-puzzle', title: 'Skills (Python or JS Code)' },
  { path: '/settings', icon: 'mdi-cog', title: 'Settings' },
//   { path: '/settings/models', icon: 'mdi-brain', title: 'Models' },
//   { path: '/settings/api-keys', icon: 'mdi-key', title: 'API Keys' },
  { path: '/ollama', icon: 'mdi-creation', title: 'Ollama' },
  { path: '/files', icon: 'mdi-folder-open', title: 'Files' },
  { path: '/terminal', icon: 'mdi-console', title: 'Terminal' },
  { path: '/system', icon: 'mdi-monitor-dashboard', title: 'System' },
  { path: '/system/logs', icon: 'mdi-text-box-search', title: 'System Logs' },
]

const handleLogout = async () => {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.chat-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 100;
}
</style>
