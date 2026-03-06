<template>
  <div v-if="project">
    <!-- Header -->
    <div class="d-flex align-center mb-4">
      <v-btn icon variant="text" class="mr-2" @click="$router.push('/projects')">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div>
        <h1 class="text-h4">{{ project.name }}</h1>
        <div class="text-medium-emphasis text-body-2">
          <v-chip size="x-small" :color="statusColor(project.status)" variant="flat" class="mr-2">
            {{ project.status }}
          </v-chip>
          <span v-if="project.tech_stack">{{ project.tech_stack }}</span>
        </div>
      </div>
      <v-spacer />
      <v-chip variant="tonal" color="info" class="mr-2" prepend-icon="mdi-file-document-outline">
        {{ project.file_count }} files
      </v-chip>
      <v-chip variant="tonal" color="primary" prepend-icon="mdi-clipboard-list-outline">
        {{ project.task_stats?.done || 0 }}/{{ project.task_stats?.total || 0 }} tasks
      </v-chip>
    </div>

    <!-- Tabs -->
    <v-tabs v-model="activeTab" color="primary" class="mb-4">
      <v-tab value="tasks" prepend-icon="mdi-clipboard-list">Backlog</v-tab>
      <v-tab value="code" prepend-icon="mdi-code-braces">Code</v-tab>
      <v-tab value="terminal" prepend-icon="mdi-console">Terminal</v-tab>
      <v-tab value="logs" prepend-icon="mdi-text-box-search">Logs</v-tab>
      <v-tab value="settings" prepend-icon="mdi-cog">Settings</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">

      <!-- ═══ TASKS TAB ═══ -->
      <v-window-item value="tasks">
        <div class="d-flex align-center mb-3">
          <v-btn-toggle v-model="taskViewMode" density="compact" mandatory variant="outlined" divided>
            <v-btn value="list" icon="mdi-format-list-bulleted" size="small" />
            <v-btn value="kanban" icon="mdi-view-column" size="small" />
          </v-btn-toggle>
          <v-spacer />
          <v-btn size="small" color="primary" prepend-icon="mdi-plus" @click="showTaskDialog = true">
            New Task
          </v-btn>
        </div>

        <!-- List View -->
        <template v-if="taskViewMode === 'list'">
          <v-data-table
            :headers="taskHeaders"
            :items="tasks"
            :loading="tasksLoading"
            hover
            density="compact"
            items-per-page="50"
            no-data-text="No tasks yet. Create your first task!"
          >
            <template #item.key="{ item }">
              <span class="font-weight-medium text-info">{{ item.key }}</span>
            </template>
            <template #item.status="{ item }">
              <v-select
                :model-value="item.status"
                :items="taskStatuses"
                density="compact"
                variant="plain"
                hide-details
                style="max-width: 140px"
                @update:model-value="moveTask(item, $event)"
              >
                <template #selection="{ item: statusItem }">
                  <v-chip size="x-small" :color="taskStatusColor(statusItem.value)" variant="flat">
                    {{ statusItem.title }}
                  </v-chip>
                </template>
              </v-select>
            </template>
            <template #item.priority="{ item }">
              <v-chip size="x-small" :color="priorityColor(item.priority)" variant="tonal">
                {{ item.priority }}
              </v-chip>
            </template>
            <template #item.assignee="{ item }">
              <span class="text-caption">{{ item.assignee || '—' }}</span>
            </template>
            <template #item.actions="{ item }">
              <v-btn icon size="x-small" variant="text" @click="editTask(item)">
                <v-icon size="16">mdi-pencil</v-icon>
              </v-btn>
              <v-btn icon size="x-small" variant="text" color="error" @click="removeTask(item)">
                <v-icon size="16">mdi-delete</v-icon>
              </v-btn>
            </template>
          </v-data-table>
        </template>

        <!-- Kanban View -->
        <template v-if="taskViewMode === 'kanban'">
          <div class="kanban-board d-flex ga-3" style="overflow-x: auto">
            <div
              v-for="col in kanbanColumns"
              :key="col.value"
              class="kanban-column"
              style="min-width: 220px; flex: 1; max-width: 300px"
            >
              <div class="d-flex align-center mb-2 px-1">
                <v-chip size="x-small" :color="taskStatusColor(col.value)" variant="flat">
                  {{ col.title }}
                </v-chip>
                <v-spacer />
                <span class="text-caption text-medium-emphasis">{{ kanbanTasks(col.value).length }}</span>
              </div>
              <div
                class="kanban-drop-zone rounded-lg pa-1"
                style="min-height: 100px; background: rgba(var(--v-theme-surface-variant), 0.3)"
                @dragover.prevent
                @drop="onDrop($event, col.value)"
              >
                <v-card
                  v-for="task in kanbanTasks(col.value)"
                  :key="task.id"
                  class="mb-2 kanban-card"
                  variant="outlined"
                  density="compact"
                  draggable="true"
                  @dragstart="onDragStart($event, task)"
                >
                  <v-card-text class="pa-2">
                    <div class="d-flex align-center">
                      <span class="text-caption text-info mr-1">{{ task.key }}</span>
                      <v-chip v-if="task.priority !== 'medium'" size="x-small" :color="priorityColor(task.priority)" variant="tonal" class="ml-auto">
                        {{ task.priority[0].toUpperCase() }}
                      </v-chip>
                    </div>
                    <div class="text-body-2 mt-1">{{ task.title }}</div>
                    <div v-if="task.assignee" class="text-caption text-medium-emphasis mt-1">
                      <v-icon size="12">mdi-account</v-icon> {{ task.assignee }}
                    </div>
                  </v-card-text>
                </v-card>
              </div>
            </div>
          </div>
        </template>
      </v-window-item>

      <!-- ═══ CODE TAB ═══ -->
      <v-window-item value="code">
        <div class="d-flex" style="height: calc(100vh - 280px)">
          <!-- File Tree -->
          <div class="file-tree-panel" :style="{ width: treePanelWidth + 'px' }">
            <div class="d-flex align-center pa-2">
              <span class="text-subtitle-2">Files</span>
              <v-spacer />
              <v-btn icon size="x-small" variant="text" @click="createNewFile(false)" title="New File">
                <v-icon size="16">mdi-file-plus</v-icon>
              </v-btn>
              <v-btn icon size="x-small" variant="text" @click="createNewFile(true)" title="New Folder">
                <v-icon size="16">mdi-folder-plus</v-icon>
              </v-btn>
              <v-btn icon size="x-small" variant="text" @click="loadFiles" title="Refresh">
                <v-icon size="16">mdi-refresh</v-icon>
              </v-btn>
            </div>
            <v-divider />
            <div class="file-tree-content" style="overflow-y: auto; height: calc(100% - 44px)">
              <div v-if="!files.length" class="text-center text-medium-emphasis pa-4 text-caption">
                Empty project. Create your first file!
              </div>
              <file-tree-node
                v-for="item in files"
                :key="item.path"
                :item="item"
                :depth="0"
                :selected-path="selectedFile?.path"
                @select="selectFile"
                @delete="deleteFileItem"
              />
            </div>
          </div>

          <!-- Resize handle -->
          <div
            class="resize-handle"
            style="width: 4px; cursor: col-resize; background: rgba(var(--v-theme-on-surface), 0.1)"
            @mousedown="startResize"
          />

          <!-- Editor -->
          <div class="flex-grow-1 d-flex flex-column" style="min-width: 0">
            <div v-if="selectedFile" class="d-flex align-center pa-2 bg-surface-variant">
              <v-icon size="16" class="mr-1">mdi-file-document</v-icon>
              <span class="text-body-2">{{ selectedFile.path }}</span>
              <v-chip v-if="fileModified" size="x-small" color="warning" variant="tonal" class="ml-2">Modified</v-chip>
              <v-spacer />
              <v-btn size="small" variant="tonal" color="primary" @click="saveFile" :disabled="!fileModified" :loading="fileSaving">
                <v-icon size="16" class="mr-1">mdi-content-save</v-icon> Save
              </v-btn>
            </div>
            <div v-if="selectedFile" class="flex-grow-1" style="overflow: auto">
              <textarea
                ref="editorRef"
                v-model="fileContent"
                class="code-editor"
                spellcheck="false"
                @keydown.ctrl.s.prevent="saveFile"
                @keydown.meta.s.prevent="saveFile"
              />
            </div>
            <div v-else class="d-flex align-center justify-center flex-grow-1 text-medium-emphasis">
              <div class="text-center">
                <v-icon size="48" color="grey">mdi-file-code-outline</v-icon>
                <p class="mt-2">Select a file to edit</p>
              </div>
            </div>
          </div>
        </div>
      </v-window-item>

      <!-- ═══ TERMINAL TAB ═══ -->
      <v-window-item value="terminal">
        <v-card variant="outlined">
          <v-card-text>
            <div ref="terminalOutput" class="terminal-output mb-3" style="height: 400px; overflow-y: auto; background: #1e1e1e; border-radius: 4px; padding: 12px; font-family: monospace; font-size: 13px; color: #d4d4d4">
              <div v-for="(line, i) in terminalLines" :key="i" :class="line.type === 'stderr' ? 'text-error' : line.type === 'command' ? 'text-info' : ''">
                <span v-if="line.type === 'command'" class="text-success mr-1">$</span>{{ line.text }}
              </div>
              <div v-if="terminalRunning" class="d-flex align-center mt-1">
                <v-progress-circular size="14" width="2" indeterminate class="mr-2" />
                <span class="text-medium-emphasis">Running...</span>
              </div>
            </div>
            <div class="d-flex ga-2">
              <v-text-field
                v-model="terminalCommand"
                label="Command"
                placeholder="python main.py"
                variant="outlined"
                density="compact"
                hide-details
                class="flex-grow-1"
                prepend-inner-icon="mdi-console"
                @keydown.enter="runCommand"
                :disabled="terminalRunning"
              />
              <v-btn color="primary" :loading="terminalRunning" @click="runCommand" :disabled="!terminalCommand">
                <v-icon>mdi-play</v-icon>
              </v-btn>
              <v-btn variant="outlined" @click="terminalLines = []">
                <v-icon>mdi-delete-sweep</v-icon>
              </v-btn>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- ═══ LOGS TAB ═══ -->
      <v-window-item value="logs">
        <div class="d-flex align-center mb-3">
          <v-select
            v-model="logLevel"
            :items="['all', 'info', 'warning', 'error']"
            label="Level"
            density="compact"
            variant="outlined"
            style="max-width: 150px"
            hide-details
            class="mr-3"
          />
          <v-select
            v-model="logSource"
            :items="['all', 'system', 'user', 'execution', 'agent']"
            label="Source"
            density="compact"
            variant="outlined"
            style="max-width: 150px"
            hide-details
          />
          <v-spacer />
          <v-btn icon size="small" variant="text" @click="loadLogs">
            <v-icon>mdi-refresh</v-icon>
          </v-btn>
        </div>
        <v-data-table
          :headers="logHeaders"
          :items="logs"
          :loading="logsLoading"
          density="compact"
          items-per-page="50"
          no-data-text="No logs yet"
        >
          <template #item.level="{ item }">
            <v-chip size="x-small" :color="logLevelColor(item.level)" variant="flat">
              {{ item.level }}
            </v-chip>
          </template>
          <template #item.timestamp="{ item }">
            <span class="text-caption">{{ formatTime(item.timestamp) }}</span>
          </template>
          <template #item.source="{ item }">
            <v-chip size="x-small" variant="tonal">{{ item.source }}</v-chip>
          </template>
        </v-data-table>
      </v-window-item>

      <!-- ═══ SETTINGS TAB ═══ -->
      <v-window-item value="settings">
        <v-card variant="outlined" class="mb-4">
          <v-card-title>Project Settings</v-card-title>
          <v-card-text>
            <v-text-field
              v-model="settingsForm.name"
              label="Project Name"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-textarea
              v-model="settingsForm.description"
              label="Description"
              variant="outlined"
              density="compact"
              rows="3"
              class="mb-2"
            />
            <v-textarea
              v-model="settingsForm.goals"
              label="Goals"
              variant="outlined"
              density="compact"
              rows="3"
              class="mb-2"
            />
            <v-textarea
              v-model="settingsForm.success_criteria"
              label="Success Criteria"
              variant="outlined"
              density="compact"
              rows="3"
              class="mb-2"
            />
            <v-text-field
              v-model="settingsForm.tech_stack"
              label="Tech Stack"
              variant="outlined"
              density="compact"
              class="mb-2"
            />
            <v-row>
              <v-col cols="4">
                <v-select
                  v-model="settingsForm.status"
                  :items="[{title:'Active',value:'active'},{title:'Paused',value:'paused'},{title:'Completed',value:'completed'},{title:'Archived',value:'archived'}]"
                  label="Status"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
              <v-col cols="4">
                <v-select
                  v-model="settingsForm.access_level"
                  :items="[{title:'All Agents',value:'full'},{title:'Restricted',value:'restricted'}]"
                  label="Access Level"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
              <v-col cols="4">
                <v-select
                  v-model="settingsForm.execution_access"
                  :items="[{title:'Restricted (project dir)',value:'restricted'},{title:'Full System',value:'full'}]"
                  label="Execution Access"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
            </v-row>
            <v-combobox
              v-model="settingsForm.tags"
              label="Tags"
              variant="outlined"
              density="compact"
              multiple
              chips
              closable-chips
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn color="primary" :loading="settingsSaving" @click="saveSettings">
              Save Settings
            </v-btn>
          </v-card-actions>
        </v-card>

        <v-card variant="outlined" color="error">
          <v-card-title class="text-error">Danger Zone</v-card-title>
          <v-card-text>
            <v-btn color="error" variant="outlined" @click="$router.push('/projects')">
              Delete this project from Projects list
            </v-btn>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Task Create/Edit Dialog -->
    <v-dialog v-model="showTaskDialog" max-width="550" persistent>
      <v-card>
        <v-card-title>{{ editingTask ? 'Edit Task' : 'New Task' }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="taskForm.title"
            label="Task Title *"
            variant="outlined"
            density="compact"
            class="mb-2"
          />
          <v-textarea
            v-model="taskForm.description"
            label="Description"
            variant="outlined"
            density="compact"
            rows="3"
            class="mb-2"
          />
          <v-row>
            <v-col cols="4">
              <v-select
                v-model="taskForm.status"
                :items="taskStatuses"
                label="Status"
                variant="outlined"
                density="compact"
              />
            </v-col>
            <v-col cols="4">
              <v-select
                v-model="taskForm.priority"
                :items="priorityItems"
                label="Priority"
                variant="outlined"
                density="compact"
              />
            </v-col>
            <v-col cols="4">
              <v-text-field
                v-model.number="taskForm.story_points"
                label="Story Points"
                type="number"
                variant="outlined"
                density="compact"
              />
            </v-col>
          </v-row>
          <v-text-field
            v-model="taskForm.assignee"
            label="Assignee"
            placeholder="Agent name or 'human'"
            variant="outlined"
            density="compact"
            class="mb-2"
          />
          <v-combobox
            v-model="taskForm.labels"
            label="Labels"
            variant="outlined"
            density="compact"
            multiple
            chips
            closable-chips
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="closeTaskDialog">Cancel</v-btn>
          <v-btn color="primary" :loading="taskSaving" @click="saveTask" :disabled="!taskForm.title">
            {{ editingTask ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- New File Dialog -->
    <v-dialog v-model="showNewFileDialog" max-width="400">
      <v-card>
        <v-card-title>{{ newFileIsDir ? 'New Folder' : 'New File' }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="newFilePath"
            :label="newFileIsDir ? 'Folder path' : 'File path'"
            :placeholder="newFileIsDir ? 'src/utils' : 'src/main.py'"
            variant="outlined"
            density="compact"
            autofocus
            @keydown.enter="doCreateFile"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showNewFileDialog = false">Cancel</v-btn>
          <v-btn color="primary" :disabled="!newFilePath" @click="doCreateFile">Create</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>

  <!-- Loading state -->
  <div v-else class="d-flex justify-center align-center" style="height: 300px">
    <v-progress-circular indeterminate size="48" />
  </div>
</template>

<script>
// Recursive file tree component
const FileTreeNode = {
  name: 'FileTreeNode',
  props: {
    item: Object,
    depth: { type: Number, default: 0 },
    selectedPath: String,
  },
  emits: ['select', 'delete'],
  data() {
    return { expanded: this.depth < 2 }
  },
  methods: {
    toggle() {
      if (this.item.is_dir) this.expanded = !this.expanded
      else this.$emit('select', this.item)
    },
    getIcon() {
      if (this.item.is_dir) return this.expanded ? 'mdi-folder-open' : 'mdi-folder'
      const lang = this.item.language
      if (lang === 'python') return 'mdi-language-python'
      if (lang === 'javascript' || lang === 'typescript') return 'mdi-language-javascript'
      if (lang === 'html') return 'mdi-language-html5'
      if (lang === 'css' || lang === 'scss') return 'mdi-language-css3'
      if (lang === 'json') return 'mdi-code-json'
      if (lang === 'markdown') return 'mdi-language-markdown'
      return 'mdi-file-document-outline'
    },
  },
  template: `
    <div>
      <div
        class="file-tree-item d-flex align-center px-2 py-1"
        :class="{ 'bg-primary-darken-2': selectedPath === item.path && !item.is_dir }"
        :style="{ paddingLeft: (depth * 16 + 4) + 'px', cursor: 'pointer' }"
        @click="toggle"
        @contextmenu.prevent="$emit('delete', item)"
      >
        <v-icon :size="16" class="mr-1" :color="item.is_dir ? 'amber' : 'grey'">{{ getIcon() }}</v-icon>
        <span class="text-body-2 text-truncate">{{ item.name }}</span>
        <span v-if="!item.is_dir" class="text-caption text-medium-emphasis ml-auto">
          {{ item.size < 1024 ? item.size + 'B' : (item.size / 1024).toFixed(1) + 'K' }}
        </span>
      </div>
      <div v-if="item.is_dir && expanded && item.children">
        <file-tree-node
          v-for="child in item.children"
          :key="child.path"
          :item="child"
          :depth="depth + 1"
          :selected-path="selectedPath"
          @select="$emit('select', $event)"
          @delete="$emit('delete', $event)"
        />
      </div>
    </div>
  `,
}

export default { components: { FileTreeNode } }
</script>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '../stores/projects'
import api from '../api'

const route = useRoute()
const router = useRouter()
const store = useProjectsStore()

const slug = computed(() => route.params.slug)
const project = ref(null)
const activeTab = ref('tasks')

// ── Tasks ──
const tasks = ref([])
const tasksLoading = ref(false)
const taskViewMode = ref('kanban')
const showTaskDialog = ref(false)
const editingTask = ref(null)
const taskSaving = ref(false)
const draggedTask = ref(null)

const taskHeaders = [
  { title: 'Key', key: 'key', width: '70px' },
  { title: 'Title', key: 'title' },
  { title: 'Status', key: 'status', width: '150px' },
  { title: 'Priority', key: 'priority', width: '100px' },
  { title: 'Assignee', key: 'assignee', width: '120px' },
  { title: 'SP', key: 'story_points', width: '50px' },
  { title: '', key: 'actions', width: '80px', sortable: false },
]

const taskStatuses = [
  { title: 'Backlog', value: 'backlog' },
  { title: 'Todo', value: 'todo' },
  { title: 'In Progress', value: 'in_progress' },
  { title: 'Review', value: 'review' },
  { title: 'Done', value: 'done' },
  { title: 'Cancelled', value: 'cancelled' },
]

const kanbanColumns = taskStatuses.filter(s => s.value !== 'cancelled')

const priorityItems = [
  { title: 'Lowest', value: 'lowest' },
  { title: 'Low', value: 'low' },
  { title: 'Medium', value: 'medium' },
  { title: 'High', value: 'high' },
  { title: 'Highest', value: 'highest' },
]

const defaultTaskForm = () => ({
  title: '', description: '', status: 'backlog', priority: 'medium',
  assignee: '', labels: [], story_points: null,
})
const taskForm = ref(defaultTaskForm())

function taskStatusColor(s) {
  return { backlog: 'grey', todo: 'blue-grey', in_progress: 'info', review: 'warning', done: 'success', cancelled: 'error' }[s] || 'grey'
}

function priorityColor(p) {
  return { lowest: 'grey', low: 'blue-grey', medium: 'info', high: 'warning', highest: 'error' }[p] || 'grey'
}

function statusColor(s) {
  return { active: 'success', paused: 'warning', completed: 'info', archived: 'grey' }[s] || 'grey'
}

function kanbanTasks(status) {
  return tasks.value.filter(t => t.status === status)
}

function onDragStart(evt, task) {
  draggedTask.value = task
  evt.dataTransfer.effectAllowed = 'move'
}

async function onDrop(evt, status) {
  if (!draggedTask.value) return
  await moveTask(draggedTask.value, status)
  draggedTask.value = null
}

async function moveTask(task, newStatus) {
  try {
    await store.updateTask(slug.value, task.id, { status: newStatus })
    task.status = newStatus
  } catch (e) { console.error(e) }
}

async function loadTasks() {
  tasksLoading.value = true
  try {
    tasks.value = await store.fetchTasks(slug.value)
  } finally { tasksLoading.value = false }
}

function editTask(task) {
  editingTask.value = task
  taskForm.value = { ...task }
  showTaskDialog.value = true
}

function closeTaskDialog() {
  showTaskDialog.value = false
  editingTask.value = null
  taskForm.value = defaultTaskForm()
}

async function saveTask() {
  if (!taskForm.value.title) return
  taskSaving.value = true
  try {
    if (editingTask.value) {
      await store.updateTask(slug.value, editingTask.value.id, taskForm.value)
    } else {
      await store.createTask(slug.value, taskForm.value)
    }
    closeTaskDialog()
    await loadTasks()
  } finally { taskSaving.value = false }
}

async function removeTask(task) {
  try {
    await store.deleteTask(slug.value, task.id)
    await loadTasks()
  } catch (e) { console.error(e) }
}

// ── Code / Files ──
const files = ref([])
const selectedFile = ref(null)
const fileContent = ref('')
const originalContent = ref('')
const fileModified = computed(() => fileContent.value !== originalContent.value)
const fileSaving = ref(false)
const treePanelWidth = ref(250)
const showNewFileDialog = ref(false)
const newFilePath = ref('')
const newFileIsDir = ref(false)
const editorRef = ref(null)

async function loadFiles() {
  try {
    files.value = await store.fetchFiles(slug.value)
  } catch (e) { console.error(e) }
}

async function selectFile(item) {
  if (item.is_dir) return
  try {
    const data = await store.readFile(slug.value, item.path)
    selectedFile.value = item
    fileContent.value = data.content
    originalContent.value = data.content
  } catch (e) { console.error(e) }
}

async function saveFile() {
  if (!selectedFile.value || !fileModified.value) return
  fileSaving.value = true
  try {
    await store.writeFile(slug.value, selectedFile.value.path, fileContent.value)
    originalContent.value = fileContent.value
  } finally { fileSaving.value = false }
}

function createNewFile(isDir) {
  newFileIsDir.value = isDir
  newFilePath.value = ''
  showNewFileDialog.value = true
}

async function doCreateFile() {
  if (!newFilePath.value) return
  try {
    await store.createFile(slug.value, { path: newFilePath.value, is_dir: newFileIsDir.value, content: '' })
    showNewFileDialog.value = false
    await loadFiles()
  } catch (e) { console.error(e) }
}

async function deleteFileItem(item) {
  if (!confirm(`Delete ${item.is_dir ? 'folder' : 'file'} "${item.path}"?`)) return
  try {
    await store.deleteFile(slug.value, item.path)
    if (selectedFile.value?.path === item.path) {
      selectedFile.value = null
      fileContent.value = ''
      originalContent.value = ''
    }
  } catch (e) { console.error(e) }
}

let resizing = false
function startResize(evt) {
  resizing = true
  const startX = evt.clientX
  const startWidth = treePanelWidth.value
  const onMove = (e) => {
    if (!resizing) return
    treePanelWidth.value = Math.max(150, Math.min(500, startWidth + e.clientX - startX))
  }
  const onUp = () => { resizing = false; document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// ── Terminal ──
const terminalCommand = ref('')
const terminalLines = ref([])
const terminalRunning = ref(false)
const terminalOutput = ref(null)

async function runCommand() {
  if (!terminalCommand.value || terminalRunning.value) return
  const cmd = terminalCommand.value
  terminalLines.value.push({ type: 'command', text: cmd })
  terminalCommand.value = ''
  terminalRunning.value = true
  try {
    const result = await store.executeCommand(slug.value, { command: cmd, timeout: 60 })
    if (result.stdout) {
      result.stdout.split('\n').forEach(line => {
        if (line) terminalLines.value.push({ type: 'stdout', text: line })
      })
    }
    if (result.stderr) {
      result.stderr.split('\n').forEach(line => {
        if (line) terminalLines.value.push({ type: 'stderr', text: line })
      })
    }
    terminalLines.value.push({ type: 'info', text: `[exit ${result.exit_code}] ${result.duration_ms}ms${result.timed_out ? ' (timed out)' : ''}` })
  } catch (e) {
    terminalLines.value.push({ type: 'stderr', text: `Error: ${e.response?.data?.detail || e.message}` })
  } finally {
    terminalRunning.value = false
    await nextTick()
    if (terminalOutput.value) terminalOutput.value.scrollTop = terminalOutput.value.scrollHeight
  }
}

// ── Logs ──
const logs = ref([])
const logsLoading = ref(false)
const logLevel = ref('all')
const logSource = ref('all')

const logHeaders = [
  { title: 'Time', key: 'timestamp', width: '170px' },
  { title: 'Level', key: 'level', width: '80px' },
  { title: 'Source', key: 'source', width: '100px' },
  { title: 'Message', key: 'message' },
]

function logLevelColor(level) {
  return { info: 'info', warning: 'warning', error: 'error' }[level] || 'grey'
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

async function loadLogs() {
  logsLoading.value = true
  try {
    const params = { limit: 200 }
    if (logLevel.value && logLevel.value !== 'all') params.level = logLevel.value
    if (logSource.value && logSource.value !== 'all') params.source = logSource.value
    logs.value = await store.fetchLogs(slug.value, params)
  } finally { logsLoading.value = false }
}

watch([logLevel, logSource], loadLogs)

// ── Settings ──
const settingsForm = ref({})
const settingsSaving = ref(false)

async function saveSettings() {
  settingsSaving.value = true
  try {
    const data = await store.updateProject(slug.value, settingsForm.value)
    project.value = data
  } finally { settingsSaving.value = false }
}

// ── Load project ──
async function loadProject() {
  try {
    const data = await store.fetchProject(slug.value)
    project.value = data
    settingsForm.value = {
      name: data.name, description: data.description, goals: data.goals,
      success_criteria: data.success_criteria, tech_stack: data.tech_stack,
      status: data.status, access_level: data.access_level,
      execution_access: data.execution_access, tags: data.tags || [],
    }
    // Load all sub-data
    await Promise.all([loadTasks(), loadFiles(), loadLogs()])
  } catch (e) {
    console.error(e)
    router.push('/projects')
  }
}

onMounted(loadProject)
watch(slug, loadProject)
</script>

<style scoped>
.file-tree-panel {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
  flex-shrink: 0;
}

.file-tree-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.code-editor {
  width: 100%;
  height: 100%;
  background: #1e1e1e;
  color: #d4d4d4;
  border: none;
  outline: none;
  resize: none;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.5;
  padding: 12px;
  tab-size: 2;
  white-space: pre;
  overflow: auto;
}

.kanban-card {
  cursor: grab;
}
.kanban-card:active {
  cursor: grabbing;
}
</style>
