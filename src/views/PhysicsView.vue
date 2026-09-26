<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import { useConfigStore } from '@/stores/configStore'
import { useUiStore } from '@/stores/uiStore'
import { PHYSICS_CATEGORIES, type PhysicsCategory, type GraphEdge, type SourceEvidence } from '@/types/graph'

const route = useRoute()
const router = useRouter()
const graphStore = useGraphStore()
const configStore = useConfigStore()
const uiStore = useUiStore()

const categories = Object.entries(PHYSICS_CATEGORIES).map(([key, value]) => ({
  id: key as PhysicsCategory,
  ...value
}))

const selectedCategoryId = ref<PhysicsCategory | null>(null)
const selectedSchemeValue = ref<string | null>(null)

onMounted(() => {
  const cat = route.params.category as PhysicsCategory
  if (cat && categories.find(c => c.id === cat)) {
    selectedCategoryId.value = cat
  } else {
    selectedCategoryId.value = categories[0].id
  }
})

watch(() => selectedCategoryId.value, (newVal) => {
  if (newVal && newVal !== route.params.category) {
    router.push(`/physics/${newVal}`)
  }
  selectedSchemeValue.value = null
})

watch(() => route.params.category, (newCat) => {
  if (newCat && newCat !== selectedCategoryId.value) {
    const cat = newCat as PhysicsCategory
    if (categories.find(c => c.id === cat)) {
      selectedCategoryId.value = cat
    }
  }
})

const currentCategory = computed(() => {
  return categories.find(c => c.id === selectedCategoryId.value)
})

const availableSchemes = computed(() => {
  if (!currentCategory.value || !graphStore.isLoaded) return []
  return graphStore.getPackagesForNamelist(currentCategory.value.namelist)
})

const activeSchemeValue = computed(() => {
  if (!currentCategory.value) return null
  return String(configStore.getConfig(currentCategory.value.namelist))
})

const selectScheme = (value: string) => {
  selectedSchemeValue.value = value === selectedSchemeValue.value ? null : value
}

const activateScheme = (value: string) => {
  if (currentCategory.value) {
    configStore.setConfig(currentCategory.value.namelist, parseInt(value))
  }
}

const isAuxiliaryCall = (edge: GraphEdge) => /^(wrf_debug|wrf_error_fatal|add_multi_perturb|remove_multi_perturb)/i
  .test(graphStore.getNodeById(edge.target)?.label || edge.target.replace('subroutine:', ''))

const selectedSchemeDetails = computed(() => {
  if (!selectedSchemeValue.value || !currentCategory.value) return null
  const selector = currentCategory.value.namelist
  const path = graphStore.getExecutionPath(selector, selectedSchemeValue.value)
  const registry = path.edges.find(edge => edge.type === 'SELECTS')
  const calls = path.edges.filter(edge => edge.type === 'CALLS')
    .sort((a, b) => Number(isAuxiliaryCall(a)) - Number(isAuxiliaryCall(b)))
  const callLocations = new Set(calls.map(edge => `${edge.target}:${edge.data?.evidence?.[0]?.path}:${edge.data?.evidence?.[0]?.startLine}`))
  const conditionalCalls = graphStore.getActiveSubroutines(selector, selectedSchemeValue.value)
    .filter(item => !callLocations.has(`${item.edge.source}:${item.evidence?.[0]?.path}:${item.evidence?.[0]?.startLine}`))
  const configReads = graphStore.getEdgesTo(`namelist:${selector}`)
    .filter(edge => edge.type === 'READS_CONFIG' && edge.data?.evidence?.length)
    .slice(0, 5)
  const packageNode = path.nodes.find(node => node.type === 'registry_package')
  const driverName = graphStore.getNodeById(`namelist:${selector}`)?.data?.driver as string | undefined
  const driverPhase = driverName
    ? graphStore.getEdgesFrom(`subroutine:${driverName}`).find(edge => edge.type === 'EXECUTES_DURING')
    : undefined
  const primaryCalls = calls.filter(edge => !isAuxiliaryCall(edge))
  const driverFile = driverName ? graphStore.getNodeById(`subroutine:${driverName}`)?.data?.file : undefined
  const implementationCalls = primaryCalls.filter(edge => {
    const targetFile = graphStore.getNodeById(edge.target)?.data?.file
    return targetFile && targetFile !== driverFile
  })
  const nestedCalls = implementationCalls.slice(0, 2).flatMap(parent =>
    graphStore.getEdgesFrom(parent.target)
      .filter(edge => edge.type === 'CALLS' && !isAuxiliaryCall(edge))
      .slice(0, 5)
      .map(edge => ({ parent, edge })))
  const fields = [...new Set((implementationCalls.length ? implementationCalls : primaryCalls).flatMap(edge =>
    (edge.data?.state_args || []).map((arg: { name: string }) => arg.name as string)))]
  return { registry, packageNode, driverName, driverPhase, calls, conditionalCalls, configReads, nestedCalls, fields }
})

