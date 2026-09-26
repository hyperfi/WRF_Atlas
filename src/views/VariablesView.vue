<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import { useEvidenceStore } from '@/stores/evidenceStore'
import ExecutionTrace from '@/components/graph/ExecutionTrace.vue'
import type { TraceStep } from '@/lib/presentation'
import type { GraphEdge, GraphNode, SourceEvidence } from '@/types/graph'

const graphStore = useGraphStore()
const route = useRoute()
const router = useRouter()
const evidenceStore = useEvidenceStore()

const searchQuery = ref('')
const displayCount = ref(50)
const siteCount = ref(18)
const callerFilter = ref('all')
const selectedVar = ref<GraphNode | null>(null)
const journeyStage = ref('registry')
const featuredFields = ['HFX', 'QFX', 'TSK', 'SMOIS', 'PBLH']

const stateVariables = computed(() => {
  return graphStore.getNodesByType('state_variable')
    .filter(node => /^[a-z][\w]*$/i.test(node.label))
    .sort((a, b) => a.label.localeCompare(b.label))
})

const filteredVariables = computed(() => {
  const query = searchQuery.value.toLowerCase()
  if (!query) return stateVariables.value
  
  return stateVariables.value.filter(v => 
    v.label.toLowerCase().includes(query) || 
    (v.data.description && v.data.description.toLowerCase().includes(query))
  )
})

const displayedVariables = computed(() => {
  return filteredVariables.value.slice(0, displayCount.value)
})

const loadMore = () => {
  displayCount.value += 50
}

const closeVariable = () => {
  selectedVar.value = null
  const { field, selector, value, ...rest } = route.query
  router.replace({ query: rest })
}
const selectVariable = (v: GraphNode) => {
  if (selectedVar.value?.id === v.id) {
    closeVariable()
    return
  }
  selectedVar.value = v
  siteCount.value = 18
  callerFilter.value = 'all'
  journeyStage.value = 'registry'
  router.replace({ query: { field: v.label } })
}

const selectByName = (name: string) => {
  const found = graphStore.getNodeById(`state:${name.toLowerCase()}`)
  if (found) {
    selectVariable(found)
  }
}

// Compute details for selected variable
const relatedPackages = computed(() => {
  if (!selectedVar.value) return []
  const varName = selectedVar.value.data.name || selectedVar.value.label
  return graphStore.getNodesByType('registry_package').filter(p => 
    p.data.state_vars && p.data.state_vars.includes(varName)
  )
})

const referencingSubroutines = computed(() => {
  if (!selectedVar.value) return []
  const varName = selectedVar.value.data.name || selectedVar.value.label
  return graphStore.getNodesByType('subroutine').filter(s => 
    s.data.args && (s.data.args.includes(varName) || s.data.args.includes(selectedVar.value!.label))
  )
})

const selectedScheme = computed(() => {
  const selector = route.query.selector
  const value = route.query.value
  if (typeof selector !== 'string' || typeof value !== 'string') return null
  const path = graphStore.getExecutionPath(selector, value)
  return {
    label: path.nodes.find(node => node.type === 'registry_package')?.label || `${selector}=${value}`,
    keys: new Set(path.edges.filter(edge => edge.type === 'CALLS')
      .map(edge => `${edge.source}:${edge.target}:${edge.data.evidence?.[0]?.startLine}`)),
  }
})
const allCallSites = computed(() => {
  if (!selectedVar.value) return []
  return graphStore.getCallSitesForField(selectedVar.value.label)
    .sort((a, b) => {
      const aKey = `${a.source}:${a.target}:${a.data.evidence?.[0]?.startLine}`
      const bKey = `${b.source}:${b.target}:${b.data.evidence?.[0]?.startLine}`
      const aLinked = selectedScheme.value?.keys.has(aKey) ? 0 : 1
      const bLinked = selectedScheme.value?.keys.has(bKey) ? 0 : 1
      const aDriver = graphStore.getNodeById(a.source)?.type === 'driver' ? 0 : 1
      const bDriver = graphStore.getNodeById(b.source)?.type === 'driver' ? 0 : 1
      return aLinked - bLinked || aDriver - bDriver || a.source.localeCompare(b.source)
    })
})
const callerOptions = computed(() => [...new Set(allCallSites.value.map(edge => edge.source))]
  .sort((a, b) => a.localeCompare(b)))
