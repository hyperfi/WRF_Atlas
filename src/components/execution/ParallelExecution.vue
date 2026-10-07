<template>
  <section class="parallel-execution" aria-label="MPI and OpenMP execution">
    <fieldset class="mode-control">
      <legend>WRF execution mode</legend>
      <div class="mode-options">
        <button v-for="item in BUILD_MODES" :key="item.id" :aria-pressed="mode === item.id" @click="mode = item.id">{{ item.label }}</button>
      </div>
      <p>{{ profile.mpi ? `${dimensions.x * dimensions.y} illustrative compute ranks` : 'One process' }} · {{ dimensions.threads }} {{ dimensions.threads === 1 ? 'thread' : 'threads' }} per {{ profile.mpi ? 'rank' : 'process' }}. Build assumptions, not a detected WRF binary.</p>
    </fieldset>

    <div v-if="parallel.loading" class="index-state" role="status">Reading parallel evidence for {{ graph.activeSnapshot?.label }}…</div>
    <div v-else-if="parallel.error" class="index-state" role="alert"><p>{{ parallel.error }}</p><button @click="parallel.load()"><RefreshCw :size="16" /> Retry</button></div>
    <template v-else-if="parallel.index">
      <div class="scope-toolbar">
        <label>Source episode<select v-model="scopeId" aria-label="Parallel source scope"><option v-for="scope in episodeScopes" :key="scope.id" :value="scope.id">{{ scope.name }} · {{ scope.path }}</option></select></label>
        <details class="scope-browser"><summary><Search :size="16" /> All source scopes</summary><label>Find a scope<input v-model="scopeQuery" type="search" aria-label="Find a source scope" placeholder="Routine or file path" /></label><select v-model="scopeId" aria-label="Matching source scopes"><option v-for="scope in filteredScopes" :key="scope.id" :value="scope.id">{{ scope.name }} · {{ scope.path }}</option></select><p>{{ filteredScopes.length }} matching scopes</p></details>
      <details class="build-settings"><summary><Settings2 :size="16" /> Partition settings</summary>
        <div class="settings-layout"><div class="parallel-controls">
          <label>X ranks<select :value="dimensions.x" @change="meshX = Number(($event.target as HTMLSelectElement).value)" :disabled="!profile.mpi" aria-label="Illustrative X ranks"><option v-for="n in 3" :key="n" :value="n">{{ n }}</option></select></label>
          <label>Y ranks<select :value="dimensions.y" @change="meshY = Number(($event.target as HTMLSelectElement).value)" :disabled="!profile.mpi" aria-label="Illustrative Y ranks"><option v-for="n in 3" :key="n" :value="n">{{ n }}</option></select></label>
          <label>Threads<select :value="dimensions.threads" @change="teamSize = Number(($event.target as HTMLSelectElement).value)" :disabled="!profile.omp" aria-label="Illustrative threads per rank"><option v-for="n in 4" :key="n" :value="n">{{ n }}</option></select></label>
          <label class="checkbox-control"><input v-model="showExcluded" type="checkbox" /> Excluded mechanisms</label>
        </div><div class="mesh-tool">
          <h3>{{ profile.mpi ? 'Rank patches' : 'Single-process domain' }}</h3>
          <div class="mesh" :style="{ gridTemplateColumns: `repeat(${dimensions.x}, minmax(0, 1fr))`, gridTemplateRows: `repeat(${dimensions.y}, minmax(0, 1fr))` }"><button v-for="rank in ranks" :key="rank" :aria-label="`${profile.mpi ? 'Rank' : 'Process'} ${rank}, ${neighbors.includes(rank) ? 'illustrative neighbor' : 'select patch'}`" :aria-pressed="selectedRank === rank" :class="{ selected: selectedRank === rank, neighbor: neighbors.includes(rank) }" @click="selectedRank = rank">{{ profile.mpi ? 'Rank' : 'Process' }} {{ rank }}</button></div>
          <p>{{ profile.mpi && communicationVisible ? collective ? 'Communicator membership is unresolved.' : `Illustrative adjacent patches: ${neighbors.length ? neighbors.map(n => `rank ${n}`).join(', ') : 'none on this axis'}.` : 'Illustrative partition, not CPU or machine placement.' }}</p>
        </div></div>
      </details></div>
      <p v-if="selectionNotice" class="selection-notice" role="status">{{ selectionNotice }}</p>
      <div class="walkthrough-controls">
        <div class="playback">
          <button title="Previous source event" aria-label="Previous source event" :disabled="cursor === 0 || !events.length" @click="step(-1)"><SkipBack :size="18" /></button>
          <button :title="playing ? 'Pause walkthrough' : 'Play walkthrough'" :aria-label="playing ? 'Pause walkthrough' : 'Play walkthrough'" :disabled="!events.length" @click="togglePlay"><Pause v-if="playing" :size="18" /><Play v-else :size="18" /></button>
          <button title="Next source event" aria-label="Next source event" :disabled="cursor >= events.length - 1" @click="step(1)"><SkipForward :size="18" /></button>
          <label>Speed<select v-model.number="delay"><option :value="1800">0.75×</option><option :value="1200">1×</option><option :value="800">1.5×</option></select></label>
        </div>
        <span>{{ events.length ? cursor + 1 : 0 }} / {{ events.length }} source events · not measured time or a resolved runtime trace</span>
      </div>

      <div class="execution-workspace"><ParallelLanes :events="events" :scope-events="scopeEvents" :selected-id="selectedId" :mode="mode" :ranks="ranks" :threads="dimensions.threads" :selected-rank="selectedRank" :scope-name="activeScope?.name || ''" :path="activeScope?.path || ''" :researcher="ui.mode === 'researcher'" @select="selectEvent" @rank="selectedRank = $event" />

      <section v-if="selectedEvent" ref="inspector" class="event-inspector" aria-label="Parallel event evidence" tabindex="-1">
        <div class="event-title"><div><h3><code>{{ selectedEvent.operation }}</code></h3><p>{{ eventMeaning(selectedEvent, mode).label }} · {{ availabilityLabel }}</p></div><button class="evidence-button" @click="openEvidence(selectedEvent.evidence[0]!)"><FileCode :size="17" /> Show source</button></div>
        <p class="event-explanation">{{ eventMeaning(selectedEvent, mode).detail }}</p>
        <dl class="event-facts">
          <div><dt>Execution scope</dt><dd>{{ threadScope }}</dd></div>
          <div><dt>Who may wait?</dt><dd>{{ waitScope }}</dd></div>
          <div><dt>Selected source</dt><dd>{{ selectedEvent.evidence[0]?.path }}:{{ selectedEvent.evidence[0]?.startLine }} · {{ selectedEvent.scope }}</dd></div>
        </dl>
        <div v-if="selectedRequest" class="request-association"><h4>Request association · inferred</h4><p><code>{{ selectedRequest.request }}</code> appears in the post and completion call with matching indexed guards. This does not prove runtime request identity, reachability, overlap, or a remote peer.</p><div class="implementation-links"><button @click="selectEvent(selectedRequest.post)"><ArrowLeft :size="16" /> {{ selectedRequest.post.operation }} · line {{ selectedRequest.post.evidence[0]?.startLine }}</button><button @click="selectEvent(selectedRequest.wait)"><Hourglass :size="16" /> {{ selectedRequest.wait.operation }} · line {{ selectedRequest.wait.evidence[0]?.startLine }}</button></div></div>
        <p v-else-if="selectedEvent.kind === 'mpi_wait' && eventAvailability(selectedEvent, mode) !== 'inactive'" class="request-unresolved">Request association unresolved. No peer or posting dependency is drawn.</p>
        <details :open="ui.mode === 'researcher'" class="source-details"><summary>Conditions and source arguments</summary>
        <div v-if="selectedEvent.guards.length || selectedEvent.conditions.length" class="conditions"><h4>Conditions retained from source</h4><code v-for="condition in [...selectedEvent.guards, ...selectedEvent.conditions]" :key="condition">{{ condition }}</code></div>
        <div v-if="selectedEvent.arguments?.length" class="request-arguments"><h4>{{ selectedEvent.kind === 'mpi_wait' ? 'Completion arguments' : 'Source arguments' }}</h4><code>{{ selectedEvent.arguments.join(', ') }}</code></div>
        <p v-if="!selectedEvent.arguments?.length && !selectedEvent.guards.length && !selectedEvent.conditions.length">No arguments or guards indexed for this stop.</p></details>
        <div v-if="communication" class="exchange-fields">
          <h4>Fields in this Registry exchange</h4>
          <div class="field-links"><button v-for="field in communicationFields" :key="field" @click="openField(field)">{{ field }}</button></div>
          <button class="evidence-button" @click="openEvidence(communication.evidence[0]!)"><FileCode :size="16" /> Registry declaration</button>
          <p>Matching include and Registry names are direct evidence. The generated implementation link is inferred; generated files may not exist in an unbuilt checkout.</p>
          <div class="implementation-links"><button v-for="implementation in exchangeImplementations" :key="implementation.scopeId" @click="scopeId = implementation.scopeId; cursor = 0"><Network :size="16" /> Inspect {{ implementation.label }}</button></div>
          <details><summary>Generation evidence</summary><button v-for="anchor in parallel.index.generatorEvidence" :key="anchor.startLine" class="source-anchor" @click="openEvidence(anchor)">{{ anchor.description }} · {{ anchor.path }}:{{ anchor.startLine }}</button></details>
        </div>
        <div class="inspector-links"><button v-if="scopeId !== solverScope?.id && solverScope" @click="scopeId = solverScope.id"><ArrowLeft :size="16" /> ARW solver</button><RouterLink :to="{ path: '/execution', query: { view: 'timestep' } }">Timestep storyboard <ArrowRight :size="16" /></RouterLink><a v-if="selectedEvent.semantics" :href="selectedEvent.semantics" target="_blank" rel="noopener noreferrer">{{ selectedEvent.kind.startsWith('mpi_') ? selectedEvent.operation : 'OpenMP' }} semantics <ExternalLink :size="15" /></a></div>
      </section></div>

      <section class="parallel-catalog">
        <div class="catalog-heading"><h3>Find a communication or thread boundary</h3><label><Search :size="16" /><input v-model="query" type="search" aria-label="Find parallel evidence" placeholder="MPI_Wait, monitor, PARALLEL DO…" /></label></div>
        <div class="catalog-results"><button v-for="event in catalogResults" :key="event.id" @click="openCatalogEvent(event)"><strong>{{ event.operation }}</strong><span>{{ event.scope }} · {{ event.evidence[0]?.path }}:{{ event.evidence[0]?.startLine }}</span><small>{{ eventAvailability(event, mode) === 'inactive' ? 'excluded in this mode' : eventMeaning(event, mode).label }}</small></button></div>
        <div class="catalog-pagination"><p>{{ catalogCount }} matching source events · {{ catalogCount ? catalogPage * 12 + 1 : 0 }}–{{ Math.min((catalogPage + 1) * 12, catalogCount) }} shown</p><div><button aria-label="Previous evidence results" :disabled="catalogPage === 0" @click="catalogPage--"><ChevronLeft :size="18" /></button><button aria-label="Next evidence results" :disabled="(catalogPage + 1) * 12 >= catalogCount" @click="catalogPage++"><ChevronRight :size="18" /></button></div></div>
        <p v-if="!catalogCount">No matches. Try a routine name, directive, or file path.</p>
      </section>

      <details class="parallel-limits"><summary>Evidence boundaries and indexing diagnostics</summary><ul><li v-for="limit in parallel.index.limitations" :key="limit">{{ limit }}</li></ul><p>Snapshot {{ parallel.index.metadata.commit.slice(0, 12) }} · {{ parallel.index.metadata.dirty ? 'modified checkout' : 'clean checkout' }} · {{ parallel.index.diagnostics.length }} diagnostics. This is not a performance profile.</p><div v-if="ui.mode === 'researcher'"><p v-for="issue in parallel.index.diagnostics" :key="`${issue.path}:${issue.line}:${issue.message}`">{{ issue.path }}:{{ issue.line }} · {{ issue.message }}</p></div></details>
    </template>
    <p class="sr-only" role="status" aria-live="polite">{{ playing ? '' : announcement }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, ChevronLeft, ChevronRight, ExternalLink, FileCode, Hourglass, Network, Pause, Play, RefreshCw, Search, Settings2, SkipBack, SkipForward } from '@lucide/vue'
