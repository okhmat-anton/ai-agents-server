<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-icon size="32" class="mr-3" color="primary">mdi-account-heart</v-icon>
      <div>
        <div class="text-h4 font-weight-bold">Creator Profile</div>
        <div class="text-body-2 text-medium-emphasis">
          Information about you — the person who manages the bots. Agents use this context to personalize responses.
        </div>
      </div>
    </div>

    <v-tabs v-model="tab" color="primary" class="mb-4">
      <v-tab value="profile">
        <v-icon start>mdi-account</v-icon>
        Profile
      </v-tab>
      <v-tab value="goals">
        <v-icon start color="amber">mdi-target</v-icon>
        Goals
        <v-chip v-if="form.goals.length" size="x-small" class="ml-2">{{ form.goals.length }}</v-chip>
      </v-tab>
      <v-tab value="dreams">
        <v-icon start color="deep-purple">mdi-weather-night</v-icon>
        Dreams
        <v-chip v-if="form.dreams.length" size="x-small" class="ml-2">{{ form.dreams.length }}</v-chip>
      </v-tab>
      <v-tab value="ideas">
        <v-icon start color="yellow">mdi-lightbulb</v-icon>
        Ideas
        <v-chip v-if="form.ideas.length" size="x-small" class="ml-2">{{ form.ideas.length }}</v-chip>
      </v-tab>
    </v-tabs>

    <v-card :loading="loading">
      <v-card-text>
        <v-form @submit.prevent="save">
          <v-window v-model="tab">

            <!-- ══════════ TAB: Profile ══════════ -->
            <v-window-item value="profile">
              <v-text-field
                v-model="form.name"
                label="Name"
                prepend-inner-icon="mdi-account"
                hint="How should agents refer to you?"
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="form.who"
                label="Who you are"
                prepend-inner-icon="mdi-card-account-details"
                rows="10"
                auto-grow
                hint="Brief description: profession, role, identity"
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="form.skills_and_abilities"
                label="Skills & Abilities"
                prepend-inner-icon="mdi-hammer-wrench"
                rows="10"
                auto-grow
                hint="What are your skills and expertise?"
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="form.current_situation"
                label="Current Situation"
                prepend-inner-icon="mdi-map-marker"
                rows="10"
                auto-grow
                hint="What's going on in your life right now?"
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="form.principles"
                label="Principles"
                prepend-inner-icon="mdi-shield-star"
                rows="10"
                auto-grow
                hint="Your core principles and values"
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="form.successes"
                label="Successes"
                prepend-inner-icon="mdi-trophy"
                rows="10"
                auto-grow
                hint="What have you achieved?"
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="form.failures"
                label="Failures"
                prepend-inner-icon="mdi-alert-decagram"
                rows="10"
                auto-grow
                hint="What didn't work? Lessons learned."
                persistent-hint
                class="mb-4"
              />

              <v-textarea
                v-model="form.action_history"
                label="Action History"
                prepend-inner-icon="mdi-history"
                rows="10"
                auto-grow
                hint="History of your attempts and actions"
                persistent-hint
                class="mb-4"
              />
            </v-window-item>

            <!-- ══════════ TAB: Goals ══════════ -->
            <v-window-item value="goals">
              <div class="d-flex align-center mb-4">
                <div class="text-h6">Your Goals</div>
                <v-btn icon size="small" color="primary" class="ml-3" @click="addGoal" title="Add goal">
                  <v-icon>mdi-plus</v-icon>
                </v-btn>
              </div>

              <div v-if="!form.goals.length" class="text-body-1 text-medium-emphasis text-center py-12">
                <v-icon size="64" color="grey-darken-1" class="mb-4">mdi-target</v-icon>
                <div>No goals yet. Click <v-icon size="18">mdi-plus</v-icon> to add your first goal.</div>
              </div>

              <div v-for="(goal, gi) in form.goals" :key="goal.id" class="mb-4">
                <v-card variant="outlined" class="pa-4">
                  <div class="d-flex align-start ga-3">
                    <div class="flex-grow-1">
                      <v-text-field
                        v-model="goal.title"
                        label="Goal title"
                        density="compact"
                        hide-details
                        class="mb-3"
                      />
                      <v-row dense class="mb-1">
                        <v-col cols="12" sm="8">
                          <v-textarea
                            v-model="goal.description"
                            label="Description"
                            rows="3"
                            auto-grow
                            density="compact"
                            hide-details
                          />
                        </v-col>
                        <v-col cols="12" sm="4">
                          <v-text-field
                            v-model="goal.target_date"
                            label="Target date"
                            type="date"
                            density="compact"
                            hide-details
                          />
                        </v-col>
                      </v-row>
                    </div>
                    <div class="d-flex flex-column ga-1">
                      <v-btn icon size="x-small" color="primary" @click="addSubGoal(gi)" title="Add sub-goal">
                        <v-icon size="16">mdi-subdirectory-arrow-right</v-icon>
                      </v-btn>
                      <v-btn icon size="x-small" color="error" variant="text" @click="removeGoal(gi)" title="Remove goal">
                        <v-icon size="16">mdi-close</v-icon>
                      </v-btn>
                    </div>
                  </div>

                  <!-- Sub-goals -->
                  <div v-if="goal.children && goal.children.length" class="ml-8 mt-4">
                    <div v-for="(sub, si) in goal.children" :key="sub.id" class="mb-3">
                      <v-card variant="tonal" class="pa-3">
                        <div class="d-flex align-start ga-3">
                          <div class="flex-grow-1">
                            <v-text-field
                              v-model="sub.title"
                              label="Sub-goal title"
                              density="compact"
                              hide-details
                              class="mb-2"
                            />
                            <v-row dense>
                              <v-col cols="12" sm="8">
                                <v-textarea
                                  v-model="sub.description"
                                  label="Description"
                                  rows="2"
                                  auto-grow
                                  density="compact"
                                  hide-details
                                />
                              </v-col>
                              <v-col cols="12" sm="4">
                                <v-text-field
                                  v-model="sub.target_date"
                                  label="Target date"
                                  type="date"
                                  density="compact"
                                  hide-details
                                />
                              </v-col>
                            </v-row>
                          </div>
                          <v-btn icon size="x-small" color="error" variant="text" @click="removeSubGoal(gi, si)" title="Remove sub-goal">
                            <v-icon size="16">mdi-close</v-icon>
                          </v-btn>
                        </div>
                      </v-card>
                    </div>
                  </div>
                </v-card>
              </div>
            </v-window-item>

            <!-- ══════════ TAB: Dreams ══════════ -->
            <v-window-item value="dreams">
              <div class="d-flex align-center mb-4">
                <div class="text-h6">Your Dreams</div>
                <v-btn icon size="small" color="primary" class="ml-3" @click="addDream" title="Add dream">
                  <v-icon>mdi-plus</v-icon>
                </v-btn>
              </div>

              <div v-if="!form.dreams.length" class="text-body-1 text-medium-emphasis text-center py-12">
                <v-icon size="64" color="grey-darken-1" class="mb-4">mdi-weather-night</v-icon>
                <div>No dreams yet. Click <v-icon size="18">mdi-plus</v-icon> to add your first dream.</div>
              </div>

              <div v-for="(dream, di) in form.dreams" :key="dream.id" class="mb-3">
                <v-card variant="outlined" class="pa-4">
                  <div class="d-flex align-start ga-3">
                    <div class="flex-grow-1">
                      <v-text-field
                        v-model="dream.title"
                        label="Dream"
                        density="compact"
                        hide-details
                        class="mb-3"
                      />
                      <v-textarea
                        v-model="dream.description"
                        label="Description"
                        rows="3"
                        auto-grow
                        density="compact"
                        hide-details
                      />
                    </div>
                    <v-btn icon size="x-small" color="error" variant="text" @click="removeDream(di)" title="Remove dream">
                      <v-icon size="16">mdi-close</v-icon>
                    </v-btn>
                  </div>
                </v-card>
              </div>
            </v-window-item>

            <!-- ══════════ TAB: Ideas ══════════ -->
            <v-window-item value="ideas">
              <div class="d-flex align-center mb-4">
                <div class="text-h6">Your Ideas</div>
                <v-btn icon size="small" color="primary" class="ml-3" @click="addIdea" title="Add idea">
                  <v-icon>mdi-plus</v-icon>
                </v-btn>
              </div>

              <div v-if="!form.ideas.length" class="text-body-1 text-medium-emphasis text-center py-12">
                <v-icon size="64" color="grey-darken-1" class="mb-4">mdi-lightbulb</v-icon>
                <div>No ideas yet. Click <v-icon size="18">mdi-plus</v-icon> to add your first idea.</div>
              </div>

              <div v-for="(idea, ii) in form.ideas" :key="idea.id" class="mb-3">
                <v-card variant="outlined" class="pa-4">
                  <div class="d-flex align-start ga-3">
                    <div class="flex-grow-1">
                      <v-text-field
                        v-model="idea.title"
                        label="Idea"
                        density="compact"
                        hide-details
                        class="mb-3"
                      />
                      <v-textarea
                        v-model="idea.description"
                        label="Description"
                        rows="3"
                        auto-grow
                        density="compact"
                        hide-details
                      />
                    </div>
                    <v-btn icon size="x-small" color="error" variant="text" @click="removeIdea(ii)" title="Remove idea">
                      <v-icon size="16">mdi-close</v-icon>
                    </v-btn>
                  </div>
                </v-card>
              </div>
            </v-window-item>

          </v-window>

          <div class="d-flex justify-end mt-6 ga-3">
            <v-btn variant="text" @click="load" :disabled="saving">
              <v-icon start>mdi-refresh</v-icon>
              Reset
            </v-btn>
            <v-btn type="submit" color="primary" :loading="saving" size="large">
              <v-icon start>mdi-content-save</v-icon>
              Save
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>

    <v-snackbar v-model="snackbar" :color="snackColor" timeout="3000">
      {{ snackText }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const tab = ref('profile')
const loading = ref(false)
const saving = ref(false)
const snackbar = ref(false)
const snackColor = ref('success')
const snackText = ref('')

function uid() {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)
}

