<template>
  <div>
    <div class="d-flex align-center mb-6">
      <div class="text-h4 font-weight-bold">File Browser</div>
      <v-spacer />
      <v-chip
        v-if="!fsEnabled"
        color="error"
        variant="flat"
        prepend-icon="mdi-lock"
        class="mr-3"
      >
        Disabled — enable in Settings
      </v-chip>
      <v-btn
        icon="mdi-refresh"
        variant="text"
        :loading="loading"
        @click="loadDir(currentPath)"
      />
    </div>

    <!-- Disabled overlay -->
    <v-alert v-if="!fsEnabled" type="warning" variant="tonal" class="mb-4">
      File system access is disabled.
      <v-btn to="/settings" variant="text" color="warning" size="small" class="ml-2">
        Go to Settings
      </v-btn>
    </v-alert>

    <template v-if="fsEnabled">
      <!-- Breadcrumb / Path bar -->
      <v-card class="mb-4">
        <v-card-text class="pa-3">
          <div class="d-flex align-center">
            <v-btn
              icon="mdi-arrow-up"
              size="small"
              variant="text"
              :disabled="!parentPath"
              @click="loadDir(parentPath)"
              class="mr-2"
            />
            <v-breadcrumbs :items="breadcrumbs" density="compact" class="pa-0 flex-grow-1">
              <template #item="{ item }">
                <v-breadcrumbs-item @click="loadDir(item.path)" style="cursor: pointer">
                  {{ item.title }}
                </v-breadcrumbs-item>
              </template>
            </v-breadcrumbs>
            <v-btn
              size="small"
              variant="outlined"
              prepend-icon="mdi-harddisk"
              @click="showDrives = true"
              class="ml-2"
            >
              Drives
            </v-btn>
            <v-btn
              size="small"
              variant="outlined"
              prepend-icon="mdi-eye"
              :color="showHidden ? 'primary' : undefined"
              @click="showHidden = !showHidden; loadDir(currentPath)"
              class="ml-2"
            >
              Hidden
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Toolbar -->
      <v-card class="mb-4">
        <v-card-text class="pa-2 d-flex align-center ga-2">
          <v-btn
            size="small"
            variant="tonal"
            prepend-icon="mdi-folder-plus"
            @click="newFolderDialog = true"
          >
            New Folder
          </v-btn>
          <v-btn
            size="small"
            variant="tonal"
            prepend-icon="mdi-file-plus"
            @click="openNewFileDialog"
          >
            New File
          </v-btn>
          <v-spacer />
          <v-text-field
            v-model="searchQuery"
            density="compact"
            variant="outlined"
            hide-details
            placeholder="Search files (glob: *.py)"
            prepend-inner-icon="mdi-magnify"
            style="max-width: 300px"
            clearable
            @keyup.enter="doSearch"
          />
          <v-btn size="small" variant="tonal" @click="doSearch" :loading="searching">Search</v-btn>
        </v-card-text>
      </v-card>

      <!-- File List -->
      <v-card>
        <v-data-table
          :headers="headers"
          :items="items"
          :loading="loading"
          density="compact"
          items-per-page="50"
          hover
          @click:row="(e, { item }) => onRowClick(item)"
        >
          <template #item.name="{ item }">
            <div class="d-flex align-center" style="cursor: pointer">
              <v-icon :color="item.is_dir ? 'amber-darken-2' : 'grey'" class="mr-2">
                {{ item.is_dir ? 'mdi-folder' : getFileIcon(item.name) }}
              </v-icon>
              {{ item.name }}
            </div>
          </template>

          <template #item.size="{ item }">
            {{ item.is_dir ? '—' : formatSize(item.size) }}
          </template>

          <template #item.modified="{ item }">
            {{ item.modified ? new Date(item.modified).toLocaleString() : '—' }}
          </template>

          <template #item.permissions="{ item }">
            <code class="text-caption">{{ item.permissions }}</code>
          </template>

          <template #item.actions="{ item }">
            <v-btn
              v-if="item.is_file"
              icon="mdi-eye"
              size="x-small"
              variant="text"
              @click.stop="viewFile(item)"
            />
            <v-btn
              icon="mdi-pencil"
              size="x-small"
              variant="text"
              @click.stop="renameItem(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="x-small"
              variant="text"
              color="error"
              @click.stop="deleteItem(item)"
            />
          </template>
        </v-data-table>
      </v-card>
    </template>

    <!-- Drives dialog -->
    <v-dialog v-model="showDrives" max-width="400">
      <v-card>
        <v-card-title>Drives / Mount Points</v-card-title>
        <v-list>
          <v-list-item
            v-for="d in drives"
            :key="d.path"
            :title="d.name"
            :subtitle="d.path"
            prepend-icon="mdi-harddisk"
            @click="loadDir(d.path); showDrives = false"
          />
        </v-list>
        <v-card-actions>
          <v-spacer /><v-btn @click="showDrives = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- File viewer/editor dialog -->
    <v-dialog v-model="fileDialog" max-width="900" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-file-document</v-icon>
          {{ viewingFile?.name }}
          <v-spacer />
          <v-chip size="small" class="mr-2">{{ formatSize(viewingFile?.size || 0) }}</v-chip>
          <v-btn icon="mdi-close" size="small" variant="text" @click="fileDialog = false" />
        </v-card-title>
        <v-divider />
        <v-card-text style="max-height: 70vh; overflow: auto">
          <v-textarea
            v-model="fileContent"
            variant="outlined"
            rows="25"
            auto-grow
            :readonly="!editMode"
            class="file-editor"
            style="font-family: monospace; font-size: 13px"
          />
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="!editMode"
            prepend-icon="mdi-pencil"
            @click="editMode = true"
          >
            Edit
          </v-btn>
          <v-btn
            v-if="editMode"
            prepend-icon="mdi-content-save"
            color="primary"
            :loading="fileSaving"
            @click="saveFile"
          >
            Save
          </v-btn>
          <v-btn
            v-if="editMode"
            @click="editMode = false; fileContent = originalContent"
          >
            Cancel
          </v-btn>
          <v-spacer />
          <v-btn @click="fileDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- New folder dialog -->
    <v-dialog v-model="newFolderDialog" max-width="420">
      <v-card>
        <v-card-title>New Folder</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newFolderName"
            label="Folder name"
            autofocus
            @keyup.enter="createFolder"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="newFolderDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="creating" @click="createFolder">Create</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- New file dialog -->
    <v-dialog v-model="newFileDialog" max-width="420">
      <v-card>
        <v-card-title>New File</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newFileName"
            label="File name"
            autofocus
            @keyup.enter="createFile"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="newFileDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="creating" @click="createFile">Create</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Rename dialog -->
    <v-dialog v-model="renameDialog" max-width="420">
      <v-card>
        <v-card-title>Rename</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="renameName"
            label="New name"
            autofocus
            @keyup.enter="doRename"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="renameDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="renaming" @click="doRename">Rename</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete confirmation -->
    <ConfirmDeleteDialog
      v-model="deleteDialog"
      :title="`Delete ${deleteTarget?.name}?`"
      :message="deleteTarget?.is_dir ? 'This will recursively delete the directory and all its contents.' : 'This file will be permanently deleted.'"
      :loading="deleting"
      @confirm="doDelete"
    />

    <!-- Search results dialog -->
    <v-dialog v-model="searchDialog" max-width="800" scrollable>
      <v-card>
        <v-card-title>
          Search Results
          <v-chip size="small" class="ml-2">{{ searchResults.length }}</v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text style="max-height: 60vh">
          <v-list density="compact">
            <v-list-item
              v-for="r in searchResults"
              :key="r.path"
              :title="r.name"
              :subtitle="r.path"
              @click="r.is_dir ? loadDir(r.path) : viewFile(r); searchDialog = false"
            >
              <template #prepend>
                <v-icon :color="r.is_dir ? 'amber-darken-2' : 'grey'">
                  {{ r.is_dir ? 'mdi-folder' : 'mdi-file' }}
                </v-icon>
              </template>
              <template #append>
                <span class="text-caption">{{ formatSize(r.size) }}</span>
              </template>
            </v-list-item>
          </v-list>
          <div v-if="!searchResults.length" class="text-center text-medium-emphasis pa-4">
            No results found
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer /><v-btn @click="searchDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue'
import api from '../api'
import { useSettingsStore } from '../stores/settings'
import ConfirmDeleteDialog from '../components/ConfirmDeleteDialog.vue'

