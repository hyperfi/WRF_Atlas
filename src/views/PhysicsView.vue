<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import { useConfigStore } from '@/stores/configStore'
import { useUiStore } from '@/stores/uiStore'
import { useEvidenceStore } from '@/stores/evidenceStore'
import ExecutionTrace from '@/components/graph/ExecutionTrace.vue'
import { uniqueTargets, type TraceStep } from '@/lib/presentation'
import { PHYSICS_CATEGORIES, type PhysicsCategory, type GraphEdge, type SourceEvidence } from '@/types/graph'

const route = useRoute()
const router = useRouter()
const graph = useGraphStore()
const config = useConfigStore()
const ui = useUiStore()
const evidence = useEvidenceStore()
const categories = Object.entries(PHYSICS_CATEGORIES).map(([id, value]) => ({ id: id as PhysicsCategory, ...value }))
const categoryId = ref<PhysicsCategory>(categories.find(c => c.id === route.params.category)?.id || categories[0].id)
const selectedValue = ref<string | null>(typeof route.query.scheme === 'string' ? route.query.scheme : null)
const selectedStep = ref(typeof route.query.step === 'string' && ['config', 'registry', 'driver', 'calls'].includes(route.query.step) ? route.query.step : 'registry')
const inspectorEl = ref<HTMLElement>()
const catalogueEl = ref<HTMLElement>()
watch(selectedValue, async value => {
  await nextTick()
  const target = value === null ? catalogueEl.value : inspectorEl.value
  target?.focus({ preventScroll: true })
  target?.scrollIntoView({ block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })
})
watch(categoryId, value => {
  if (value !== route.params.category) router.push(`/physics/${value}`)
  selectedValue.value = null
})
watch(() => route.params.category, value => {
  if (categories.some(c => c.id === value)) categoryId.value = value as PhysicsCategory
})
watch(() => graph.activeSnapshotId, () => { selectedValue.value = null })
const category = computed(() => categories.find(c => c.id === categoryId.value)!)
const schemes = computed(() => graph.getPackagesForNamelist(category.value.namelist))
const selected = computed(() => schemes.value.find(scheme => scheme.value === selectedValue.value))
const activeValue = computed(() => {
  const value = config.getConfig(category.value.namelist)
  return value === undefined ? null : String(value)
})
const active = computed(() => schemes.value.find(scheme => scheme.value === activeValue.value))
const select = (value: string) => {
  selectedValue.value = selectedValue.value === value ? null : value
  selectedStep.value = 'registry'
}
const activate = (value: string) => config.setConfig(category.value.namelist, Number(value))
const callLabel = (edge: GraphEdge) => graph.getNodeById(edge.target)?.label || edge.target.replace('subroutine:', '')
const auxiliary = (edge: GraphEdge) => /^(wrf_debug|wrf_error_fatal|add_multi_perturb|remove_multi_perturb)/i.test(callLabel(edge))
const detail = computed(() => {
  if (selectedValue.value === null) return null
  const selector = category.value.namelist
  const path = graph.getExecutionPath(selector, selectedValue.value)
  const registry = path.edges.find(edge => edge.type === 'SELECTS')
  const calls = path.edges.filter(edge => edge.type === 'CALLS').sort((a, b) => Number(auxiliary(a)) - Number(auxiliary(b)))
  const packageNode = path.nodes.find(node => node.type === 'registry_package')
  const driver = graph.getNodeById(`namelist:${selector}`)?.data?.driver as string | undefined
  const phase = driver ? graph.getEdgesFrom(`subroutine:${driver}`).find(edge => edge.type === 'EXECUTES_DURING') : undefined
  const primary = calls.filter(edge => !auxiliary(edge))
  const driverFile = driver ? graph.getNodeById(`subroutine:${driver}`)?.data?.file : undefined
  const implementations = primary.filter(edge => {
    const file = graph.getNodeById(edge.target)?.data?.file
    return file && file !== driverFile
  })
  const nested = uniqueTargets(implementations).slice(0, 2).flatMap(parent => graph.getEdgesFrom(parent.target)
    .filter(edge => edge.type === 'CALLS' && !auxiliary(edge)).slice(0, 5).map(edge => ({ parent, edge })))
  const fields = [...new Set((implementations.length ? implementations : primary).flatMap(edge =>
    (edge.data?.state_args || []).map((arg: { name: string }) => arg.name as string)))]
  const conditional = graph.getActiveSubroutines(selector, selectedValue.value)
  const reads = graph.getEdgesTo(`namelist:${selector}`).filter(edge => edge.type === 'READS_CONFIG' && edge.data?.evidence?.length).slice(0, 5)
  return { registry, packageNode, driver, phase, calls, nested, fields, conditional, reads }
})
const steps = computed<TraceStep[]>(() => !detail.value ? [] : [
  { id: 'config', label: 'Configuration', value: `${category.value.namelist} = ${selectedValue.value}`, confidence: 'exact', grade: selectedValue.value === activeValue.value ? 'Current value' : 'Preview value' },
  { id: 'registry', label: 'Registry package', value: detail.value.packageNode?.label || 'Unresolved mapping', confidence: detail.value.registry ? 'exact' : 'unresolved' },
  { id: 'driver', label: 'Runtime driver', value: detail.value.driver || 'Not resolved', confidence: detail.value.calls.length ? 'inferred' : 'unresolved' },
  { id: 'calls', label: 'Branch calls', value: detail.value.calls.length ? `${uniqueTargets(detail.value.calls).length} routine targets` : 'Not resolved', confidence: detail.value.calls.length ? 'exact' : 'unresolved' },
])
const proof = (edge: GraphEdge): SourceEvidence | undefined => edge.data?.evidence?.[0]
const definition = (id: string): SourceEvidence | undefined => {
  const node = graph.getNodeById(id)
  return node?.data?.file && node.data.line ? { path: node.data.file, startLine: node.data.line } : undefined
}
const inspect = (source: SourceEvidence | undefined, title = 'Source evidence', explanation = '') => {
  if (source) evidence.open(source, title, 'exact', explanation, `/physics/${categoryId.value}?scheme=${encodeURIComponent(selectedValue.value || '')}&step=${selectedStep.value}`)
}
const inspectCall = (edge: GraphEdge) => inspect(proof(edge), `${graph.getNodeById(edge.source)?.label || edge.source} → ${callLabel(edge)}`, 'Direct CALL at this source location. Nested guards and preprocessing may still control whether it executes.')
const openLab = () => router.push({ path: '/namelist', query: { focus: category.value.namelist, value: selectedValue.value } })
const openField = (name: string) => router.push({ path: '/variables', query: { field: name, selector: category.value.namelist, value: selectedValue.value } })
onMounted(() => graph.loadGraph())
</script>

