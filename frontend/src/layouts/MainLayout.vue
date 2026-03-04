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
    </v-main>
  </v-layout>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()
const drawer = ref(true)
const rail = ref(false)

const navItems = [
  { path: '/', icon: 'mdi-view-dashboard', title: 'Dashboard' },
  { path: '/agents', icon: 'mdi-robot', title: 'Agents' },
  { path: '/tasks', icon: 'mdi-clipboard-list', title: 'Tasks' },
  { path: '/skills', icon: 'mdi-puzzle', title: 'Skills' },
  { path: '/settings', icon: 'mdi-cog', title: 'Settings' },
//   { path: '/settings/models', icon: 'mdi-brain', title: 'Models' },
//   { path: '/settings/api-keys', icon: 'mdi-key', title: 'API Keys' },
  { path: '/ollama', icon: 'mdi-creation', title: 'Ollama' },
  { path: '/system/logs', icon: 'mdi-text-box-search', title: 'System Logs' },
]

const handleLogout = async () => {
  await auth.logout()
  router.push('/login')
}
</script>