const showSnackbar = inject('showSnackbar')
const settingsStore = useSettingsStore()

// State
const fsEnabled = ref(false)
const loading = ref(false)
const currentPath = ref('/')
const parentPath = ref(null)
const items = ref([])
const showHidden = ref(false)

// Drives
const showDrives = ref(false)
const drives = ref([])

// File viewer
const fileDialog = ref(false)
const viewingFile = ref(null)
const fileContent = ref('')
const originalContent = ref('')
const editMode = ref(false)
const fileSaving = ref(false)

// New folder / file
const newFolderDialog = ref(false)
const newFolderName = ref('')
const newFileDialog = ref(false)
const newFileName = ref('')
const creating = ref(false)

// Rename
const renameDialog = ref(false)
const renameTarget = ref(null)
const renameName = ref('')
const renaming = ref(false)

// Delete
const deleteDialog = ref(false)
const deleteTarget = ref(null)
const deleting = ref(false)

// Search
const searchQuery = ref('')
const searchDialog = ref(false)
const searchResults = ref([])
const searching = ref(false)

const headers = [
  { title: 'Name', key: 'name', sortable: true },
  { title: 'Size', key: 'size', sortable: true, width: '120px' },
  { title: 'Modified', key: 'modified', sortable: true, width: '200px' },
  { title: 'Permissions', key: 'permissions', sortable: false, width: '120px' },
  { title: 'Actions', key: 'actions', sortable: false, width: '130px', align: 'end' },
]