const callLabel = (edge: GraphEdge) => graphStore.getNodeById(edge.target)?.label || edge.target.replace('subroutine:', '')
const evidenceOf = (edge: GraphEdge): SourceEvidence | undefined => edge.data?.evidence?.[0]
const definitionOf = (id: string): SourceEvidence | undefined => {
  const node = graphStore.getNodeById(id)
  const path = node?.data?.file
  const line = node?.data?.line
  return typeof path === 'string' && typeof line === 'number' ? { path, startLine: line } : undefined
}
const openEvidence = (evidence: SourceEvidence | undefined) => {
  if (evidence?.path) router.push({ path: '/source', query: { file: evidence.path, line: String(evidence.startLine || 1) } })
}
const openNamelistTrace = () => {
  if (currentCategory.value && selectedSchemeValue.value) {
    router.push({ path: '/namelist', query: { focus: currentCategory.value.namelist, value: selectedSchemeValue.value } })
  }
}
const openField = (name: string) => router.push({
  path: '/variables',
  query: { field: name, selector: currentCategory.value?.namelist, value: selectedSchemeValue.value },
})
</script>

<template>
  <div class="physics-view glass-panel">
    <div class="header">
      <div class="header-main">
        <div>
          <h2>Physics Explorer</h2>
          <p class="subtitle">Browse physical parameterization schemes by category</p>
        </div>
        <div class="mode-badge-wrapper">
          <span class="mode-badge" :class="uiStore.mode">
            {{ uiStore.mode === 'learning' ? '🌱 Learning Mode' : '🔬 Researcher Mode' }}
          </span>
        </div>
      </div>
    </div>

    <div class="layout" v-if="graphStore.isLoaded">
      <!-- Categories Sidebar -->
      <div class="categories-list">
        <button 
          v-for="cat in categories" 
          :key="cat.id"
          class="category-btn"
          :class="{ active: cat.id === selectedCategoryId }"
          :style="{ '--cat-color': cat.color }"
          @click="selectedCategoryId = cat.id"
        >
          <span class="icon">{{ cat.icon }}</span>
          <span class="label">{{ cat.label }}</span>
        </button>
      </div>

      <!-- Schemes Grid -->
      <div class="schemes-content" v-if="currentCategory">
        <div class="category-header">
          <span class="icon" style="font-size: 2rem;">{{ currentCategory.icon }}</span>
          <div>
            <h3 style="margin: 0 0 0.25rem 0; font-size: 1.5rem;">{{ currentCategory.label }} Schemes</h3>
            <span class="namelist-badge" v-if="uiStore.mode === 'researcher'">{{ currentCategory.namelist }}</span>
            <span class="namelist-badge learning" v-else>Namelist Selector: {{ currentCategory.namelist }}</span>
          </div>
        </div>

        <div class="schemes-grid">
          <div 
            v-for="scheme in availableSchemes" 
            :key="scheme.value"
            class="scheme-card"
            :class="{ 
              active: scheme.value === activeSchemeValue,
              expanded: scheme.value === selectedSchemeValue
            }"
            @click="selectScheme(scheme.value)"
          >
            <div class="scheme-header">
              <span class="value-badge">{{ scheme.value }}</span>
              <h4>{{ scheme.packageName }}</h4>
            </div>
            
            <p class="description">{{ scheme.description || 'No description available' }}</p>

            <!-- Learning Mode Metadata -->
            <div v-if="uiStore.mode === 'learning'" class="learning-box">
              <div class="meta-item">
                <span class="meta-lbl">Role:</span> {{ currentCategory.label }} parameterization
              </div>
            </div>

            <!-- Researcher Mode Metadata -->
            <div v-else-if="scheme.node?.data?.state_vars?.length" class="scheme-meta">
               <strong>State Variables:</strong> {{ scheme.node.data.state_vars.join(', ') }}
            </div>

            <div class="actions">
              <button 
                class="activate-btn" 
                v-if="scheme.value !== activeSchemeValue"
                @click.stop="activateScheme(scheme.value)"
              >
                Set Active
              </button>
              <span class="active-label" v-else>Currently Active</span>
            </div>

            <!-- Details when selected -->
            <div class="scheme-details" v-if="scheme.value === selectedSchemeValue" @click.stop>
              <h5>How this selection reaches WRF code</h5>
              <div v-if="selectedSchemeDetails" class="execution-trace">
                <div class="trace-step">
                  <span class="trace-index">01</span>
                  <div>
                    <strong>Configuration and Registry</strong>
                    <p><code>{{ currentCategory.namelist }} = {{ scheme.value }}</code> selects <code>{{ selectedSchemeDetails.packageNode?.data?.package_name || scheme.packageName }}</code>.</p>
                    <button v-if="selectedSchemeDetails.registry?.data?.evidence?.[0]" class="evidence-link" @click="openEvidence(evidenceOf(selectedSchemeDetails.registry))">View Registry line ↗</button>
                  </div>
                </div>
                <div class="trace-step">
                  <span class="trace-index">02</span>
                  <div>
                    <strong>Runtime branch</strong>
                    <p v-if="selectedSchemeDetails.calls.length">The indexed <code>{{ selectedSchemeDetails.driverName }}</code> driver has matching CASE-branch calls. The join from the numeric Registry value to its symbolic constant is inferred. Individual calls may have further conditions; the locations below are exact source references.</p>
                    <p v-else-if="selectedSchemeDetails.driverName">The index associates this selector with <code>{{ selectedSchemeDetails.driverName }}</code>, but has not resolved a matching runtime CASE-branch call for this value.</p>
                    <p v-else>No standalone driver dispatch is resolved for this selector in the current index.</p>
                  </div>
                </div>
                <div v-if="selectedSchemeDetails.calls.length" class="trace-step">
                  <span class="trace-index">03</span>
                  <div>
                    <strong>Calls in the matching branch</strong>
                    <div class="evidence-list">
                      <div v-for="(call, i) in selectedSchemeDetails.calls" :key="`${call.target}-${i}`" class="call-entry">
                        <button @click="openEvidence(evidenceOf(call))">
                          <code>{{ callLabel(call) }}</code><span>Call: {{ evidenceOf(call)?.path }}:{{ evidenceOf(call)?.startLine }}</span>
                        </button>
                        <button v-if="definitionOf(call.target)" class="definition-link" @click="openEvidence(definitionOf(call.target))">
                          Open routine definition · {{ definitionOf(call.target)?.path }}:{{ definitionOf(call.target)?.startLine }} ↗
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="selectedSchemeDetails.driverPhase" class="trace-step">
                  <span class="trace-index">04</span>
                  <div>
                    <strong>Where the driver is called</strong>
                    <p><code>{{ selectedSchemeDetails.driverName }}</code> has an indexed call during <code>{{ selectedSchemeDetails.driverPhase.target.replace('phase:', '') }}</code>. This locates the driver, not a guarantee that every branch runs on every timestep.</p>
                    <button class="evidence-link" @click="openEvidence(evidenceOf(selectedSchemeDetails.driverPhase))">View timestep call ↗</button>
                  </div>
                </div>
                <div v-if="selectedSchemeDetails.nestedCalls.length" class="trace-step">
                  <span class="trace-index">05</span>
                  <div>
                    <strong>One level inside the called routine</strong>
                    <p>These are direct calls found inside the implementation routine. Their own guards and preprocessor conditions are not yet resolved, so they are possible next steps, not an unconditional sequence.</p>
                    <div class="evidence-list">
                      <button v-for="(item, i) in selectedSchemeDetails.nestedCalls" :key="`${item.edge.target}-${i}`" @click="openEvidence(evidenceOf(item.edge))">
                        <code>{{ callLabel(item.parent) }} → {{ callLabel(item.edge) }}</code><span>{{ evidenceOf(item.edge)?.path }}:{{ evidenceOf(item.edge)?.startLine }}</span>
                      </button>
                    </div>
                  </div>
                </div>
                <div v-if="selectedSchemeDetails.fields.length" class="trace-step">
                  <span class="trace-index">06</span>
                  <div>
                    <strong>Registry fields passed at this branch</strong>
                    <p>These field names match direct call arguments. Passing a field does not establish whether the routine reads or writes it.</p>
                    <div class="field-links">
                      <button v-for="field in selectedSchemeDetails.fields.slice(0, 16)" :key="field" @click="openField(field)">{{ field.toUpperCase() }} ↗</button>
                      <span v-if="selectedSchemeDetails.fields.length > 16">+{{ selectedSchemeDetails.fields.length - 16 }} more arguments</span>
                    </div>
                  </div>
                </div>
                <div v-if="selectedSchemeDetails.conditionalCalls.length && !selectedSchemeDetails.calls.length" class="trace-step">
                  <span class="trace-index">03</span>
                  <div>
                    <strong>Conditional calls found elsewhere</strong>
                    <p>These calls carry the selected symbolic condition in source, but the Atlas has not connected them into a complete runtime path.</p>
                    <div class="evidence-list">
                      <button v-for="(item, i) in selectedSchemeDetails.conditionalCalls.slice(0, 8)" :key="`${item.edge.source}-${i}`" @click="openEvidence(item.evidence?.[0])">
                        <code>{{ item.node?.label || item.edge.source }}</code><span>{{ item.evidence?.[0]?.path }}:{{ item.evidence?.[0]?.startLine }}</span>
                      </button>
                    </div>
                  </div>
                </div>
                <div v-if="!selectedSchemeDetails.calls.length && !selectedSchemeDetails.conditionalCalls.length" class="trace-step unresolved-trace">
                  <span class="trace-index">?</span>
                  <div>
                    <strong>Implementation path not yet resolved</strong>
                    <p>The Registry selection is known, but this index does not prove which scheme routine executes for it. These source references read the selector; a read alone does not prove activation.</p>
                    <div class="evidence-list" v-if="selectedSchemeDetails.configReads.length">
                      <button v-for="(read, i) in selectedSchemeDetails.configReads" :key="`${read.source}-${i}`" @click="openEvidence(evidenceOf(read))">
                        <code>{{ read.source.replace('subroutine:', '') }}</code><span>{{ evidenceOf(read)?.path }}:{{ evidenceOf(read)?.startLine }}</span>
                      </button>
                    </div>
                  </div>
                </div>
                <button class="trace-deep-link" @click="openNamelistTrace">Open full trace in Namelist Lab ↗</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="loading-state">
      <div class="spinner"></div>
      Loading graph data...
    </div>
  </div>
