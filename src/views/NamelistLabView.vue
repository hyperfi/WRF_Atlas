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
      <section class="namelist-import surface-panel">
        <div class="import-heading">
          <div>
            <p class="eyebrow">Configuration workspace</p>
            <h2>{{ configStore.namelistText === null ? 'Explore an example, or load your namelist' : 'Loaded namelist.input' }}</h2>
            <p>{{ configStore.namelistText === null ? 'The initial selections are an illustrative example, not WRF defaults.' : 'Edits to the controls update this local working copy. Nothing is uploaded or written to your WRF checkout.' }}</p>
          </div>
          <div class="import-actions">
            <input ref="namelistFileInput" type="file" accept=".input,.txt,.nml,.namelist,text/plain" hidden @change="loadNamelistFile" />
            <button @click="namelistFileInput?.click()">Load file</button>
            <button @click="showNamelistEditor = !showNamelistEditor">{{ showNamelistEditor ? 'Hide text' : 'Paste / edit text' }}</button>
            <button v-if="configStore.namelistText !== null" @click="configStore.clearNamelist(); showNamelistEditor = false">Clear</button>
          </div>
        </div>
        <textarea
          v-if="showNamelistEditor"
          class="namelist-editor"
          :value="configStore.namelistText ?? ''"
          placeholder="Paste the contents of namelist.input here. The Atlas reads it locally in your browser."
          spellcheck="false"
          aria-label="Namelist input text"
          @input="configStore.setNamelistText(($event.target as HTMLTextAreaElement).value, false)"
        ></textarea>
        <div v-if="configStore.namelistText !== null" class="import-status">
          <label>Domain
            <select v-model.number="configStore.activeDomain">
              <option v-for="domain in configStore.maxDomain" :key="domain" :value="domain">d{{ String(domain).padStart(2, '0') }}</option>
            </select>
          </label>
          <span>{{ configStore.maxDomain }} domain{{ configStore.maxDomain === 1 ? '' : 's' }} detected</span>
          <span>Physics suite: <code>{{ configStore.physicsSuite || 'none / unspecified' }}</code></span>
          <span v-if="configStore.parsedNamelist?.warnings.length" class="parse-warning">{{ configStore.parsedNamelist.warnings[0] }}</span>
        </div>
        <div v-if="configStore.namelistText !== null && suiteSettings.length" class="suite-summary">
          <strong>Suite resolution for d{{ String(configStore.activeDomain).padStart(2, '0') }}</strong>
          <p>WRF fills an option from this suite only when its configured value is <code>-1</code>; an explicit value takes precedence. Each row below is joined to this checkout's Registry value and suite-setting line.</p>
          <div class="suite-rows">
            <button v-for="edge in suiteSettings" :key="edge.target" @click="openEvidence(edge.data.evidence?.[0])">
              <code>{{ edge.target.replace('namelist:', '') }}</code>
              <span>{{ configStore.getConfigOrigin(edge.target.replace('namelist:', '')) === 'namelist' ? 'explicit override' : 'from suite' }}</span>
              <strong>{{ configStore.getConfig(edge.target.replace('namelist:', '')) ?? '?' }}</strong>
              <small>source ↗</small>
            </button>
          </div>
        </div>
        <div v-if="configStore.namelistText !== null" class="constraint-summary">
          <strong>Indexed combination checks · d{{ String(configStore.activeDomain).padStart(2, '0') }}</strong>
          <p>These are source-extracted two-option checks, not a replacement for WRF's full namelist validation.</p>
          <div v-if="constraintWarnings.length" class="constraint-list">
            <button v-for="(edge, i) in constraintWarnings" :key="i" @click="openEvidence(edge.data.evidence?.[0])">
              <code>{{ edge.source.replace('namelist:', '') }} = {{ edge.data.value }}</code>
              requires <code>{{ edge.target.replace('namelist:', '') }} = {{ edge.data.required_value }}</code>
              <span>Current: {{ configStore.getConfig(edge.target.replace('namelist:', '')) }} · source ↗</span>
            </button>
          </div>
          <span v-else class="constraint-clear">No mismatch found among {{ indexedConstraints.length }} indexed two-option checks for this domain.</span>
        </div>
      </section>
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
              :value="selectedValue ?? ''"
              @change="setFocusedValue(Number(($event.target as HTMLSelectElement).value))"
            >
              <option v-if="selectedValue === null" value="" disabled>Not resolved from loaded namelist</option>
              <option v-for="option in focusedOptions" :key="option.value" :value="Number(option.value)">
                {{ option.value }} · {{ option.description }}
              </option>
            </select>
          </div>

          <div class="namelist-snippet">
            <div class="snippet-header"><span>{{ configStore.namelistText === null ? 'Example selection' : `namelist.input · d${String(configStore.activeDomain).padStart(2, '0')}` }}</span><span>&amp;physics</span></div>
            <pre><span>{{ focusedNamelist }}</span> = <strong>{{ configStore.namelistText === null ? selectedValue : (configStore.getRawConfig(focusedNamelist) ?? 'not specified') }}</strong><template v-if="configStore.getConfigOrigin(focusedNamelist) === 'suite'">  → effective {{ selectedValue }} from suite</template></pre>
          </div>

          <dl class="selection-facts">
            <div>
              <dt>Registry package</dt>
              <dd><code>{{ activePackage?.data?.package_name || activePackage?.label || 'Unresolved' }}</code></dd>
            </div>
            <div>
              <dt>Value origin</dt>
              <dd>{{ originLabel }}</dd>
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
              <h2>{{ focusedNamelist }} = {{ selectedValue ?? 'unresolved' }}</h2>
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
            <strong>{{ selectedValue === null ? 'No effective value was resolved for this domain.' : 'No implementation branch was resolved for this value.' }}</strong>
            <p>{{ selectedValue === null ? 'Check the loaded namelist or select a value. The Atlas will not substitute an arbitrary scheme.' : 'The Registry option is indexed, but the current parser could not join it to a matching driver CASE. The Atlas will not invent that relationship.' }}</p>
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
              <span class="reason-marker" :class="selectedValue === null ? 'unresolved' : 'exact'">1</span>
              <div>
                <span class="confidence-label" :class="selectedValue === null ? 'unresolved' : 'exact'">{{ selectedValue === null ? 'Unresolved · no selection' : 'Exact · Registry' }}</span>
                <h3>{{ selectedValue === null ? 'No effective value is available for this domain.' : 'The selected value satisfies a package predicate.' }}</h3>
                <code v-if="selectedValue !== null">{{ focusedNamelist }} == {{ selectedValue }} → {{ activePackage?.data?.package_name || activePackage?.label }}</code>
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
                  <h3>{{ selectedValue === null ? 'No branch can be selected yet.' : 'No standalone driver dispatch has been joined.' }}</h3>
                  <p>{{ selectedValue === null ? 'Provide a value in the namelist or choose one above to trace a code path.' : 'The Registry mapping is indexed, but this value has no proven standalone driver CASE edge in the current graph.' }}</p>
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
import { useEvidenceStore } from '@/stores/evidenceStore'
import GraphView from '@/components/graph/GraphView.vue'
import { PHYSICS_CATEGORIES } from '@/types/graph'
import type { GraphEdge, GraphNode, SourceEvidence } from '@/types/graph'