<template>
  <div class="physics-view">
    <header class="page-heading"><div><p class="eyebrow">Configuration → code → fields</p><h1>Physics Explorer</h1><p>Inspect what a physics choice selects, and where the source evidence stops.</p></div><span class="source-mode">{{ ui.mode === 'learning' ? 'Learning' : 'Researcher' }} view</span></header>
    <div v-if="graph.isLoaded" class="physics-layout">
      <nav class="category-list" aria-label="Physics families"><button v-for="(cat, i) in categories" :key="cat.id" :aria-current="cat.id === categoryId ? 'true' : undefined" :class="{ active: cat.id === categoryId }" @click="categoryId = cat.id"><span>{{ String(i + 1).padStart(2, '0') }}</span>{{ cat.label }}</button></nav>
      <div class="scheme-workspace">
        <div class="family-heading"><div><h2>{{ category.label }}</h2><code>{{ category.namelist }}</code></div><span>{{ schemes.length }} indexed choices</span></div>
        <div class="configuration-strip"><span>Current configuration · d{{ String(config.activeDomain).padStart(2, '0') }}</span><strong>{{ active?.description || active?.packageName || (activeValue === null ? 'Unresolved value' : `Value ${activeValue}`) }}</strong><code>{{ category.namelist }} = {{ activeValue ?? '?' }}</code></div>

        <section v-if="selected && detail" ref="inspectorEl" tabindex="-1" class="scheme-inspector" aria-label="Scheme detail inspector">
          <header class="inspector-header"><div><p class="eyebrow">Selection inspector</p><h3>{{ selected.description || selected.packageName }}</h3><p><code>{{ selected.packageName }}</code> · option {{ selected.value }}</p></div><button @click="selectedValue = null">← All schemes</button></header>
          <div class="inspector-status"><span :class="{ matches: selected.value === activeValue }">{{ selected.value === activeValue ? 'Selected by current configuration' : 'Preview only · not selected by current configuration' }}</span><button v-if="selected.value !== activeValue" @click="activate(selected.value)">Use this value</button></div>
          <ExecutionTrace :steps="steps" :selected="selectedStep" @inspect="selectedStep = $event" caption="Configuration relationships, not a timestep timeline. Select a stop to inspect its evidence." />

          <div class="why-inspector">
            <div class="why-heading"><h4>{{ selected.value === activeValue ? 'Why active?' : 'What would select this scheme?' }}</h4><span>{{ steps.find(step => step.id === selectedStep)?.label }}</span></div>
            <div v-if="selectedStep === 'config'">
              <p>The {{ config.namelistText === null ? 'Atlas example' : 'loaded namelist' }} resolves this selector to <code>{{ activeValue ?? '?' }}</code> for domain {{ config.activeDomain }}. This preview requires <code>{{ category.namelist }} = {{ selected.value }}</code>.</p>
              <p>This describes the static selection, not evidence from a completed WRF run.</p><button class="text-action" @click="openLab">Inspect configuration in Namelist Lab ↗</button>
            </div>
            <div v-else-if="selectedStep === 'registry'">
              <p v-if="detail.registry">The indexed Registry associates value <code>{{ selected.value }}</code> with package <code>{{ selected.packageName }}</code>. This is configuration metadata, not a runtime call.</p><p v-else>The Registry link is not resolved in this snapshot.</p>
              <button v-if="detail.registry" class="proof-button" @click="inspect(proof(detail.registry), 'Registry selection', 'Registry package association for the selected option value.')">Inspect Registry evidence <span>↗</span></button>
            </div>
            <div v-else-if="selectedStep === 'driver'">
              <p v-if="detail.calls.length">The numeric Registry value is joined to a symbolic CASE branch in <code>{{ detail.driver }}</code>. That join is inferred; the individual call sites are direct source evidence. Other guards may apply.</p><p v-else>The index has not resolved a matching runtime branch{{ detail.driver ? ` in ${detail.driver}` : '' }}. A selector read alone does not prove activation.</p>
              <div v-if="detail.phase" class="phase-anchor"><span>Indexed timestep location</span><strong>{{ detail.phase.target.replace('phase:', '') }}</strong><button @click="inspect(proof(detail.phase), 'Driver timestep call')">Inspect call ↗</button></div>
            </div>
            <div v-else>
              <p>Direct calls found in the matching branch. These are alternative or conditional targets, not an unconditional sequence.</p>
              <div v-if="detail.calls.length" class="call-grid"><div v-for="call in uniqueTargets(detail.calls).slice(0, 4)" :key="call.target" class="call-tile"><button @click="inspectCall(call)"><code>{{ callLabel(call) }}</code><span>Inspect CALL ↗</span></button><button v-if="definition(call.target)" class="definition-link" @click="inspect(definition(call.target), `${callLabel(call)} definition`)">Routine definition ↗</button></div></div>
              <p v-else class="unresolved">Implementation path not resolved. No call is fabricated to fill this gap.</p>
            </div>
          </div>

          <details v-if="detail.calls.length" class="source-disclosure"><summary>All branch call sites <span>{{ detail.calls.length }} locations</span></summary><div class="source-list"><div v-for="(call, i) in detail.calls" :key="`${call.target}-${i}`"><button @click="inspectCall(call)"><code>{{ callLabel(call) }}</code><span>{{ proof(call)?.path }}:{{ proof(call)?.startLine }} ↗</span></button><button v-if="definition(call.target)" class="definition-link" @click="inspect(definition(call.target), `${callLabel(call)} definition`)">Routine definition ↗</button></div></div></details>
          <details v-if="detail.nested.length" class="source-disclosure"><summary>One level inside implementation <span>{{ detail.nested.length }} sampled calls</span></summary><p>Possible direct callees; their guards and preprocessor conditions remain unresolved. This is a bounded sample, not the entire call graph.</p><div class="source-list"><button v-for="(item, i) in detail.nested" :key="i" @click="inspectCall(item.edge)"><code>{{ callLabel(item.parent) }} → {{ callLabel(item.edge) }}</code><span>{{ proof(item.edge)?.path }}:{{ proof(item.edge)?.startLine }} ↗</span></button></div></details>
          <details v-if="!detail.calls.length" class="source-disclosure"><summary>Other indexed references <span>Not a complete path</span></summary><p>Conditional calls and selector reads below do not establish a connected runtime path.</p><div class="source-list"><button v-for="(item, i) in detail.conditional.slice(0, 8)" :key="`condition-${i}`" @click="inspect(item.evidence?.[0], 'Conditional source reference')"><code>{{ item.node?.label || item.edge.source }}</code><span>{{ item.evidence?.[0]?.path }}:{{ item.evidence?.[0]?.startLine }}</span></button><button v-for="(read, i) in detail.reads" :key="`read-${i}`" @click="inspect(proof(read), 'Selector read')"><code>{{ read.source.replace('subroutine:', '') }}</code><span>{{ proof(read)?.path }}:{{ proof(read)?.startLine }}</span></button></div></details>
          <section v-if="detail.fields.length" class="field-section"><h4>Fields passed at this branch</h4><p>Argument-name matches; read/write direction remains unresolved.</p><div class="field-links"><button v-for="field in detail.fields.slice(0, 12)" :key="field" @click="openField(field)">{{ field.toUpperCase() }} ↗</button></div><details v-if="detail.fields.length > 12"><summary>{{ detail.fields.length - 12 }} more field arguments</summary><div class="field-links"><button v-for="field in detail.fields.slice(12)" :key="field" @click="openField(field)">{{ field.toUpperCase() }} ↗</button></div></details></section>
        </section>

        <div ref="catalogueEl" tabindex="-1" class="catalogue-heading"><h3>Scheme catalogue</h3><span>Click a choice to inspect · click again to close</span></div>
        <div class="schemes-grid"><article v-for="scheme in schemes" :key="scheme.value" :class="['scheme-card', { active: scheme.value === activeValue, selected: scheme.value === selectedValue }]"><button class="scheme-select" :aria-expanded="scheme.value === selectedValue" @click="select(scheme.value)"><span class="value-badge">{{ scheme.value }}</span><span><strong>{{ scheme.description || scheme.packageName }}</strong><code>{{ scheme.packageName }}</code></span><span class="selection-mark">{{ scheme.value === selectedValue ? '−' : '+' }}</span></button><div class="scheme-footer"><span>{{ scheme.value === activeValue ? 'Selected in configuration' : 'Alternative' }}</span><button v-if="scheme.value !== activeValue" @click="activate(scheme.value)">Use value {{ scheme.value }}</button></div></article></div>
      </div>
    </div>
    <p v-else role="status">Loading indexed physics…</p>
  </div>
