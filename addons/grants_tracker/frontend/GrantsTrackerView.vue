<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-4">
      <v-icon size="32" color="amber-accent-3" class="mr-3">mdi-trophy-award</v-icon>
      <div class="text-h4 font-weight-bold">Grants Tracker</div>
      <v-spacer />
      <v-btn color="amber" variant="tonal" prepend-icon="mdi-refresh" @click="scrapeAll" :loading="scraping" class="mr-2">
        Scrape Grants
      </v-btn>
      <v-chip v-if="lastScrape" variant="tonal" color="grey" size="small">
        Last: {{ fmtDate(lastScrape) }}
      </v-chip>
    </div>

    <!-- Stats -->
    <div class="d-flex flex-wrap ga-2 mb-4" v-if="stats">
      <v-chip variant="tonal" color="amber" size="large">
        <v-icon start size="16">mdi-file-document-multiple</v-icon>
        Total: {{ stats.total || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="green" size="large">
        <v-icon start size="16">mdi-check-circle</v-icon>
        Open: {{ stats.open || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="red" size="large">
        <v-icon start size="16">mdi-clock-alert</v-icon>
        Deadlines (30d): {{ stats.upcoming_deadlines || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="blue" size="large">
        <v-icon start size="16">mdi-star</v-icon>
        Bookmarked: {{ stats.bookmarked || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="purple" size="large">
        <v-icon start size="16">mdi-link-variant</v-icon>
        Resources: {{ stats.resources || 0 }}
      </v-chip>
    </div>

    <!-- Tabs -->
    <v-tabs v-model="activeTab" color="amber-accent-3" class="mb-4" show-arrows>
      <v-tab value="browse">
        <v-icon start size="18">mdi-magnify</v-icon>
        Browse Grants
      </v-tab>
      <v-tab value="deadlines">
        <v-icon start size="18">mdi-calendar-clock</v-icon>
        Deadlines
      </v-tab>
      <v-tab value="bookmarked">
        <v-icon start size="18">mdi-star</v-icon>
        Bookmarked
      </v-tab>
      <v-tab value="resources">
        <v-icon start size="18">mdi-link-variant</v-icon>
        Resources
      </v-tab>
      <v-tab value="settings">
        <v-icon start size="18">mdi-cog-outline</v-icon>
        Settings
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">

      <!-- ═══════ BROWSE GRANTS ═══════ -->
      <v-window-item value="browse">
        <!-- Filters -->
        <v-card variant="outlined" class="pa-3 mb-4">
          <v-row dense>
            <v-col cols="12" sm="4">
              <v-text-field
                v-model="filters.keyword"
                label="Search"
                variant="outlined"
                density="compact"
                prepend-inner-icon="mdi-magnify"
                clearable
                hide-details
                @keyup.enter="loadGrants"
              />
            </v-col>
            <v-col cols="6" sm="2">
              <v-select
                v-model="filters.category"
                :items="categoryItems"
                label="Category"
                variant="outlined"
                density="compact"
                clearable
                hide-details
              />
            </v-col>
            <v-col cols="6" sm="2">
              <v-select
                v-model="filters.status"
                :items="[{title:'Open',value:'open'},{title:'Closed',value:'closed'}]"
                label="Status"
                variant="outlined"
                density="compact"
                clearable
                hide-details
              />
            </v-col>
            <v-col cols="6" sm="2">
              <v-text-field
                v-model.number="filters.min_amount"
                label="Min Amount ($)"
                variant="outlined"
                density="compact"
                type="number"
                hide-details
              />
            </v-col>
            <v-col cols="6" sm="2">
              <v-btn block color="amber" variant="tonal" @click="loadGrants" class="mt-1">Search</v-btn>
            </v-col>
          </v-row>
        </v-card>

        <v-progress-linear v-if="loadingGrants" indeterminate color="amber" class="mb-2" />

        <!-- Grants table -->
        <v-table v-if="grants.length > 0" density="compact" hover>
          <thead>
            <tr>
              <th style="width:30px"></th>
              <th>Title</th>
              <th>Agency</th>
              <th>Category</th>
              <th>Award</th>
              <th>Deadline</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="g in grants" :key="g._id" @click="selectedGrant = g; showDetail = true" style="cursor:pointer">
              <td>
                <v-icon
                  :color="g.bookmarked ? 'amber' : 'grey'"
                  size="18"
                  @click.stop="toggleBookmark(g)"
                >
                  {{ g.bookmarked ? 'mdi-star' : 'mdi-star-outline' }}
                </v-icon>
              </td>
              <td class="font-weight-medium" style="max-width:350px">
                <div class="text-truncate">{{ g.title || 'Untitled' }}</div>
                <div class="text-caption text-grey">{{ g.opportunity_number }}</div>
              </td>
              <td class="text-caption">{{ g.agency || '—' }}</td>
              <td>
                <v-chip v-if="g.category" size="x-small" variant="tonal" color="blue">{{ g.category }}</v-chip>
              </td>
              <td class="font-weight-bold text-green">
                {{ g.award_ceiling ? '$' + fmtNum(g.award_ceiling) : '—' }}
              </td>
              <td :class="isUrgent(g.close_date) ? 'text-red font-weight-bold' : 'text-caption'">
                {{ g.close_date ? fmtDate(g.close_date) : 'Open' }}
              </td>
              <td>
                <v-chip :color="g.status === 'open' ? 'green' : 'grey'" size="x-small" variant="tonal">
                  {{ g.status || 'unknown' }}
                </v-chip>
              </td>
              <td>
                <v-btn v-if="g.url" icon="mdi-open-in-new" size="x-small" variant="text" :href="g.url" target="_blank" @click.stop />
              </td>
            </tr>
          </tbody>
        </v-table>

        <v-card v-else-if="!loadingGrants" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-trophy-outline</v-icon>
          <div class="text-h6 mt-2 text-grey">No grants found</div>
          <div class="text-body-2 text-grey mb-3">Click "Scrape Grants" to fetch from grants.gov</div>
          <v-btn color="amber" variant="tonal" @click="scrapeAll">Scrape Now</v-btn>
        </v-card>
      </v-window-item>

      <!-- ═══════ DEADLINES ═══════ -->
      <v-window-item value="deadlines">
        <v-row dense class="mb-3">
          <v-col cols="auto">
            <v-btn-toggle v-model="deadlineDays" mandatory density="compact" variant="outlined" color="red">
              <v-btn :value="14" size="small">14 days</v-btn>
              <v-btn :value="30" size="small">30 days</v-btn>
              <v-btn :value="90" size="small">90 days</v-btn>
            </v-btn-toggle>
          </v-col>
        </v-row>

        <v-progress-linear v-if="loadingDeadlines" indeterminate color="red" class="mb-2" />

        <v-timeline v-if="deadlines.length > 0" density="compact" side="end">
          <v-timeline-item
            v-for="d in deadlines"
            :key="d._id"
            :dot-color="isUrgent(d.close_date) ? 'red' : 'amber'"
            size="small"
          >
            <template v-slot:opposite>
              <span class="text-caption" :class="isUrgent(d.close_date) ? 'text-red font-weight-bold' : ''">
                {{ fmtDate(d.close_date) }}
              </span>
            </template>
            <v-card variant="outlined" class="pa-3">
              <div class="d-flex align-center">
                <span class="text-subtitle-2 font-weight-bold">{{ d.title }}</span>
                <v-spacer />
                <v-chip v-if="d.award_ceiling" size="x-small" variant="tonal" color="green">
                  ${{ fmtNum(d.award_ceiling) }}
                </v-chip>
              </div>
              <div class="text-caption text-grey">{{ d.agency }} — {{ d.category }}</div>
              <div class="text-body-2 mt-1" style="max-height:60px;overflow:hidden">
                {{ (d.description || '').substring(0, 200) }}{{ (d.description || '').length > 200 ? '...' : '' }}
              </div>
              <v-btn v-if="d.url" :href="d.url" target="_blank" size="x-small" variant="text" color="amber" class="mt-1">
                View on grants.gov
              </v-btn>
            </v-card>
          </v-timeline-item>
        </v-timeline>

        <v-card v-else-if="!loadingDeadlines" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-calendar-check</v-icon>
          <div class="text-h6 mt-2 text-grey">No upcoming deadlines</div>
        </v-card>
      </v-window-item>

      <!-- ═══════ BOOKMARKED ═══════ -->
      <v-window-item value="bookmarked">
        <v-progress-linear v-if="loadingBookmarks" indeterminate color="amber" class="mb-2" />

        <v-row v-if="bookmarkedGrants.length > 0">
          <v-col v-for="g in bookmarkedGrants" :key="g._id" cols="12" sm="6" md="4">
            <v-card variant="outlined" class="pa-3 h-100">
              <div class="d-flex align-center mb-2">
                <v-icon color="amber" size="20" class="mr-2">mdi-star</v-icon>
                <span class="text-subtitle-2 font-weight-bold text-truncate" style="max-width:250px">{{ g.title }}</span>
                <v-spacer />
                <v-btn icon="mdi-star-off" size="x-small" variant="text" color="grey" @click="toggleBookmark(g)" />
              </div>
              <div class="text-caption text-grey mb-1">{{ g.agency }}</div>
              <v-chip v-if="g.category" size="x-small" variant="tonal" color="blue" class="mb-2">{{ g.category }}</v-chip>
              <div v-if="g.award_ceiling" class="text-h6 font-weight-bold text-green mb-1">${{ fmtNum(g.award_ceiling) }}</div>
              <div v-if="g.close_date" class="text-caption" :class="isUrgent(g.close_date) ? 'text-red' : 'text-grey'">
                Deadline: {{ fmtDate(g.close_date) }}
              </div>
              <div class="text-body-2 mt-2" style="max-height:80px;overflow:hidden">
                {{ (g.description || '').substring(0, 200) }}
              </div>
              <div class="d-flex ga-1 mt-2">
                <v-btn v-if="g.url" :href="g.url" target="_blank" size="small" variant="tonal" color="amber" prepend-icon="mdi-open-in-new">
                  Details
                </v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>

        <v-card v-else-if="!loadingBookmarks" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-star-outline</v-icon>
          <div class="text-h6 mt-2 text-grey">No bookmarked grants</div>
          <div class="text-body-2 text-grey">Click the star icon to bookmark grants</div>
        </v-card>
      </v-window-item>

      <!-- ═══════ RESOURCES ═══════ -->
      <v-window-item value="resources">
        <v-card variant="outlined" class="pa-4 mb-4" style="max-width:600px">
          <div class="text-h6 mb-3">Add Grant Resource</div>
          <v-text-field v-model="newResource.name" label="Resource Name" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newResource.url" label="URL" variant="outlined" density="compact" class="mb-2" />
          <v-select
            v-model="newResource.resource_type"
            :items="['website', 'api', 'newsletter', 'database', 'rss']"
            label="Type"
            variant="outlined"
            density="compact"
            class="mb-2"
          />
          <v-text-field v-model="newResource.description" label="Description" variant="outlined" density="compact" class="mb-2" />
          <v-btn color="amber" variant="tonal" prepend-icon="mdi-plus" @click="addResource" :disabled="!newResource.name">
            Add Resource
          </v-btn>
        </v-card>

        <div v-if="resources.length > 0">
          <v-card v-for="r in resources" :key="r._id" variant="outlined" class="pa-3 mb-2" style="max-width:600px">
            <div class="d-flex align-center">
              <v-icon color="purple" size="20" class="mr-2">mdi-link-variant</v-icon>
              <span class="font-weight-bold">{{ r.name }}</span>
              <v-chip size="x-small" variant="tonal" color="blue" class="ml-2">{{ r.resource_type }}</v-chip>
              <v-spacer />
              <v-btn icon="mdi-delete" size="x-small" variant="text" color="red" @click="deleteResource(r._id)" />
            </div>
            <div v-if="r.url" class="text-caption text-blue mt-1">
              <a :href="r.url" target="_blank">{{ r.url }}</a>
            </div>
            <div v-if="r.description" class="text-body-2 text-grey mt-1">{{ r.description }}</div>
          </v-card>
        </div>

        <v-card v-else variant="tonal" class="pa-8 text-center" style="max-width:600px">
          <v-icon size="48" color="grey">mdi-link-variant-off</v-icon>
          <div class="text-h6 mt-2 text-grey">No resources added</div>
          <div class="text-body-2 text-grey">Add grant databases, websites, RSS feeds to track</div>
        </v-card>
      </v-window-item>

      <!-- ═══════ SETTINGS ═══════ -->
      <v-window-item value="settings">
        <v-card variant="outlined" class="pa-4" style="max-width:650px">
          <div class="text-h6 mb-4">Grants Tracker Settings</div>

          <v-select
            v-model="settFreq"
            :items="[{title:'Every hour',value:'hourly'},{title:'Daily',value:'daily'},{title:'Weekly',value:'weekly'},{title:'Manual only',value:'manual'}]"
            label="Scrape Frequency"
            variant="outlined"
            density="compact"
            class="mb-3"
            @update:model-value="saveSetting('grants_scrape_frequency', $event)"
          />

          <v-text-field
            v-model="settKeywords"
            label="Keyword Filters (comma-separated)"
            variant="outlined"
            density="compact"
            hint="Filter grants by keywords, e.g.: AI, biotechnology, small business"
            persistent-hint
            class="mb-3"
            @blur="saveSetting('grants_keywords', settKeywords)"
          />

          <v-text-field
            v-model="settMinAmount"
            label="Minimum Award Amount ($)"
            variant="outlined"
            density="compact"
            type="number"
            class="mb-3"
            @blur="saveSetting('grants_min_amount', settMinAmount)"
          />

          <v-text-field
            v-model="settEligible"
            label="Eligible Applicant Types"
            variant="outlined"
            density="compact"
            hint="e.g.: small business, nonprofit, individual"
            persistent-hint
            class="mb-3"
            @blur="saveSetting('grants_eligible_types', settEligible)"
          />

          <v-textarea
            v-model="settSources"
            label="Additional Sources (one URL per line)"
            variant="outlined"
            density="compact"
            rows="3"
            class="mb-3"
            @blur="saveSetting('grants_sources', settSources)"
          />

          <v-card variant="tonal" class="pa-3 mb-4">
            <div class="text-subtitle-2 mb-2">Scrape Status</div>
            <div v-if="scrapeStatusData">
              <div v-for="(info, key) in scrapeStatusData" :key="key" class="text-body-2 mb-1">
                <strong>{{ key.replace(/_/g, ' ') }}:</strong>
                {{ info.last_scrape ? fmtDate(info.last_scrape) : 'Never' }}
                ({{ info.count }} items)
              </div>
            </div>
            <div v-else class="text-body-2 text-grey">No scrape data yet.</div>
          </v-card>

          <div class="d-flex ga-2">
            <v-btn color="amber" variant="tonal" prepend-icon="mdi-refresh" @click="scrapeAll" :loading="scraping">
              Scrape All Now
            </v-btn>
            <v-btn color="red" variant="tonal" prepend-icon="mdi-delete-outline" @click="confirmClear = true">
              Clear All Data
            </v-btn>
          </div>
        </v-card>

        <!-- Skills docs -->
        <v-card variant="outlined" class="pa-4 mt-4" style="max-width:650px">
          <div class="text-h6 mb-4">Available Skills</div>
          <v-card variant="tonal" class="pa-3 mb-3">
            <div class="d-flex align-center mb-2">
              <v-icon color="amber" size="20" class="mr-2">mdi-magnify</v-icon>
              <span class="text-subtitle-1 font-weight-bold">grants_search</span>
              <v-chip size="x-small" variant="outlined" color="amber" class="ml-2">grants</v-chip>
            </div>
            <div class="text-body-2 mb-2">Search grants by keyword, category, amount, and deadline.</div>
            <v-table density="compact" class="text-body-2">
              <thead><tr><th>Name</th><th>Type</th><th>Description</th></tr></thead>
              <tbody>
                <tr><td><code>query</code></td><td>string</td><td>Search text across grants</td></tr>
                <tr><td><code>category</code></td><td>string</td><td>Filter by grant category</td></tr>
                <tr><td><code>limit</code></td><td>integer</td><td>Max results (default: 20)</td></tr>
              </tbody>
            </v-table>
          </v-card>
          <v-alert type="info" variant="tonal" density="compact">
            Add <strong>grants_search</strong> to an agent's skill list to enable grant lookups.
          </v-alert>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Grant detail dialog -->
    <v-dialog v-model="showDetail" max-width="700">
      <v-card v-if="selectedGrant" class="pa-4">
        <v-card-title class="d-flex align-center">
          <v-icon color="amber" class="mr-2">mdi-trophy-award</v-icon>
          {{ selectedGrant.title }}
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" size="small" @click="showDetail = false" />
        </v-card-title>
        <v-card-text>
          <div class="d-flex flex-wrap ga-2 mb-3">
            <v-chip v-if="selectedGrant.category" variant="tonal" color="blue">{{ selectedGrant.category }}</v-chip>
            <v-chip v-if="selectedGrant.status" variant="tonal" :color="selectedGrant.status === 'open' ? 'green' : 'grey'">{{ selectedGrant.status }}</v-chip>
            <v-chip v-if="selectedGrant.opportunity_number" variant="outlined" size="small">{{ selectedGrant.opportunity_number }}</v-chip>
          </div>
          <div v-if="selectedGrant.agency" class="text-body-1 mb-2"><strong>Agency:</strong> {{ selectedGrant.agency }}</div>
          <div v-if="selectedGrant.award_ceiling" class="text-h5 font-weight-bold text-green mb-2">
            ${{ fmtNum(selectedGrant.award_floor || 0) }} — ${{ fmtNum(selectedGrant.award_ceiling) }}
          </div>
          <div v-if="selectedGrant.close_date" class="text-body-2 mb-2">
            <strong>Deadline:</strong>
            <span :class="isUrgent(selectedGrant.close_date) ? 'text-red font-weight-bold' : ''">
              {{ fmtDate(selectedGrant.close_date) }}
            </span>
          </div>
          <div v-if="selectedGrant.posted_date" class="text-caption text-grey mb-2">Posted: {{ fmtDate(selectedGrant.posted_date) }}</div>
          <v-divider class="mb-3" />
          <div class="text-body-2">{{ selectedGrant.description }}</div>
          <div v-if="selectedGrant.eligible_applicants" class="mt-3 text-body-2">
            <strong>Eligible Applicants:</strong> {{ selectedGrant.eligible_applicants }}
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn v-if="selectedGrant.url" :href="selectedGrant.url" target="_blank" color="amber" variant="tonal" prepend-icon="mdi-open-in-new">
            View on grants.gov
          </v-btn>
          <v-spacer />
          <v-btn variant="text" @click="showDetail = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Clear confirmation -->
    <v-dialog v-model="confirmClear" max-width="400">
      <v-card>
        <v-card-title>Clear All Grant Data?</v-card-title>
        <v-card-text>
          <v-text-field v-model="deleteConfirmText" label="Type DELETE to confirm" variant="outlined" density="compact" class="mt-3" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmClear = false">Cancel</v-btn>
          <v-btn color="red" variant="tonal" :disabled="deleteConfirmText !== 'DELETE'" @click="clearAllData">Clear All</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack" :color="snackColor" timeout="3000">{{ snackText }}</v-snackbar>
  </div>
</template>

<script>
import api from '@src/api'
import { useSettingsStore } from '@src/stores/settings'

const API = '/api/addons/grants_tracker'

export default {
  name: 'GrantsTrackerView',

  data() {
    return {
      activeTab: localStorage.getItem('grants_tab') || 'browse',
      stats: null,
      lastScrape: null,
      scraping: false,
      scrapeStatusData: null,

      // Browse
      filters: { keyword: '', category: '', status: '', min_amount: null },
      grants: [],
      loadingGrants: false,
      categoryItems: [],

      // Deadlines
      deadlines: [],
      deadlineDays: 30,
      loadingDeadlines: false,

      // Bookmarked
      bookmarkedGrants: [],
      loadingBookmarks: false,

      // Resources
      resources: [],
      newResource: { name: '', url: '', resource_type: 'website', description: '' },

      // Detail
      selectedGrant: null,
      showDetail: false,

      // Settings
      settFreq: 'daily',
      settKeywords: '',
      settMinAmount: '',
      settEligible: '',
      settSources: '',

      // Clear
      confirmClear: false,
      deleteConfirmText: '',

      // Snack
      snack: false,
      snackText: '',
      snackColor: 'success',
    }
  },

  watch: {
    activeTab(val) {
      localStorage.setItem('grants_tab', val)
      this.loadTabData(val)
    },
    deadlineDays() {
      this.loadDeadlines()
    },
  },

  async mounted() {
    this.loadSettings()
    this.loadStats()
    this.loadScrapeStatus()
    this.loadCategories()
    this.loadTabData(this.activeTab)
  },

  methods: {
    fmtDate(d) {
      if (!d) return ''
      try { return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) }
      catch { return d }
    },
    fmtNum(n) {
      if (n == null) return '0'
      return Number(n).toLocaleString('en-US')
    },
    notify(text, color = 'success') {
      this.snackText = text; this.snackColor = color; this.snack = true
    },
    isUrgent(dateStr) {
      if (!dateStr) return false
      const diff = new Date(dateStr) - new Date()
      return diff > 0 && diff < 14 * 86400000
    },

    loadTabData(tab) {
      switch (tab) {
        case 'browse': this.loadGrants(); break
        case 'deadlines': this.loadDeadlines(); break
        case 'bookmarked': this.loadBookmarks(); break
        case 'resources': this.loadResources(); break
        case 'settings': this.loadScrapeStatus(); break
      }
    },

    loadSettings() {
      const ss = useSettingsStore()
      const s = ss.systemSettings || {}
      this.settFreq = s.grants_scrape_frequency || 'daily'
      this.settKeywords = s.grants_keywords || ''
      this.settMinAmount = s.grants_min_amount || ''
      this.settEligible = s.grants_eligible_types || ''
      this.settSources = s.grants_sources || ''
    },
    async saveSetting(key, value) {
      try { const ss = useSettingsStore(); await ss.updateSystemSetting(key, value) }
      catch { this.notify('Failed to save setting', 'error') }
    },

    async loadStats() {
      try { const { data } = await api.get(`${API}/stats`); this.stats = data } catch {}
    },
    async loadScrapeStatus() {
      try {
        const { data } = await api.get(`${API}/scrape/status`)
        this.scrapeStatusData = data
        let latest = null
        for (const v of Object.values(data)) {
          if (v.last_scrape && (!latest || v.last_scrape > latest)) latest = v.last_scrape
        }
        this.lastScrape = latest
      } catch {}
    },
    async loadCategories() {
      try {
        const { data } = await api.get(`${API}/categories`)
        this.categoryItems = (data.items || []).map(c => ({ title: c, value: c }))
      } catch {}
    },

    async loadGrants() {
      this.loadingGrants = true
      try {
        const params = {}
        if (this.filters.keyword) params.keyword = this.filters.keyword
        if (this.filters.category) params.category = this.filters.category
        if (this.filters.status) params.status = this.filters.status
        if (this.filters.min_amount) params.min_amount = this.filters.min_amount
        const { data } = await api.get(`${API}/grants`, { params })
        this.grants = data.items || []
      } catch {} finally { this.loadingGrants = false }
    },

    async loadDeadlines() {
      this.loadingDeadlines = true
      try {
        const { data } = await api.get(`${API}/deadlines`, { params: { days: this.deadlineDays } })
        this.deadlines = data.items || []
      } catch {} finally { this.loadingDeadlines = false }
    },

    async loadBookmarks() {
      this.loadingBookmarks = true
      try {
        const { data } = await api.get(`${API}/grants`, { params: { bookmarked: true } })
        this.bookmarkedGrants = data.items || []
      } catch {} finally { this.loadingBookmarks = false }
    },

    async toggleBookmark(g) {
      try {
        await api.patch(`${API}/grants/${g._id}`, { bookmarked: !g.bookmarked })
        g.bookmarked = !g.bookmarked
        this.loadStats()
      } catch {}
    },

    async loadResources() {
      try {
        const { data } = await api.get(`${API}/resources`)
        this.resources = data.items || []
      } catch {}
    },
    async addResource() {
      try {
        await api.post(`${API}/resources`, this.newResource)
        this.notify('Resource added')
        this.newResource = { name: '', url: '', resource_type: 'website', description: '' }
        this.loadResources()
        this.loadStats()
      } catch { this.notify('Failed to add resource', 'error') }
    },
    async deleteResource(id) {
      try {
        await api.delete(`${API}/resources/${id}`)
        this.resources = this.resources.filter(r => r._id !== id)
        this.loadStats()
      } catch {}
    },

    async scrapeAll() {
      this.scraping = true
      try {
        const { data } = await api.post(`${API}/scrape-all`)
        const r = data.grants_gov || {}
        this.notify(`Scraped ${r.scraped || 0} new, updated ${r.updated || 0}`)
        this.loadStats()
        this.loadScrapeStatus()
        this.loadTabData(this.activeTab)
      } catch (e) {
        this.notify('Scrape failed: ' + (e.response?.data?.detail || e.message), 'error')
      } finally { this.scraping = false }
    },

    async clearAllData() {
      try {
        await api.delete(`${API}/clear`)
        this.notify('All data cleared')
        this.confirmClear = false; this.deleteConfirmText = ''
        this.loadStats()
        this.loadTabData(this.activeTab)
      } catch { this.notify('Clear failed', 'error') }
    },
  },
}
</script>

<style scoped>
</style>