const route = useRoute()
const router = useRouter()
const configStore = useConfigStore()
const graphStore = useGraphStore()
const evidenceStore = useEvidenceStore()

const initialFocus = typeof route.query.focus === 'string' && Object.values(PHYSICS_CATEGORIES).some(c => c.namelist === route.query.focus)
  ? route.query.focus
  : 'sf_surface_physics'
const focusedNamelist = ref(initialFocus)
const selectedNode = ref<GraphNode | null>(null)
const showAllCalls = ref(false)
const showNamelistEditor = ref(false)
const namelistFileInput = ref<HTMLInputElement | null>(null)

const loadNamelistFile = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  configStore.setNamelistText(await file.text())
  showNamelistEditor.value = true
  input.value = ''
}

const focusedCategory = computed(() => Object.values(PHYSICS_CATEGORIES).find(category => category.namelist === focusedNamelist.value))
const focusedNamelistNode = computed(() => graphStore.getNodeById(`namelist:${focusedNamelist.value}`))
const focusedOptions = computed(() => graphStore.getPackagesForNamelist(focusedNamelist.value))
const suiteSettings = computed(() => configStore.physicsSuite ? graphStore.getSuiteSettings(configStore.physicsSuite) : [])
const indexedConstraints = computed(() => graphStore.getEdgesOfType('REQUIRES_OPTION'))
const constraintWarnings = computed(() => indexedConstraints.value.filter(edge => {
  const selected = configStore.getConfig(edge.source.replace('namelist:', ''))
  const required = configStore.getConfig(edge.target.replace('namelist:', ''))
  return selected !== undefined && required !== undefined &&
    String(selected) === String(edge.data.value) && String(required) !== String(edge.data.required_value)
}))
const selectedValue = computed<number | null>(() => {
  const raw = configStore.getConfig(focusedNamelist.value)
  if (raw === undefined || raw === null) return configStore.namelistText === null
    ? Number(focusedOptions.value[0]?.value ?? 0)
    : null
  const configured = Number(raw)
  if (focusedOptions.value.some(option => Number(option.value) === configured)) return configured
  return configStore.namelistText === null ? Number(focusedOptions.value[0]?.value ?? 0) : null
})
const originLabel = computed(() => ({
  example: 'Illustrative example', namelist: 'Explicit namelist value', suite: `Physics suite: ${configStore.physicsSuite}`,
  'registry-default': 'Registry default', unresolved: 'Not resolved',
})[configStore.getConfigOrigin(focusedNamelist.value)])
const activePackage = computed(() => selectedValue.value === null ? undefined : focusedOptions.value.find(option => Number(option.value) === selectedValue.value)?.node)
const executionPath = computed(() => selectedValue.value === null
  ? { nodes: [] as GraphNode[], edges: [] as GraphEdge[] }
  : graphStore.getExecutionPath(focusedNamelist.value, String(selectedValue.value)))
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
  if (configStore.namelistText === null && !focusedOptions.value.some(option => Number(option.value) === configured) && focusedOptions.value[0]) {
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

const openEvidence = (evidence: SourceEvidence | undefined) => {
  if (evidence) evidenceStore.open(evidence, `${focusedNamelist.value} · source evidence`, 'exact', 'This source location supports an indexed configuration fact or call. The complete selection path may include inferred joins and additional conditions.')
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
  router.replace({ query: { ...route.query, focus: namelist, value: selectedValue.value === null ? undefined : String(selectedValue.value) } })
})