const callSites = computed(() => callerFilter.value === 'all'
  ? allCallSites.value
  : allCallSites.value.filter(edge => edge.source === callerFilter.value))
const fieldArgument = (edge: GraphEdge) => edge.data?.state_args?.find(
  (arg: { name: string }) => arg.name === selectedVar.value?.label.toLowerCase())?.argument || selectedVar.value?.label
const routineLabel = (id: string) => graphStore.getNodeById(id)?.label || id.replace(/^\w+:/, '')
const openEvidence = (evidence: SourceEvidence | undefined) => {
  if (evidence?.path) evidenceStore.open(evidence, `${selectedVar.value?.label.toUpperCase()} · source reference`, 'exact', 'A matching field name in a declaration or CALL argument does not establish read/write direction or runtime execution.')
}
const registryEvidence = computed<SourceEvidence | undefined>(() => {
  const node = selectedVar.value
  return node?.data?.source_file ? { path: node.data.source_file, startLine: node.data.source_line } : undefined
})

const journeySteps = computed<TraceStep[]>(() => [
  { id: 'registry', label: 'Registry', value: selectedVar.value?.label.toUpperCase() || 'Field', confidence: registryEvidence.value ? 'exact' : 'unresolved' },
  { id: 'interfaces', label: 'Interfaces', value: `${referencingSubroutines.value.length} name matches`, confidence: 'inferred' },
  { id: 'calls', label: 'CALL arguments', value: `${allCallSites.value.length} handoffs`, confidence: allCallSites.value.length ? 'inferred' : 'unresolved' },
])
watch(() => [route.query.field, graphStore.isLoaded, graphStore.activeSnapshotId], () => {
  if (!graphStore.isLoaded) return
  if (typeof route.query.field !== 'string') { selectedVar.value = null; return }
  const found = graphStore.getNodeById(`state:${route.query.field.toLowerCase()}`)
  if (found) {
    selectedVar.value = found
    callerFilter.value = 'all'
    siteCount.value = 18
    journeyStage.value = route.query.selector ? 'calls' : 'registry'
  } else selectedVar.value = null
}, { immediate: true })

onMounted(() => graphStore.loadGraph())
</script>

