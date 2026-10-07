<template>
  <section class="lane-tool" aria-label="Rank and thread source walkthrough">
    <div class="lane-heading">
      <div><h3>Rank work and synchronization</h3><p>{{ scopeName }} <span v-if="researcher">· {{ path }}</span></p></div>
      <button class="view-switch" :aria-pressed="listView" @click="listView = !listView"><List :size="16" /> Source list</button>
    </div>
    <p class="order-note">Source order, not elapsed time. Aligned ranks are illustrative, not simultaneous execution.</p>
    <div v-if="!events.length" class="empty-events">No events apply to this scope and mode. Choose another scope or show excluded mechanisms.</div>
    <ol v-else-if="listView" class="source-list">
      <li v-for="event in window.events" :key="event.id"><button :aria-current="event.id === selectedId ? 'step' : undefined" @click="emit('select', event)"><code>{{ event.operation }}</code><span>Line {{ event.evidence[0]?.startLine }} · {{ eventMeaning(event, mode).label }}</span></button></li>
    </ol>
    <div v-else ref="viewport" class="lanes-scroll" tabindex="0" aria-label="Scrollable rank lanes">
      <div class="lanes-canvas" :style="{ width: `${width}px`, height: `${height}px` }">
        <div class="source-axis" :style="{ width: `${width}px` }">
          <span class="axis-label">Source stops</span>
          <button v-for="(event, column) in window.events" :key="event.id" :data-source-id="event.id" :style="{ left: `${x(column) - 66}px` }" :class="{ current: event.id === selectedId, inactive: eventAvailability(event, mode) === 'inactive' }" tabindex="-1" @click="emit('select', event)">
            <strong>{{ event.operation }}</strong><small>Line {{ event.evidence[0]?.startLine }}{{ eventAvailability(event, mode) === 'inactive' ? ' · excluded' : eventAvailability(event, mode) === 'conditional' ? ' · conditional' : '' }}</small>
          </button>
        </div>
        <svg class="lane-geometry" :width="width" :height="height" aria-hidden="true">
          <g v-for="lane in lanes" :key="lane.rank">
            <rect :x="0" :y="lane.top" :width="width" :height="lane.height - 6" rx="4" :class="['rank-surface', { chosen: lane.rank === selectedRank }]" />
            <g v-for="(event, column) in window.events" :key="event.id" :class="{ excluded: eventAvailability(event, mode) === 'inactive' }">
              <path v-for="(segment, i) in segments(event, column, lane)" :key="i" :d="segment" :class="team(event) ? 'thread-track' : 'local-track'" />
              <line v-if="team(event) && event.kind === 'omp_join'" :x1="x(column)" :x2="x(column)" :y1="lane.center - spread(lane)" :y2="lane.center + spread(lane)" class="team-gate" />
            </g>
            <path v-for="link in visibleRequests" :key="link.request" :d="requestPath(link, lane)" class="request-link" />
            <text v-if="lane.rank === selectedRank && hasTeam" v-for="thread in threads" :key="thread" :x="LABEL + 3" :y="threadY(thread - 1, lane) + 4" class="thread-label">T{{ thread - 1 }}</text>
            <text v-if="selected && lane.rank === selectedRank" :x="x(window.events.findIndex(event => event.id === selectedId))" :y="lane.top + lane.height - 12" text-anchor="middle" class="participation-label">{{ participation(selected) }}</text>
          </g>
        </svg>
        <div class="rank-labels" :style="{ height: `${height - HEADER}px` }"><button v-for="lane in lanes" :key="lane.rank" class="rank-label" :style="{ top: `${lane.top - HEADER}px`, height: `${lane.height - 6}px` }" :aria-pressed="lane.rank === selectedRank" @click="emit('rank', lane.rank)"><strong>{{ mpi ? 'Rank' : 'Process' }} {{ lane.rank }}</strong><small>{{ hasTeam ? `${threads} thread tracks` : 'Local source order' }}</small></button></div>
        <template v-for="lane in lanes" :key="lane.rank">
          <button v-for="(event, column) in window.events" :key="event.id" class="event-node" :class="[event.kind, eventAvailability(event, mode), { current: event.id === selectedId && lane.rank === selectedRank, team: team(event) }]" :style="{ left: `${x(column) - 20}px`, top: `${nodeY(event, lane) - 20}px` }" :title="nodeLabel(event, lane.rank)" :aria-label="nodeLabel(event, lane.rank)" :aria-pressed="event.id === selectedId && lane.rank === selectedRank" :tabindex="event.id === selectedId && lane.rank === selectedRank ? 0 : -1" @click="emit('rank', lane.rank); emit('select', event)" @keydown="navigate($event, column)">
            <component :is="icon(event)" :size="18" />
          </button>
        </template>
      </div>
    </div>
    <div v-if="events.length" class="lane-footer">
      <span>Stops {{ window.start + 1 }}–{{ window.start + window.events.length }} of {{ events.length }}</span>
      <div><button aria-label="Previous source page" title="Previous source page" :disabled="window.start === 0" @click="emit('select', events[Math.max(0, window.start - 10)]!)"><ChevronLeft :size="17" /></button><button aria-label="Next source page" title="Next source page" :disabled="window.start + window.events.length >= events.length" @click="emit('select', events[window.start + window.events.length]!)"><ChevronRight :size="17" /></button></div>
    </div>
    <div class="diagram-legend"><span><i class="local-key"></i>Rank-local order</span><span v-if="omp"><GitFork :size="14" />Thread region <GitMerge :size="14" />Team join</span><span v-if="mpi"><Hourglass :size="14" />Request wait</span><span v-if="visibleRequests.length"><i class="request-key"></i>Inferred request association</span></div>
    <p v-if="selected?.kind === 'mpi_barrier' && eventAvailability(selected, mode) !== 'inactive'" class="communicator-gate"><Users :size="17" /><span>Communicator gate: <code>{{ selected.arguments?.[0] || 'unresolved communicator' }}</code>. Membership is unresolved; these illustrative ranks are not a proven member list.</span></p>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ArrowLeftRight, ChevronLeft, ChevronRight, CircleDot, GitFork, GitMerge, Hourglass, List, Lock, Users } from '@lucide/vue'