watch(() => [route.query.focus, route.query.value], ([focus, value]) => {
  if (typeof focus !== 'string' || !Object.values(PHYSICS_CATEGORIES).some(category => category.namelist === focus)) return
  focusedNamelist.value = focus
  if (configStore.namelistText !== null) {
    selectedNode.value = null
    showAllCalls.value = false
    return
  }
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
  if (configStore.namelistText === null && typeof route.query.value === 'string') {
    const queryValue = Number(route.query.value)
    if (Number.isFinite(queryValue) && focusedOptions.value.some(option => Number(option.value) === queryValue)) {
      configStore.setConfig(focusedNamelist.value, queryValue)
    }
  }
})
</script>

<style scoped>
.namelist-view { display: flex; width: 100%; max-width: 1540px; margin: 0 auto; flex-direction: column; gap: 18px; }
.namelist-import { padding: 16px 19px; }
.import-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 22px; }
.import-heading h2 { margin-top: 5px; font-size: .98rem; }
.import-heading p:last-child { margin-top: 5px; color: var(--text-muted); font-size: .68rem; line-height: 1.5; }
.import-actions { display: flex; flex-wrap: wrap; gap: 7px; flex-shrink: 0; }
.import-actions button { padding: 7px 9px; border: 1px solid var(--border-strong); border-radius: 4px; background: var(--bg-inset); color: var(--text-secondary); cursor: pointer; font-size: .65rem; }
.import-actions button:hover { border-color: var(--accent-emerald); color: var(--text-primary); }
.namelist-editor { display: block; width: 100%; min-height: 190px; margin-top: 14px; padding: 12px; resize: vertical; border: 1px solid var(--border-strong); border-radius: 4px; outline: none; background: var(--bg-inset); color: var(--text-primary); font: .7rem/1.55 var(--font-mono); }
.namelist-editor:focus { border-color: var(--accent-emerald); }
.import-status { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 17px; margin-top: 13px; color: var(--text-muted); font-size: .65rem; }
.import-status label { display: flex; align-items: center; gap: 7px; color: var(--text-secondary); }
.import-status select { padding: 5px 8px; border: 1px solid var(--border-strong); background: var(--bg-inset); color: var(--text-primary); }
.import-status code { color: var(--text-primary); }
.import-status .parse-warning { color: var(--accent-amber); }
.suite-summary { margin-top: 14px; padding-top: 13px; border-top: 1px solid var(--border-subtle); }
.suite-summary > strong { font-size: .72rem; }
.suite-summary > p { max-width: 900px; margin: 5px 0 10px; color: var(--text-muted); font-size: .65rem; line-height: 1.55; }
.suite-summary > p code { color: var(--accent-amber); }
.suite-rows { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 5px; }
.suite-rows button { display: grid; grid-template-columns: 1fr auto; gap: 3px 8px; padding: 8px 9px; border: 1px solid var(--border-subtle); border-radius: 4px; background: var(--bg-inset); color: var(--text-secondary); cursor: pointer; text-align: left; }
.suite-rows button:hover { border-color: var(--accent-emerald); }
.suite-rows code { color: var(--text-primary); font-size: .61rem; }
.suite-rows span { color: var(--text-muted); font-size: .58rem; }
.suite-rows strong { color: var(--accent-emerald); font: 650 .66rem var(--font-mono); }
.suite-rows small { color: var(--text-muted); font-size: .55rem; text-align: right; }
.constraint-summary { margin-top: 13px; padding-top: 12px; border-top: 1px solid var(--border-subtle); }
.constraint-summary > strong { font-size: .71rem; }
.constraint-summary > p { margin: 4px 0 8px; color: var(--text-muted); font-size: .63rem; }
.constraint-clear { color: var(--text-muted); font-size: .64rem; }
.constraint-list { display: grid; gap: 5px; }
.constraint-list button { padding: 9px 10px; border: 1px solid color-mix(in srgb,var(--accent-amber) 35%,var(--border-subtle)); border-radius: 4px; background: color-mix(in srgb,var(--accent-amber) 7%,var(--bg-inset)); color: var(--text-secondary); cursor: pointer; text-align: left; font-size: .66rem; }
.constraint-list button:hover { border-color: var(--accent-amber); }
.constraint-list code { color: var(--accent-amber); font-size: .64rem; }
.constraint-list span { margin-left: 8px; color: var(--text-muted); }
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
