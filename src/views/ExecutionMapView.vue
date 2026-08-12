<template>
  <div class="execution-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">Source-derived execution</p>
        <h1>How control moves through WRF</h1>
        <p>Follow indexed call sites from the executable entry into ARW integration, then play the physics sequence visible around one conceptual timestep.</p>
      </div>
      <div class="source-state"><span><i></i>{{ exactCallCount }} exact source anchors shown</span><small>Ordering is taken from source line positions. Unresolved conditions remain explicit.</small></div>
    </header>

    <nav class="view-tabs surface-panel" aria-label="Execution views">
      <button :class="{ active: activeView === 'lifecycle' }" @click="setView('lifecycle')"><span>01</span><div><strong>Run lifecycle</strong><small>wrf.exe to solve_em</small></div></button>
      <button :class="{ active: activeView === 'timestep' }" @click="setView('timestep')"><span>02</span><div><strong>One timestep</strong><small>RK and physics call sites</small></div></button>
    </nav>

    <div v-if="!graphStore.isLoaded" class="loading-panel surface-panel">Building the execution story from indexed calls…</div>

    <section v-else-if="activeView === 'lifecycle'" class="lifecycle-layout">
      <main class="lifecycle-map surface-panel">
        <div class="map-heading"><div><p class="eyebrow">Forward ARW path</p><h2>Executable entry → integration core</h2></div><span>Click a stop for evidence</span></div>
        <div class="lifecycle-chain">
          <template v-for="(stage, index) in lifecycleStages" :key="stage.id">
            <button class="lifecycle-stage" :class="[{ active: selectedLifecycleStage.id === stage.id }, stage.confidence]" @click="selectedLifecycleStage = stage">
              <span class="stage-index">{{ String(index + 1).padStart(2, '0') }}</span>
              <div><small>{{ stage.role }}</small><strong><code>{{ stage.label }}</code></strong><span>{{ stage.callFile || stage.file }}</span></div>
              <i :class="stage.confidence"></i>
            </button>
            <span v-if="index < lifecycleStages.length - 1" class="chain-link"><i></i><small>{{ stage.transition }}</small></span>
          </template>
        </div>
      </main>

      <aside class="stage-inspector surface-panel">
        <div class="inspector-heading"><p class="eyebrow">Selected evidence</p><span>03</span></div>
        <span class="confidence-label" :class="selectedLifecycleStage.confidence">{{ selectedLifecycleStage.confidence }} relationship</span>
        <h2><code>{{ selectedLifecycleStage.label }}</code></h2>
        <p>{{ selectedLifecycleStage.description }}</p>
        <dl>
          <div><dt>Source entity</dt><dd>{{ selectedLifecycleStage.node?.type || 'conceptual stage' }}</dd></div>
          <div><dt>Defined at</dt><dd><code>{{ selectedLifecycleStage.file }}:{{ selectedLifecycleStage.definitionLine || '?' }}</code></dd></div>
          <div><dt>Reached from</dt><dd><code>{{ selectedLifecycleStage.parentLabel || 'process entry' }}</code></dd></div>
          <div><dt>Call evidence</dt><dd><code>{{ selectedLifecycleStage.callLine ? `${selectedLifecycleStage.callFile}:${selectedLifecycleStage.callLine}` : 'definition anchor' }}</code></dd></div>
        </dl>
        <button v-if="selectedLifecycleStage.file" class="source-button" @click="openSource(selectedLifecycleStage.callFile || selectedLifecycleStage.file, selectedLifecycleStage.callLine || selectedLifecycleStage.definitionLine)">Open source evidence <span>↗</span></button>
        <div class="meaning-card"><strong>Why this stop matters</strong><p>{{ selectedLifecycleStage.meaning }}</p></div>
      </aside>
    </section>

    <section v-else class="timestep-layout">
      <div class="story-controls surface-panel">
        <div><p class="eyebrow">Conceptual playback</p><h2>One ARW timestep</h2></div>
        <div class="playback-controls">
          <button @click="previousStage" aria-label="Previous stage">←</button>
          <button class="play-button" @click="togglePlayback">{{ playing ? 'Pause' : 'Play' }}</button>
          <button @click="nextStage" aria-label="Next stage">→</button>
          <label>Speed<select v-model.number="playbackDelay"><option :value="1800">0.75×</option><option :value="1100">1×</option><option :value="650">1.5×</option></select></label>
        </div>
      </div>

      <main class="storyboard surface-panel">
        <div class="time-axis"><span>TIME t</span><i></i><span>TIME t + Δt</span></div>
        <div class="phase-bands">
          <div class="phase-label"><span>CALL SITE</span><span>PHYSICAL ROLE</span><span>EVIDENCE</span></div>
          <button v-for="(stage, index) in timestepStages" :key="stage.id" class="story-stage" :class="[{ active: index === currentStageIndex, passed: index < currentStageIndex }, stage.confidence]" @click="selectTimestepStage(index)">
            <div class="pulse-marker"><i></i><span>{{ String(index + 1).padStart(2, '0') }}</span></div>
            <div class="stage-code"><small>{{ stage.phase }}</small><strong><code>{{ stage.label }}</code></strong><span>{{ stage.parentLabel }}:{{ stage.line || '?' }}</span></div>
            <div class="stage-physics"><strong>{{ stage.physicalRole }}</strong><span>{{ stage.description }}</span></div>
            <div class="stage-proof"><span class="confidence-label" :class="stage.confidence">{{ stage.confidence }}</span><button v-if="stage.path" @click.stop="openSource(stage.path, stage.line)">Source ↗</button></div>
          </button>
        </div>
      </main>

      <aside class="current-stage surface-panel">
        <div class="current-index">{{ String(currentStageIndex + 1).padStart(2, '0') }} / {{ String(timestepStages.length).padStart(2, '0') }}</div>
        <p class="eyebrow">Now explaining</p>
        <h2><code>{{ currentTimestepStage.label }}</code></h2>
        <p>{{ currentTimestepStage.description }}</p>
        <div class="stage-context"><strong>{{ currentTimestepStage.physicalRole }}</strong><span>{{ currentTimestepStage.context }}</span></div>
        <dl>
          <div><dt>Parent scope</dt><dd><code>{{ currentTimestepStage.parentLabel }}</code></dd></div>
          <div><dt>Source order</dt><dd>{{ currentTimestepStage.line ? `call at line ${currentTimestepStage.line}` : 'bounded inference' }}</dd></div>
          <div><dt>Scheduling</dt><dd>{{ currentTimestepStage.scheduling }}</dd></div>
        </dl>
        <button v-if="currentTimestepStage.path" class="source-button" @click="openSource(currentTimestepStage.path, currentTimestepStage.line)">Show this call in source <span>↗</span></button>
      </aside>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import type { GraphEdge, GraphNode } from '@/types/graph'