import ParallelLanes from './ParallelLanes.vue'
import { useGraphStore } from '@/stores/graphStore'
import { useParallelStore } from '@/stores/parallelStore'
import { useEvidenceStore } from '@/stores/evidenceStore'
import { useUiStore } from '@/stores/uiStore'
import { BUILD_MODES, communicationTopology, eventAvailability, eventMeaning, illustrativeDimensions, modeSettings, rankNeighbors, requestAssociations, retainedSelection, type BuildMode, type ParallelEvent } from '@/lib/parallel'
import type { SourceEvidence } from '@/types/graph'

const graph = useGraphStore(), parallel = useParallelStore(), evidence = useEvidenceStore(), ui = useUiStore()
const route = useRoute(), router = useRouter()
const mode = ref<BuildMode>(BUILD_MODES.some(item => item.id === route.query.mode) ? route.query.mode as BuildMode : 'hybrid')
const meshX = ref(2), meshY = ref(2), teamSize = ref(4), selectedRank = ref(0)
const scopeId = ref(''), selectedId = ref(''), showExcluded = ref(true), query = ref(''), playing = ref(false), delay = ref(1200)
const scopeQuery = ref(''), catalogPage = ref(0), selectionNotice = ref('')
const inspector = ref<HTMLElement>()
let timer: ReturnType<typeof setTimeout> | undefined
const profile = computed(() => modeSettings(mode.value))
const dimensions = computed(() => illustrativeDimensions(mode.value, meshX.value, meshY.value, teamSize.value))
const ranks = computed(() => Array.from({ length: dimensions.value.x * dimensions.value.y }, (_, index) => index))
const scopes = computed(() => parallel.index?.scopes || [])
const solverScope = computed(() => scopes.value.find(scope => scope.name === 'solve_em' && scope.path === 'dyn_em/solve_em.F'))
const activeScope = computed(() => scopes.value.find(scope => scope.id === scopeId.value))
const filteredScopes = computed(() => scopes.value.filter(scope => `${scope.name} ${scope.path}`.toLowerCase().includes(scopeQuery.value.trim().toLowerCase())))
const episodeScopes = computed(() => {
  const exchangeIds = exchangeImplementations.value.map(item => item.scopeId)
  const barrierId = parallel.index?.events.find(event => event.kind === 'mpi_barrier')?.scopeId
  return scopes.value.filter(scope => [solverScope.value?.id, ...exchangeIds, barrierId, scopeId.value].includes(scope.id))
})
const scopeEvents = computed(() => (parallel.index?.events || []).filter(event => event.scopeId === scopeId.value))
const events = computed(() => scopeEvents.value.filter(event => showExcluded.value || eventAvailability(event, mode.value) !== 'inactive'))
const cursor = computed({ get: () => Math.max(0, events.value.findIndex(event => event.id === selectedId.value)), set: value => { selectedId.value = events.value[value]?.id || ''; selectionNotice.value = '' } })
const selectedEvent = computed(() => events.value.find(event => event.id === selectedId.value))
const selectedRequest = computed(() => requestAssociations(scopeEvents.value, mode.value).find(link => link.post.id === selectedId.value || link.wait.id === selectedId.value))
const availabilityLabel = computed(() => !selectedEvent.value ? '' : ({ active: 'build-compatible; runtime reachability unproven', conditional: 'conditional participation', inactive: 'excluded mechanism' })[eventAvailability(selectedEvent.value, mode.value)])
const communication = computed(() => parallel.index?.communications.find(item => item.id === selectedEvent.value?.communicationId))
const communicationFields = computed(() => [...new Set(communication.value?.groups.flatMap(group => group.fields) || [])])
const exchangeImplementations = computed(() => [...new Map((parallel.index?.generatorEvidence || []).flatMap(anchor => {
  const scope = scopes.value.find(item => item.name === anchor.description?.toLowerCase())
  return scope ? [[scope.id, { scopeId: scope.id, label: anchor.description }]] as const : []
})).values()])
const topology = computed(() => communicationTopology(selectedEvent.value, events.value))
const collective = computed(() => topology.value === 'communicator')
const communicationVisible = computed(() => !!selectedEvent.value && !!topology.value && eventAvailability(selectedEvent.value, mode.value) !== 'inactive')
const neighbors = computed(() => !profile.value.mpi || !communicationVisible.value ? [] : collective.value ? ranks.value.filter(rank => rank !== selectedRank.value) : rankNeighbors(selectedRank.value, dimensions.value.x, dimensions.value.y, topology.value as 'x' | 'y' | 'both'))
const threadScope = computed(() => {
  const event = selectedEvent.value
  if (!event) return ''
  if (event.kind === 'monitor') return 'Monitor predicate; communicator-relative rank ownership needs source inspection.'
  if (profile.value.omp && (event.kind.startsWith('omp_') || event.threadContext)) return `OpenMP construct within a participating rank: ${event.construct || event.threadContext || 'team boundary'}. Actual team size remains runtime-dependent.`
  return profile.value.mpi ? 'Lexically outside a modeled OpenMP region. Which ranks reach it remains unresolved.' : 'One process; transitive threading and runtime branches remain unresolved.'
})
const waitScope = computed(() => {
  const event = selectedEvent.value
  if (!event || eventAvailability(event, mode.value) === 'inactive') return 'No synchronization from this excluded mechanism.'
  if (event.kind === 'mpi_wait') return 'The caller, for the request(s) shown below; not all ranks.'
  if (event.kind === 'mpi_barrier') return 'Members of the supplied communicator; not automatically all launched processes.'
  if (event.kind === 'omp_join') return 'The relevant OpenMP team within each participating rank.'
  if (profile.value.omp && (event.construct === 'critical' || event.threadContext === 'critical')) return 'Threads competing for this critical region may wait for mutual exclusion; no team join is implied.'
  if (event.kind === 'exchange' || event.kind === 'mpi_collective' || event.kind === 'mpi_transfer') return 'Communication completion can constrain progress; actual wait duration is unknown.'
  return 'No wait established by this source event.'
})
const catalogMatches = computed(() => (parallel.index?.events || []).filter(event => event.kind !== 'call' && (showExcluded.value || eventAvailability(event, mode.value) !== 'inactive') && (!query.value.trim() || `${event.operation} ${event.directive || ''} ${event.scope} ${event.kind} ${event.evidence[0]?.path}`.toLowerCase().includes(query.value.trim().toLowerCase()))))
const catalogCount = computed(() => catalogMatches.value.length)
const catalogResults = computed(() => catalogMatches.value.slice(catalogPage.value * 12, (catalogPage.value + 1) * 12))
const announcement = computed(() => `${mode.value}, ${ranks.value.length} processes and ${dimensions.value.threads} threads per process. ${selectedEvent.value?.operation || 'No source event'}, ${selectedEvent.value ? eventMeaning(selectedEvent.value, mode.value).label : ''}.`)
const selectEvent = (event: ParallelEvent) => { stop(); selectedId.value = event.id; selectionNotice.value = '' }
const stop = () => { playing.value = false; if (timer) clearTimeout(timer); timer = undefined }
const step = (direction: number) => { stop(); cursor.value = Math.max(0, Math.min(events.value.length - 1, cursor.value + direction)) }
const schedule = () => { if (timer) clearTimeout(timer); timer = setTimeout(() => { if (cursor.value + 1 >= events.value.length) stop(); else { cursor.value++; schedule() } }, delay.value) }
const togglePlay = () => { if (playing.value) stop(); else { if (cursor.value + 1 >= events.value.length) cursor.value = 0; playing.value = true; schedule() } }
const openEvidence = (anchor: SourceEvidence) => { stop(); evidence.open(anchor, 'Parallel execution evidence', 'exact', 'This anchor proves a source statement or declaration, not runtime participation or elapsed waiting time.', route.fullPath) }
const openField = (field: string) => { stop(); router.push({ path: '/variables', query: { field } }) }
const openCatalogEvent = async (event: ParallelEvent) => {
  stop(); scopeId.value = event.scopeId
  await nextTick()
  cursor.value = Math.max(0, events.value.findIndex(item => item.id === event.id))
  await nextTick()
  inspector.value?.scrollIntoView({ block: 'start' })
  inspector.value?.focus({ preventScroll: true })
}
const firstBoundary = () => Math.max(0, events.value.findIndex(event => ['omp_region', 'mpi_post', 'mpi_wait', 'mpi_barrier', 'mpi_collective'].includes(event.kind)))