<template>
  <div class="variables-view" :class="{ 'has-selection': selectedVar }">
    <div class="sidebar glass-panel">
      <div class="search-box">
        <p class="eyebrow">Registry field index</p>
        <h2>Variable Journey</h2>
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="Search variables by name or description..." 
          class="search-input"
          @input="displayCount = 50"
        />
        <div class="var-count">{{ filteredVariables.length }} variables found</div>
        <div class="featured-fields">
          <button v-for="name in featuredFields" :key="name" :aria-pressed="selectedVar?.label.toLowerCase() === name.toLowerCase()" @click="selectByName(name)">{{ name }}</button>
        </div>
        <p class="selection-hint">Click a field again to close its details.</p>
      </div>
      
      <div class="var-list">
        <button
          v-for="v in displayedVariables" 
          :key="v.id"
          class="var-card"
          :class="{ active: selectedVar?.id === v.id }"
          :aria-pressed="selectedVar?.id === v.id"
          @click="selectVariable(v)"
          type="button"
        >
          <div class="var-header">
            <span class="var-name">{{ v.label }}</span>
            <span class="var-type" v-if="v.data.type">{{ v.data.type }}</span>
          </div>
          <div class="var-desc" v-if="v.data.description">{{ v.data.description }}</div>
        </button>
        
        <button 
          v-if="displayCount < filteredVariables.length" 
          @click="loadMore"
          class="load-more-btn"
        >
          Load More
        </button>
      </div>
    </div>
    
    <div class="detail-panel glass-panel">
      <div v-if="selectedVar" class="detail-content">
        <div class="detail-header">
          <button class="back-to-variables" @click="closeVariable">← Back to variables</button>
          <p class="eyebrow">Source-grounded field path</p>
          <h2>{{ selectedVar.label.toUpperCase() }}</h2>
          <div class="tags">
            <span class="tag" v-if="selectedVar.data.type">Type: {{ selectedVar.data.type }}</span>
            <span class="tag" v-if="selectedVar.data.dims">Dims: {{ selectedVar.data.dims }}</span>
            <span class="tag" v-if="selectedVar.data.units">Units: {{ selectedVar.data.units }}</span>
          </div>
        </div>
        
        <div class="detail-section">
          <h3>Description</h3>
          <p class="desc-text">{{ selectedVar.data.description || 'No description available.' }}</p>
        </div>

        <ExecutionTrace :steps="journeySteps" :selected="journeyStage" @inspect="journeyStage = $event" caption="Evidence groups, not an ordered lifecycle. Name matches do not prove a connected data-flow path." />
        <details class="journey-contract">
          <summary>What this trace proves—and what it doesn't</summary>
          <p>Registry identifies the field. A matching name in a routine interface or CALL argument identifies a source-level handoff, not whether that routine reads, modifies, or outputs the field. The Atlas does not infer write direction from argument order.</p>
        </details>
        <div v-if="selectedScheme" class="journey-context">From Physics Explorer: <strong>{{ selectedScheme.label }}</strong>. Matching dispatch calls appear first when this field is passed there.</div>
        
        <div class="journey-step" v-if="journeyStage === 'registry'">
          <span>01</span>
          <div>
            <h3>Registry definition</h3>
            <p>Declared as a WRF state field in the indexed checkout.</p>
            <button v-if="registryEvidence" class="source-info" @click="openEvidence(registryEvidence)">Inspect definition · {{ registryEvidence.path }}:{{ registryEvidence.startLine }} ↗</button>
            <p v-else>No Registry source anchor was resolved in this snapshot.</p>
          </div>
        </div>

        <div class="journey-step" v-if="journeyStage === 'interfaces'">
          <span>02</span>
          <div>
            <h3>Routine interfaces <small>{{ referencingSubroutines.length }} name matches</small></h3>
            <p>These routine declarations include an argument with the same name. This is not a call or an execution claim.</p>
            <div v-if="referencingSubroutines.length" class="routine-list">
              <button v-for="sub in referencingSubroutines.slice(0, 12)" :key="sub.id" @click="openEvidence({ path: sub.data.file, startLine: sub.data.line })">
                <code>{{ sub.label }}</code><span>{{ sub.data.file }}:{{ sub.data.line }} ↗</span>
              </button>
              <small v-if="referencingSubroutines.length > 12">Showing 12 of {{ referencingSubroutines.length }} matching interfaces</small>
            </div>
            <p v-else class="text-muted">No routine declaration has a matching argument in this index.</p>
          </div>
        </div>

        <div class="journey-step" v-if="journeyStage === 'calls'">
          <span>03</span>
          <div>
            <h3>Call-site handoffs <small>{{ callSites.length }} of {{ allCallSites.length }} name matches</small></h3>
            <p>The field name appears as a direct argument at these exact CALL sites. Driver calls appear first; nested conditions may still govern execution.</p>
            <label v-if="callerOptions.length > 1" class="caller-filter">Caller
              <select v-model="callerFilter" @change="siteCount = 18">
                <option value="all">All callers</option>
                <option v-for="caller in callerOptions" :key="caller" :value="caller">{{ routineLabel(caller) }}</option>
              </select>
            </label>
            <div v-if="callSites.length" class="handoff-list">
              <button v-for="(edge, i) in callSites.slice(0, siteCount)" :key="`${edge.source}-${edge.target}-${i}`" @click="openEvidence(edge.data.evidence?.[0])">
                <span class="handoff-chain"><code>{{ routineLabel(edge.source) }}</code> → <code>{{ routineLabel(edge.target) }}</code></span>
                <span class="handoff-meta"><code>{{ fieldArgument(edge) }}</code> · {{ edge.data.evidence?.[0]?.path }}:{{ edge.data.evidence?.[0]?.startLine }} ↗</span>
              </button>
              <button v-if="siteCount < callSites.length" class="more-sites" @click="siteCount += 18">Show more call sites</button>
            </div>
            <p v-else class="text-muted">No direct CALL argument match was found. This is not evidence that the field is unused.</p>
          </div>
        </div>

        <div v-if="relatedPackages.length" class="detail-section package-section">
          <h3>Registry package associations</h3>
          <p>Package membership is configuration metadata; it does not prove a field is exchanged during every run.</p>
          <div class="chip-container"><span v-for="pkg in relatedPackages" :key="pkg.id" class="chip package-chip">{{ pkg.label }}</span></div>
        </div>
      </div>
      
      <div v-else class="empty-state">
        <h3>Select a variable</h3>
        <p>Choose a Registry field to inspect its source definition, routine interfaces, and evidenced call-site handoffs.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.variables-view {
  height: 100%;
  display: flex;
  gap: 1.5rem;
  min-height: 0;
  box-sizing: border-box;
}