type ExecutionView = 'lifecycle' | 'timestep'
interface LifecycleStage { id: string; label: string; role: string; description: string; meaning: string; transition: string; confidence: 'exact' | 'inferred'; node?: GraphNode; file: string; callFile?: string; definitionLine?: number; callLine?: number; parentLabel?: string }
interface TimestepStage { id: string; label: string; phase: string; physicalRole: string; description: string; context: string; scheduling: string; confidence: 'exact' | 'inferred'; parentLabel: string; path?: string; line?: number }

const graphStore = useGraphStore()
const route = useRoute()
const router = useRouter()
const activeView = ref<ExecutionView>(route.query.view === 'timestep' ? 'timestep' : 'lifecycle')

const node = (id: string) => graphStore.getNodeById(id)
const exactCall = (source: string, target: string): GraphEdge | undefined => graphStore.getEdgesFrom(source)
  .filter(edge => edge.type === 'CALLS' && edge.target === target && edge.data?.evidence?.length)
  .sort((a, b) => (a.data.evidence?.[0]?.startLine || 0) - (b.data.evidence?.[0]?.startLine || 0))[0]
const evidencePath = (edge?: GraphEdge) => edge?.data?.evidence?.[0]?.path
const evidenceLine = (edge?: GraphEdge) => edge?.data?.evidence?.[0]?.startLine

