<template>
  <div class="namelist-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">Configuration → executable code</p>
        <h1>Trace a namelist decision</h1>
        <p>Choose one physics selector and follow the evidence WRF uses to reach its active implementation branch.</p>
      </div>
      <div class="evidence-key" aria-label="Evidence confidence legend">
        <span><i class="exact"></i> Direct source evidence</span>
        <span><i class="inferred"></i> Joined from source facts</span>
      </div>
    </header>

    <div v-if="!graphStore.isLoaded" class="loading-panel surface-panel">Reading configuration and dispatch indexes…</div>

    <template v-else>
      <section class="decision-bar surface-panel">
        <div class="decision-question">
          <span class="decision-index">01</span>
          <div>
            <p class="eyebrow">Physics family</p>
            <h2>Which WRF decision should we trace?</h2>
          </div>
        </div>
        <div class="category-tabs" role="tablist" aria-label="Physics selectors">
          <button
            v-for="(category, key) in PHYSICS_CATEGORIES"
            :key="key"
            :class="{ active: focusedNamelist === category.namelist }"
            role="tab"
            @click="focusCategory(category.namelist)"
          >
            <span>{{ categoryCode(String(key)) }}</span>
            {{ shortCategoryLabel(category.label) }}
          </button>
        </div>
      </section>

      <div class="lab-grid">
        <aside class="configuration-panel surface-panel">
          <div class="panel-heading">
            <div>
              <p class="eyebrow">Selected configuration</p>
              <h2>{{ focusedCategory?.label }}</h2>
            </div>
            <span class="panel-number">02</span>
          </div>

          <div class="config-control">
            <label :for="focusedNamelist"><code>{{ focusedNamelist }}</code></label>
            <select
              :id="focusedNamelist"
              :value="selectedValue"
              @change="setFocusedValue(Number(($event.target as HTMLSelectElement).value))"
            >
              <option v-for="option in focusedOptions" :key="option.value" :value="Number(option.value)">
                {{ option.value }} · {{ option.description }}
              </option>
            </select>
          </div>

          <div class="namelist-snippet">
            <div class="snippet-header"><span>namelist.input</span><span>&amp;physics</span></div>
            <pre><span>{{ focusedNamelist }}</span> = <strong>{{ selectedValue }}</strong>,</pre>
          </div>

          <dl class="selection-facts">
            <div>
              <dt>Registry package</dt>
              <dd><code>{{ activePackage?.data?.package_name || activePackage?.label || 'Unresolved' }}</code></dd>
            </div>
            <div>
              <dt>Runtime driver</dt>
              <dd><code>{{ hasRuntimeDispatch ? focusedNamelistNode?.data?.driver : 'Not yet resolved' }}</code></dd>
            </div>
            <div>
              <dt>Calls in matching branch</dt>
              <dd>{{ dispatchCalls.length }} indexed call{{ dispatchCalls.length === 1 ? '' : 's' }}</dd>
            </div>
          </dl>

          <div class="source-contract">
            <strong>Evidence contract</strong>
            <p>Solid relationships come from an indexed Registry predicate or Fortran call. Dotted joins connect those separately proven facts and remain marked inferred.</p>
          </div>
        </aside>

        <main class="trace-workspace surface-panel">
          <div class="workspace-heading">
            <div>
              <p class="eyebrow">Active path</p>
              <h2>{{ focusedNamelist }} = {{ selectedValue }}</h2>
            </div>
            <div class="workspace-summary">
              <button v-if="dispatchCalls.length > focusedDispatchCalls.length" @click="showAllCalls = !showAllCalls">
                {{ showAllCalls ? 'Show focused path' : `Show all ${dispatchCalls.length} calls` }}
              </button>
              <span>{{ graphNodes.length }} visible nodes</span>
              <span>{{ exactEvidenceCount }} evidenced edges</span>
            </div>
          </div>

          <div v-if="pathNodes.length > 1" class="graph-stage">
            <GraphView
              :nodes="graphNodes"
              :edges="graphEdges"
              layout="tree-tb"
              @node-click="selectedNode = $event"
            />
          </div>
          <div v-else class="unresolved-state">
            <strong>No implementation branch was resolved for this value.</strong>
            <p>The Registry option is indexed, but the current parser could not join it to a matching driver CASE. The Atlas will not invent that relationship.</p>
          </div>
        </main>

        <aside class="evidence-panel surface-panel">
          <div class="panel-heading">
            <div>
              <p class="eyebrow">Why active?</p>
              <h2>{{ activePackage?.label || focusedNamelist }}</h2>
            </div>
            <span class="panel-number">03</span>
          </div>

          <div class="reasoning-chain">
            <article class="reason-step">
              <span class="reason-marker exact">1</span>
              <div>
                <span class="confidence-label exact">Exact · Registry</span>
                <h3>The selected value satisfies a package predicate.</h3>
                <code>{{ focusedNamelist }} == {{ selectedValue }} → {{ activePackage?.data?.package_name || activePackage?.label }}</code>
                <button v-if="registryEvidence" @click="openEvidence(registryEvidence)">Open Registry evidence <span>↗</span></button>
              </div>
            </article>

            <article class="reason-step">
              <span class="reason-marker" :class="hasRuntimeDispatch ? 'inferred' : 'unresolved'">2</span>
              <div>
                <template v-if="hasRuntimeDispatch">
                  <span class="confidence-label inferred">Inferred · symbolic join</span>
                  <h3>The package constant matches a driver dispatch branch.</h3>
                  <code>CASE ({{ activePackage?.data?.package_name || activePackage?.label || '?' }})</code>
                  <p>The numeric Registry value and symbolic CASE are joined through the package constant.</p>
                </template>
                <template v-else>
                  <span class="confidence-label unresolved">Unresolved · runtime join</span>
                  <h3>No standalone driver dispatch has been joined.</h3>
                  <p>This selector is handled through conditional logic embedded in other physics branches. The Registry mapping is exact; the Atlas does not manufacture a CASE edge.</p>
                </template>
              </div>
            </article>

            <article class="reason-step">
              <span class="reason-marker" :class="dispatchCalls.length ? 'exact' : 'unresolved'">3</span>
              <div>
                <span class="confidence-label" :class="dispatchCalls.length ? 'exact' : 'unresolved'">{{ dispatchCalls.length ? 'Exact · Fortran calls' : 'Unresolved · conditional calls' }}</span>
                <h3>{{ dispatchCalls.length ? `The matching CASE contains ${dispatchCalls.length} indexed calls.` : 'No calls are attributed to a resolved selector branch.' }}</h3>
                <div class="call-list">
                  <button
                    v-for="edge in dispatchCalls.slice(0, 8)"
                    :key="`${edge.target}-${edge.data?.evidence?.[0]?.startLine}`"
                    @click="selectCall(edge)"
                  >
                    <code>{{ graphStore.getNodeById(edge.target)?.label || edge.target }}</code>
                    <span>L{{ edge.data?.evidence?.[0]?.startLine || '?' }}</span>
                  </button>
                </div>
                <p v-if="dispatchCalls.length > 8" class="more-calls">+ {{ dispatchCalls.length - 8 }} more calls in the graph</p>
              </div>
            </article>
          </div>

          <div v-if="selectedNode" class="selected-inspector">
            <div class="inspector-heading">
              <span>{{ formatNodeType(selectedNode.type) }}</span>
              <button @click="selectedNode = null" aria-label="Close selection">×</button>
            </div>
            <h3><code>{{ selectedNode.label }}</code></h3>
            <p>{{ nodeExplanation(selectedNode) }}</p>
            <button v-if="nodeEvidence(selectedNode)" class="open-source" @click="openEvidence(nodeEvidence(selectedNode)!)">
              View source at line {{ nodeEvidence(selectedNode)?.startLine || selectedNode.data?.line }} <span>↗</span>
            </button>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConfigStore } from '@/stores/configStore'