</template>

<style scoped>
.physics-view { height: 100%; min-height: 0; display: flex; flex-direction: column; }
.page-heading { display: flex; justify-content: space-between; align-items: start; gap: 20px; margin-bottom: 24px; }.page-heading h1 { margin: 6px 0; font-size: 1.7rem; }.page-heading p:not(.eyebrow) { color: var(--text-secondary); font-size: .87rem; }.source-mode { padding: 6px 10px; border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); font-size: .72rem; white-space: nowrap; }
.physics-layout { display: grid; grid-template-columns: 205px minmax(0, 1fr); gap: 26px; min-height: 0; flex: 1; }.category-list { display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }.category-list button { display: flex; gap: 12px; padding: 12px 11px; text-align: left; color: var(--text-secondary); background: transparent; border: 1px solid transparent; border-radius: 4px; cursor: pointer; font-size: .82rem; }.category-list button span { color: var(--text-muted); font: .68rem var(--font-mono); padding-top: 3px; }.category-list button.active { background: var(--accent-soft); border-color: var(--border-strong); color: var(--text-primary); }.category-list button.active span { color: var(--accent-emerald); }.category-list button:hover { background: var(--bg-surface); }
.scheme-workspace { overflow-y: auto; min-width: 0; padding-right: 8px; }.family-heading { display: flex; justify-content: space-between; align-items: center; gap: 20px; margin-bottom: 18px; }.family-heading h2 { font-size: 1.2rem; margin-bottom: 5px; }.family-heading code { color: var(--accent-emerald); font-size: .73rem; }.family-heading > span { color: var(--text-secondary); font-size: .71rem; }
.configuration-strip { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 18px; padding: 13px 16px; background: var(--bg-surface); border-left: 2px solid var(--accent-emerald); margin-bottom: 22px; }.configuration-strip span { color: var(--text-secondary); font-size: .7rem; }.configuration-strip strong { font-size: .8rem; }.configuration-strip code { color: var(--text-secondary); font-size: .68rem; }
.scheme-inspector { border: 1px solid var(--border-strong); border-radius: 6px; background: var(--bg-panel); padding: 22px; margin-bottom: 30px; }.inspector-header { display: flex; justify-content: space-between; align-items: start; gap: 16px; }.inspector-header h3 { font-size: 1.2rem; margin: 4px 0; }.inspector-header p:not(.eyebrow) { color: var(--text-secondary); font-size: .74rem; }.inspector-header button,.inspector-status button { background: var(--bg-inset); border: 1px solid var(--border-strong); border-radius: 4px; color: var(--text-primary); padding: 7px 10px; cursor: pointer; font-size: .73rem; white-space: nowrap; }
.inspector-status { display: flex; justify-content: space-between; gap: 12px; align-items: center; margin: 18px 0; font-size: .73rem; color: var(--text-secondary); }.inspector-status .matches { color: var(--accent-emerald); }
.why-inspector { padding: 17px 0; margin: 18px 0 0; border-top: 1px solid var(--border-subtle); }.why-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px; }.why-heading h4 { font-size: .95rem; }.why-heading span { font-size: .7rem; color: var(--accent-emerald); }.why-inspector p,.source-disclosure p,.field-section p { color: var(--text-secondary); font-size: .81rem; line-height: 1.65; margin: 7px 0; }.why-inspector code { color: var(--text-primary); font-size: .76rem; }
.proof-button { display: flex; justify-content: space-between; gap: 16px; width: 100%; padding: 10px 12px; margin-top: 12px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--accent-emerald); cursor: pointer; font-size: .77rem; }.text-action { padding: 6px 0; background: transparent; border: 0; color: var(--accent-emerald); cursor: pointer; font-size: .78rem; }
.phase-anchor { display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: center; padding: 12px; background: var(--bg-inset); margin-top: 12px; font-size: .72rem; }.phase-anchor span { color: var(--text-secondary); }.phase-anchor strong { font-family: var(--font-mono); overflow-wrap: anywhere; }.phase-anchor button { margin-left: auto; border: 0; background: transparent; color: var(--accent-emerald); cursor: pointer; }
.call-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 9px; margin-top: 12px; }.call-tile { padding: 12px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; }.call-tile > button:first-child { display: flex; flex-direction: column; gap: 10px; width: 100%; text-align: left; border: 0; background: transparent; color: var(--text-primary); cursor: pointer; }.call-tile span { color: var(--accent-emerald); font-size: .69rem; }
.source-disclosure { border-top: 1px solid var(--border-subtle); padding: 13px 0; }.source-disclosure summary { cursor: pointer; color: var(--text-primary); font-size: .79rem; }.source-disclosure summary span { margin-left: 12px; color: var(--text-secondary); font-size: .69rem; }.source-list { display: grid; gap: 6px; margin-top: 12px; }.source-list button:not(.definition-link) { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 5px 14px; width: 100%; text-align: left; padding: 10px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-primary); cursor: pointer; }.source-list code { font-size: .74rem; overflow-wrap: anywhere; }.source-list span { color: var(--text-secondary); font: .65rem var(--font-mono); overflow-wrap: anywhere; }.definition-link { display: block; padding: 6px 0; border: 0; background: transparent; color: var(--accent-emerald); font-size: .68rem; cursor: pointer; }.unresolved { color: var(--accent-amber) !important; }
.field-section { padding-top: 15px; border-top: 1px solid var(--border-subtle); }.field-section h4 { font-size: .85rem; }.field-links { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }.field-links button { padding: 5px 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--accent-emerald); cursor: pointer; font: .69rem var(--font-mono); }.field-section summary { font-size: .72rem; color: var(--text-secondary); cursor: pointer; }
.catalogue-heading { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 12px; }.catalogue-heading h3 { font-size: .9rem; }.catalogue-heading span { color: var(--text-secondary); font-size: .69rem; }.schemes-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(min(100%,280px),1fr)); gap: 12px; }.scheme-card { border: 1px solid var(--border-subtle); border-radius: 5px; background: var(--bg-panel); }.scheme-card.active { border-left: 3px solid var(--accent-emerald); }.scheme-card.selected { border-color: var(--accent-emerald); }.scheme-select { display: flex; gap: 12px; width: 100%; align-items: start; padding: 16px; background: transparent; color: var(--text-primary); border: 0; text-align: left; cursor: pointer; }.scheme-select strong { display: block; font-size: .84rem; font-weight: 600; }.scheme-select code { display: block; margin-top: 5px; color: var(--text-secondary); font-size: .67rem; overflow-wrap: anywhere; }.value-badge { min-width: 29px; padding: 3px 5px; text-align: center; border: 1px solid var(--border-strong); border-radius: 3px; font: .71rem var(--font-mono); }.selection-mark { margin-left: auto; color: var(--text-secondary); }.scheme-footer { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 9px 16px; border-top: 1px solid var(--border-subtle); font-size: .67rem; color: var(--text-secondary); }.active .scheme-footer > span { color: var(--accent-emerald); }.scheme-footer button { background: transparent; border: 0; color: var(--accent-emerald); cursor: pointer; font-size: .67rem; }
@media (max-width: 1100px) { .physics-layout { grid-template-columns: 170px minmax(0,1fr); gap: 16px; }.scheme-inspector { padding: 17px; } }
@media (max-width: 800px) { .physics-view { height: auto; }.physics-layout { display: block; }.category-list { flex-direction: row; overflow-x: auto; min-height: 50px; margin-bottom: 20px; padding-bottom: 8px; }.category-list button { white-space: nowrap; flex: 0 0 auto; min-height: 40px; }.category-list button span { display: none; }.scheme-workspace { overflow: visible; padding: 0; }.page-heading { flex-direction: column; }.catalogue-heading { align-items: start; flex-direction: column; gap: 4px; }.inspector-header { flex-wrap: wrap; } }
</style>