const lifecycleSpecs = [
  { id: 'program:wrf', role: 'Executable entry', description: 'PROGRAM wrf is the compiled entry point that orders initialization, the forward run, and finalization.', meaning: 'This is the narrow top of the execution tree. Its direct calls define the visible lifecycle of wrf.exe.', transition: 'CALL wrf_init' },
  { id: 'subroutine:wrf_init', parent: 'program:wrf', role: 'Initialization', description: 'wrf_init begins model-service, configuration, and domain initialization work.', meaning: 'Configuration becomes allocated model state before time integration begins.', transition: 'program sequence' },
  { id: 'subroutine:wrf_run', parent: 'program:wrf', role: 'Forward run', description: 'wrf_run starts domains and calls the integration mediator.', meaning: 'This separates process-level startup from the recursive, multi-domain integration machinery.', transition: 'CALL integrate' },
  { id: 'subroutine:integrate', parent: 'subroutine:wrf_run', role: 'Domain mediator', description: 'integrate manages per-domain setup, I/O boundaries, nesting operations, and calls solve_interface.', meaning: 'WRF domain orchestration surrounds the dynamical-core solver rather than living inside a single flat timestep loop.', transition: 'CALL solve_interface' },
  { id: 'subroutine:solve_interface', parent: 'subroutine:integrate', role: 'Core dispatch', description: 'solve_interface selects the configured dynamical core and calls solve_em for ARW.', meaning: 'This boundary is where the framework reaches the ARW-specific solver implementation.', transition: 'CALL solve_em' },
  { id: 'subroutine:solve_em', parent: 'subroutine:solve_interface', role: 'ARW integration', description: 'solve_em contains the ARW Runge-Kutta integration and the physics call sites indexed by this Atlas.', meaning: 'Most timestep-oriented exploration begins here, but important mediation and initialization occur above it.', transition: 'return to program' },
  { id: 'subroutine:wrf_finalize', parent: 'program:wrf', role: 'Finalization', description: 'The top-level program calls wrf_finalize after the selected run path completes.', meaning: 'Execution returns to the program boundary for model-service and process shutdown.', transition: 'complete' },
]

const lifecycleStages = computed<LifecycleStage[]>(() => lifecycleSpecs.map(spec => {
  const stageNode = node(spec.id)
  const callEdge = spec.parent ? exactCall(spec.parent, spec.id) : undefined
  return {
    ...spec,
    label: stageNode?.label || spec.id.split(':')[1],
    node: stageNode,
    file: stageNode?.data?.file || '',
    callFile: evidencePath(callEdge),
    definitionLine: stageNode?.data?.line,
    callLine: evidenceLine(callEdge),
    parentLabel: spec.parent ? node(spec.parent)?.label || spec.parent : undefined,
    confidence: stageNode && (!spec.parent || callEdge) ? 'exact' : 'inferred',
  }
}))
const selectedLifecycleStage = ref<LifecycleStage>({ ...lifecycleSpecs[0], label: 'wrf', file: 'main/wrf.F', confidence: 'exact' })

const phaseEdges = computed(() => graphStore.getEdgesOfType('EXECUTES_DURING').filter(edge => edge.data?.confidence === 'exact' && edge.data?.evidence?.length))
const firstPartDrivers = computed(() => phaseEdges.value.filter(edge => edge.target === 'phase:first_rk_step_part1').sort((a, b) => Number(a.data.order) - Number(b.data.order)))
const microphysicsPhaseEdge = computed(() => phaseEdges.value.find(edge => edge.source === 'subroutine:microphysics_driver'))

const driverMeaning: Record<string, { physicalRole: string; description: string; context: string }> = {
  radiation_driver: { physicalRole: 'Radiative transfer', description: 'Longwave and shortwave radiation schemes exchange energy with the atmospheric and surface state.', context: 'The call exists in first_rk_step_part1. Its scheduling condition is outside the current condition index.' },
  surface_driver: { physicalRole: 'Surface exchange and land state', description: 'Surface-layer and land-surface selections compute near-surface exchange and update land variables.', context: 'This is the shared runtime gateway for several surface and land-surface scheme branches.' },
  pbl_driver: { physicalRole: 'Boundary-layer mixing', description: 'The PBL selection operates on turbulent mixing and lower-atmosphere tendencies.', context: 'It follows the surface call in the indexed source order of first_rk_step_part1.' },
  cumulus_driver: { physicalRole: 'Sub-grid convection', description: 'The selected cumulus parameterization represents convection not explicitly resolved by the grid.', context: 'The call site is exact; whether it runs on a given step depends on configuration and scheduling logic not yet attached to this edge.' },
  shallowcu_driver: { physicalRole: 'Shallow convection', description: 'Optional shallow-convection work appears after the main cumulus driver in this source routine.', context: 'This is a distinct driver call and should not be conflated with the deep-convection selector.' },
  microphysics_driver: { physicalRole: 'Cloud and precipitation microphysics', description: 'The microphysics driver is called later from solve_em after the earlier first-RK physics call sites.', context: 'The source location establishes relative placement in this routine; detailed enclosing conditions remain to be indexed.' },
}

