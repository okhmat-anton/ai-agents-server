<template>
  <div>
    <div class="text-h4 font-weight-bold mb-6">Settings</div>

    <v-card class="mb-6">
      <v-card-title>Change Password</v-card-title>
      <v-card-text>
        <v-form @submit.prevent="changePassword">
          <v-row>
            <v-col cols="4">
              <v-text-field v-model="oldPass" label="Old Password" type="password" />
            </v-col>
            <v-col cols="4">
              <v-text-field v-model="newPass" label="New Password" type="password" />
            </v-col>
            <v-col cols="4" class="d-flex align-center">
              <v-btn type="submit" color="primary" :loading="saving">Change</v-btn>
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>
    </v-card>

    <v-row>
      <v-col cols="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-brain</v-icon>Models
          </v-card-title>
          <v-card-text>Manage LLM provider connections</v-card-text>
          <v-card-actions><v-btn to="/settings/models" color="primary">Manage Models</v-btn></v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="6">
        <v-card>
          <v-card-title>
            <v-icon class="mr-2">mdi-key</v-icon>API Keys
          </v-card-title>
          <v-card-text>Manage API keys for VSCode / external clients</v-card-text>
          <v-card-actions><v-btn to="/settings/api-keys" color="primary">Manage Keys</v-btn></v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { useSettingsStore } from '../stores/settings'

const store = useSettingsStore()
const showSnackbar = inject('showSnackbar')
const oldPass = ref('')
const newPass = ref('')
const saving = ref(false)

const changePassword = async () => {
  saving.value = true
  try {
    await store.changePassword(oldPass.value, newPass.value)
    showSnackbar('Password changed')
    oldPass.value = ''
    newPass.value = ''
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error', 'error')
  } finally {
    saving.value = false
  }
}
</script>