</template>

<style scoped>
.physics-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.header { 
  padding: 1.5rem 2rem; 
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
}
.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header h2 {
  margin: 0 0 0.25rem 0;
  color: #e2e8f0;
}
.subtitle { 
  color: #94a3b8; 
  margin: 0; 
  font-size: 0.95rem;
}
.mode-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}
.mode-badge.learning {
  background: rgba(52, 211, 153, 0.2);
  color: #34d399;
}
.mode-badge.researcher {
  background: rgba(96, 165, 250, 0.2);
  color: #60a5fa;
}

.layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.categories-list {
  width: 280px;
  border-right: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  gap: 0.75rem;
  overflow-y: auto;
  background: rgba(10, 14, 39, 0.3);
}

.category-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1.25rem;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  font-size: 1rem;
  font-weight: 500;
}
.category-btn:hover {
  background: rgba(255,255,255,0.08);
  border-color: var(--cat-color);
  color: #f8fafc;
}
.category-btn.active {
  background: rgba(255,255,255,0.1);
  border-color: var(--cat-color);
  box-shadow: 0 0 12px var(--cat-color);
  color: #fff;
}
.category-btn .icon {
  font-size: 1.25rem;
}

.schemes-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  background: linear-gradient(to bottom, rgba(10, 14, 39, 0.1), transparent);
}