const breadcrumbs = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  const crumbs = [{ title: '/', path: '/' }]
  let acc = ''
  for (const p of parts) {
    acc += '/' + p
    crumbs.push({ title: p, path: acc })
  }
  return crumbs
})

onMounted(async () => {
  await settingsStore.fetchSystemSettings()
  fsEnabled.value = settingsStore.systemSettings.filesystem_access_enabled?.value === 'true'
  if (fsEnabled.value) {
    loadDir('/')
    loadDrives()
  }
})

async function loadDir(path) {
  loading.value = true
  try {
    const { data } = await api.get('/fs/list', { params: { path, show_hidden: showHidden.value } })
    currentPath.value = data.path
    parentPath.value = data.parent
    items.value = data.items
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error listing directory', 'error')
  } finally {
    loading.value = false
  }
}

async function loadDrives() {
  try {
    const { data } = await api.get('/fs/drives')
    drives.value = data.drives || []
  } catch {
    // ignore
  }
}

function onRowClick(item) {
  if (item.is_dir) {
    loadDir(item.path)
  } else {
    viewFile(item)
  }
}

async function viewFile(item) {
  try {
    const { data } = await api.get('/fs/read', { params: { path: item.path } })
    viewingFile.value = { ...item, size: data.size }
    fileContent.value = data.content
    originalContent.value = data.content
    editMode.value = false
    fileDialog.value = true
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error reading file', 'error')
  }
}

async function saveFile() {
  fileSaving.value = true
  try {
    await api.post('/fs/write', { path: viewingFile.value.path, content: fileContent.value })
    originalContent.value = fileContent.value
    editMode.value = false
    showSnackbar('File saved')
    loadDir(currentPath.value)
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error saving file', 'error')
  } finally {
    fileSaving.value = false
  }
}