const timestepStages = computed<TimestepStage[]>(() => {
  const stages: TimestepStage[] = []
  const part1Call = exactCall('subroutine:solve_em', 'subroutine:first_rk_step_part1')
  if (part1Call) stages.push({ id: 'part1', label: 'first_rk_step_part1', phase: 'RK stage preparation', physicalRole: 'Prepare and run first-part physics', description: 'solve_em calls the first physics/tendency part at this indexed source location.', context: 'This routine contains the ordered radiation, surface, PBL, and convection driver calls shown next.', scheduling: 'Exact call site; enclosing RK condition not yet modeled.', confidence: 'exact', parentLabel: 'solve_em', path: evidencePath(part1Call), line: evidenceLine(part1Call) })
  for (const edge of firstPartDrivers.value) {
    const name = node(edge.source)?.label || edge.source.replace('subroutine:', '')
    const info = driverMeaning[name] || { physicalRole: 'Physics driver', description: 'Indexed driver call.', context: 'Inspect source for details.' }
    stages.push({ id: edge.source, label: name, phase: 'first_rk_step_part1', ...info, scheduling: 'Condition not yet attached to the indexed call.', confidence: 'exact', parentLabel: 'first_rk_step_part1', path: evidencePath(edge), line: evidenceLine(edge) })
  }
  const part2Call = exactCall('subroutine:solve_em', 'subroutine:first_rk_step_part2')
  if (part2Call) stages.push({ id: 'part2', label: 'first_rk_step_part2', phase: 'RK physics tendencies', physicalRole: 'Apply tendencies and diffusion work', description: 'solve_em calls the second first-RK routine after part1.', context: 'The routine contains physics-tendency conversion, diffusion, and boundary-condition work.', scheduling: 'Exact call site; enclosing RK condition not yet modeled.', confidence: 'exact', parentLabel: 'solve_em', path: evidencePath(part2Call), line: evidenceLine(part2Call) })
  stages.push({ id: 'rk-work', label: 'solve_em RK integration', phase: 'Dynamics interval', physicalRole: 'Advance the resolved atmospheric state', description: 'Substantial dynamics and small-step work occurs in solve_em between the early part1/part2 calls and the later microphysics call.', context: 'This is a bounded orientation inferred from exact surrounding call positions, not a single Fortran CALL.', scheduling: 'Inferred span within solve_em.', confidence: 'inferred', parentLabel: 'solve_em', path: node('subroutine:solve_em')?.data?.file, line: node('subroutine:solve_em')?.data?.line })
  const mp = microphysicsPhaseEdge.value
  if (mp) { const info = driverMeaning.microphysics_driver; stages.push({ id: mp.source, label: 'microphysics_driver', phase: 'Later solve_em physics', ...info, scheduling: 'Condition not yet attached to the indexed call.', confidence: 'exact', parentLabel: 'solve_em', path: evidencePath(mp), line: evidenceLine(mp) }) }
  return stages
})