watch(() => [graph.activeSnapshotId, graph.isLoaded], () => { stop(); parallel.load() }, { immediate: true })
watch(() => parallel.index, index => { if (!index) return; scopeId.value = solverScope.value?.id || scopes.value[0]?.id || ''; cursor.value = 0 })
watch(scopeId, () => { stop(); cursor.value = firstBoundary() })
watch(events, (next, previous) => {
  stop()
  if (previous.length && next.length && previous[0]?.scopeId !== next[0]?.scopeId) return
  const old = previous.find(event => event.id === selectedId.value)
  const id = retainedSelection(previous, next, selectedId.value)
  if (id !== selectedId.value) {
    selectedId.value = id
    selectionNotice.value = old ? `${old.operation} at line ${old.evidence[0]?.startLine} is hidden by the current mode/filter. ${id ? 'Selected the nearest remaining source stop.' : 'No source stops remain.'}` : ''
  }
})
watch([query, mode, showExcluded, () => parallel.index], () => { catalogPage.value = 0 })
watch(mode, value => router.replace({ query: { ...route.query, view: 'parallel', mode: value } }))
watch(() => route.query.mode, value => { if (BUILD_MODES.some(item => item.id === value)) mode.value = value as BuildMode })
watch(dimensions, () => { if (!ranks.value.includes(selectedRank.value)) selectedRank.value = 0 })
watch(delay, () => { if (playing.value) schedule() })
onBeforeUnmount(stop)
</script>