.category-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  margin-bottom: 2rem;
  color: #f8fafc;
}
.namelist-badge {
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  border: 1px solid rgba(59, 130, 246, 0.3);
}
.namelist-badge.learning {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border-color: rgba(16, 185, 129, 0.3);
  font-family: var(--font-sans);
}

.schemes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1.5rem;
}

.scheme-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.scheme-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
  background: rgba(30, 41, 59, 0.7);
}
.scheme-card.active {
  border-color: #10b981;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.15), inset 0 0 0 1px #10b981;
}

.scheme-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.scheme-header h4 { 
  margin: 0; 
  font-size: 1.15rem; 
  color: #f8fafc;
}
.value-badge {
  background: rgba(255,255,255,0.1);
  color: #e2e8f0;
  font-family: monospace;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
  font-weight: bold;
  font-size: 0.9rem;
  min-width: 2.5rem;
  text-align: center;
}

.description {
  color: #94a3b8;
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0;
}

.learning-box {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #a7f3d0;
}

.meta-lbl {
  font-weight: bold;
  color: #34d399;
}

.scheme-meta {
  font-size: 0.9rem;
  color: #64748b;
  background: rgba(0,0,0,0.2);
  padding: 0.75rem;
  border-radius: 6px;
}

.actions {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px dashed rgba(255,255,255,0.1);
}