import { useGraphStore } from '@/stores/graphStore'
import GraphView from '@/components/graph/GraphView.vue'
import { PHYSICS_CATEGORIES } from '@/types/graph'
import type { GraphEdge, GraphNode, SourceEvidence } from '@/types/graph'

const route = useRoute()
const router = useRouter()
const configStore = useConfigStore()
const graphStore = useGraphStore()

const initialFocus = typeof route.query.focus === 'string' && Object.values(PHYSICS_CATEGORIES).some(c => c.namelist === route.query.focus)
  ? route.query.focus
  : 'sf_surface_physics'
const focusedNamelist = ref(initialFocus)
const selectedNode = ref<GraphNode | null>(null)
const showAllCalls = ref(false)

const focusedCategory = computed(() => Object.values(PHYSICS_CATEGORIES).find(category => category.namelist === focusedNamelist.value))
const focusedNamelistNode = computed(() => graphStore.getNodeById(`namelist:${focusedNamelist.value}`))
const focusedOptions = computed(() => graphStore.getPackagesForNamelist(focusedNamelist.value))
const selectedValue = computed(() => {
  const configured = Number(configStore.getConfig(focusedNamelist.value))
  if (focusedOptions.value.some(option => Number(option.value) === configured)) return configured
  return Number(focusedOptions.value[0]?.value ?? 0)
})
const activePackage = computed(() => focusedOptions.value.find(option => Number(option.value) === selectedValue.value)?.node)
const executionPath = computed(() => graphStore.getExecutionPath(focusedNamelist.value, String(selectedValue.value)))
const pathNodes = computed(() => executionPath.value.nodes)
const pathEdges = computed(() => executionPath.value.edges)
const dispatchCalls = computed(() => pathEdges.value.filter(edge => edge.type === 'CALLS'))
const focusedDispatchCalls = computed(() => {
  const infrastructure = /^(wrf_debug|wrf_error_fatal|add_multi_perturb|remove_multi_perturb)/i
  const scientific = dispatchCalls.value.filter(edge => !infrastructure.test(graphStore.getNodeById(edge.target)?.label || ''))
  return (scientific.length ? scientific : dispatchCalls.value).slice(0, 4)
})
const graphEdges = computed(() => {
  if (showAllCalls.value) return pathEdges.value
  const shownCalls = new Set(focusedDispatchCalls.value)
  return pathEdges.value.filter(edge => edge.type !== 'CALLS' || shownCalls.has(edge))
})
const graphNodes = computed(() => {
  if (showAllCalls.value) return pathNodes.value
  const visibleIds = new Set(graphEdges.value.flatMap(edge => [edge.source, edge.target]))
  return pathNodes.value.filter(node => visibleIds.has(node.id))
})
const hasRuntimeDispatch = computed(() => pathEdges.value.some(edge => edge.type === 'DISPATCHES_THROUGH'))
const exactEvidenceCount = computed(() => pathEdges.value.filter(edge => edge.data?.confidence === 'exact' && edge.data?.evidence?.length).length)
const registryEdge = computed(() => pathEdges.value.find(edge => edge.type === 'SELECTS'))
const registryEvidence = computed(() => registryEdge.value?.data?.evidence?.[0])

