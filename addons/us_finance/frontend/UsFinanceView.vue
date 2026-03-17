<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-4">
      <v-icon size="32" color="green-accent-3" class="mr-3">mdi-finance</v-icon>
      <div class="text-h4 font-weight-bold">US & Canada Finance</div>
      <v-spacer />
      <v-btn
        color="green"
        variant="tonal"
        prepend-icon="mdi-refresh"
        @click="scrapeAll"
        :loading="scraping"
        class="mr-2"
      >
        Scrape All
      </v-btn>
      <v-chip v-if="lastScrape" variant="tonal" color="grey" size="small">
        Last: {{ fmtDate(lastScrape) }}
      </v-chip>
    </div>

    <!-- Stats chips -->
    <div class="d-flex flex-wrap ga-2 mb-4" v-if="stats">
      <v-chip variant="tonal" color="blue" size="large">
        <v-icon start size="16">mdi-newspaper</v-icon>
        News: {{ stats.news || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="green" size="large">
        <v-icon start size="16">mdi-home-city</v-icon>
        Real Estate: {{ stats.real_estate || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="orange" size="large">
        <v-icon start size="16">mdi-file-document-check</v-icon>
        Valuations: {{ stats.valuations || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="deep-purple" size="large">
        <v-icon start size="16">mdi-gavel</v-icon>
        Auctions: {{ stats.auction_items || 0 }}
        <v-badge v-if="stats.matched_auctions > 0" :content="stats.matched_auctions" color="red" floating inline />
      </v-chip>
      <v-chip variant="tonal" color="brown" size="large">
        <v-icon start size="16">mdi-oil</v-icon>
        Oil: {{ stats.oil || 0 }}
      </v-chip>
      <v-chip variant="tonal" color="cyan" size="large">
        <v-icon start size="16">mdi-flag</v-icon>
        Programs: {{ stats.programs || 0 }}
      </v-chip>
    </div>

    <!-- Tabs -->
    <v-tabs v-model="activeTab" color="green-accent-3" class="mb-4" show-arrows>
      <v-tab value="news">
        <v-icon start size="18">mdi-newspaper-variant-outline</v-icon>
        Financial News
      </v-tab>
      <v-tab value="real_estate">
        <v-icon start size="18">mdi-home-city-outline</v-icon>
        Real Estate
      </v-tab>
      <v-tab value="valuation">
        <v-icon start size="18">mdi-calculator-variant-outline</v-icon>
        Property Valuation
      </v-tab>
      <v-tab value="property_search">
        <v-icon start size="18">mdi-magnify</v-icon>
        Property Search
      </v-tab>
      <v-tab value="oil">
        <v-icon start size="18">mdi-oil</v-icon>
        Oil & Energy
      </v-tab>
      <v-tab value="taxation">
        <v-icon start size="18">mdi-receipt-text-outline</v-icon>
        Taxation
      </v-tab>
      <v-tab value="programs">
        <v-icon start size="18">mdi-flag-outline</v-icon>
        Programs
      </v-tab>
      <v-tab value="settings">
        <v-icon start size="18">mdi-cog-outline</v-icon>
        Settings
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">

      <!-- ═══════════════════════════════════════ -->
      <!-- 1. FINANCIAL NEWS -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="news">
        <div class="d-flex align-center mb-3">
          <v-btn-toggle v-model="newsSource" mandatory density="compact" variant="outlined" color="blue" class="mr-3">
            <v-btn value="fred" size="small">FRED</v-btn>
            <v-btn value="bls" size="small">BLS</v-btn>
          </v-btn-toggle>
          <v-btn
            color="blue"
            variant="tonal"
            size="small"
            prepend-icon="mdi-download"
            @click="scrapeNews"
            :loading="scrapingNews"
          >
            Scrape {{ newsSource.toUpperCase() }}
          </v-btn>
        </div>

        <v-progress-linear v-if="loadingNews" indeterminate color="blue" class="mb-2" />

        <v-row v-if="newsItems.length > 0">
          <v-col
            v-for="item in newsItems"
            :key="item.series_id"
            cols="12"
            sm="6"
            md="4"
            lg="3"
          >
            <v-card variant="outlined" class="pa-3 h-100">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">{{ item.label }}</div>
              <div class="text-h5 font-weight-bold mb-1">
                {{ item.latest_value }}
                <span class="text-caption text-grey">{{ item.unit }}</span>
              </div>
              <div class="text-caption text-grey mb-2">as of {{ item.latest_date }}</div>

              <!-- Mini trend (simple text-based) -->
              <div v-if="item.history && item.history.length > 1" class="d-flex align-center ga-1">
                <v-icon
                  :color="trendColor(item.history)"
                  size="16"
                >
                  {{ trendIcon(item.history) }}
                </v-icon>
                <span class="text-caption" :class="`text-${trendColor(item.history)}`">
                  {{ trendText(item.history) }}
                </span>
              </div>

              <!-- Sparkline with history values -->
              <div v-if="sparklineData(item.history).length > 1" class="mt-2">
                <v-sparkline
                  :model-value="sparklineData(item.history)"
                  :gradient="['#1B5E20', '#4CAF50', '#81C784']"
                  :line-width="2"
                  :padding="4"
                  height="40"
                  smooth
                  auto-draw
                />
              </div>
            </v-card>
          </v-col>
        </v-row>

        <v-card v-else-if="!loadingNews" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-newspaper-remove</v-icon>
          <div class="text-h6 mt-2 text-grey">No economic data yet</div>
          <div class="text-body-2 text-grey mb-3">Click "Scrape" to fetch latest economic indicators</div>
          <v-btn color="blue" variant="tonal" @click="scrapeNews">Scrape Now</v-btn>
        </v-card>
      </v-window-item>

      <!-- ═══════════════════════════════════════ -->
      <!-- 2. REAL ESTATE -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="real_estate">
        <div class="d-flex align-center mb-3">
          <v-btn
            color="green"
            variant="tonal"
            size="small"
            prepend-icon="mdi-download"
            @click="scrapeRealEstate"
            :loading="scrapingRE"
          >
            Scrape Real Estate Data
          </v-btn>
        </div>

        <v-progress-linear v-if="loadingRE" indeterminate color="green" class="mb-2" />

        <v-row v-if="realEstateItems.length > 0">
          <v-col
            v-for="item in realEstateItems"
            :key="item.series_id"
            cols="12"
            sm="6"
            md="4"
          >
            <v-card variant="outlined" class="pa-3 h-100">
              <div class="text-subtitle-2 text-medium-emphasis mb-1">{{ item.label }}</div>
              <div class="text-h5 font-weight-bold mb-1">{{ item.latest_value }}</div>
              <div class="text-caption text-grey mb-2">as of {{ item.latest_date }}</div>

              <div v-if="item.history && item.history.length > 1" class="d-flex align-center ga-1 mb-2">
                <v-icon :color="trendColor(item.history)" size="16">{{ trendIcon(item.history) }}</v-icon>
                <span class="text-caption" :class="`text-${trendColor(item.history)}`">{{ trendText(item.history) }}</span>
              </div>

              <div v-if="sparklineData(item.history).length > 1" class="mt-1">
                <v-sparkline
                  :model-value="sparklineData(item.history)"
                  :gradient="['#1B5E20', '#4CAF50', '#81C784']"
                  :line-width="2"
                  :padding="4"
                  height="50"
                  smooth
                  auto-draw
                />
              </div>
            </v-card>
          </v-col>
        </v-row>

        <v-card v-else-if="!loadingRE" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-home-remove</v-icon>
          <div class="text-h6 mt-2 text-grey">No real estate data yet</div>
          <v-btn color="green" variant="tonal" class="mt-3" @click="scrapeRealEstate">Scrape Now</v-btn>
        </v-card>
      </v-window-item>

      <!-- ═══════════════════════════════════════ -->
      <!-- 3. PROPERTY VALUATION -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="valuation">
        <v-row>
          <!-- Left: form -->
          <v-col cols="12" md="5">
            <v-card variant="outlined" class="pa-4">
              <div class="text-h6 mb-3">Property Valuation</div>

              <v-text-field
                v-model="valForm.address"
                label="Property Address"
                variant="outlined"
                density="compact"
                prepend-inner-icon="mdi-map-marker"
                placeholder="123 Main St, City, State ZIP"
                class="mb-2"
              />

              <v-row dense>
                <v-col cols="4">
                  <v-text-field
                    v-model.number="valForm.bedrooms"
                    label="Bedrooms"
                    variant="outlined"
                    density="compact"
                    type="number"
                    min="0"
                  />
                </v-col>
                <v-col cols="4">
                  <v-text-field
                    v-model.number="valForm.bathrooms"
                    label="Bathrooms"
                    variant="outlined"
                    density="compact"
                    type="number"
                    min="0"
                  />
                </v-col>
                <v-col cols="4">
                  <v-text-field
                    v-model.number="valForm.floors"
                    label="Floors"
                    variant="outlined"
                    density="compact"
                    type="number"
                    min="1"
                  />
                </v-col>
              </v-row>

              <v-row dense>
                <v-col cols="6">
                  <v-text-field
                    v-model.number="valForm.year_built"
                    label="Year Built"
                    variant="outlined"
                    density="compact"
                    type="number"
                  />
                </v-col>
                <v-col cols="6">
                  <v-text-field
                    v-model.number="valForm.lot_size_sqft"
                    label="Lot Size (sqft)"
                    variant="outlined"
                    density="compact"
                    type="number"
                  />
                </v-col>
              </v-row>

              <v-select
                v-model="valForm.condition"
                :items="conditionOptions"
                label="Condition"
                variant="outlined"
                density="compact"
                class="mb-2"
              />

              <v-textarea
                v-model="valForm.notes"
                label="Additional Notes"
                variant="outlined"
                density="compact"
                rows="2"
                class="mb-2"
              />

              <v-btn
                block
                color="orange"
                variant="tonal"
                prepend-icon="mdi-chart-box-outline"
                @click="createValuation"
                :loading="creatingValuation"
                :disabled="!valForm.address"
              >
                Run Analysis
              </v-btn>
            </v-card>
          </v-col>

          <!-- Right: valuation history -->
          <v-col cols="12" md="7">
            <v-progress-linear v-if="loadingValuations" indeterminate color="orange" class="mb-2" />

            <div v-if="valuations.length > 0">
              <v-card
                v-for="val in valuations"
                :key="val._id"
                variant="outlined"
                class="pa-3 mb-3"
              >
                <div class="d-flex align-center mb-2">
                  <v-icon color="orange" size="20" class="mr-2">mdi-map-marker</v-icon>
                  <span class="text-subtitle-1 font-weight-bold">{{ val.address }}</span>
                  <v-spacer />
                  <v-chip
                    :color="val.status === 'complete' ? 'green' : val.status === 'pending' ? 'orange' : 'grey'"
                    size="x-small"
                    variant="tonal"
                  >
                    {{ val.status }}
                  </v-chip>
                  <v-btn icon="mdi-delete" size="x-small" variant="text" color="red" class="ml-1" @click="deleteValuation(val._id)" />
                </div>

                <div class="d-flex flex-wrap ga-2 mb-2">
                  <v-chip size="x-small" variant="tonal">{{ val.bedrooms }} bd</v-chip>
                  <v-chip size="x-small" variant="tonal">{{ val.bathrooms }} ba</v-chip>
                  <v-chip size="x-small" variant="tonal">{{ val.floors }} floor{{ val.floors > 1 ? 's' : '' }}</v-chip>
                  <v-chip size="x-small" variant="tonal">Built {{ val.year_built }}</v-chip>
                  <v-chip size="x-small" variant="tonal">{{ fmtNum(val.lot_size_sqft) }} sqft lot</v-chip>
                  <v-chip size="x-small" variant="tonal" :color="conditionColor(val.condition)">{{ val.condition }}</v-chip>
                </div>

                <div v-if="val.estimated_value" class="text-h5 font-weight-bold text-green mb-2">
                  ${{ fmtNum(val.estimated_value) }}
                </div>

                <div v-if="val.analysis" class="text-body-2 darpa-body" v-html="renderMd(val.analysis)" />

                <div v-if="val.status === 'pending'" class="mt-3">
                  <v-btn
                    color="orange"
                    variant="tonal"
                    size="small"
                    prepend-icon="mdi-robot"
                    @click="runLLMValuation(val)"
                    :loading="val._analyzing"
                  >
                    Analyze with AI
                  </v-btn>
                </div>

                <div class="text-caption text-grey mt-2">
                  Created: {{ fmtDate(val.created_at) }}
                  <span v-if="val.neighborhood_data?.display_name"> | {{ val.neighborhood_data.display_name }}</span>
                </div>
              </v-card>
            </div>

            <v-card v-else-if="!loadingValuations" variant="tonal" class="pa-8 text-center">
              <v-icon size="48" color="grey">mdi-home-search-outline</v-icon>
              <div class="text-h6 mt-2 text-grey">No valuations yet</div>
              <div class="text-body-2 text-grey">Enter property details and click "Run Analysis"</div>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- ═══════════════════════════════════════ -->
      <!-- 4. PROPERTY SEARCH / AUCTIONS -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="property_search">
        <!-- Search criteria -->
        <v-card variant="outlined" class="pa-4 mb-4">
          <div class="text-h6 mb-3">Search Criteria</div>
          <v-row dense>
            <v-col cols="6" sm="3">
              <v-text-field
                v-model.number="searchCriteria.min_price"
                label="Min Price ($)"
                variant="outlined"
                density="compact"
                type="number"
              />
            </v-col>
            <v-col cols="6" sm="3">
              <v-text-field
                v-model.number="searchCriteria.max_price"
                label="Max Price ($)"
                variant="outlined"
                density="compact"
                type="number"
              />
            </v-col>
            <v-col cols="6" sm="2">
              <v-text-field
                v-model.number="searchCriteria.min_bedrooms"
                label="Min Beds"
                variant="outlined"
                density="compact"
                type="number"
              />
            </v-col>
            <v-col cols="6" sm="2">
              <v-text-field
                v-model="searchCriteria.state"
                label="State"
                variant="outlined"
                density="compact"
                placeholder="e.g. FL"
              />
            </v-col>
            <v-col cols="12" sm="2">
              <v-select
                v-model="searchCriteria.property_type"
                :items="['', 'house', 'condo', 'land']"
                label="Type"
                variant="outlined"
                density="compact"
                clearable
              />
            </v-col>
          </v-row>
          <v-text-field
            v-model="searchCriteria.keywords"
            label="Keywords"
            variant="outlined"
            density="compact"
            placeholder="foreclosure, waterfront, ..."
            class="mb-2"
          />
          <div class="d-flex ga-2">
            <v-btn color="green" variant="tonal" size="small" prepend-icon="mdi-content-save" @click="saveCriteria" :loading="savingCriteria">
              Save Criteria
            </v-btn>
            <v-btn color="deep-purple" variant="tonal" size="small" prepend-icon="mdi-magnify" @click="scrapeAuctions" :loading="scrapingAuctions">
              Scrape Auctions
            </v-btn>
            <v-spacer />
            <v-switch v-model="matchedOnly" label="Matched only" density="compact" hide-details color="red" @update:model-value="loadAuctions" />
          </div>
        </v-card>

        <v-progress-linear v-if="loadingAuctions" indeterminate color="deep-purple" class="mb-2" />

        <!-- Auction results -->
        <v-table v-if="auctionItems.length > 0" density="compact" hover>
          <thead>
            <tr>
              <th style="width: 30px"></th>
              <th>Title</th>
              <th>Price</th>
              <th>Address</th>
              <th>Source</th>
              <th>Scraped</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in auctionItems" :key="item.uid" :class="item.matched ? 'bg-green-darken-4' : ''">
              <td>
                <v-icon v-if="item.matched" color="red" size="12">mdi-star</v-icon>
              </td>
              <td class="font-weight-medium" style="max-width: 300px">
                <div class="text-truncate">{{ item.title || 'Untitled' }}</div>
              </td>
              <td class="font-weight-bold" :class="item.matched ? 'text-red' : ''">
                {{ item.price_raw || '—' }}
              </td>
              <td class="text-caption">{{ item.address || '—' }}</td>
              <td class="text-caption">
                <a :href="item.source_url" target="_blank" class="text-blue">Source</a>
              </td>
              <td class="text-caption">{{ fmtDate(item.scraped_at) }}</td>
            </tr>
          </tbody>
        </v-table>

        <v-card v-else-if="!loadingAuctions" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-gavel</v-icon>
          <div class="text-h6 mt-2 text-grey">No auction items</div>
          <div class="text-body-2 text-grey">Configure auction URLs in Settings, then click "Scrape Auctions"</div>
        </v-card>
      </v-window-item>

      <!-- ═══════════════════════════════════════ -->
      <!-- 5. OIL & ENERGY -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="oil">
        <div class="d-flex align-center mb-3">
          <v-btn
            color="brown"
            variant="tonal"
            size="small"
            prepend-icon="mdi-download"
            @click="scrapeOil"
            :loading="scrapingOil"
          >
            Scrape Oil & Energy Prices
          </v-btn>
        </div>

        <v-progress-linear v-if="loadingOil" indeterminate color="brown" class="mb-2" />

        <v-row v-if="oilItems.length > 0">
          <v-col
            v-for="item in oilItems"
            :key="item.series_id"
            cols="12"
            sm="6"
          >
            <v-card variant="outlined" class="pa-4 h-100">
              <div class="d-flex align-center mb-2">
                <v-icon color="brown" size="24" class="mr-2">mdi-oil</v-icon>
                <span class="text-subtitle-1 font-weight-bold">{{ item.label }}</span>
              </div>
              <div class="text-h4 font-weight-bold mb-1">
                {{ item.latest_value }}
                <span class="text-body-1 text-grey">{{ item.unit }}</span>
              </div>
              <div class="text-caption text-grey mb-3">as of {{ item.latest_date }}</div>

              <div v-if="item.history && item.history.length > 1" class="d-flex align-center ga-1 mb-2">
                <v-icon :color="trendColor(item.history)" size="16">{{ trendIcon(item.history) }}</v-icon>
                <span class="text-caption" :class="`text-${trendColor(item.history)}`">{{ trendText(item.history) }}</span>
              </div>

              <div v-if="sparklineData(item.history).length > 1">
                <v-sparkline
                  :model-value="sparklineData(item.history)"
                  :gradient="['#4E342E', '#795548', '#A1887F']"
                  :line-width="2"
                  :padding="4"
                  height="60"
                  smooth
                  auto-draw
                />
              </div>
            </v-card>
          </v-col>
        </v-row>

        <v-card v-else-if="!loadingOil" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-oil</v-icon>
          <div class="text-h6 mt-2 text-grey">No oil/energy data yet</div>
          <v-btn color="brown" variant="tonal" class="mt-3" @click="scrapeOil">Scrape Now</v-btn>
        </v-card>
      </v-window-item>

      <!-- ═══════════════════════════════════════ -->
      <!-- 6. TAXATION -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="taxation">
        <v-tabs v-model="taxSubTab" color="cyan" class="mb-3">
          <v-tab value="individual">Individual Taxes</v-tab>
          <v-tab value="corporate">LLC / Corporate Taxes</v-tab>
        </v-tabs>

        <v-text-field
          v-model="taxSearch"
          density="compact"
          variant="outlined"
          prepend-inner-icon="mdi-magnify"
          placeholder="Search state..."
          hide-details
          clearable
          style="max-width: 300px"
          class="mb-3"
        />

        <v-window v-model="taxSubTab">
          <!-- Individual -->
          <v-window-item value="individual">
            <v-table density="compact" hover fixed-header height="70vh">
              <thead>
                <tr>
                  <th>State</th>
                  <th>Income Tax</th>
                  <th>Sales Tax</th>
                  <th>Property Tax (eff.)</th>
                  <th>No Income Tax</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="s in filteredIndividualTax"
                  :key="s.abbr"
                  :class="s.no_income_tax ? 'bg-green-darken-4' : ''"
                >
                  <td class="font-weight-bold">
                    {{ s.state }}
                    <span class="text-caption text-grey ml-1">({{ s.abbr }})</span>
                  </td>
                  <td>{{ s.income_tax }}</td>
                  <td>{{ s.sales_tax }}</td>
                  <td>{{ s.property_tax }}</td>
                  <td>
                    <v-icon v-if="s.no_income_tax" color="green" size="18">mdi-check-circle</v-icon>
                    <v-icon v-else color="grey" size="18">mdi-close-circle-outline</v-icon>
                  </td>
                  <td class="text-caption text-grey">{{ s.notes }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-window-item>

          <!-- Corporate -->
          <v-window-item value="corporate">
            <v-table density="compact" hover fixed-header height="70vh">
              <thead>
                <tr>
                  <th>State</th>
                  <th>Corporate Tax</th>
                  <th>Franchise Tax</th>
                  <th>LLC Annual Fee</th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in filteredCorpTax" :key="s.abbr">
                  <td class="font-weight-bold">
                    {{ s.state }}
                    <span class="text-caption text-grey ml-1">({{ s.abbr }})</span>
                  </td>
                  <td>{{ s.corp_tax }}</td>
                  <td>{{ s.franchise_tax }}</td>
                  <td>{{ s.llc_fee }}</td>
                  <td class="text-caption text-grey">{{ s.notes }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-window-item>
        </v-window>
      </v-window-item>

      <!-- ═══════════════════════════════════════ -->
      <!-- 7. PROGRAMS -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="programs">
        <div class="d-flex align-center mb-3">
          <v-btn
            color="cyan"
            variant="tonal"
            size="small"
            prepend-icon="mdi-download"
            @click="scrapePrograms"
            :loading="scrapingPrograms"
          >
            Scrape Programs
          </v-btn>
          <v-spacer />
          <v-text-field
            v-model="programSearch"
            density="compact"
            variant="outlined"
            prepend-inner-icon="mdi-magnify"
            placeholder="Search programs..."
            hide-details
            clearable
            style="max-width: 300px"
          />
        </div>

        <v-progress-linear v-if="loadingPrograms" indeterminate color="cyan" class="mb-2" />

        <v-row v-if="filteredPrograms.length > 0">
          <v-col
            v-for="prog in filteredPrograms"
            :key="prog._id || prog.uid"
            cols="12"
            sm="6"
            md="4"
          >
            <v-card variant="outlined" class="pa-3 h-100">
              <div class="text-subtitle-1 font-weight-bold mb-1">{{ prog.title }}</div>
              <div class="d-flex flex-wrap ga-1 mb-2">
                <v-chip size="x-small" variant="tonal" color="cyan">{{ prog.source || 'Unknown' }}</v-chip>
                <v-chip size="x-small" variant="tonal" color="blue">{{ prog.state || 'National' }}</v-chip>
                <v-chip v-if="prog.program_type" size="x-small" variant="tonal" color="purple">{{ prog.program_type }}</v-chip>
                <v-chip v-if="prog.award_ceiling" size="x-small" variant="tonal" color="green">Up to ${{ fmtNum(prog.award_ceiling) }}</v-chip>
              </div>
              <div class="text-body-2 mb-2" style="max-height: 100px; overflow: hidden;">
                {{ (prog.description || '').substring(0, 250) }}{{ (prog.description || '').length > 250 ? '...' : '' }}
              </div>
              <div v-if="prog.agency" class="text-caption text-grey mb-1">Agency: {{ prog.agency }}</div>
              <div v-if="prog.close_date" class="text-caption text-orange mb-1">Closes: {{ fmtDate(prog.close_date) }}</div>
              <v-btn
                v-if="prog.url"
                :href="prog.url"
                target="_blank"
                variant="tonal"
                color="cyan"
                size="small"
                prepend-icon="mdi-open-in-new"
                class="mt-1"
              >
                Apply / Details
              </v-btn>
            </v-card>
          </v-col>
        </v-row>

        <v-card v-else-if="!loadingPrograms" variant="tonal" class="pa-8 text-center">
          <v-icon size="48" color="grey">mdi-flag-outline</v-icon>
          <div class="text-h6 mt-2 text-grey">No programs found</div>
          <v-btn color="cyan" variant="tonal" class="mt-3" @click="scrapePrograms">Scrape Now</v-btn>
        </v-card>
      </v-window-item>

      <!-- ═══════════════════════════════════════ -->
      <!-- 8. SETTINGS -->
      <!-- ═══════════════════════════════════════ -->
      <v-window-item value="settings">
        <v-card variant="outlined" class="pa-4" style="max-width: 650px">
          <div class="text-h6 mb-4">US Finance Settings</div>

          <v-select
            v-model="settNewsSource"
            :items="[{title: 'FRED (Federal Reserve)', value: 'fred'}, {title: 'BLS (Bureau of Labor Statistics)', value: 'bls'}]"
            label="Default News Source"
            variant="outlined"
            density="compact"
            class="mb-3"
            @update:model-value="saveSetting('us_finance_news_source', $event)"
          />

          <v-select
            v-model="settScrapeFreq"
            :items="[{title: 'Every hour', value: 'hourly'}, {title: 'Daily', value: 'daily'}, {title: 'Weekly', value: 'weekly'}, {title: 'Manual only', value: 'manual'}]"
            label="Scrape Frequency"
            variant="outlined"
            density="compact"
            class="mb-3"
            @update:model-value="saveSetting('us_finance_scrape_frequency', $event)"
          />

          <v-text-field
            v-model="settFredKey"
            label="FRED API Key"
            variant="outlined"
            density="compact"
            hint="Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html — leave blank for DEMO_KEY"
            persistent-hint
            class="mb-3"
            @blur="saveSetting('us_finance_fred_api_key', settFredKey)"
          />

          <v-textarea
            v-model="settAuctionUrls"
            label="Auction URLs (one per line)"
            variant="outlined"
            density="compact"
            rows="4"
            hint="Property auction websites to scrape for deals"
            persistent-hint
            class="mb-3"
            @blur="saveSetting('us_finance_auction_urls', settAuctionUrls)"
          />

          <v-select
            v-model="settAuctionHours"
            :items="[{title: 'Every 6 hours', value: '6'}, {title: 'Every 12 hours', value: '12'}, {title: 'Every 24 hours', value: '24'}, {title: 'Every 48 hours', value: '48'}]"
            label="Auction Scrape Interval"
            variant="outlined"
            density="compact"
            class="mb-3"
            @update:model-value="saveSetting('us_finance_auction_scrape_hours', $event)"
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
            <v-btn
              color="green"
              variant="tonal"
              prepend-icon="mdi-refresh"
              @click="scrapeAll"
              :loading="scraping"
            >
              Scrape All Now
            </v-btn>
            <v-btn
              color="red"
              variant="tonal"
              prepend-icon="mdi-delete-outline"
              @click="confirmClear = true"
            >
              Clear All Data
            </v-btn>
          </div>
        </v-card>

        <!-- Available Skills -->
        <v-card variant="outlined" class="pa-4 mt-4" style="max-width: 650px">
          <div class="text-h6 mb-4">Available Skills</div>
          <p class="text-medium-emphasis mb-4">
            Skills that agents can use to interact with US Finance data.
          </p>
          <v-card variant="tonal" class="pa-3 mb-3">
            <div class="d-flex align-center mb-2">
              <v-icon color="green" size="20" class="mr-2">mdi-magnify</v-icon>
              <span class="text-subtitle-1 font-weight-bold">us_finance_search</span>
              <v-chip size="x-small" variant="outlined" color="green" class="ml-2">finance</v-chip>
            </div>
            <div class="text-body-2 mb-2">
              Search US economic indicators, real estate data, oil prices, tax info, and government programs.
            </div>
            <v-table density="compact" class="text-body-2">
              <thead>
                <tr>
                  <th style="width: 120px">Name</th>
                  <th style="width: 80px">Type</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>query</code></td>
                  <td>string</td>
                  <td>Search text across all US finance data</td>
                </tr>
                <tr>
                  <td><code>section</code></td>
                  <td>string</td>
                  <td>Filter by section: news, real_estate, oil, programs, taxation</td>
                </tr>
                <tr>
                  <td><code>limit</code></td>
                  <td>integer</td>
                  <td>Max results (default: 20)</td>
                </tr>
              </tbody>
            </v-table>
          </v-card>
          <v-alert type="info" variant="tonal" density="compact">
            To use this skill, add <strong>us_finance_search</strong> to an agent's skill list.
          </v-alert>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Clear confirmation dialog -->
    <v-dialog v-model="confirmClear" max-width="400">
      <v-card>
        <v-card-title>Clear All US Finance Data?</v-card-title>
        <v-card-text>
          This deletes all stored data. You can re-scrape at any time.
          <v-text-field
            v-model="deleteConfirmText"
            label="Type DELETE to confirm"
            variant="outlined"
            density="compact"
            class="mt-3"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmClear = false">Cancel</v-btn>
          <v-btn color="red" variant="tonal" :disabled="deleteConfirmText !== 'DELETE'" @click="clearAllData">
            Clear All
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar -->
    <v-snackbar v-model="snack" :color="snackColor" timeout="3000">
      {{ snackText }}
    </v-snackbar>
  </div>
</template>

<script>
import api from '@src/api'
import { useSettingsStore } from '@src/stores/settings'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const API = '/api/addons/us_finance'

export default {
  name: 'UsFinanceView',

  data() {
    return {
      activeTab: localStorage.getItem('usf_tab') || 'news',

      // Stats & scrape status
      stats: null,
      lastScrape: null,
      scraping: false,
      scrapeStatusData: null,

      // News tab
      newsSource: 'fred',
      newsItems: [],
      loadingNews: false,
      scrapingNews: false,

      // Real estate
      realEstateItems: [],
      loadingRE: false,
      scrapingRE: false,

      // Valuation
      valForm: {
        address: '',
        bedrooms: 3,
        bathrooms: 2,
        floors: 1,
        year_built: 2000,
        lot_size_sqft: 5000,
        condition: 'good',
        notes: '',
      },
      conditionOptions: [
        { title: 'Poor — needs major repairs', value: 'poor' },
        { title: 'Good — standard condition', value: 'good' },
        { title: 'Excellent — recently renovated', value: 'excellent' },
      ],
      valuations: [],
      loadingValuations: false,
      creatingValuation: false,

      // Property search / auctions
      searchCriteria: {
        min_price: null,
        max_price: null,
        min_bedrooms: null,
        state: '',
        property_type: null,
        keywords: '',
      },
      auctionItems: [],
      loadingAuctions: false,
      savingCriteria: false,
      scrapingAuctions: false,
      matchedOnly: false,

      // Oil
      oilItems: [],
      loadingOil: false,
      scrapingOil: false,

      // Taxation
      taxSubTab: 'individual',
      taxSearch: '',
      individualTax: [],
      corpTax: [],

      // Programs
      programs: [],
      loadingPrograms: false,
      scrapingPrograms: false,
      programSearch: '',

      // Settings
      settNewsSource: 'fred',
      settScrapeFreq: 'daily',
      settFredKey: '',
      settAuctionUrls: '',
      settAuctionHours: '24',

      // Clear dialog
      confirmClear: false,
      deleteConfirmText: '',

      // Snackbar
      snack: false,
      snackText: '',
      snackColor: 'success',
    }
  },

  computed: {
    filteredIndividualTax() {
      if (!this.taxSearch) return this.individualTax
      const q = this.taxSearch.toLowerCase()
      return this.individualTax.filter(s =>
        s.state.toLowerCase().includes(q) || s.abbr.toLowerCase().includes(q)
      )
    },
    filteredCorpTax() {
      if (!this.taxSearch) return this.corpTax
      const q = this.taxSearch.toLowerCase()
      return this.corpTax.filter(s =>
        s.state.toLowerCase().includes(q) || s.abbr.toLowerCase().includes(q)
      )
    },
    filteredPrograms() {
      if (!this.programSearch) return this.programs
      const q = this.programSearch.toLowerCase()
      return this.programs.filter(p =>
        (p.title || '').toLowerCase().includes(q) ||
        (p.description || '').toLowerCase().includes(q) ||
        (p.state || '').toLowerCase().includes(q) ||
        (p.agency || '').toLowerCase().includes(q)
      )
    },
  },

  watch: {
    activeTab(val) {
      localStorage.setItem('usf_tab', val)
      this.loadTabData(val)
    },
    newsSource() {
      this.loadNews()
    },
  },

  async mounted() {
    this.loadSettings()
    this.loadStats()
    this.loadScrapeStatus()
    this.loadTabData(this.activeTab)
  },

  methods: {
    // ---- Helpers ----
    fmtDate(d) {
      if (!d) return ''
      try {
        return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
      } catch { return d }
    },
    fmtNum(n) {
      if (n == null) return '0'
      return Number(n).toLocaleString('en-US')
    },
    renderMd(text) {
      if (!text) return ''
      return DOMPurify.sanitize(marked.parse(text))
    },
    notify(text, color = 'success') {
      this.snackText = text
      this.snackColor = color
      this.snack = true
    },
    conditionColor(c) {
      return c === 'excellent' ? 'green' : c === 'poor' ? 'red' : 'orange'
    },

    sparklineData(history) {
      if (!history) return []
      return history
        .slice()
        .reverse()
        .map(h => parseFloat(h.value))
        .filter(v => !isNaN(v))
    },
    trendColor(history) {
      const vals = this.sparklineData(history)
      if (vals.length < 2) return 'grey'
      return vals[vals.length - 1] >= vals[vals.length - 2] ? 'green' : 'red'
    },
    trendIcon(history) {
      const vals = this.sparklineData(history)
      if (vals.length < 2) return 'mdi-minus'
      return vals[vals.length - 1] >= vals[vals.length - 2] ? 'mdi-trending-up' : 'mdi-trending-down'
    },
    trendText(history) {
      const vals = this.sparklineData(history)
      if (vals.length < 2) return ''
      const diff = vals[vals.length - 1] - vals[vals.length - 2]
      const pct = vals[vals.length - 2] !== 0 ? ((diff / vals[vals.length - 2]) * 100).toFixed(1) : '—'
      return `${diff >= 0 ? '+' : ''}${pct}%`
    },

    // ---- Load tab data ----
    loadTabData(tab) {
      switch (tab) {
        case 'news': this.loadNews(); break
        case 'real_estate': this.loadRealEstate(); break
        case 'valuation': this.loadValuations(); break
        case 'property_search': this.loadCriteria(); this.loadAuctions(); break
        case 'oil': this.loadOil(); break
        case 'taxation': this.loadTaxation(); break
        case 'programs': this.loadPrograms(); break
        case 'settings': this.loadScrapeStatus(); break
      }
    },

    // ---- Settings ----
    loadSettings() {
      const ss = useSettingsStore()
      const s = ss.systemSettings || {}
      this.settNewsSource = s.us_finance_news_source || 'fred'
      this.settScrapeFreq = s.us_finance_scrape_frequency || 'daily'
      this.settFredKey = s.us_finance_fred_api_key || ''
      this.settAuctionUrls = s.us_finance_auction_urls || ''
      this.settAuctionHours = s.us_finance_auction_scrape_hours || '24'
      this.newsSource = this.settNewsSource
    },
    async saveSetting(key, value) {
      try {
        const ss = useSettingsStore()
        await ss.updateSystemSetting(key, value)
      } catch (e) {
        this.notify('Failed to save setting', 'error')
      }
    },

    // ---- Stats ----
    async loadStats() {
      try {
        const { data } = await api.get(`${API}/stats`)
        this.stats = data
      } catch {}
    },
    async loadScrapeStatus() {
      try {
        const { data } = await api.get(`${API}/scrape/status`)
        this.scrapeStatusData = data
        // Find latest scrape time
        let latest = null
        for (const v of Object.values(data)) {
          if (v.last_scrape && (!latest || v.last_scrape > latest)) latest = v.last_scrape
        }
        this.lastScrape = latest
      } catch {}
    },

    // ---- Scrape All ----
    async scrapeAll() {
      this.scraping = true
      try {
        await api.post(`${API}/scrape-all`)
        this.notify('All data scraped successfully')
        this.loadStats()
        this.loadScrapeStatus()
        this.loadTabData(this.activeTab)
      } catch (e) {
        this.notify('Scrape failed: ' + (e.response?.data?.detail || e.message), 'error')
      } finally {
        this.scraping = false
      }
    },

    // ---- News ----
    async loadNews() {
      this.loadingNews = true
      try {
        const { data } = await api.get(`${API}/news`, { params: { source: this.newsSource, limit: 100 } })
        this.newsItems = data.items || []
      } catch {} finally { this.loadingNews = false }
    },
    async scrapeNews() {
      this.scrapingNews = true
      try {
        const { data } = await api.post(`${API}/news/scrape`, null, { params: { source: this.newsSource } })
        this.notify(`Scraped ${data.scraped} indicators from ${this.newsSource.toUpperCase()}`)
        this.loadNews()
        this.loadStats()
      } catch (e) {
        this.notify('Scrape failed: ' + (e.response?.data?.detail || e.message), 'error')
      } finally { this.scrapingNews = false }
    },

    // ---- Real Estate ----
    async loadRealEstate() {
      this.loadingRE = true
      try {
        const { data } = await api.get(`${API}/real-estate`)
        this.realEstateItems = data.items || []
      } catch {} finally { this.loadingRE = false }
    },
    async scrapeRealEstate() {
      this.scrapingRE = true
      try {
        const { data } = await api.post(`${API}/real-estate/scrape`)
        this.notify(`Scraped ${data.scraped} real estate indicators`)
        this.loadRealEstate()
        this.loadStats()
      } catch (e) {
        this.notify('Scrape failed', 'error')
      } finally { this.scrapingRE = false }
    },

    // ---- Valuations ----
    async loadValuations() {
      this.loadingValuations = true
      try {
        const { data } = await api.get(`${API}/valuations`)
        this.valuations = (data.items || []).map(v => ({ ...v, _analyzing: false }))
      } catch {} finally { this.loadingValuations = false }
    },
    async createValuation() {
      if (!this.valForm.address) return
      this.creatingValuation = true
      try {
        await api.post(`${API}/valuations`, this.valForm)
        this.notify('Valuation created — click "Analyze with AI" to run')
        this.loadValuations()
        this.loadStats()
      } catch (e) {
        this.notify('Failed to create valuation', 'error')
      } finally { this.creatingValuation = false }
    },
    async deleteValuation(id) {
      try {
        await api.delete(`${API}/valuations/${id}`)
        this.valuations = this.valuations.filter(v => v._id !== id)
        this.loadStats()
      } catch {}
    },
    async runLLMValuation(val) {
      val._analyzing = true
      try {
        // Build a prompt for LLM analysis
        const prompt = `Analyze this property for its estimated market value.

Property Details:
- Address: ${val.address}
- Bedrooms: ${val.bedrooms}, Bathrooms: ${val.bathrooms}, Floors: ${val.floors}
- Year Built: ${val.year_built}
- Lot Size: ${val.lot_size_sqft} sqft
- Condition: ${val.condition}
${val.notes ? `- Notes: ${val.notes}` : ''}
${val.neighborhood_data?.display_name ? `- Location: ${val.neighborhood_data.display_name}` : ''}
${val.neighborhood_data?.lat ? `- Coordinates: ${val.neighborhood_data.lat}, ${val.neighborhood_data.lon}` : ''}

Provide:
1. Estimated market value range (low/mid/high)
2. Key factors affecting value
3. Neighborhood analysis
4. Comparable price ranges in the area
5. Investment potential assessment

Format as clear markdown with sections.`

        // Use the chat endpoint for LLM analysis
        const { data: chatResp } = await api.post('/api/ollama/chat', {
          messages: [{ role: 'user', content: prompt }],
          stream: false,
        })

        const analysis = chatResp.message?.content || chatResp.content || 'Analysis could not be generated'

        // Extract estimated value from analysis (look for dollar amounts)
        const priceMatch = analysis.match(/\$[\d,]+(?:,\d{3})*/)
        const estimatedValue = priceMatch ? parseInt(priceMatch[0].replace(/[$,]/g, '')) : null

        // Update valuation in backend
        await api.patch(`${API}/valuations/${val._id}`, {
          analysis,
          estimated_value: estimatedValue,
          status: 'complete',
        })

        val.analysis = analysis
        val.estimated_value = estimatedValue
        val.status = 'complete'
        this.notify('Analysis complete')
      } catch (e) {
        this.notify('AI analysis failed: ' + (e.response?.data?.detail || e.message), 'error')
      } finally {
        val._analyzing = false
      }
    },

    // ---- Property Search / Auctions ----
    async loadCriteria() {
      try {
        const { data } = await api.get(`${API}/property-search/criteria`)
        if (data.criteria) {
          Object.assign(this.searchCriteria, data.criteria)
        }
      } catch {}
    },
    async saveCriteria() {
      this.savingCriteria = true
      try {
        await api.post(`${API}/property-search/criteria`, this.searchCriteria)
        this.notify('Search criteria saved')
      } catch (e) {
        this.notify('Failed to save criteria', 'error')
      } finally { this.savingCriteria = false }
    },
    async loadAuctions() {
      this.loadingAuctions = true
      try {
        const { data } = await api.get(`${API}/property-search/items`, { params: { matched_only: this.matchedOnly, limit: 200 } })
        this.auctionItems = data.items || []
      } catch {} finally { this.loadingAuctions = false }
    },
    async scrapeAuctions() {
      this.scrapingAuctions = true
      try {
        const { data } = await api.post(`${API}/property-search/scrape`)
        this.notify(`Scraped ${data.scraped} auction items`)
        this.loadAuctions()
        this.loadStats()
      } catch (e) {
        this.notify(e.response?.data?.message || 'Scrape failed', 'error')
      } finally { this.scrapingAuctions = false }
    },

    // ---- Oil ----
    async loadOil() {
      this.loadingOil = true
      try {
        const { data } = await api.get(`${API}/oil`)
        this.oilItems = data.items || []
      } catch {} finally { this.loadingOil = false }
    },
    async scrapeOil() {
      this.scrapingOil = true
      try {
        const { data } = await api.post(`${API}/oil/scrape`)
        this.notify(`Scraped ${data.scraped} oil/energy indicators`)
        this.loadOil()
        this.loadStats()
      } catch (e) {
        this.notify('Scrape failed', 'error')
      } finally { this.scrapingOil = false }
    },

    // ---- Taxation ----
    async loadTaxation() {
      try {
        const [indRes, corpRes] = await Promise.all([
          api.get(`${API}/taxation/individual`),
          api.get(`${API}/taxation/corporate`),
        ])
        this.individualTax = indRes.data.items || []
        this.corpTax = corpRes.data.items || []
      } catch {}
    },

    // ---- Programs ----
    async loadPrograms() {
      this.loadingPrograms = true
      try {
        const { data } = await api.get(`${API}/programs`)
        this.programs = data.items || []
      } catch {} finally { this.loadingPrograms = false }
    },
    async scrapePrograms() {
      this.scrapingPrograms = true
      try {
        const { data } = await api.post(`${API}/programs/scrape`)
        this.notify(`Scraped ${data.scraped} programs`)
        this.loadPrograms()
        this.loadStats()
      } catch (e) {
        this.notify('Scrape failed', 'error')
      } finally { this.scrapingPrograms = false }
    },

    // ---- Clear ----
    async clearAllData() {
      try {
        await api.delete(`${API}/clear`)
        this.notify('All data cleared')
        this.confirmClear = false
        this.deleteConfirmText = ''
        this.loadStats()
        this.loadTabData(this.activeTab)
      } catch (e) {
        this.notify('Clear failed', 'error')
      }
    },
  },
}
</script>

<style scoped>
.darpa-body :deep(h1), .darpa-body :deep(h2), .darpa-body :deep(h3) {
  margin: 0.5em 0 0.3em;
}
.darpa-body :deep(ul), .darpa-body :deep(ol) {
  padding-left: 1.5em;
}
.darpa-body :deep(p) {
  margin-bottom: 0.5em;
}
</style>
