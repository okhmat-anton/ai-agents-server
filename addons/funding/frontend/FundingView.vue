<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-4">
      <v-icon size="32" color="green-accent-3" class="mr-3">mdi-currency-usd</v-icon>
      <div class="text-h4 font-weight-bold">Funding & Investors</div>
      <v-spacer />
      <v-btn color="green" variant="tonal" prepend-icon="mdi-database-import" @click="seedAll" :loading="seeding" class="mr-2">
        Seed Data
      </v-btn>
    </div>

    <!-- Stats -->
    <div class="d-flex flex-wrap ga-2 mb-4" v-if="stats">
      <v-chip variant="tonal" color="deep-purple" size="large">
        <v-icon start size="16">mdi-office-building</v-icon>
        VC Firms: {{ stats.vc_firms || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="blue" size="large">
        <v-icon start size="16">mdi-account-group</v-icon>
        Investors: {{ stats.investors || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="orange" size="large">
        <v-icon start size="16">mdi-store</v-icon>
        SMB Programs: {{ stats.smb_programs || 0 }}
      </v-chip>
    </div>

    <!-- Tabs -->
    <v-tabs v-model="activeTab" color="green-accent-3" class="mb-4" show-arrows>
      <v-tab value="vc">
        <v-icon start size="18">mdi-office-building</v-icon>
        VC & Accelerators
      </v-tab>
      <v-tab value="investors">
        <v-icon start size="18">mdi-account-group</v-icon>
        Investors
      </v-tab>
      <v-tab value="smb">
        <v-icon start size="18">mdi-store</v-icon>
        SMB Financing
      </v-tab>
      <v-tab value="settings">
        <v-icon start size="18">mdi-cog-outline</v-icon>
        Settings
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">

      <!-- ═══════ VC FIRMS ═══════ -->
      <v-window-item value="vc">
        <v-row dense class="mb-3">
          <v-col cols="12" sm="4">
            <v-text-field v-model="vcSearch" label="Search firms..." variant="outlined" density="compact" prepend-inner-icon="mdi-magnify" clearable hide-details @keyup.enter="loadVC" />
          </v-col>
          <v-col cols="6" sm="2">
            <v-select v-model="vcStageFilter" :items="stageOptions" label="Stage" variant="outlined" density="compact" clearable hide-details />
          </v-col>
          <v-col cols="6" sm="2">
            <v-select v-model="vcTypeFilter" :items="[{title:'VC',value:'vc'},{title:'Accelerator',value:'accelerator'}]" label="Type" variant="outlined" density="compact" clearable hide-details />
          </v-col>
          <v-col cols="auto">
            <v-btn color="green" variant="tonal" @click="loadVC" class="mt-1">Search</v-btn>
          </v-col>
          <v-spacer />
          <v-col cols="auto">
            <v-btn color="deep-purple" variant="tonal" size="small" prepend-icon="mdi-plus" @click="showAddVC = true">Add Firm</v-btn>
          </v-col>
        </v-row>

        <v-progress-linear v-if="loadingVC" indeterminate color="deep-purple" class="mb-2" />

        <v-row v-if="vcFirms.length > 0">
          <v-col v-for="f in vcFirms" :key="f._id" cols="12" sm="6" md="4" lg="3">
            <v-card variant="outlined" class="pa-3 h-100">
              <div class="d-flex align-center mb-2">
                <v-icon :color="f.type === 'accelerator' ? 'orange' : 'deep-purple'" size="20" class="mr-2">
                  {{ f.type === 'accelerator' ? 'mdi-rocket-launch' : 'mdi-office-building' }}
                </v-icon>
                <span class="text-subtitle-2 font-weight-bold text-truncate" style="max-width:200px">{{ f.name }}</span>
                <v-spacer />
                <v-btn v-if="f.website" icon="mdi-open-in-new" size="x-small" variant="text" :href="f.website" target="_blank" />
              </div>
              <v-chip size="x-small" variant="tonal" :color="f.type === 'accelerator' ? 'orange' : 'deep-purple'" class="mb-2">{{ f.type }}</v-chip>
              <v-chip v-if="f.aum" size="x-small" variant="outlined" class="ml-1 mb-2">${{ f.aum }}</v-chip>
              <div class="text-caption text-grey mb-1">{{ f.location }}</div>
              <div v-if="f.stages && f.stages.length" class="d-flex flex-wrap ga-1 mb-2">
                <v-chip v-for="s in f.stages" :key="s" size="x-small" variant="tonal" color="blue">{{ s }}</v-chip>
              </div>
              <div v-if="f.sectors && f.sectors.length" class="d-flex flex-wrap ga-1 mb-2">
                <v-chip v-for="s in f.sectors" :key="s" size="x-small" variant="tonal" color="green">{{ s }}</v-chip>
              </div>
              <div v-if="f.notable_investments" class="text-caption text-grey">
                <strong>Portfolio:</strong> {{ f.notable_investments }}
              </div>
              <div class="d-flex mt-2">
                <v-btn icon="mdi-delete" size="x-small" variant="text" color="red" @click="deleteVCFirm(f._id)" />
              </div>
            </v-card>
          </v-col>
        </v-row>

        <v-card v-else-if="!loadingVC" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-office-building-outline</v-icon>
          <div class="text-h6 mt-2 text-grey">No VC firms yet</div>
          <v-btn color="green" variant="tonal" class="mt-3" @click="seedAll">Seed Database</v-btn>
        </v-card>
      </v-window-item>

      <!-- ═══════ INVESTORS ═══════ -->
      <v-window-item value="investors">
        <v-row dense class="mb-3">
          <v-col cols="12" sm="4">
            <v-text-field v-model="invSearch" label="Search investors..." variant="outlined" density="compact" prepend-inner-icon="mdi-magnify" clearable hide-details @keyup.enter="loadInvestors" />
          </v-col>
          <v-col cols="6" sm="2">
            <v-select v-model="invTypeFilter" :items="[{title:'Angel',value:'angel'},{title:'Venture Partner',value:'venture_partner'},{title:'LP',value:'lp'},{title:'Family Office',value:'family_office'}]" label="Type" variant="outlined" density="compact" clearable hide-details />
          </v-col>
          <v-col cols="auto">
            <v-btn color="blue" variant="tonal" @click="loadInvestors">Search</v-btn>
          </v-col>
          <v-spacer />
          <v-col cols="auto">
            <v-btn color="blue" variant="tonal" size="small" prepend-icon="mdi-plus" @click="showAddInvestor = true">Add Investor</v-btn>
          </v-col>
        </v-row>

        <v-progress-linear v-if="loadingInv" indeterminate color="blue" class="mb-2" />

        <v-table v-if="investors.length > 0" density="compact" hover>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Firm</th>
              <th>Sectors</th>
              <th>Check Size</th>
              <th>Location</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in investors" :key="inv._id">
              <td class="font-weight-bold">
                {{ inv.name }}
                <div v-if="inv.title" class="text-caption text-grey">{{ inv.title }}</div>
              </td>
              <td><v-chip size="x-small" variant="tonal" color="blue">{{ inv.investor_type }}</v-chip></td>
              <td class="text-caption">{{ inv.firm || '—' }}</td>
              <td>
                <div class="d-flex flex-wrap ga-1">
                  <v-chip v-for="s in (inv.sectors || []).slice(0, 3)" :key="s" size="x-small" variant="tonal" color="green">{{ s }}</v-chip>
                </div>
              </td>
              <td class="text-caption">
                <span v-if="inv.check_size_min || inv.check_size_max">
                  ${{ fmtNum(inv.check_size_min || 0) }} — ${{ fmtNum(inv.check_size_max || 0) }}
                </span>
                <span v-else>—</span>
              </td>
              <td class="text-caption">{{ inv.location || '—' }}</td>
              <td>
                <v-btn v-if="inv.linkedin" icon="mdi-linkedin" size="x-small" variant="text" color="blue" :href="inv.linkedin" target="_blank" />
                <v-btn icon="mdi-delete" size="x-small" variant="text" color="red" @click="deleteInvestor(inv._id)" />
              </td>
            </tr>
          </tbody>
        </v-table>

        <v-card v-else-if="!loadingInv" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-account-search</v-icon>
          <div class="text-h6 mt-2 text-grey">No investors yet</div>
          <div class="text-body-2 text-grey">Click "Add Investor" to start building your network</div>
        </v-card>
      </v-window-item>

      <!-- ═══════ SMB FINANCING ═══════ -->
      <v-window-item value="smb">
        <div class="d-flex align-center mb-3">
          <v-text-field v-model="smbSearch" label="Search programs..." variant="outlined" density="compact" prepend-inner-icon="mdi-magnify" clearable hide-details style="max-width:300px" class="mr-3" />
          <v-btn-toggle v-model="smbTypeFilter" density="compact" variant="outlined" color="orange" class="mr-3">
            <v-btn value="" size="small">All</v-btn>
            <v-btn value="loan" size="small">Loans</v-btn>
            <v-btn value="grant" size="small">Grants</v-btn>
          </v-btn-toggle>
          <v-spacer />
          <v-btn color="orange" variant="tonal" size="small" prepend-icon="mdi-plus" @click="showAddSMB = true">Add Program</v-btn>
        </div>

        <v-progress-linear v-if="loadingSMB" indeterminate color="orange" class="mb-2" />

        <v-row v-if="filteredSMB.length > 0">
          <v-col v-for="p in filteredSMB" :key="p._id" cols="12" sm="6" md="4">
            <v-card variant="outlined" class="pa-3 h-100">
              <div class="d-flex align-center mb-2">
                <v-icon :color="p.type === 'grant' ? 'green' : 'orange'" size="20" class="mr-2">
                  {{ p.type === 'grant' ? 'mdi-gift' : 'mdi-bank' }}
                </v-icon>
                <span class="text-subtitle-2 font-weight-bold">{{ p.name }}</span>
              </div>
              <div class="d-flex ga-1 mb-2">
                <v-chip size="x-small" variant="tonal" :color="p.type === 'grant' ? 'green' : 'orange'">{{ p.type }}</v-chip>
                <v-chip v-if="p.agency" size="x-small" variant="outlined">{{ p.agency }}</v-chip>
              </div>
              <div v-if="p.max_amount" class="text-h6 font-weight-bold text-green mb-1">Up to ${{ fmtNum(p.max_amount) }}</div>
              <div class="text-body-2 mb-2" style="max-height:80px;overflow:hidden">{{ p.description }}</div>
              <div v-if="p.eligible" class="text-caption text-grey mb-1"><strong>Eligible:</strong> {{ p.eligible }}</div>
              <div class="d-flex ga-1 mt-2">
                <v-btn v-if="p.url" :href="p.url" target="_blank" size="small" variant="tonal" color="blue" prepend-icon="mdi-open-in-new">Details</v-btn>
                <v-spacer />
                <v-btn icon="mdi-delete" size="x-small" variant="text" color="red" @click="deleteSMB(p._id)" />
              </div>
            </v-card>
          </v-col>
        </v-row>

        <v-card v-else-if="!loadingSMB" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-store-outline</v-icon>
          <div class="text-h6 mt-2 text-grey">No SMB programs yet</div>
          <v-btn color="green" variant="tonal" class="mt-3" @click="seedAll">Seed Database</v-btn>
        </v-card>
      </v-window-item>

      <!-- ═══════ SETTINGS ═══════ -->
      <v-window-item value="settings">
        <v-card variant="outlined" class="pa-4" style="max-width:650px">
          <div class="text-h6 mb-4">Funding Settings</div>

          <v-select
            v-model="settFreq"
            :items="[{title:'Daily',value:'daily'},{title:'Weekly',value:'weekly'},{title:'Monthly',value:'monthly'},{title:'Manual only',value:'manual'}]"
            label="Scrape Frequency"
            variant="outlined"
            density="compact"
            class="mb-3"
            @update:model-value="saveSetting('funding_scrape_frequency', $event)"
          />

          <v-text-field
            v-model="settSectors"
            label="Focus Sectors (comma-separated)"
            variant="outlined"
            density="compact"
            hint="e.g.: AI, Fintech, Healthcare, SaaS"
            persistent-hint
            class="mb-3"
            @blur="saveSetting('funding_focus_sectors', settSectors)"
          />

          <v-text-field
            v-model="settStages"
            label="Investment Stages"
            variant="outlined"
            density="compact"
            hint="e.g.: Seed, Series A, Growth"
            persistent-hint
            class="mb-3"
            @blur="saveSetting('funding_focus_stages', settStages)"
          />

          <v-text-field
            v-model="settCrunchbaseKey"
            label="Crunchbase API Key (optional)"
            variant="outlined"
            density="compact"
            class="mb-3"
            @blur="saveSetting('funding_crunchbase_key', settCrunchbaseKey)"
          />

          <div class="d-flex ga-2">
            <v-btn color="green" variant="tonal" prepend-icon="mdi-database-import" @click="seedAll" :loading="seeding">Seed All</v-btn>
            <v-btn color="red" variant="tonal" prepend-icon="mdi-delete-outline" @click="confirmClear = true">Clear All Data</v-btn>
          </div>
        </v-card>

        <v-card variant="outlined" class="pa-4 mt-4" style="max-width:650px">
          <div class="text-h6 mb-4">Available Skills</div>
          <v-card variant="tonal" class="pa-3 mb-3">
            <div class="d-flex align-center mb-2">
              <v-icon color="green" size="20" class="mr-2">mdi-magnify</v-icon>
              <span class="text-subtitle-1 font-weight-bold">funding_search</span>
            </div>
            <div class="text-body-2">Search VC firms, investors, and SMB financing programs.</div>
          </v-card>
          <v-alert type="info" variant="tonal" density="compact">
            Add <strong>funding_search</strong> to an agent's skill list.
          </v-alert>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Add VC dialog -->
    <v-dialog v-model="showAddVC" max-width="500">
      <v-card class="pa-4">
        <v-card-title>Add VC Firm</v-card-title>
        <v-card-text>
          <v-text-field v-model="newVC.name" label="Firm Name" variant="outlined" density="compact" class="mb-2" />
          <v-select v-model="newVC.type" :items="['vc','accelerator']" label="Type" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newVC.location" label="Location" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newVC.website" label="Website" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newVC.aum" label="AUM" variant="outlined" density="compact" class="mb-2" />
          <v-combobox v-model="newVC.stages" :items="stageOptions.map(s=>s.value)" label="Stages" variant="outlined" density="compact" multiple chips class="mb-2" />
          <v-text-field v-model="newVC.notable_investments" label="Notable Investments" variant="outlined" density="compact" />
        </v-card-text>
        <v-card-actions>
          <v-spacer /><v-btn variant="text" @click="showAddVC = false">Cancel</v-btn>
          <v-btn color="green" variant="tonal" @click="addVCFirm" :disabled="!newVC.name">Add</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Investor dialog -->
    <v-dialog v-model="showAddInvestor" max-width="500">
      <v-card class="pa-4">
        <v-card-title>Add Investor</v-card-title>
        <v-card-text>
          <v-text-field v-model="newInv.name" label="Name" variant="outlined" density="compact" class="mb-2" />
          <v-select v-model="newInv.investor_type" :items="['angel','venture_partner','lp','family_office']" label="Type" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newInv.firm" label="Firm" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newInv.title" label="Title" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newInv.location" label="Location" variant="outlined" density="compact" class="mb-2" />
          <v-row dense class="mb-2">
            <v-col><v-text-field v-model.number="newInv.check_size_min" label="Min Check ($)" variant="outlined" density="compact" type="number" /></v-col>
            <v-col><v-text-field v-model.number="newInv.check_size_max" label="Max Check ($)" variant="outlined" density="compact" type="number" /></v-col>
          </v-row>
          <v-text-field v-model="newInv.linkedin" label="LinkedIn URL" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model="newInv.email" label="Email" variant="outlined" density="compact" />
        </v-card-text>
        <v-card-actions>
          <v-spacer /><v-btn variant="text" @click="showAddInvestor = false">Cancel</v-btn>
          <v-btn color="blue" variant="tonal" @click="addInvestor" :disabled="!newInv.name">Add</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add SMB dialog -->
    <v-dialog v-model="showAddSMB" max-width="500">
      <v-card class="pa-4">
        <v-card-title>Add SMB Program</v-card-title>
        <v-card-text>
          <v-text-field v-model="newSMB.name" label="Program Name" variant="outlined" density="compact" class="mb-2" />
          <v-select v-model="newSMB.type" :items="['loan','grant','equity','other']" label="Type" variant="outlined" density="compact" class="mb-2" />
          <v-text-field v-model.number="newSMB.max_amount" label="Max Amount ($)" variant="outlined" density="compact" type="number" class="mb-2" />
          <v-text-field v-model="newSMB.agency" label="Agency" variant="outlined" density="compact" class="mb-2" />
          <v-textarea v-model="newSMB.description" label="Description" variant="outlined" density="compact" rows="2" class="mb-2" />
          <v-text-field v-model="newSMB.url" label="URL" variant="outlined" density="compact" />
        </v-card-text>
        <v-card-actions>
          <v-spacer /><v-btn variant="text" @click="showAddSMB = false">Cancel</v-btn>
          <v-btn color="orange" variant="tonal" @click="addSMBProgram" :disabled="!newSMB.name">Add</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Clear dialog -->
    <v-dialog v-model="confirmClear" max-width="400">
      <v-card>
        <v-card-title>Clear All Funding Data?</v-card-title>
        <v-card-text>
          <v-text-field v-model="deleteConfirmText" label="Type DELETE to confirm" variant="outlined" density="compact" class="mt-3" />
        </v-card-text>
        <v-card-actions>
          <v-spacer /><v-btn variant="text" @click="confirmClear = false">Cancel</v-btn>
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

const API = '/api/addons/funding'

export default {
  name: 'FundingView',

  data() {
    return {
      activeTab: localStorage.getItem('funding_tab') || 'vc',
      stats: null,
      seeding: false,

      // VC
      vcFirms: [],
      loadingVC: false,
      vcSearch: '',
      vcStageFilter: null,
      vcTypeFilter: null,
      showAddVC: false,
      newVC: { name: '', type: 'vc', location: '', website: '', aum: '', stages: [], notable_investments: '' },

      stageOptions: [
        { title: 'Pre-Seed', value: 'Pre-Seed' },
        { title: 'Seed', value: 'Seed' },
        { title: 'Series A', value: 'Series A' },
        { title: 'Series B', value: 'Series B' },
        { title: 'Growth', value: 'Growth' },
        { title: 'Late Stage', value: 'Late Stage' },
      ],

      // Investors
      investors: [],
      loadingInv: false,
      invSearch: '',
      invTypeFilter: null,
      showAddInvestor: false,
      newInv: { name: '', investor_type: 'angel', firm: '', title: '', location: '', check_size_min: null, check_size_max: null, linkedin: '', email: '' },

      // SMB
      smbPrograms: [],
      loadingSMB: false,
      smbSearch: '',
      smbTypeFilter: '',
      showAddSMB: false,
      newSMB: { name: '', type: 'loan', max_amount: null, agency: '', description: '', url: '' },

      // Settings
      settFreq: 'weekly',
      settSectors: '',
      settStages: '',
      settCrunchbaseKey: '',

      confirmClear: false,
      deleteConfirmText: '',
      snack: false,
      snackText: '',
      snackColor: 'success',
    }
  },

  computed: {
    filteredSMB() {
      let items = this.smbPrograms
      if (this.smbTypeFilter) {
        items = items.filter(p => p.type === this.smbTypeFilter)
      }
      if (this.smbSearch) {
        const q = this.smbSearch.toLowerCase()
        items = items.filter(p =>
          (p.name || '').toLowerCase().includes(q) ||
          (p.description || '').toLowerCase().includes(q) ||
          (p.agency || '').toLowerCase().includes(q)
        )
      }
      return items
    },
  },

  watch: {
    activeTab(val) {
      localStorage.setItem('funding_tab', val)
      this.loadTabData(val)
    },
  },

  async mounted() {
    this.loadSettings()
    this.loadStats()
    this.loadTabData(this.activeTab)
  },

  methods: {
    fmtNum(n) { return n != null ? Number(n).toLocaleString('en-US') : '0' },
    notify(text, color = 'success') { this.snackText = text; this.snackColor = color; this.snack = true },

    loadTabData(tab) {
      switch (tab) {
        case 'vc': this.loadVC(); break
        case 'investors': this.loadInvestors(); break
        case 'smb': this.loadSMB(); break
      }
    },

    loadSettings() {
      const ss = useSettingsStore()
      const s = ss.systemSettings || {}
      this.settFreq = s.funding_scrape_frequency || 'weekly'
      this.settSectors = s.funding_focus_sectors || ''
      this.settStages = s.funding_focus_stages || ''
      this.settCrunchbaseKey = s.funding_crunchbase_key || ''
    },
    async saveSetting(key, value) {
      try { const ss = useSettingsStore(); await ss.updateSystemSetting(key, value) }
      catch { this.notify('Failed to save', 'error') }
    },

    async loadStats() {
      try { const { data } = await api.get(`${API}/stats`); this.stats = data } catch {}
    },

    // VC
    async loadVC() {
      this.loadingVC = true
      try {
        const params = {}
        if (this.vcSearch) params.search = this.vcSearch
        if (this.vcStageFilter) params.stage = this.vcStageFilter
        if (this.vcTypeFilter) params.firm_type = this.vcTypeFilter
        const { data } = await api.get(`${API}/vc`, { params })
        this.vcFirms = data.items || []
      } catch {} finally { this.loadingVC = false }
    },
    async addVCFirm() {
      try {
        await api.post(`${API}/vc`, this.newVC)
        this.notify('Firm added')
        this.showAddVC = false
        this.newVC = { name: '', type: 'vc', location: '', website: '', aum: '', stages: [], notable_investments: '' }
        this.loadVC(); this.loadStats()
      } catch { this.notify('Failed', 'error') }
    },
    async deleteVCFirm(id) {
      try { await api.delete(`${API}/vc/${id}`); this.vcFirms = this.vcFirms.filter(f => f._id !== id); this.loadStats() } catch {}
    },

    // Investors
    async loadInvestors() {
      this.loadingInv = true
      try {
        const params = {}
        if (this.invSearch) params.search = this.invSearch
        if (this.invTypeFilter) params.investor_type = this.invTypeFilter
        const { data } = await api.get(`${API}/investors`, { params })
        this.investors = data.items || []
      } catch {} finally { this.loadingInv = false }
    },
    async addInvestor() {
      try {
        await api.post(`${API}/investors`, this.newInv)
        this.notify('Investor added')
        this.showAddInvestor = false
        this.newInv = { name: '', investor_type: 'angel', firm: '', title: '', location: '', check_size_min: null, check_size_max: null, linkedin: '', email: '' }
        this.loadInvestors(); this.loadStats()
      } catch { this.notify('Failed', 'error') }
    },
    async deleteInvestor(id) {
      try { await api.delete(`${API}/investors/${id}`); this.investors = this.investors.filter(i => i._id !== id); this.loadStats() } catch {}
    },

    // SMB
    async loadSMB() {
      this.loadingSMB = true
      try {
        const { data } = await api.get(`${API}/smb`)
        this.smbPrograms = data.items || []
      } catch {} finally { this.loadingSMB = false }
    },
    async addSMBProgram() {
      try {
        await api.post(`${API}/smb`, this.newSMB)
        this.notify('Program added')
        this.showAddSMB = false
        this.newSMB = { name: '', type: 'loan', max_amount: null, agency: '', description: '', url: '' }
        this.loadSMB(); this.loadStats()
      } catch { this.notify('Failed', 'error') }
    },
    async deleteSMB(id) {
      try { await api.delete(`${API}/smb/${id}`); this.smbPrograms = this.smbPrograms.filter(p => p._id !== id); this.loadStats() } catch {}
    },

    // Seed & Clear
    async seedAll() {
      this.seeding = true
      try {
        const { data } = await api.post(`${API}/scrape-all`)
        const vc = data.vc?.seeded || 0
        const smb = data.smb?.seeded || 0
        this.notify(`Seeded ${vc} VC firms, ${smb} SMB programs`)
        this.loadStats()
        this.loadTabData(this.activeTab)
      } catch (e) {
        this.notify('Seed failed: ' + (e.response?.data?.detail || e.message), 'error')
      } finally { this.seeding = false }
    },
    async clearAllData() {
      try {
        await api.delete(`${API}/clear`)
        this.notify('All data cleared')
        this.confirmClear = false; this.deleteConfirmText = ''
        this.loadStats(); this.loadTabData(this.activeTab)
      } catch { this.notify('Clear failed', 'error') }
    },
  },
}
</script>

<style scoped>
</style>