const categoryCode = (key: string) => key.split('_').map(word => word[0]).join('').slice(0, 3).toUpperCase()
const shortCategoryLabel = (label: string) => label
  .replace('Planetary Boundary Layer', 'PBL')
  .replace('Longwave Radiation', 'LW Radiation')
  .replace('Shortwave Radiation', 'SW Radiation')

const focusCategory = (namelist: string) => {
  focusedNamelist.value = namelist
  const configured = Number(configStore.getConfig(namelist))
  if (!focusedOptions.value.some(option => Number(option.value) === configured) && focusedOptions.value[0]) {
    configStore.setConfig(namelist, Number(focusedOptions.value[0].value))
  }
  selectedNode.value = null
  showAllCalls.value = false
}

const setFocusedValue = (value: number) => {
  configStore.setConfig(focusedNamelist.value, value)
  selectedNode.value = null
  showAllCalls.value = false
}

const openEvidence = (evidence: SourceEvidence) => {
  router.push({ path: '/source', query: { file: evidence.path, line: String(evidence.startLine || 1) } })
}

const selectCall = (edge: GraphEdge) => {
  selectedNode.value = graphStore.getNodeById(edge.target) || null
  const evidence = edge.data?.evidence?.[0]
  if (evidence) openEvidence(evidence)
}