<style scoped>
.parallel-execution { display: grid; gap: 20px; min-width: 0; }
.event-inspector { scroll-margin-top: 140px; }
.parallel-heading,.event-title,.catalog-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.parallel-heading h2 { font-size: 1.5rem; }.parallel-heading p { margin-top: 5px; color: var(--text-secondary); font-size: .9rem; }
.fidelity { padding-top: 7px; color: var(--text-muted); font-size: .8rem; }
fieldset { min-width: 0; border: 0; margin: 0; padding: 16px 0; border-block: 1px solid var(--border-subtle); }legend { padding: 0 10px 0 0; font-size: .85rem; font-weight: 650; }
.mode-options { display: flex; flex-wrap: wrap; gap: 6px; }.mode-options button { min-height: 44px; padding: 8px 15px; border: 1px solid var(--border-strong); border-radius: 5px; background: var(--bg-inset); color: var(--text-secondary); cursor: pointer; font-size: .85rem; }.mode-options button[aria-pressed="true"] { background: var(--accent-soft); border-color: var(--accent-emerald); color: var(--text-primary); }.mode-control p { margin-top: 10px; font-size: .85rem; color: var(--text-secondary); }
.parallel-controls { display: flex; align-items: flex-end; flex-wrap: wrap; gap: 12px; }.parallel-controls > label:first-child { flex: 1; min-width: 230px; }.parallel-controls label,.playback label { display: flex; flex-direction: column; gap: 5px; font-size: .8rem; color: var(--text-secondary); }select { min-width: 60px; min-height: 44px; max-width: 100%; padding: 6px 10px; border: 1px solid var(--border-strong); border-radius: 4px; background: var(--bg-inset); color: var(--text-primary); font: .8rem var(--font-sans); }select:disabled { opacity: .55; } .parallel-controls .checkbox-control { min-height: 44px; flex-direction: row; align-items: center; gap: 7px; }
.walkthrough-controls { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }.walkthrough-controls > span { color: var(--text-muted); font-size: .8rem; }.playback { display: flex; align-items: center; gap: 6px; }.playback label { margin-left: 8px; flex-direction: row; align-items: center; }.playback button,.index-state button { display: inline-flex; justify-content: center; align-items: center; gap: 8px; min-width: 44px; min-height: 44px; background: var(--bg-inset); color: var(--text-primary); border: 1px solid var(--border-strong); border-radius: 4px; cursor: pointer; }.playback button:disabled { opacity: .4; cursor: default; }
.parallel-diagrams { display: grid; grid-template-columns: 240px minmax(0,1fr); gap: 20px; align-items: start; }.mesh-tool,.lane-tool { min-width: 0; border: 1px solid var(--border-subtle); border-radius: 6px; overflow: hidden; background: var(--bg-inset); }.mesh-tool { padding: 16px; }.mesh-tool h3,.lane-heading h3 { font-size: .95rem; }.mesh { display: grid; gap: 8px; margin-top: 18px; aspect-ratio: 1; align-content: center; }.mesh > button { display: flex; min-width: 0; aspect-ratio: 1; flex-direction: column; justify-content: center; align-items: center; gap: 8px; padding: 5px; border: 1px dashed var(--border-strong); border-radius: 3px; background: var(--bg-raised); color: var(--text-secondary); cursor: pointer; font-size: .8rem; }.mesh > button.selected { border: 2px solid var(--accent-emerald); background: var(--accent-soft); color: var(--text-primary); }.mesh > button.neighbor { border-color: var(--accent-amber); background: color-mix(in srgb,var(--accent-amber) 9%,var(--bg-raised)); }.mesh small { font-size: .7rem; }.mesh-threads { display: grid; grid-template-columns: repeat(2,1fr); gap: 2px; width: 85%; }.mesh-threads i { border: 1px solid var(--border-subtle); color: var(--text-muted); font: normal .65rem var(--font-mono); text-align: center; }.mesh-tool p { color: var(--text-secondary); font-size: .8rem; line-height: 1.6; margin-top: 15px; }.mesh-legend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 13px; color: var(--text-muted); font-size: .75rem; }.mesh-legend span { display: flex; gap: 5px; align-items: center; }.mesh-legend i { width: 9px; height: 9px; border: 1px solid var(--accent-emerald); }.mesh-legend .neighbor-key { border-color: var(--accent-amber); }
.lane-heading { padding: 16px; display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 6px; }.lane-heading span { color: var(--text-muted); font-size: .75rem; }.lanes-scroll { overflow: auto; max-height: 570px; }.lanes { display: grid; width: max-content; gap: 1px; background: var(--border-subtle); }.lanes > * { border: 0; }.lane-corner,.rank-label { position: sticky; left: 0; z-index: 1; background: var(--bg-raised); color: var(--text-secondary); padding: 12px; font-size: .8rem; text-align: left; }.lane-corner { display: flex; align-items: center; }.rank-label { cursor: pointer; }.rank-label[aria-pressed="true"] { color: var(--accent-emerald); box-shadow: inset 0 0 0 1px var(--accent-emerald); }.event-heading { min-height: 78px; padding: 10px; background: var(--bg-raised); color: var(--text-secondary); text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 7px; }.event-heading strong { font: 550 .8rem var(--font-mono); overflow-wrap: anywhere; }.event-heading small { font-size: .75rem; color: var(--text-muted); }.event-heading[aria-pressed="true"] { box-shadow: inset 0 -2px var(--accent-emerald); color: var(--text-primary); }.event-cell { height: 92px; padding: 10px; display: flex; flex-direction: column; justify-content: center; gap: 7px; background: var(--bg-inset); color: var(--text-secondary); text-align: left; cursor: pointer; }.event-cell > span { font-size: .8rem; line-height: 1.35; }.event-cell small { color: var(--text-muted); font-size: .7rem; }.event-cell.current { background: var(--bg-surface-hover); }.event-cell.current.selected { outline: 1px solid var(--accent-emerald); outline-offset: -1px; }.event-cell.omp_join,.event-cell.mpi_wait { color: var(--accent-amber); }.event-cell.mpi_barrier { background: color-mix(in srgb,var(--accent-amber) 10%,var(--bg-inset)); }.event-cell.inactive,.event-heading.inactive { color: var(--text-muted); background: var(--bg-raised); }.thread-slots { display: flex; gap: 3px; }.thread-slots i { flex: 1; border: 1px solid var(--border-strong); font: normal .65rem var(--font-mono); text-align: center; padding: 2px; color: var(--text-secondary); }.diagram-legend { display: flex; flex-wrap: wrap; gap: 10px 18px; padding: 12px 16px; color: var(--text-muted); font-size: .75rem; }.empty-events { min-height: 200px; padding: 25px; color: var(--text-secondary); font-size: .9rem; }
.event-inspector { border-block: 1px solid var(--border-subtle); padding: 22px 0; }.event-title h3 { font-size: 1.1rem; overflow-wrap: anywhere; }.event-title p { margin-top: 4px; color: var(--accent-emerald); font-size: .8rem; }.event-explanation { max-width: 75ch; margin-top: 14px; font-size: .95rem; color: var(--text-secondary); line-height: 1.65; }.evidence-button,.inspector-links button,.implementation-links button { display: inline-flex; gap: 7px; align-items: center; min-height: 44px; padding: 7px 12px; background: var(--bg-inset); border: 1px solid var(--border-strong); border-radius: 4px; color: var(--text-primary); font-size: .8rem; cursor: pointer; }.event-facts { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 18px 0; }.event-facts dt { font-size: .8rem; color: var(--text-muted); }.event-facts dd { margin: 5px 0 0; font-size: .85rem; color: var(--text-secondary); line-height: 1.55; overflow-wrap: anywhere; }.conditions,.exchange-fields,.request-arguments { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-subtle); }.event-inspector h4 { font-size: .9rem; margin-bottom: 8px; }.conditions > code { display: block; font-size: .8rem; line-height: 1.7; overflow-wrap: anywhere; color: var(--text-secondary); }.request-arguments > code { display: block; max-height: 130px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--text-secondary); font-size: .85rem; line-height: 1.7; }.field-links { display: flex; flex-wrap: wrap; gap: 5px; margin: 10px 0; }.field-links button { min-height: 36px; background: var(--bg-inset); color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: 3px; padding: 5px 9px; cursor: pointer; font: .8rem var(--font-mono); }.exchange-fields p { color: var(--text-muted); max-width: 75ch; font-size: .85rem; line-height: 1.6; margin: 10px 0; }.implementation-links,.inspector-links { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 14px; }.inspector-links a { display: flex; align-items: center; gap: 6px; min-height: 44px; font-size: .85rem; color: var(--accent-emerald); }.source-anchor { display: block; min-height: 44px; background: transparent; border: 0; color: var(--text-secondary); text-align: left; font: .8rem var(--font-mono); cursor: pointer; overflow-wrap: anywhere; }details summary { min-height: 44px; cursor: pointer; padding-block: 12px; color: var(--text-secondary); font-size: .85rem; }
.catalog-heading { align-items: center; }.catalog-heading h3 { font-size: 1rem; }.catalog-heading label { display: flex; align-items: center; gap: 8px; min-width: 250px; max-width: 100%; border: 1px solid var(--border-strong); background: var(--bg-inset); border-radius: 4px; padding: 0 10px; }.catalog-heading input { width: 100%; min-width: 0; min-height: 44px; border: 0; color: var(--text-primary); background: transparent; font-size: .85rem; }.catalog-results { margin-top: 13px; display: grid; grid-template-columns: 1fr 1fr; gap: 1px; }.catalog-results button { min-width: 0; display: flex; flex-direction: column; gap: 5px; text-align: left; padding: 12px 10px; border: 0; border-bottom: 1px solid var(--border-subtle); background: transparent; cursor: pointer; }.catalog-results strong { font: 550 .85rem var(--font-mono); color: var(--text-primary); }.catalog-results span { color: var(--text-secondary); font-size: .75rem; overflow-wrap: anywhere; }.catalog-results small { color: var(--text-muted); font-size: .75rem; }.parallel-catalog > p,.parallel-limits p,.parallel-limits li { font-size: .85rem; color: var(--text-secondary); line-height: 1.7; }.parallel-catalog > p { margin-top: 12px; }.parallel-limits ul { padding-left: 20px; }.index-state { min-height: 200px; padding: 25px 0; color: var(--text-secondary); }.index-state button { padding-inline: 12px; margin-top: 12px; }button:hover:not(:disabled) { filter: brightness(1.08); }button:focus-visible { outline: 2px solid var(--accent-emerald); outline-offset: 2px; }
.mesh > button { aspect-ratio: auto; min-height: 0; }
.parallel-execution { gap: 14px; }.mode-control { padding: 8px 0 12px; }.scope-toolbar { display: flex; align-items: flex-end; gap: 16px; }.scope-toolbar > label { flex: 1; min-width: 0; display: grid; gap: 5px; color: var(--text-secondary); font-size: .8rem; }.scope-toolbar select { width: 100%; }.scope-browser { width: min(330px,40%); }.scope-browser summary,.build-settings summary { display: flex; align-items: center; gap: 8px; min-height: 44px; padding: 8px 0; }.scope-browser label { display: grid; gap: 5px; font-size: .8rem; color: var(--text-secondary); }.scope-browser input { min-width: 0; width: 100%; min-height: 44px; margin-bottom: 8px; padding: 6px 10px; background: var(--bg-inset); border: 1px solid var(--border-strong); border-radius: 4px; color: var(--text-primary); font: inherit; }.scope-browser p { color: var(--text-secondary); font-size: .75rem; margin-top: 6px; }
.settings-layout { display: grid; grid-template-columns: 1fr 320px; gap: 20px; align-items: start; padding: 8px 0 14px; }.parallel-controls { align-items: flex-start; }.parallel-controls > label:first-child { flex: none; min-width: 0; }.settings-layout .mesh-tool { display: grid; grid-template-columns: 120px 1fr; gap: 10px; border: 0; border-radius: 0; padding: 0; background: transparent; }.settings-layout .mesh-tool h3 { grid-column: 1/-1; }.settings-layout .mesh { margin: 0; width: 120px; grid-row: auto; }.settings-layout .mesh-tool p { margin: 0; }.settings-layout .mesh > button { font-size: .65rem; }
.selection-notice { font-size: .85rem; line-height: 1.6; color: var(--accent-amber); }.request-association,.request-unresolved { margin-top: 16px; color: var(--text-secondary); font-size: .85rem; line-height: 1.6; }.request-association p { max-width: 75ch; }.source-details > p { font-size: .85rem; color: var(--text-secondary); }.catalog-pagination { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-top: 12px; }.catalog-pagination p { color: var(--text-secondary); font-size: .8rem; }.catalog-pagination div { display: flex; gap: 6px; }.catalog-pagination button { width: 44px; height: 44px; display: grid; place-items: center; border: 1px solid var(--border-strong); border-radius: 4px; background: var(--bg-inset); color: var(--text-primary); cursor: pointer; }.catalog-pagination button:disabled { opacity: .4; cursor: default; }
@media(max-width:800px) { .settings-layout { grid-template-columns: 1fr; }.scope-toolbar { flex-wrap: wrap; }.scope-toolbar > label { flex-basis: 100%; }.scope-browser { width: 100%; } }
.scope-toolbar { align-items: flex-start; }.scope-toolbar > label { min-width: 180px; }.scope-browser,.build-settings { position: relative; flex: none; width: auto; padding-top: 20px; }.scope-browser summary,.build-settings summary { padding: 6px 0; font-size: .8rem; }.scope-browser[open] { width: min(330px,100%); }.build-settings[open] { width: 100%; flex-basis: 100%; padding-top: 0; }.scope-toolbar:has(.build-settings[open]) { flex-wrap: wrap; }.settings-layout { grid-template-columns: 1fr 320px; }.execution-workspace { display: grid; grid-template-columns: minmax(0,1fr) 320px; gap: 22px; align-items: start; }.execution-workspace .event-inspector { border: 0; padding: 4px 0; }.execution-workspace .event-title { flex-direction: column; gap: 8px; }.execution-workspace .event-title h3 { font-size: 1rem; }.execution-workspace .event-explanation { font-size: .85rem; }.execution-workspace .event-facts { grid-template-columns: 1fr; gap: 12px; }.execution-workspace .event-facts dd { font-size: .8rem; }.execution-workspace .inspector-links { gap: 5px 10px; }.walkthrough-controls > span { max-width: 48ch; line-height: 1.4; text-align: right; }
@media(max-width:1280px) { .execution-workspace { grid-template-columns: 1fr; }.execution-workspace .event-title { flex-direction: row; }.execution-workspace .event-facts { grid-template-columns: repeat(3,minmax(0,1fr)); }.execution-workspace .event-inspector { border-block: 1px solid var(--border-subtle); padding-block: 16px; } }
@media(max-width:800px) { .scope-toolbar { gap: 6px 20px; }.scope-browser,.build-settings { padding-top: 0; }.settings-layout { grid-template-columns: 1fr; }.execution-workspace .event-title { flex-wrap: wrap; }.execution-workspace .event-facts { grid-template-columns: 1fr; }.walkthrough-controls > span { text-align: left; } }
@media(max-width:1000px) { .parallel-diagrams { grid-template-columns: 1fr; }.mesh-tool { display: grid; grid-template-columns: 190px 1fr; gap: 10px 20px; }.mesh-tool h3 { grid-column: 1/-1; }.mesh { margin-top: 0; grid-row: 2/4; }.mesh-tool p { margin-top: 0; }.event-facts { grid-template-columns: 1fr; gap: 12px; } }
@media(max-width:600px) { .parallel-heading,.event-title,.catalog-heading { flex-direction: column; gap: 10px; }.mode-options { display: grid; grid-template-columns: 1fr 1fr; }.mode-options button { padding-inline: 7px; font-size: .8rem; }.parallel-controls > label:first-child { flex-basis: 100%; min-width: 0; }.parallel-controls > label:first-child select { width: 100%; }.mesh-tool { display: block; }.mesh { width: min(230px,100%); margin: 15px auto; }.mesh-tool p { margin-top: 12px; }.catalog-heading label { width: 100%; min-width: 0; }.catalog-results { grid-template-columns: 1fr; }.walkthrough-controls > span { line-height: 1.6; }.field-links button { min-height: 44px; } }
</style>