.sidebar {
  width: 300px;
  flex-shrink: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel, rgba(15, 23, 42, 0.6));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 8px;
  overflow: hidden;
}

.search-box {
  padding: 1.25rem;
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  background: var(--bg-surface);
}
.search-box h2 { margin: 4px 0 15px; font-size: 1.15rem; font-weight: 620; }
.eyebrow { margin: 0; color: var(--accent-emerald); font: 600 .61rem var(--font-mono); letter-spacing: .08em; text-transform: uppercase; }
.featured-fields { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.featured-fields button { padding: 5px 8px; border: 1px solid var(--border-subtle); border-radius: 4px; background: var(--bg-inset); color: var(--text-secondary); font: .65rem var(--font-mono); cursor: pointer; }
.featured-fields button:hover { border-color: var(--accent-emerald); color: var(--text-primary); }
.featured-fields button[aria-pressed="true"] { background: var(--accent-soft); border-color: var(--accent-emerald); color: var(--text-primary); }
.selection-hint { margin-top: 12px; color: var(--text-secondary); font-size: .7rem; }

.search-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--text-primary, #e2e8f0);
  font-size: 0.95rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--accent-blue, #3b82f6);
}

.var-count {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: var(--text-muted, #64748b);
}

.var-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.var-list::-webkit-scrollbar {
  width: 6px;
}
.var-list::-webkit-scrollbar-thumb {
  background: var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 3px;
}

.var-card {
  width: 100%;
  text-align: left;
  color: var(--text-primary);
  padding: 1rem;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.var-card:hover {
  border-color: var(--accent-blue, #3b82f6);
  background: var(--bg-surface-hover);
}

.var-card.active {
  border-color: var(--accent-blue, #3b82f6);
  background: var(--accent-soft);
}

.var-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.var-name {
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  font-size: 1.05rem;
}

.var-type {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 4px;
  color: var(--accent-cyan, #06b6d4);
  text-transform: uppercase;
}

.var-desc {
  font-size: 0.85rem;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.load-more-btn {
  margin: 1rem 0;
  padding: 0.75rem;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  color: var(--text-primary, #e2e8f0);
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.load-more-btn:hover {
  background: var(--bg-surface-hover);
}

.detail-panel {
  flex: 1;
  min-width: 0;
  background: var(--bg-panel, rgba(15, 23, 42, 0.6));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 8px;
  overflow-y: auto;
}

.detail-content {
  padding: 24px;
}
.back-to-variables { display: block; margin-bottom: 18px; padding: 6px 10px; border: 1px solid var(--border-strong); border-radius: 4px; background: var(--bg-inset); color: var(--text-primary); font-size: .76rem; cursor: pointer; }
.journey-contract { margin: 18px 0 25px; padding: 13px 16px; border-left: 2px solid var(--accent-amber); background: var(--bg-inset); }
.journey-contract summary { cursor: pointer; color: var(--text-secondary); font-size: .75rem; }
.journey-contract strong { font-size: .76rem; }
.journey-context { margin: -12px 0 25px; padding: 10px 13px; border: 1px solid var(--border-subtle); border-radius: 4px; background: var(--accent-soft); color: var(--text-secondary); font-size: .69rem; }
.journey-context strong { color: var(--text-primary); }
.journey-contract p,.journey-step p,.package-section p { margin: 6px 0 0; color: var(--text-secondary); font-size: .8rem; line-height: 1.65; }
.journey-step { display: grid; grid-template-columns: 30px minmax(0,1fr); gap: 12px; margin-bottom: 27px; }
.journey-step > span { padding-top: 2px; color: var(--accent-emerald); font: 650 .69rem var(--font-mono); }
.journey-step h3 { margin: 0; font-size: .94rem; font-weight: 620; }
.journey-step h3 small { margin-left: 8px; color: var(--text-muted); font-size: .65rem; font-weight: 450; }
.routine-list,.handoff-list { display: grid; gap: 5px; margin-top: 12px; }
.routine-list button,.handoff-list button { display: flex; width: 100%; justify-content: space-between; gap: 14px; padding: 9px 11px; border: 1px solid var(--border-subtle); border-radius: 4px; background: var(--bg-inset); color: var(--text-primary); cursor: pointer; text-align: left; }
.routine-list button:hover,.handoff-list button:hover { border-color: var(--accent-emerald); }
.routine-list code,.handoff-chain code { font-size: .69rem; }
.routine-list button span,.handoff-meta { color: var(--text-secondary); font: .69rem var(--font-mono); overflow-wrap: anywhere; text-align: right; }
.routine-list > small { color: var(--text-muted); font-size: .65rem; }
.handoff-list button { flex-direction: column; gap: 4px; }
.handoff-meta { text-align: left; }
.handoff-meta code { color: var(--accent-emerald); }
.caller-filter { display: flex; align-items: center; gap: 10px; margin-top: 12px; color: var(--text-muted); font-size: .67rem; }
.caller-filter select { min-width: 210px; max-width: 100%; padding: 6px 9px; border: 1px solid var(--border-strong); border-radius: 4px; background: var(--bg-inset); color: var(--text-primary); font-size: .67rem; }
.handoff-list .more-sites { display: block; color: var(--accent-emerald); text-align: center; }
.package-section { margin-left: 42px; }
.package-section h3 { margin-bottom: 5px; }
.package-section .chip-container { margin-top: 10px; }

.detail-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
}

.detail-header h2 {
  font-size: 1.8rem;
  margin: 0 0 1rem 0;
  color: var(--text-primary, #e2e8f0);
}

.tags {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.85rem;
  padding: 0.35rem 0.75rem;
  background: var(--bg-inset);
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 4px;
  color: var(--text-secondary, #94a3b8);
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h3 {
  font-size: 1.1rem;
  color: var(--text-primary, #e2e8f0);
  margin: 0 0 1rem 0;
  font-weight: 600;
}

.desc-text {
  color: var(--text-secondary, #94a3b8);
  line-height: 1.6;
  font-size: 1.05rem;
  margin: 0;
}

.source-info {
  display: block;
  width: 100%;
  margin-top: 11px;
  cursor: pointer;
  text-align: left;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  color: var(--text-secondary, #94a3b8);
  font-family: monospace;
  font-size: 0.95rem;
}

.source-info code {
  color: var(--accent-purple, #8b5cf6);
}

.chip-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  padding: 0.4rem 0.8rem;
  border-radius: 16px;
  font-size: 0.85rem;
  font-weight: 500;
}

.package-chip {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.sub-chip {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.text-muted {
  color: var(--text-muted, #64748b);
  font-style: italic;
  margin: 0;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted, #64748b);
  text-align: center;
  padding: 2rem;
}

.empty-state .icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h3 {
  color: var(--text-secondary, #94a3b8);
  margin: 0 0 0.5rem 0;
}

.empty-state p {
  max-width: 300px;
  margin: 0;
}
@media (max-width: 1100px) { .sidebar { width: 250px; }.variables-view { gap: 16px; }.detail-content { padding: 19px; }.routine-list button { flex-direction: column; gap: 5px; }.routine-list button span { text-align: left; } }
@media (max-width: 800px) { .variables-view { height: auto; min-height: 70vh; }.sidebar { width: 100%; min-height: 65vh; }.detail-panel { display: none; }.has-selection .sidebar { display: none; }.has-selection .detail-panel { display: block; width: 100%; }.detail-content { padding: 18px; }.caller-filter { flex-direction: column; align-items: start; }.caller-filter select { min-width: 0; width: 100%; }.source-info { overflow-wrap: anywhere; font-size: .76rem; } }
</style>