const nodeEvidence = (node: GraphNode): SourceEvidence | undefined => {
  const connected = pathEdges.value.find(edge => edge.target === node.id || edge.source === node.id)
  const indexed = connected?.data?.evidence?.[0]
  if (indexed) return indexed
  const path = node.data?.file || node.data?.path || node.data?.source_file
  if (!path) return undefined
  return { path, startLine: node.data?.line || node.data?.source_line || 1 }
}

const formatNodeType = (type: string) => type.replaceAll('_', ' ')
const nodeExplanation = (node: GraphNode) => {
  if (node.type === 'namelist_option') return 'A user-facing configuration value stored by WRF configuration machinery.'
  if (node.type === 'registry_package') return 'A Registry package predicate that associates a symbolic constant with the selected value.'
  if (node.type === 'driver') return 'The runtime driver containing the indexed SELECT CASE dispatch.'
  if (node.type === 'subroutine') return 'A routine called inside the matching dispatch branch. Open the source to inspect its arguments and surrounding conditions.'
  return node.data?.description || 'An indexed WRF source entity in this configuration path.'
}

watch(focusedNamelist, namelist => {
  router.replace({ query: { ...route.query, focus: namelist, value: String(selectedValue.value) } })
})

watch(() => [route.query.focus, route.query.value], ([focus, value]) => {
  if (typeof focus !== 'string' || !Object.values(PHYSICS_CATEGORIES).some(category => category.namelist === focus)) return
  focusedNamelist.value = focus
  const requested = Number(value)
  if (Number.isFinite(requested) && focusedOptions.value.some(option => Number(option.value) === requested)) {
    configStore.setConfig(focus, requested)
  } else if (focusedOptions.value[0]) {
    configStore.setConfig(focus, Number(focusedOptions.value[0].value))
  }
  selectedNode.value = null
  showAllCalls.value = false
}, { flush: 'post' })

onMounted(async () => {
  await graphStore.loadGraph()
  if (typeof route.query.value === 'string') {
    const queryValue = Number(route.query.value)
    if (Number.isFinite(queryValue) && focusedOptions.value.some(option => Number(option.value) === queryValue)) {
      configStore.setConfig(focusedNamelist.value, queryValue)
    }
  }
})
</script>

<style scoped>
.namelist-view { display: flex; width: 100%; max-width: 1540px; margin: 0 auto; flex-direction: column; gap: 18px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; padding: 4px 2px 8px; }
.page-header h1 { margin-top: 7px; font-size: 2rem; font-weight: 580; }
.page-header > div > p:last-child { max-width: 730px; margin-top: 8px; color: var(--text-secondary); font-size: 0.83rem; }
.evidence-key { display: flex; gap: 18px; padding-bottom: 5px; color: var(--text-muted); font-size: 0.66rem; }
.evidence-key span { display: flex; align-items: center; gap: 6px; }.evidence-key i { width: 14px; height: 2px; }.evidence-key i.exact { background: var(--accent-emerald); }.evidence-key i.inferred { border-top: 2px dotted var(--accent-amber); }
.loading-panel { display: grid; min-height: 420px; place-items: center; color: var(--text-muted); }

.decision-bar { display: grid; grid-template-columns: 330px minmax(0, 1fr); align-items: center; min-height: 82px; padding: 14px 16px 14px 20px; }
.decision-question { display: flex; align-items: center; gap: 15px; }
.decision-question h2 { margin-top: 3px; font-size: 0.9rem; }
.decision-index, .panel-number { color: var(--border-strong); font-family: var(--font-mono); font-size: 0.68rem; }
.category-tabs { display: flex; justify-content: flex-end; gap: 5px; overflow-x: auto; }
.category-tabs button { display: flex; height: 38px; align-items: center; gap: 7px; padding: 0 10px; background: transparent; border: 1px solid transparent; border-radius: 5px; color: var(--text-muted); cursor: pointer; font-size: 0.68rem; white-space: nowrap; }
.category-tabs button:hover { background: var(--bg-surface-hover); color: var(--text-secondary); }.category-tabs button.active { background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent-emerald) 28%, var(--border-subtle)); color: var(--text-primary); }
.category-tabs button span { color: var(--accent-emerald); font-family: var(--font-mono); font-size: 0.55rem; font-weight: 650; }

