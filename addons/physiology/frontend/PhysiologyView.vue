<template>
  <v-container fluid class="pa-6">
    <!-- Header -->
    <v-row class="mb-4" align="center">
      <v-col>
        <div class="d-flex align-center ga-3">
          <v-icon size="32" color="teal">mdi-human</v-icon>
          <div>
            <h1 class="text-h4 font-weight-bold">Human Physiology</h1>
            <p class="text-subtitle-2 text-medium-emphasis mb-0">
              Lab results, hormone tracking &amp; medication simulation
            </p>
          </div>
        </div>
      </v-col>
      <v-col cols="auto">
        <v-chip variant="tonal" color="teal" class="mr-2">
          <v-icon start>mdi-flask</v-icon>
          {{ stats.lab_results || 0 }} results
        </v-chip>
        <v-chip variant="tonal" color="cyan">
          <v-icon start>mdi-pill</v-icon>
          {{ stats.simulations || 0 }} simulations
        </v-chip>
      </v-col>
    </v-row>

    <!-- Tabs -->
    <v-tabs v-model="tab" color="teal" class="mb-4">
      <v-tab value="profiles">
        <v-icon start>mdi-account-heart</v-icon> Profiles
      </v-tab>
      <v-tab value="lab">
        <v-icon start>mdi-flask-outline</v-icon> Lab Results
      </v-tab>
      <v-tab value="substances">
        <v-icon start>mdi-pill</v-icon> Substances
      </v-tab>
      <v-tab value="simulate">
        <v-icon start>mdi-chart-timeline-variant</v-icon> Simulate
      </v-tab>
      <v-tab value="reference">
        <v-icon start>mdi-book-open-variant</v-icon> Reference
      </v-tab>
      <v-tab value="settings">
        <v-icon start>mdi-cog</v-icon> Settings
      </v-tab>
    </v-tabs>

    <!-- ========== Profiles Tab ========== -->
    <div v-if="tab === 'profiles'">
      <v-row class="mb-4">
        <v-col>
          <v-btn color="teal" variant="flat" @click="showProfileDialog = true">
            <v-icon start>mdi-plus</v-icon> New Profile
          </v-btn>
        </v-col>
      </v-row>

      <v-row v-if="profiles.length === 0">
        <v-col cols="12">
          <v-card variant="outlined" class="text-center pa-8">
            <v-icon size="64" color="grey">mdi-account-plus</v-icon>
            <p class="text-h6 mt-4">No profiles yet</p>
            <p class="text-medium-emphasis">
              Create a health profile to start tracking lab results and running simulations.
            </p>
          </v-card>
        </v-col>
      </v-row>

      <v-row>
        <v-col v-for="p in profiles" :key="p._id" cols="12" md="6" lg="4">
          <v-card variant="outlined" class="fill-height">
            <v-card-title class="d-flex align-center">
              <v-icon start :color="p.gender === 'female' ? 'pink' : 'blue'">
                {{ p.gender === 'female' ? 'mdi-gender-female' : 'mdi-gender-male' }}
              </v-icon>
              {{ p.name }}
              <v-spacer />
              <v-btn icon size="x-small" variant="text" color="red" @click="deleteProfile(p._id)">
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </v-card-title>
            <v-card-text>
              <div class="d-flex ga-2 flex-wrap mb-2">
                <v-chip size="small" variant="tonal">Age: {{ p.age }}</v-chip>
                <v-chip v-if="p.weight_kg" size="small" variant="tonal">{{ p.weight_kg }} kg</v-chip>
                <v-chip v-if="p.height_cm" size="small" variant="tonal">{{ p.height_cm }} cm</v-chip>
              </div>
              <div v-if="p.current_medications?.length" class="mb-2">
                <span class="text-caption text-medium-emphasis">Medications:</span>
                <div class="d-flex ga-1 flex-wrap mt-1">
                  <v-chip v-for="m in p.current_medications" :key="m" size="x-small" variant="tonal" color="orange">
                    {{ m }}
                  </v-chip>
                </div>
              </div>
              <p v-if="p.notes" class="text-caption text-medium-emphasis">{{ p.notes }}</p>
            </v-card-text>
            <v-card-actions>
              <v-btn size="small" variant="tonal" color="teal" @click="selectProfile(p)">
                <v-icon start>mdi-flask</v-icon> Add Labs
              </v-btn>
              <v-btn size="small" variant="tonal" color="cyan" @click="simulateForProfile(p)">
                <v-icon start>mdi-chart-timeline-variant</v-icon> Simulate
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>

      <!-- Profile Dialog -->
      <v-dialog v-model="showProfileDialog" max-width="550">
        <v-card>
          <v-card-title>New Health Profile</v-card-title>
          <v-card-text>
            <v-text-field v-model="newProfile.name" label="Name" variant="outlined" class="mb-3" />
            <v-row>
              <v-col cols="6">
                <v-select v-model="newProfile.gender" :items="['male', 'female']" label="Gender" variant="outlined" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model.number="newProfile.age" label="Age" type="number" variant="outlined" />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="6">
                <v-text-field v-model.number="newProfile.weight_kg" label="Weight (kg)" type="number" variant="outlined" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model.number="newProfile.height_cm" label="Height (cm)" type="number" variant="outlined" />
              </v-col>
            </v-row>
            <v-combobox
              v-model="newProfile.current_medications"
              label="Current Medications"
              variant="outlined"
              multiple
              chips
              closable-chips
              class="mb-3"
            />
            <v-textarea v-model="newProfile.notes" label="Notes" variant="outlined" rows="2" />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="showProfileDialog = false">Cancel</v-btn>
            <v-btn color="teal" variant="flat" @click="createProfile">Create</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>

    <!-- ========== Lab Results Tab ========== -->
    <div v-if="tab === 'lab'">
      <v-row class="mb-4">
        <v-col cols="auto">
          <v-select
            v-model="selectedProfileId"
            :items="profiles"
            item-title="name"
            item-value="_id"
            label="Profile"
            variant="outlined"
            density="compact"
            style="min-width: 200px"
            clearable
          />
        </v-col>
        <v-col cols="auto">
          <v-btn color="teal" variant="flat" :disabled="!selectedProfileId" @click="showLabDialog = true">
            <v-icon start>mdi-plus</v-icon> Add Lab Results
          </v-btn>
        </v-col>
      </v-row>

      <v-card v-if="labResults.length === 0" variant="outlined" class="text-center pa-8">
        <v-icon size="64" color="grey">mdi-flask-empty-outline</v-icon>
        <p class="text-h6 mt-4">No lab results</p>
        <p class="text-medium-emphasis">Select a profile and add lab results to start tracking.</p>
      </v-card>

      <v-expansion-panels v-else variant="accordion">
        <v-expansion-panel v-for="lr in labResults" :key="lr._id">
          <v-expansion-panel-title>
            <div class="d-flex align-center ga-2 w-100">
              <v-icon size="small" color="teal">mdi-calendar</v-icon>
              <strong>{{ lr.test_date }}</strong>
              <span v-if="lr.lab_name" class="text-medium-emphasis">— {{ lr.lab_name }}</span>
              <v-spacer />
              <v-chip
                v-if="lr.flagged_count > 0"
                size="small"
                color="orange"
                variant="tonal"
              >
                {{ lr.flagged_count }} flagged
              </v-chip>
              <v-chip size="small" variant="tonal">{{ lr.values?.length || 0 }} markers</v-chip>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-table density="compact">
              <thead>
                <tr>
                  <th>Marker</th>
                  <th class="text-right">Value</th>
                  <th class="text-right">Reference</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="v in lr.values" :key="v.name">
                  <td>{{ v.name }}</td>
                  <td class="text-right font-weight-bold">
                    {{ v.value }} <span class="text-caption text-medium-emphasis">{{ v.unit }}</span>
                  </td>
                  <td class="text-right text-caption text-medium-emphasis">
                    {{ v.ref_low }} — {{ v.ref_high }}
                  </td>
                  <td>
                    <v-chip
                      :color="v.flag === 'normal' ? 'green' : v.flag === 'high' ? 'red' : 'orange'"
                      size="x-small"
                      variant="flat"
                    >
                      {{ v.flag || 'N/A' }}
                    </v-chip>
                  </td>
                </tr>
              </tbody>
            </v-table>
            <div class="text-right mt-2">
              <v-btn size="small" color="red" variant="text" @click="deleteLabResult(lr._id)">
                <v-icon start>mdi-delete</v-icon> Delete
              </v-btn>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Lab Entry Dialog -->
      <v-dialog v-model="showLabDialog" max-width="700" scrollable>
        <v-card>
          <v-card-title>Add Lab Results</v-card-title>
          <v-card-text style="max-height: 60vh">
            <v-row>
              <v-col cols="6">
                <v-text-field
                  v-model="newLab.test_date"
                  label="Test Date"
                  type="date"
                  variant="outlined"
                />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="newLab.lab_name" label="Lab Name" variant="outlined" />
              </v-col>
            </v-row>

            <h4 class="mb-2">Select markers and enter values:</h4>

            <v-text-field
              v-model="markerSearch"
              label="Search markers..."
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-magnify"
              clearable
              class="mb-2"
            />

            <div style="max-height: 300px; overflow-y: auto">
              <div v-for="ref in filteredRanges" :key="ref.name + (ref.gender || '')" class="d-flex align-center ga-2 mb-2">
                <v-checkbox
                  v-model="newLab.selected"
                  :value="ref.name"
                  density="compact"
                  hide-details
                  class="flex-grow-0"
                />
                <span class="text-body-2" style="min-width: 200px">
                  {{ ref.name }}
                  <span v-if="ref.gender" class="text-caption text-medium-emphasis">({{ ref.gender }})</span>
                </span>
                <v-text-field
                  v-if="newLab.selected.includes(ref.name)"
                  v-model.number="newLab.values[ref.name]"
                  :label="ref.unit"
                  type="number"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="max-width: 120px"
                />
                <span class="text-caption text-medium-emphasis">
                  {{ ref.low }} — {{ ref.high }} {{ ref.unit }}
                </span>
              </div>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="showLabDialog = false">Cancel</v-btn>
            <v-btn color="teal" variant="flat" @click="submitLabResults">Save</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>

    <!-- ========== Substances Tab ========== -->
    <div v-if="tab === 'substances'">
      <v-row class="mb-4" align="center">
        <v-col cols="auto">
          <v-select
            v-model="substanceFilter"
            :items="['all', 'hormone_therapy', 'medication', 'peptide_therapy', 'supplement', 'other']"
            label="Category"
            variant="outlined"
            density="compact"
            style="min-width: 200px"
          />
        </v-col>
        <v-col cols="auto">
          <v-btn color="teal" variant="flat" @click="showSubstanceDialog = true">
            <v-icon start>mdi-plus</v-icon> Add Substance
          </v-btn>
        </v-col>
      </v-row>

      <v-table density="compact">
        <thead>
          <tr>
            <th>Name</th>
            <th>Category</th>
            <th>Effects</th>
            <th width="50"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in filteredSubstances" :key="s._id">
            <td class="font-weight-medium">{{ s.name }}</td>
            <td>
              <v-chip :color="substanceCategoryColor(s.category)" size="x-small" variant="tonal">
                {{ s.category }}
              </v-chip>
            </td>
            <td>
              <div class="d-flex ga-1 flex-wrap">
                <v-chip
                  v-for="e in s.effects"
                  :key="e"
                  size="x-small"
                  :color="e.includes('↑') ? 'green' : e.includes('↓') ? 'red' : 'grey'"
                  variant="tonal"
                >{{ e }}</v-chip>
              </div>
            </td>
            <td>
              <v-btn icon size="x-small" variant="text" color="red" @click="deleteSubstance(s._id)">
                <v-icon size="small">mdi-delete</v-icon>
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>

      <!-- Add Substance Dialog -->
      <v-dialog v-model="showSubstanceDialog" max-width="500">
        <v-card>
          <v-card-title>Add Substance</v-card-title>
          <v-card-text>
            <v-text-field v-model="newSubstance.name" label="Name" variant="outlined" class="mb-3" />
            <v-select
              v-model="newSubstance.category"
              :items="['hormone_therapy', 'medication', 'peptide_therapy', 'supplement', 'other']"
              label="Category"
              variant="outlined"
              class="mb-3"
            />
            <v-combobox
              v-model="newSubstance.effects"
              label="Effects (e.g. testosterone↑, cortisol↓)"
              variant="outlined"
              multiple
              chips
              closable-chips
              class="mb-3"
            />
            <v-textarea v-model="newSubstance.description" label="Description" variant="outlined" rows="2" class="mb-3" />
            <v-text-field v-model="newSubstance.half_life" label="Half-life" variant="outlined" />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn @click="showSubstanceDialog = false">Cancel</v-btn>
            <v-btn color="teal" variant="flat" @click="createSubstance">Add</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>

    <!-- ========== Simulate Tab ========== -->
    <div v-if="tab === 'simulate'">
      <v-row>
        <v-col cols="12" md="5">
          <v-card variant="outlined">
            <v-card-title>
              <v-icon start color="cyan">mdi-chart-timeline-variant</v-icon>
              Medication Simulation
            </v-card-title>
            <v-card-text>
              <v-select
                v-model="simForm.profile_id"
                :items="profiles"
                item-title="name"
                item-value="_id"
                label="Profile"
                variant="outlined"
                clearable
                class="mb-3"
              />
              <v-autocomplete
                v-model="simForm.substance_name"
                :items="substances.map(s => s.name)"
                label="Substance"
                variant="outlined"
                class="mb-3"
              />
              <v-text-field
                v-model="simForm.dosage"
                label="Dosage (e.g. 200mg/week)"
                variant="outlined"
                class="mb-3"
              />
              <v-btn
                color="cyan"
                variant="flat"
                block
                :loading="simulating"
                @click="runSimulation"
              >
                <v-icon start>mdi-play</v-icon> Run Simulation
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="7">
          <v-card v-if="simulationResult" variant="outlined">
            <v-card-title>
              Simulation: {{ simulationResult.substance_name }}
              <span v-if="simulationResult.dosage" class="text-caption text-medium-emphasis ml-2">
                {{ simulationResult.dosage }}
              </span>
            </v-card-title>
            <v-card-text>
              <v-list density="compact">
                <v-list-item v-for="pred in simulationResult.predictions" :key="pred.marker">
                  <template #prepend>
                    <v-icon
                      :color="pred.direction === 'increase' ? 'green' : pred.direction === 'decrease' ? 'red' : 'grey'"
                      size="small"
                    >
                      {{ pred.direction === 'increase' ? 'mdi-arrow-up-bold' : pred.direction === 'decrease' ? 'mdi-arrow-down-bold' : 'mdi-swap-horizontal' }}
                    </v-icon>
                  </template>
                  <v-list-item-title>{{ pred.marker }}</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ pred.direction }} · {{ pred.confidence }} confidence
                    <span v-if="pred.current_value != null"> · Current: {{ pred.current_value }}</span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>

          <!-- Simulation History -->
          <v-card variant="outlined" class="mt-4">
            <v-card-title>Simulation History</v-card-title>
            <v-card-text v-if="simulations.length === 0" class="text-center">
              <p class="text-medium-emphasis">No simulations yet.</p>
            </v-card-text>
            <v-list v-else density="compact">
              <v-list-item
                v-for="sim in simulations.slice(0, 15)"
                :key="sim._id"
                @click="simulationResult = sim"
              >
                <v-list-item-title>
                  {{ sim.substance_name }}
                  <span v-if="sim.dosage" class="text-caption text-medium-emphasis">{{ sim.dosage }}</span>
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ sim.effects_count }} effects · {{ new Date(sim.created_at).toLocaleString() }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- ========== Reference Tab ========== -->
    <div v-if="tab === 'reference'">
      <v-row class="mb-4">
        <v-col cols="auto">
          <v-select
            v-model="refFilter"
            :items="['all', 'hormone', 'peptide', 'biochemistry', 'vitamin']"
            label="Category"
            variant="outlined"
            density="compact"
            style="min-width: 180px"
          />
        </v-col>
        <v-col cols="auto">
          <v-select
            v-model="refGender"
            :items="['all', 'male', 'female']"
            label="Gender"
            variant="outlined"
            density="compact"
            style="min-width: 140px"
          />
        </v-col>
      </v-row>

      <v-table density="compact">
        <thead>
          <tr>
            <th>Marker</th>
            <th>Category</th>
            <th class="text-right">Low</th>
            <th class="text-right">High</th>
            <th>Unit</th>
            <th>Gender</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in filteredRefRanges" :key="i">
            <td class="font-weight-medium">{{ r.name }}</td>
            <td>
              <v-chip :color="categoryColor(r.category)" size="x-small" variant="tonal">{{ r.category }}</v-chip>
            </td>
            <td class="text-right">{{ r.low }}</td>
            <td class="text-right">{{ r.high }}</td>
            <td class="text-caption">{{ r.unit }}</td>
            <td class="text-caption text-medium-emphasis">{{ r.gender || 'any' }}</td>
          </tr>
        </tbody>
      </v-table>
    </div>

    <!-- ========== Settings Tab ========== -->
    <div v-if="tab === 'settings'">
      <v-row>
        <v-col cols="12" md="8">
          <v-card variant="outlined">
            <v-card-title>
              <v-icon start>mdi-cog</v-icon> Physiology Settings
            </v-card-title>
            <v-card-text>
              <v-select
                v-model="settingsForm.physiology_default_model"
                :items="['auto', 'gpt-4', 'gpt-3.5-turbo', 'llama3', 'mistral']"
                label="Default LLM Model for Simulation"
                variant="outlined"
                class="mb-3"
              />
              <v-select
                v-model="settingsForm.physiology_units"
                :items="['SI', 'conventional']"
                label="Measurement Units"
                variant="outlined"
                class="mb-3"
              />
              <v-select
                v-model="settingsForm.physiology_age_group"
                :items="['child', 'adult', 'elderly']"
                label="Default Age Group"
                variant="outlined"
                class="mb-3"
              />
              <v-btn color="teal" variant="flat" @click="saveSettings">
                <v-icon start>mdi-content-save</v-icon> Save Settings
              </v-btn>
            </v-card-text>
          </v-card>

          <v-card variant="outlined" class="mt-4">
            <v-card-title class="text-red">
              <v-icon start color="red">mdi-alert</v-icon> Danger Zone
            </v-card-title>
            <v-card-text>
              <p class="text-body-2 mb-3">
                Clear all physiology data: profiles, lab results, substances, and simulations.
              </p>
              <v-btn color="red" variant="outlined" @click="clearAll">
                <v-icon start>mdi-delete-forever</v-icon> Clear All Data
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>
  </v-container>
</template>

<script>
import api from '@src/api'
import { useSettingsStore } from '@src/stores/settings'

const API = '/api/addons/physiology'

export default {
  name: 'PhysiologyView',

  data() {
    return {
      tab: localStorage.getItem('physiology_tab') || 'profiles',
      profiles: [],
      labResults: [],
      substances: [],
      simulations: [],
      referenceRanges: [],
      stats: {},
      selectedProfileId: null,
      simulationResult: null,
      simulating: false,

      // Filters
      substanceFilter: 'all',
      refFilter: 'all',
      refGender: 'all',
      markerSearch: '',

      // Dialogs
      showProfileDialog: false,
      showLabDialog: false,
      showSubstanceDialog: false,

      // Forms
      newProfile: { name: '', gender: 'male', age: 30, weight_kg: null, height_cm: null, notes: '', current_medications: [] },
      newLab: { test_date: new Date().toISOString().split('T')[0], lab_name: '', selected: [], values: {} },
      newSubstance: { name: '', category: 'supplement', effects: [], description: '', half_life: '' },
      simForm: { profile_id: null, substance_name: '', dosage: '' },

      // Settings
      settingsForm: {
        physiology_default_model: 'auto',
        physiology_units: 'SI',
        physiology_age_group: 'adult',
      },

      snackbar: { show: false, text: '', color: 'success' },
    }
  },

  computed: {
    filteredSubstances() {
      if (this.substanceFilter === 'all') return this.substances
      return this.substances.filter(s => s.category === this.substanceFilter)
    },

    filteredRefRanges() {
      let items = this.referenceRanges
      if (this.refFilter !== 'all') {
        items = items.filter(r => r.category === this.refFilter)
      }
      if (this.refGender !== 'all') {
        items = items.filter(r => !r.gender || r.gender === this.refGender)
      }
      return items
    },

    filteredRanges() {
      let items = this.referenceRanges
      if (this.markerSearch) {
        const q = this.markerSearch.toLowerCase()
        items = items.filter(r => r.name.toLowerCase().includes(q))
      }
      // Filter by profile gender
      const profile = this.profiles.find(p => p._id === this.selectedProfileId)
      if (profile) {
        items = items.filter(r => !r.gender || r.gender === profile.gender)
      }
      return items
    },
  },

  watch: {
    tab(v) { localStorage.setItem('physiology_tab', v) },
    selectedProfileId() { this.loadLabResults() },
  },

  async mounted() {
    await Promise.all([
      this.loadProfiles(),
      this.loadSubstances(),
      this.loadReferenceRanges(),
      this.loadSimulations(),
      this.loadStats(),
    ])
    this.loadSettings()
  },

  methods: {
    notify(text, color = 'success') {
      this.snackbar = { show: true, text, color }
    },

    // Profiles
    async loadProfiles() {
      try {
        const { data } = await api.get(`${API}/profiles`)
        this.profiles = data.items || []
      } catch (e) { console.error(e) }
    },

    async createProfile() {
      try {
        await api.post(`${API}/profiles`, this.newProfile)
        this.showProfileDialog = false
        this.newProfile = { name: '', gender: 'male', age: 30, weight_kg: null, height_cm: null, notes: '', current_medications: [] }
        this.notify('Profile created')
        await this.loadProfiles()
      } catch (e) { this.notify(e.response?.data?.detail || 'Failed', 'error') }
    },

    async deleteProfile(id) {
      if (!confirm('Delete this profile?')) return
      try {
        await api.delete(`${API}/profiles/${id}`)
        this.notify('Profile deleted')
        await this.loadProfiles()
      } catch (e) { this.notify('Delete failed', 'error') }
    },

    selectProfile(p) {
      this.selectedProfileId = p._id
      this.tab = 'lab'
    },

    simulateForProfile(p) {
      this.simForm.profile_id = p._id
      this.tab = 'simulate'
    },

    // Lab Results
    async loadLabResults() {
      try {
        const q = this.selectedProfileId ? `?profile_id=${this.selectedProfileId}` : ''
        const { data } = await api.get(`${API}/lab-results${q}`)
        this.labResults = data.items || []
      } catch (e) { console.error(e) }
    },

    async submitLabResults() {
      const values = []
      for (const name of this.newLab.selected) {
        if (this.newLab.values[name] != null) {
          values.push({ name, value: this.newLab.values[name] })
        }
      }
      if (values.length === 0) return this.notify('Select at least one marker', 'warning')

      try {
        await api.post(`${API}/lab-results`, {
          profile_id: this.selectedProfileId,
          test_date: this.newLab.test_date,
          lab_name: this.newLab.lab_name,
          values,
        })
        this.showLabDialog = false
        this.newLab = { test_date: new Date().toISOString().split('T')[0], lab_name: '', selected: [], values: {} }
        this.notify('Lab results saved')
        await Promise.all([this.loadLabResults(), this.loadStats()])
      } catch (e) { this.notify(e.response?.data?.detail || 'Failed', 'error') }
    },

    async deleteLabResult(id) {
      try {
        await api.delete(`${API}/lab-results/${id}`)
        this.notify('Lab result deleted')
        await Promise.all([this.loadLabResults(), this.loadStats()])
      } catch (e) { this.notify('Delete failed', 'error') }
    },

    // Substances
    async loadSubstances() {
      try {
        const { data } = await api.get(`${API}/substances`)
        this.substances = data.items || []
      } catch (e) { console.error(e) }
    },

    async createSubstance() {
      try {
        await api.post(`${API}/substances`, this.newSubstance)
        this.showSubstanceDialog = false
        this.newSubstance = { name: '', category: 'supplement', effects: [], description: '', half_life: '' }
        this.notify('Substance added')
        await this.loadSubstances()
      } catch (e) { this.notify(e.response?.data?.detail || 'Failed', 'error') }
    },

    async deleteSubstance(id) {
      try {
        await api.delete(`${API}/substances/${id}`)
        this.notify('Substance deleted')
        await this.loadSubstances()
      } catch (e) { this.notify('Delete failed', 'error') }
    },

    substanceCategoryColor(cat) {
      return { hormone_therapy: 'purple', medication: 'blue', peptide_therapy: 'teal', supplement: 'green', other: 'grey' }[cat] || 'grey'
    },

    // Reference Ranges
    async loadReferenceRanges() {
      try {
        const { data } = await api.get(`${API}/reference-ranges`)
        this.referenceRanges = data.items || []
      } catch (e) { console.error(e) }
    },

    categoryColor(cat) {
      return { hormone: 'purple', peptide: 'teal', biochemistry: 'blue', vitamin: 'orange' }[cat] || 'grey'
    },

    // Simulation
    async runSimulation() {
      if (!this.simForm.substance_name) return this.notify('Select a substance', 'warning')
      this.simulating = true
      try {
        const { data } = await api.post(`${API}/simulate`, this.simForm)
        this.simulationResult = data
        this.notify('Simulation completed')
        await this.loadSimulations()
      } catch (e) {
        this.notify(e.response?.data?.detail || 'Simulation failed', 'error')
      } finally { this.simulating = false }
    },

    async loadSimulations() {
      try {
        const q = this.simForm.profile_id ? `?profile_id=${this.simForm.profile_id}` : ''
        const { data } = await api.get(`${API}/simulations${q}`)
        this.simulations = data.items || []
      } catch (e) { console.error(e) }
    },

    // Stats
    async loadStats() {
      try {
        const { data } = await api.get(`${API}/stats`)
        this.stats = data
      } catch (e) { console.error(e) }
    },

    // Settings
    loadSettings() {
      const s = useSettingsStore()
      this.settingsForm.physiology_default_model = s.systemSettings?.physiology_default_model || 'auto'
      this.settingsForm.physiology_units = s.systemSettings?.physiology_units || 'SI'
      this.settingsForm.physiology_age_group = s.systemSettings?.physiology_age_group || 'adult'
    },

    async saveSettings() {
      const s = useSettingsStore()
      try {
        for (const [key, value] of Object.entries(this.settingsForm)) {
          await s.updateSystemSetting(key, value)
        }
        this.notify('Settings saved')
      } catch (e) { this.notify('Failed to save settings', 'error') }
    },

    async clearAll() {
      if (!confirm('Delete ALL physiology data?')) return
      try {
        await api.delete(`${API}/clear`)
        this.notify('All data cleared')
        await Promise.all([this.loadProfiles(), this.loadLabResults(), this.loadSubstances(), this.loadSimulations(), this.loadStats()])
      } catch (e) { this.notify('Clear failed', 'error') }
    },
  },
}
</script>