async function createFolder() {
  if (!newFolderName.value) return
  creating.value = true
  try {
    const fullPath = currentPath.value.replace(/\/$/, '') + '/' + newFolderName.value
    await api.post('/fs/mkdir', { path: fullPath })
    showSnackbar('Folder created')
    newFolderDialog.value = false
    newFolderName.value = ''
    loadDir(currentPath.value)
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error creating folder', 'error')
  } finally {
    creating.value = false
  }
}

function openNewFileDialog() {
  newFileName.value = ''
  newFileDialog.value = true
}

async function createFile() {
  if (!newFileName.value) return
  creating.value = true
  try {
    const fullPath = currentPath.value.replace(/\/$/, '') + '/' + newFileName.value
    await api.post('/fs/write', { path: fullPath, content: '' })
    showSnackbar('File created')
    newFileDialog.value = false
    newFileName.value = ''
    loadDir(currentPath.value)
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error creating file', 'error')
  } finally {
    creating.value = false
  }
}

function renameItem(item) {
  renameTarget.value = item
  renameName.value = item.name
  renameDialog.value = true
}

async function doRename() {
  if (!renameName.value || !renameTarget.value) return
  renaming.value = true
  try {
    const parent = renameTarget.value.path.substring(0, renameTarget.value.path.lastIndexOf('/'))
    const dest = parent + '/' + renameName.value
    await api.post('/fs/move', { source: renameTarget.value.path, destination: dest })
    showSnackbar('Renamed successfully')
    renameDialog.value = false
    loadDir(currentPath.value)
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error renaming', 'error')
  } finally {
    renaming.value = false
  }
}

function deleteItem(item) {
  deleteTarget.value = item
  deleteDialog.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.post('/fs/delete', {
      path: deleteTarget.value.path,
      recursive: deleteTarget.value.is_dir,
    })
    showSnackbar('Deleted')
    deleteDialog.value = false
    loadDir(currentPath.value)
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Error deleting', 'error')
  } finally {
    deleting.value = false
  }
}

async function doSearch() {
  if (!searchQuery.value) return
  searching.value = true
  try {
    const { data } = await api.get('/fs/search', {
      params: { path: currentPath.value, pattern: searchQuery.value },
    })
    searchResults.value = data.results
    searchDialog.value = true
  } catch (e) {
    showSnackbar(e.response?.data?.detail || 'Search error', 'error')
  } finally {
    searching.value = false
  }
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

function getFileIcon(name) {
  const ext = name.split('.').pop()?.toLowerCase()
  const icons = {
    py: 'mdi-language-python',
    js: 'mdi-language-javascript',
    ts: 'mdi-language-typescript',
    vue: 'mdi-vuejs',
    html: 'mdi-language-html5',
    css: 'mdi-language-css3',
    json: 'mdi-code-json',
    md: 'mdi-language-markdown',
    txt: 'mdi-file-document',
    yaml: 'mdi-file-cog',
    yml: 'mdi-file-cog',
    sh: 'mdi-console',
    sql: 'mdi-database',
    png: 'mdi-file-image',
    jpg: 'mdi-file-image',
    jpeg: 'mdi-file-image',
    gif: 'mdi-file-image',
    svg: 'mdi-file-image',
    pdf: 'mdi-file-pdf-box',
    zip: 'mdi-folder-zip',
    gz: 'mdi-folder-zip',
    tar: 'mdi-folder-zip',
    log: 'mdi-text-box',
    env: 'mdi-file-lock',
    dockerfile: 'mdi-docker',
    toml: 'mdi-file-cog',
    cfg: 'mdi-file-cog',
    ini: 'mdi-file-cog',
  }
  return icons[ext] || 'mdi-file'
}
</script>