.lab-grid { display: grid; min-height: 680px; grid-template-columns: 278px minmax(500px, 1fr) 350px; gap: 14px; }
.configuration-panel, .trace-workspace, .evidence-panel { min-width: 0; overflow: hidden; }
.panel-heading, .workspace-heading { display: flex; min-height: 74px; align-items: flex-start; justify-content: space-between; padding: 17px 18px; border-bottom: 1px solid var(--border-subtle); }
.panel-heading h2, .workspace-heading h2 { margin-top: 5px; font-size: 0.95rem; }
.config-control { padding: 20px 18px 16px; }
.config-control label { display: block; margin-bottom: 9px; color: var(--accent-amber); font-size: 0.72rem; }
.config-control select { width: 100%; height: 40px; padding: 0 30px 0 10px; background: var(--bg-inset); border: 1px solid var(--border-strong); border-radius: 5px; color: var(--text-primary); font-size: 0.76rem; }
.namelist-snippet { margin: 0 18px 18px; overflow: hidden; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 5px; }
.snippet-header { display: flex; justify-content: space-between; padding: 7px 9px; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle); font-family: var(--font-mono); font-size: 0.57rem; }
.namelist-snippet pre { overflow-x: auto; padding: 13px 10px; color: var(--text-secondary); font-family: var(--font-mono); font-size: 0.65rem; }.namelist-snippet pre span { color: var(--accent-amber); }.namelist-snippet pre strong { color: var(--text-primary); }
.selection-facts { border-top: 1px solid var(--border-subtle); }
.selection-facts div { padding: 13px 18px; border-bottom: 1px solid var(--border-subtle); }
.selection-facts dt { margin-bottom: 3px; color: var(--text-muted); font-size: 0.62rem; }.selection-facts dd { color: var(--text-secondary); font-size: 0.72rem; }.selection-facts code { color: var(--text-primary); }
.source-contract { margin: 18px; padding: 12px; background: var(--accent-soft); border-left: 2px solid var(--accent-emerald); }.source-contract strong { font-size: 0.69rem; }.source-contract p { margin-top: 5px; color: var(--text-muted); font-size: 0.63rem; line-height: 1.5; }

.trace-workspace { display: flex; flex-direction: column; }
.workspace-heading { align-items: center; }.workspace-heading h2 { font-family: var(--font-mono); }
.workspace-summary { display: flex; align-items: center; gap: 12px; color: var(--text-muted); font-family: var(--font-mono); font-size: 0.61rem; }.workspace-summary button { padding: 6px 8px; background: var(--accent-soft); border: 1px solid color-mix(in srgb,var(--accent-emerald) 30%,var(--border-subtle)); border-radius: 4px; color: var(--accent-emerald); cursor: pointer; font: inherit; }
.graph-stage { flex: 1; min-height: 600px; background: var(--bg-inset); }
.graph-stage :deep(.graph-toolbar) { top: 6px; left: 6px; right: auto; margin: 0; }
.graph-stage :deep(.toolbar-group:first-child .tool-btn:not(.active)), .graph-stage :deep(.toolbar-label), .graph-stage :deep(.toolbar-divider), .graph-stage :deep(.graph-search) { display: none; }
.graph-stage :deep(.legend-bar) { bottom: 12px; left: 12px; }
.unresolved-state { display: flex; flex: 1; flex-direction: column; align-items: center; justify-content: center; padding: 50px; text-align: center; }.unresolved-state p { max-width: 480px; margin-top: 10px; color: var(--text-muted); font-size: 0.75rem; }

