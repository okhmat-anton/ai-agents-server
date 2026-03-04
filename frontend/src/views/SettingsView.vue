<template>
  <div>
    <div class="text-h4 font-weight-bold mb-6">Settings</div>

    <!-- System Settings -->
    <v-card class="mb-6">
      <v-card-title>
        <v-icon class="mr-2">mdi-cog</v-icon>System Settings
      </v-card-title>
      <v-card-text>
        <v-row align="center">
          <v-col cols="auto">
            <v-switch
              v-model="fsAccessEnabled"
              color="error"
              :loading="fsToggling"
              hide-details
              @update:model-value="onFsToggle"
            >
              <template #label>
                <div>
                  <span class="font-weight-medium">File System Access</span>
                  <div class="text-caption text-medium-emphasis">
                    Allow the system to read, write, and delete files on this computer
                  </div>
                </div>
              </template>
            </v-switch>
          </v-col>
          <v-col cols="auto">
            <v-chip
              :color="fsAccessEnabled ? 'error' : 'grey'"
              size="small"
              variant="flat"
            >
              {{ fsAccessEnabled ? 'ENABLED' : 'DISABLED' }}
            </v-chip>
          </v-col>
        </v-row>
        <v-alert v-if="fsAccessEnabled" type="warning" variant="tonal" density="compact" class="mt-3">
          <strong>Warning:</strong> File system access is enabled. The system can read, modify, and delete any files
          accessible to the current user. Use with caution.
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Change Password -->
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

    <!-- Confirmation dialog for enabling FS access -->
    <v-dialog v-model="confirmDialog" max-width="520" persistent>
      <v-card>
        <v-card-title class="text-h6">
          <v-icon color="error" class="mr-2">mdi-shield-alert</v-icon>
          Enable File System Access?
        </v-card-title>
        <v-card-text>
          <v-alert type="error" variant="tonal" class="mb-4">
            This will grant the system <strong>full access</strong> to read, write, and delete files
            on this computer. This is a potentially dangerous operation.
          </v-alert>
          <p class="mb-3">To confirm, type <strong>ENABLE</strong> below:</p>
          <v-text-field
            v-model="confirmText"
            label="Type ENABLE to confirm"
            variant="outlined"
            density="compact"
            autofocus
            @keyup.enter="confirmText === 'ENABLE' && doEnableFs()"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="cancelFsToggle">Cancel</v-btn>
          <v-btn
            color="error"
            variant="flat"
            :disabled="confirmText !== 'ENABLE'"
            :loading="fsToggling"
            @click="doEnableFs"
          >
            Enable Access
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, inject, onMounted } from 'vue'
import { useSettingsStore } from '../stores/settings'

const store = useSettingsStore()
const showSnackbar = inject('showSnackbar')

// Password
const oldPass = ref('')
const newPass = ref('')
const saving = ref(false)

// FS access toggle
const fsAccessEnabled = ref(false)
const fsToggling = ref(false)
const confirmDialog = ref(false)
const confirmText = ref('')

onMounted(async () => {
  try {
    await store.fetchSystemSettings()
    fsAccessEnabled.value = store.systemSettings.filesystem_access_enabled?.value === 'true'
  } catch (e) {
    console.error('Failed to load system settings', e)
  }
})

const onFsToggle = (newVal) => {
  if (newVal) {
    // Turning ON: show confirmation dialog, revert toggle until confirmed
    fsAccessEnabled.value = false
    confirmText.value = ''
    confirmDialog.value = true
  } else {
    // Turning OFF: no confirmation needed
    doDisableFs()
  }
}

const doEnableFs = async () => {
  fsToggling.value = true
  try {
    await store.updateSystemSetting('filesystem_access_enabled', 'true')
    fsAccessEnabled.value = true
    confirmDialog.value = false
    showSnackbar('File system access enabled', 'warning')
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error enabling FS access', 'error')
  } finally {
    fsToggling.value = false
  }
}

const doDisableFs = async () => {
  fsToggling.value = true
  try {
    await store.updateSystemSetting('filesystem_access_enabled', 'false')
    fsAccessEnabled.value = false
    showSnackbar('File system access disabled')
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error disabling FS access', 'error')
    fsAccessEnabled.value = true
  } finally {
    fsToggling.value = false
  }
}

const cancelFsToggle = () => {
  confirmDialog.value = false
  fsAccessEnabled.value = false
  confirmText.value = ''
}

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