const form = ref({
  name: '',
  who: '',
  goals: [],
  dreams: [],
  skills_and_abilities: '',
  current_situation: '',
  principles: '',
  successes: '',
  failures: '',
  action_history: '',
  ideas: [],
})

// ── Goal helpers ──
function addGoal() {
  form.value.goals.push({ id: uid(), title: '', description: '', target_date: null, children: [] })
}
function removeGoal(i) {
  form.value.goals.splice(i, 1)
}
function addSubGoal(gi) {
  if (!form.value.goals[gi].children) form.value.goals[gi].children = []
  form.value.goals[gi].children.push({ id: uid(), title: '', description: '', target_date: null, children: [] })
}
function removeSubGoal(gi, si) {
  form.value.goals[gi].children.splice(si, 1)
}

// ── Dream helpers ──
function addDream() {
  form.value.dreams.push({ id: uid(), title: '', description: '' })
}
function removeDream(i) {
  form.value.dreams.splice(i, 1)
}

// ── Idea helpers ──
function addIdea() {
  form.value.ideas.push({ id: uid(), title: '', description: '' })
}
function removeIdea(i) {
  form.value.ideas.splice(i, 1)
}

function showSnack(text, color = 'success') {
  snackText.value = text
  snackColor.value = color
  snackbar.value = true
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/creator')
    form.value.name = data.name || ''
    form.value.who = data.who || ''
    form.value.goals = Array.isArray(data.goals) ? data.goals : []
    form.value.dreams = Array.isArray(data.dreams) ? data.dreams : []
    form.value.skills_and_abilities = data.skills_and_abilities || ''
    form.value.current_situation = data.current_situation || ''
    form.value.principles = data.principles || ''
    form.value.successes = data.successes || ''
    form.value.failures = data.failures || ''
    form.value.action_history = data.action_history || ''
    form.value.ideas = Array.isArray(data.ideas) ? data.ideas : []
    // Ensure children arrays exist on goals
    form.value.goals.forEach(g => { if (!g.children) g.children = [] })
  } catch (e) {
    console.error('Failed to load creator profile:', e)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await api.put('/creator', form.value)
    showSnack('Profile saved')
  } catch (e) {
    showSnack('Failed to save: ' + (e.response?.data?.detail || e.message), 'error')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