.evidence-panel { overflow-y: auto; }
.reasoning-chain { padding: 20px 18px; }
.reason-step { position: relative; display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 11px; padding-bottom: 21px; }
.reason-step:not(:last-child)::after { position: absolute; top: 25px; bottom: 3px; left: 12px; width: 1px; background: var(--border-subtle); content: ''; }
.reason-marker { position: relative; z-index: 1; display: grid; width: 25px; height: 25px; place-items: center; background: var(--bg-inset); border: 1px solid var(--border-strong); border-radius: 50%; font-family: var(--font-mono); font-size: 0.59rem; }.reason-marker.exact { color: var(--accent-emerald); }.reason-marker.inferred { color: var(--accent-amber); border-style: dashed; }.reason-marker.unresolved { color: var(--text-muted); border-style: dotted; }
.confidence-label { font-family: var(--font-mono); font-size: 0.56rem; text-transform: uppercase; letter-spacing: 0.05em; }.confidence-label.exact { color: var(--accent-emerald); }.confidence-label.inferred { color: var(--accent-amber); }.confidence-label.unresolved { color: var(--text-muted); }
.reason-step h3 { margin: 5px 0 7px; font-size: 0.75rem; line-height: 1.4; }.reason-step code { color: var(--text-secondary); font-size: 0.62rem; }.reason-step p { margin-top: 7px; color: var(--text-muted); font-size: 0.63rem; line-height: 1.5; }
.reason-step > div > button { display: flex; width: 100%; align-items: center; justify-content: space-between; margin-top: 9px; padding: 7px 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; font-size: 0.62rem; }.reason-step button:hover { border-color: var(--border-strong); color: var(--text-primary); }
.call-list { display: flex; flex-direction: column; gap: 4px; margin-top: 9px; }.call-list button { display: flex; width: 100%; align-items: center; justify-content: space-between; padding: 6px 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; }.call-list button code { overflow: hidden; color: var(--text-secondary); text-overflow: ellipsis; white-space: nowrap; }.call-list button span { color: var(--text-muted); font-family: var(--font-mono); font-size: 0.55rem; }.more-calls { margin-left: 8px; }
.selected-inspector { margin: 0 18px 18px; padding: 13px; background: var(--bg-inset); border: 1px solid var(--border-strong); border-radius: 5px; }.inspector-heading { display: flex; align-items: center; justify-content: space-between; color: var(--accent-blue); font-family: var(--font-mono); font-size: 0.57rem; text-transform: uppercase; }.inspector-heading button { background: transparent; border: 0; color: var(--text-muted); cursor: pointer; }.selected-inspector h3 { margin-top: 7px; font-size: 0.8rem; }.selected-inspector p { margin-top: 7px; color: var(--text-muted); font-size: 0.64rem; line-height: 1.5; }.open-source { display: flex; width: 100%; align-items: center; justify-content: space-between; margin-top: 11px; padding: 8px; background: var(--accent-soft); border: 1px solid color-mix(in srgb, var(--accent-emerald) 28%, var(--border-subtle)); border-radius: 4px; color: var(--accent-emerald); cursor: pointer; font-size: 0.62rem; }

@media (max-width: 1450px) {
  .lab-grid { grid-template-columns: 255px minmax(0, 1fr); }
  .evidence-panel { grid-column: 1 / -1; }
  .reasoning-chain { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
  .reason-step { grid-template-columns: 28px minmax(0, 1fr); padding-bottom: 0; }
  .reason-step:not(:last-child)::after { display: none; }
  .selected-inspector { max-width: 600px; }
  .decision-bar { grid-template-columns: 260px minmax(0, 1fr); }
}
@media (max-width: 1050px) { .decision-bar { grid-template-columns: 1fr; gap: 14px; }.category-tabs { justify-content: flex-start; }.lab-grid { grid-template-columns: 1fr; }.configuration-panel, .evidence-panel { grid-column: 1; }.reasoning-chain { grid-template-columns: 1fr; }.page-header { align-items: flex-start; flex-direction: column; } }
</style>