import { enclosingThreadRegion, eventAvailability, eventMeaning, modeSettings, requestAssociations, sourceWindow, type BuildMode, type ParallelEvent, type RequestAssociation } from '@/lib/parallel'

const props = defineProps<{ events: ParallelEvent[]; scopeEvents: ParallelEvent[]; selectedId: string; mode: BuildMode; ranks: number[]; threads: number; selectedRank: number; scopeName: string; path: string; researcher: boolean }>()
const emit = defineEmits<{ select: [event: ParallelEvent]; rank: [rank: number] }>()
const viewport = ref<HTMLElement>(), listView = ref(false)
const LABEL = 110, COLUMN = 148, HEADER = 88
const window = computed(() => sourceWindow(props.events, props.selectedId))
const mpi = computed(() => modeSettings(props.mode).mpi), omp = computed(() => modeSettings(props.mode).omp)
const selected = computed(() => props.events.find(event => event.id === props.selectedId))
const team = (event: ParallelEvent) => !!enclosingThreadRegion(event, props.scopeEvents, props.mode)
const hasTeam = computed(() => window.value.events.some(team))
const lanes = computed(() => {
  let top = HEADER
  return props.ranks.map(rank => {
    const height = rank === props.selectedRank ? hasTeam.value ? 100 + props.threads * 18 : 104 : 76
    const lane = { rank, top, height, center: top + height / 2 - 3 }
    top += height
    return lane
  })
})
type Lane = { rank: number; top: number; height: number; center: number }
const width = computed(() => LABEL + window.value.events.length * COLUMN + 20)
const height = computed(() => lanes.value.reduce((height, lane) => height + lane.height, HEADER))
const x = (column: number) => LABEL + COLUMN * column + COLUMN / 2
const spread = (lane: Lane) => props.threads <= 1 ? 0 : lane.rank === props.selectedRank ? (props.threads - 1) * 9 : 12
const threadY = (thread: number, lane: Lane) => props.threads <= 1 ? lane.center : lane.center - spread(lane) + thread * spread(lane) * 2 / (props.threads - 1)
const nodeY = (event: ParallelEvent, lane: Lane) => team(event) && (event.construct || event.threadContext) === 'master' ? threadY(0, lane) : lane.center
const segments = (event: ParallelEvent, column: number, lane: Lane) => {
  const left = x(column) - COLUMN / 2, right = x(column) + COLUMN / 2
  if (!team(event)) return [`M ${left} ${lane.center} H ${right}`]
  const region = enclosingThreadRegion(event, props.scopeEvents, props.mode)!
  const forks = event.id === region.id
  const ends = event.regionId === region.id
  return Array.from({ length: props.threads }, (_, thread) => {
    const y = threadY(thread, lane)
    return `M ${left} ${forks ? lane.center : y} L ${left + 24} ${y} H ${right - 24} L ${right} ${ends ? lane.center : y}`
  })
}
const icon = (event: ParallelEvent) => event.kind === 'omp_join' ? GitMerge : event.kind === 'omp_region' ? ((event.construct === 'critical') ? Lock : event.construct?.startsWith('parallel') ? GitFork : CircleDot) : event.kind === 'mpi_wait' ? Hourglass : event.kind === 'mpi_barrier' ? Users : ['exchange', 'mpi_post', 'mpi_transfer', 'mpi_collective'].includes(event.kind) ? ArrowLeftRight : CircleDot
const nodeLabel = (event: ParallelEvent, rank: number) => `${mpi.value ? 'Rank' : 'Process'} ${rank}: ${event.operation}, ${eventMeaning(event, props.mode).label}, line ${event.evidence[0]?.startLine}${eventAvailability(event, props.mode) === 'conditional' ? ', conditional participation' : ''}`
const participation = (event: ParallelEvent) => {
  if (eventAvailability(event, props.mode) === 'inactive') return 'Excluded mechanism'
  const construct = event.construct || event.threadContext
  if (omp.value && construct === 'master') return 'Primary thread only'
  if (omp.value && construct === 'single' && event.kind !== 'omp_join') return 'One thread, identity unknown'
  if (omp.value && construct === 'critical') return 'Mutual exclusion, not a join'
  if (event.kind === 'omp_join') return 'Team join, not MPI'
  if (event.kind === 'mpi_wait') return 'Caller only; request wait'
  if (event.kind === 'mpi_barrier') return 'Communicator members'
  if (event.kind === 'omp_region' && event.construct?.startsWith('parallel')) return 'Rank-local thread team'
  return team(event) ? 'Lexical thread context' : 'Local source site'
}
const visibleRequests = computed(() => requestAssociations(props.scopeEvents, props.mode).filter(link => window.value.events.some(event => event.id === link.post.id) && window.value.events.some(event => event.id === link.wait.id) && (props.selectedId === link.post.id || props.selectedId === link.wait.id)))
const requestPath = (link: RequestAssociation, lane: Lane) => {
  const start = x(window.value.events.findIndex(event => event.id === link.post.id)), end = x(window.value.events.findIndex(event => event.id === link.wait.id))
  const y = lane.center + 25
  return `M ${start} ${lane.center + 19} V ${y} H ${end} V ${lane.center + 19}`
}
const navigate = async (key: KeyboardEvent, column: number) => {
  const global = window.value.start + column
  let target: ParallelEvent | undefined
  if (key.key === 'ArrowRight') target = props.events[global + 1]
  else if (key.key === 'ArrowLeft') target = props.events[global - 1]
  else if (key.key === 'Home') target = props.events[0]
  else if (key.key === 'End') target = props.events.at(-1)
  else if (key.key === 'ArrowUp' || key.key === 'ArrowDown') {
    const rankIndex = props.ranks.indexOf(props.selectedRank) + (key.key === 'ArrowUp' ? -1 : 1)
    if (props.ranks[rankIndex] !== undefined) emit('rank', props.ranks[rankIndex]!)
  } else return
  key.preventDefault()
  if (target) emit('select', target)
  await nextTick()
  viewport.value?.querySelector<HTMLButtonElement>('.event-node.current')?.focus({ preventScroll: true })
}
const revealCurrent = async () => {
  await nextTick()
  const current = viewport.value?.querySelector<HTMLElement>('.event-node.current')
  if (!current || !viewport.value) return
  const view = viewport.value, left = current.offsetLeft, top = current.offsetTop
  // Scroll only this canvas, leaving page and inspector position undisturbed.
  if (left < view.scrollLeft + LABEL || left + 40 > view.scrollLeft + view.clientWidth) view.scrollLeft = Math.max(0, left - LABEL - (view.clientWidth - LABEL - 40) / 2)
  if (top < view.scrollTop + HEADER || top + 40 > view.scrollTop + view.clientHeight) view.scrollTop = Math.max(0, top - HEADER)
}
watch(() => [props.selectedId, props.selectedRank, props.mode, listView.value], revealCurrent, { immediate: true })
let resize: ResizeObserver | undefined
watch(viewport, view => {
  resize?.disconnect()
  if (view) { resize = new ResizeObserver(revealCurrent); resize.observe(view) }
})
onBeforeUnmount(() => resize?.disconnect())
</script>