const currentStageIndex = ref(0)
const currentTimestepStage = computed(() => timestepStages.value[currentStageIndex.value] || ({ label: 'unresolved', description: '', physicalRole: '', context: '', scheduling: '', parentLabel: '', confidence: 'inferred', id: '', phase: '' } as TimestepStage))
const playing = ref(false)
const playbackDelay = ref(1100)
let playbackTimer: ReturnType<typeof setInterval> | undefined
const stopPlayback = () => { playing.value = false; if (playbackTimer) clearInterval(playbackTimer); playbackTimer = undefined }
const startPlayback = () => { stopPlayback(); playing.value = true; playbackTimer = setInterval(() => { if (currentStageIndex.value >= timestepStages.value.length - 1) { stopPlayback(); return } currentStageIndex.value += 1 }, playbackDelay.value) }
const togglePlayback = () => playing.value ? stopPlayback() : startPlayback()
const nextStage = () => { stopPlayback(); currentStageIndex.value = Math.min(currentStageIndex.value + 1, timestepStages.value.length - 1) }
const previousStage = () => { stopPlayback(); currentStageIndex.value = Math.max(currentStageIndex.value - 1, 0) }
const selectTimestepStage = (index: number) => { stopPlayback(); currentStageIndex.value = index }
watch(playbackDelay, () => { if (playing.value) startPlayback() })

const exactCallCount = computed(() => lifecycleStages.value.filter(stage => stage.confidence === 'exact').length + timestepStages.value.filter(stage => stage.confidence === 'exact').length)
const setView = (view: ExecutionView) => { activeView.value = view; stopPlayback(); router.replace({ query: view === 'timestep' ? { view: 'timestep' } : {} }) }
const openSource = (path?: string, line?: number) => { if (path) router.push({ path: '/source', query: { file: path.replaceAll('\\', '/'), line: String(line || 1) } }) }

watch(() => graphStore.isLoaded, loaded => {
  if (loaded) selectedLifecycleStage.value = lifecycleStages.value[0]
}, { immediate: true })
onMounted(async () => { if (!graphStore.isLoaded && !graphStore.loading) await graphStore.loadGraph() })
onBeforeUnmount(stopPlayback)
</script>