.activate-btn {
  background: transparent;
  border: 1px solid #10b981;
  color: #10b981;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.9rem;
  font-weight: 500;
}
.activate-btn:hover {
  background: #10b981;
  color: #022c22;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}

.active-label {
  color: #10b981;
  font-weight: 600;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}
.active-label::before {
  content: '✓';
  font-weight: bold;
}

.scheme-details {
  border-top: 1px solid rgba(255,255,255,0.1);
  padding-top: 1.25rem;
  margin-top: 0.5rem;
  animation: slideDown 0.3s ease;
}
.scheme-details h5 {
  margin: 0 0 1rem 0;
  color: #e2e8f0;
  font-size: 1rem;
}
.execution-trace { display: grid; gap: .8rem; }
.trace-step { display: grid; grid-template-columns: 27px minmax(0,1fr); gap: .65rem; align-items: start; }
.trace-index { color: #6ee7b7; font: 600 .68rem var(--font-mono); padding-top: .12rem; }
.trace-step strong { color: #dce8e7; font-size: .8rem; font-weight: 620; }
.trace-step p { margin: .28rem 0 0; color: #a8b9c4; font-size: .76rem; line-height: 1.48; }
.trace-step p code { color: #b5d9d1; font: .72rem var(--font-mono); overflow-wrap: anywhere; }
.evidence-link, .trace-deep-link { margin-top: .48rem; padding: 0; border: 0; background: transparent; color: #8bd4c6; cursor: pointer; font-size: .72rem; text-align: left; }
.evidence-link:hover, .trace-deep-link:hover { text-decoration: underline; }
.evidence-list { display: grid; gap: .3rem; margin-top: .5rem; }
.call-entry { display: grid; gap: .12rem; }
.evidence-list button { display: flex; align-items: baseline; justify-content: space-between; gap: .5rem; width: 100%; padding: .45rem .55rem; border: 1px solid rgba(159,193,194,.15); border-radius: 4px; background: rgba(10,24,33,.38); color: #c9d9dc; cursor: pointer; text-align: left; }
.evidence-list button:hover { border-color: rgba(110,231,183,.5); }
.evidence-list .definition-link { display: block; padding: .18rem .55rem .4rem; border: 0; background: transparent; color: #8bd4c6; font: .65rem var(--font-mono); }
.evidence-list code { font: .7rem var(--font-mono); overflow-wrap: anywhere; }
.evidence-list span { color: #8da4b0; font: .59rem var(--font-mono); overflow-wrap: anywhere; text-align: right; }
.unresolved-trace .trace-index { color: #e9ba7a; }
.field-links { display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .5rem; }
.field-links button { padding: .28rem .42rem; border: 1px solid rgba(110,231,183,.23); border-radius: 3px; background: rgba(110,231,183,.06); color: #a7e0d4; font: .62rem var(--font-mono); cursor: pointer; }
.field-links button:hover { border-color: rgba(110,231,183,.6); }
.field-links span { color: #8da4b0; font-size: .62rem; }
.trace-deep-link { margin-left: 2.1rem; }
.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  gap: 1rem;
  font-size: 1.1rem;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