<style scoped>
.lane-tool { min-width: 0; border: 1px solid var(--border-subtle); border-radius: 6px; overflow: hidden; background: var(--bg-inset); }
.lane-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 16px 18px 8px; }.lane-heading h3 { font-size: 1rem; }.lane-heading p { color: var(--text-secondary); font: .8rem var(--font-mono); overflow-wrap: anywhere; margin-top: 6px; }.lane-heading p span { font-size: .75rem; }
button { cursor: pointer; color: var(--text-primary); font: inherit; }button:focus-visible { outline: 2px solid var(--accent-emerald); outline-offset: -2px; }button:disabled { opacity: .4; cursor: default; }
.view-switch { display: flex; flex: none; align-items: center; gap: 6px; min-height: 44px; border: 1px solid var(--border-strong); border-radius: 4px; background: transparent; padding: 6px 10px; font-size: .8rem; }.view-switch[aria-pressed=true] { background: var(--accent-soft); }
.order-note { color: var(--text-secondary); font-size: .8rem; padding: 0 18px 14px; line-height: 1.5; }
.lanes-scroll { overflow: auto; max-height: 460px; position: relative; scrollbar-color: var(--border-strong) var(--bg-inset); scroll-padding-left: 110px; }.lanes-canvas { position: relative; }.source-axis { position: sticky; top: 0; z-index: 3; height: 88px; background: var(--bg-raised); border-block: 1px solid var(--border-subtle); }.axis-label { position: sticky; left: 0; display: flex; align-items: center; height: 88px; width: 110px; padding: 12px; background: var(--bg-raised); z-index: 2; color: var(--text-secondary); font-size: .8rem; }.source-axis button { position: absolute; top: 0; width: 132px; height: 88px; display: flex; flex-direction: column; justify-content: center; gap: 6px; background: transparent; border: 0; padding: 10px 4px; text-align: left; }.source-axis strong { font: 550 .78rem var(--font-mono); overflow-wrap: anywhere; }.source-axis small { font-size: .72rem; color: var(--text-secondary); }.source-axis .current { box-shadow: inset 0 -2px var(--accent-emerald); }
.lane-geometry { position: absolute; inset: 0; pointer-events: none; }.rank-surface { fill: var(--bg-inset); }.rank-surface.chosen { fill: var(--bg-raised); }.local-track { stroke: var(--border-strong); fill: none; stroke-width: 1.5; }.thread-track { stroke: var(--accent-emerald); fill: none; stroke-width: 1.3; }.team-gate { stroke: var(--accent-amber); stroke-width: 3; }.thread-label { fill: var(--text-secondary); font: 11px var(--font-mono); }.request-link { fill: none; stroke: var(--accent-amber); stroke-dasharray: 4 4; stroke-width: 1.5; }
.rank-label { position: sticky; left: 0; z-index: 2; width: 110px; display: flex; flex-direction: column; justify-content: center; gap: 7px; text-align: left; padding: 12px; border: 0; border-bottom: 1px solid var(--border-subtle); background: var(--bg-inset); }.rank-label strong { font-size: .8rem; }.rank-label small { color: var(--text-secondary); font-size: .7rem; line-height: 1.5; }.rank-label[aria-pressed=true] { color: var(--accent-emerald); background: var(--bg-raised); }
.event-node { position: absolute; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-strong); border-radius: 4px; background: var(--bg-inset); color: var(--text-secondary); }.event-node.team { color: var(--accent-emerald); }.event-node.mpi_wait,.event-node.omp_join,.event-node.mpi_barrier { color: var(--accent-amber); border-color: var(--accent-amber); }.event-node.conditional { border-style: dashed; }.event-node.current { outline: 2px solid var(--accent-emerald); outline-offset: 3px; background: var(--accent-soft); }.event-node.inactive,.source-axis .inactive { color: var(--text-muted); border-color: var(--border-subtle); }.event-node.inactive { background: var(--bg-raised); border-style: dotted; }.excluded { opacity: .35; }
.lane-footer { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 6px 16px; border-top: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: .75rem; }.lane-footer div { display: flex; gap: 5px; }.lane-footer button { width: 44px; height: 44px; display: grid; place-items: center; border: 0; background: transparent; }
.diagram-legend { display: flex; flex-wrap: wrap; gap: 10px 18px; padding: 8px 18px 16px; color: var(--text-secondary); font-size: .75rem; }.diagram-legend span { display: flex; align-items: center; gap: 5px; }.local-key,.request-key { width: 18px; border-top: 1px solid var(--border-strong); }.request-key { border-top: 1px dashed var(--accent-amber); }.communicator-gate { display: flex; align-items: flex-start; gap: 10px; border-top: 1px dashed var(--accent-amber); color: var(--text-secondary); padding: 14px 18px; font-size: .85rem; line-height: 1.6; }.communicator-gate svg { flex: none; margin-top: 4px; color: var(--accent-amber); }
.source-list { list-style: none; padding: 0 18px; }.source-list button { display: flex; flex-direction: column; gap: 5px; width: 100%; min-height: 55px; border: 0; border-bottom: 1px solid var(--border-subtle); background: transparent; padding: 10px; text-align: left; }.source-list button[aria-current=step] { background: var(--accent-soft); }.source-list code { font-size: .85rem; overflow-wrap: anywhere; }.source-list span { color: var(--text-secondary); font-size: .8rem; }.empty-events { min-height: 150px; padding: 24px 18px; color: var(--text-secondary); }
.rank-labels { position: sticky; left: 0; z-index: 2; width: 110px; pointer-events: none; }.rank-labels .rank-label { position: absolute; pointer-events: auto; }
.participation-label { fill: var(--text-secondary); font: 10px var(--font-sans); }
@media(max-width:600px) { .lane-heading { flex-wrap: wrap; }.lanes-scroll { max-height: 370px; } }
</style>