<style scoped>
.execution-view { display: flex; width: 100%; max-width: 1480px; margin: 0 auto; flex-direction: column; gap: 18px; }.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 40px; padding: 5px 2px 8px; }.page-header h1 { margin-top: 6px; font-size: 2rem; font-weight: 580; }.page-header > div > p:last-child { max-width: 760px; margin-top: 7px; color: var(--text-secondary); font-size: .82rem; }.source-state { max-width: 340px; padding-left: 18px; border-left: 1px solid var(--border-subtle); }.source-state span { display: flex; align-items: center; gap: 7px; color: var(--text-secondary); font-size: .66rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }.source-state i { width: 7px; height: 7px; background: var(--accent-emerald); border-radius: 50%; }.source-state small { display: block; margin-top: 6px; color: var(--text-muted); font-size: .61rem; line-height: 1.45; }
.view-tabs { display: grid; width: 520px; grid-template-columns: 1fr 1fr; padding: 4px; }.view-tabs button { display: grid; min-height: 52px; grid-template-columns: 28px 1fr; align-items: center; gap: 8px; padding: 7px 11px; background: transparent; border: 1px solid transparent; border-radius: 5px; color: var(--text-muted); cursor: pointer; text-align: left; }.view-tabs button.active { background: var(--accent-soft); border-color: color-mix(in srgb,var(--accent-emerald) 25%,var(--border-subtle)); color: var(--text-primary); }.view-tabs button > span { color: var(--accent-emerald); font-family: var(--font-mono); font-size: .59rem; }.view-tabs button div { display: flex; flex-direction: column; }.view-tabs strong { font-size: .72rem; }.view-tabs small { margin-top: 2px; color: var(--text-muted); font-size: .58rem; }.loading-panel { display: grid; min-height: 460px; place-items: center; color: var(--text-muted); }
.lifecycle-layout { display: grid; grid-template-columns: minmax(0,1fr) 330px; gap: 14px; }.lifecycle-map,.stage-inspector { overflow: hidden; }.map-heading { display: flex; min-height: 76px; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); }.map-heading h2 { margin-top: 4px; font-size: 1rem; }.map-heading > span { color: var(--text-muted); font-size: .6rem; }.lifecycle-chain { display: flex; min-height: 610px; flex-direction: column; justify-content: center; padding: 24px 9%; }.lifecycle-stage { position: relative; display: grid; min-height: 56px; grid-template-columns: 34px 1fr 12px; align-items: center; gap: 10px; padding: 8px 13px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 5px; color: var(--text-secondary); cursor: pointer; text-align: left; }.lifecycle-stage:hover,.lifecycle-stage.active { background: var(--bg-surface-hover); border-color: var(--border-strong); }.lifecycle-stage.active { box-shadow: inset 2px 0 var(--accent-emerald); }.stage-index { color: var(--text-muted); font-family: var(--font-mono); font-size: .59rem; }.lifecycle-stage > div { display: grid; grid-template-columns: 120px 160px minmax(0,1fr); align-items: center; gap: 10px; }.lifecycle-stage small { color: var(--text-muted); font-size: .59rem; }.lifecycle-stage strong { font-size: .69rem; }.lifecycle-stage strong code { color: var(--text-primary); }.lifecycle-stage div > span { overflow: hidden; color: var(--text-muted); font-family: var(--font-mono); font-size: .55rem; text-overflow: ellipsis; white-space: nowrap; }.lifecycle-stage > i { width: 7px; height: 7px; border-radius: 50%; }.lifecycle-stage > i.exact { background: var(--accent-emerald); }.lifecycle-stage > i.inferred { border: 1px dashed var(--accent-amber); }.chain-link { display: grid; height: 22px; grid-template-columns: 34px 1fr; align-items: center; gap: 10px; margin-left: 13px; }.chain-link i { width: 1px; height: 100%; margin-left: 16px; background: var(--border-strong); }.chain-link small { color: var(--text-muted); font-family: var(--font-mono); font-size: .51rem; }
.inspector-heading { display: flex; align-items: center; justify-content: space-between; padding: 15px 17px; border-bottom: 1px solid var(--border-subtle); }.inspector-heading span { color: var(--border-strong); font-family: var(--font-mono); font-size: .6rem; }.stage-inspector > .confidence-label,.stage-inspector > h2,.stage-inspector > p,.stage-inspector > dl,.stage-inspector > button,.meaning-card { margin-left: 17px; margin-right: 17px; }.confidence-label { font-family: var(--font-mono); font-size: .53rem; text-transform: uppercase; letter-spacing: .05em; }.confidence-label.exact { color: var(--accent-emerald); }.confidence-label.inferred { color: var(--accent-amber); }.stage-inspector > .confidence-label { display: inline-block; margin-top: 19px; }.stage-inspector h2 { margin-top: 6px; font-size: 1rem; }.stage-inspector h2 code { color: var(--text-primary); }.stage-inspector > p { margin-top: 8px; color: var(--text-secondary); font-size: .68rem; line-height: 1.55; }.stage-inspector dl { margin-top: 18px; }.stage-inspector dl div { display: grid; grid-template-columns: 90px 1fr; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-subtle); font-size: .61rem; }.stage-inspector dt { color: var(--text-muted); }.stage-inspector dd { color: var(--text-secondary); }.source-button { display: flex; width: calc(100% - 34px); align-items: center; justify-content: space-between; margin-top: 15px; padding: 9px; background: var(--accent-soft); border: 1px solid color-mix(in srgb,var(--accent-emerald) 25%,var(--border-subtle)); border-radius: 4px; color: var(--accent-emerald); cursor: pointer; font-size: .62rem; }.meaning-card { margin-top: 14px; padding: 12px; background: var(--bg-inset); border-left: 2px solid var(--accent-blue); }.meaning-card strong { font-size: .65rem; }.meaning-card p { margin-top: 5px; color: var(--text-muted); font-size: .61rem; line-height: 1.5; }
.timestep-layout { display: grid; grid-template-columns: minmax(0,1fr) 320px; gap: 14px; }.story-controls { grid-column: 1/-1; display: flex; align-items: center; justify-content: space-between; padding: 13px 17px; }.story-controls h2 { margin-top: 3px; font-size: .9rem; }.playback-controls { display: flex; align-items: center; gap: 5px; }.playback-controls button { min-width: 32px; height: 30px; padding: 0 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; font-size: .63rem; }.playback-controls .play-button { min-width: 58px; background: var(--accent-emerald); color: #08130f; font-weight: 650; }.playback-controls label { display: flex; align-items: center; gap: 6px; margin-left: 8px; color: var(--text-muted); font-size: .58rem; }.playback-controls select { padding: 5px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); font-size: .58rem; }.storyboard { overflow: hidden; }.time-axis { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 12px; padding: 15px 18px; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle); font-family: var(--font-mono); font-size: .55rem; }.time-axis i { height: 1px; background: linear-gradient(90deg,var(--accent-emerald),var(--border-strong)); }.phase-bands { padding: 8px 18px 18px; }.phase-label { display: grid; grid-template-columns: 210px minmax(0,1fr) 90px; gap: 14px; margin-left: 49px; padding: 7px 10px; color: var(--text-muted); font-family: var(--font-mono); font-size: .51rem; }.story-stage { position: relative; display: grid; width: 100%; min-height: 60px; grid-template-columns: 34px 210px minmax(0,1fr) 90px; align-items: center; gap: 14px; padding: 6px 10px 6px 5px; background: transparent; border: 0; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); cursor: pointer; text-align: left; }.story-stage:hover,.story-stage.active { background: var(--bg-surface-hover); }.story-stage.active { box-shadow: inset 2px 0 var(--accent-emerald); }.story-stage.passed { opacity: .55; }.pulse-marker { position: relative; display: grid; width: 28px; height: 28px; place-items: center; }.pulse-marker i { position: absolute; width: 8px; height: 8px; background: var(--border-strong); border-radius: 50%; }.story-stage.active .pulse-marker i { background: var(--accent-emerald); box-shadow: 0 0 0 5px var(--accent-soft); }.pulse-marker span { position: absolute; left: 29px; color: var(--text-muted); font-family: var(--font-mono); font-size: .48rem; }.stage-code,.stage-physics { display: flex; min-width: 0; flex-direction: column; }.stage-code small { color: var(--text-muted); font-size: .52rem; }.stage-code strong { margin: 2px 0; overflow: hidden; font-size: .65rem; text-overflow: ellipsis; white-space: nowrap; }.stage-code strong code { color: var(--text-primary); }.stage-code > span { color: var(--text-muted); font-family: var(--font-mono); font-size: .5rem; }.stage-physics strong { font-size: .65rem; }.stage-physics span { margin-top: 3px; color: var(--text-muted); font-size: .57rem; line-height: 1.4; }.stage-proof { display: flex; align-items: center; justify-content: space-between; gap: 5px; }.stage-proof button { padding: 5px 6px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; font-size: .54rem; }
.current-stage { position: sticky; top: 0; align-self: start; padding: 18px; }.current-index { float: right; color: var(--border-strong); font-family: var(--font-mono); font-size: .59rem; }.current-stage h2 { margin-top: 7px; font-size: 1rem; }.current-stage > p:not(.eyebrow) { margin-top: 8px; color: var(--text-secondary); font-size: .68rem; line-height: 1.55; }.stage-context { margin-top: 17px; padding: 12px; background: var(--accent-soft); border-left: 2px solid var(--accent-emerald); }.stage-context { display: flex; flex-direction: column; gap: 5px; }.stage-context strong { font-size: .67rem; }.stage-context span { color: var(--text-muted); font-size: .61rem; line-height: 1.5; }.current-stage dl { margin-top: 16px; }.current-stage dl div { padding: 8px 0; border-bottom: 1px solid var(--border-subtle); }.current-stage dt { color: var(--text-muted); font-size: .57rem; }.current-stage dd { margin-top: 3px; color: var(--text-secondary); font-size: .61rem; }
@media(max-width:1050px){.lifecycle-layout,.timestep-layout{grid-template-columns:1fr}.stage-inspector,.current-stage{position:static}.phase-label{display:none}.story-stage{grid-template-columns:34px 190px 1fr 80px}}
@media(max-width:760px){.page-header{align-items:flex-start;flex-direction:column}.view-tabs{width:100%}.lifecycle-stage>div{grid-template-columns:1fr}.lifecycle-stage div>span{display:none}.story-controls{align-items:flex-start;flex-direction:column;gap:12px}.story-stage{grid-template-columns:30px 1fr}.stage-physics,.stage-proof{grid-column:2}.stage-proof{justify-content:flex-start}.lifecycle-chain{padding-inline:18px}}
</style>
