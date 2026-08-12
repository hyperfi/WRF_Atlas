<template>
  <div class="overview-view">
    <div v-if="graphStore.loading || !graphStore.isLoaded" class="loading-shell">
      <span class="loading-line"></span>
      <p>Reading the selected WRF source index…</p>
    </div>

    <template v-else>
      <header class="page-intro">
        <div>
          <p class="eyebrow">WRF {{ graphStore.metadata?.wrf_version }} · {{ sourceContextLabel }}</p>
          <h1>Understand what WRF will execute.</h1>
          <p class="intro-copy">
            Move from a namelist choice to the Registry rule, driver branch, called routines,
            and exchanged model state—with the source beside every claim.
          </p>
        </div>
        <div class="source-identity">
          <span class="identity-state"><i></i> Index available</span>
          <dl>
            <div><dt>Source</dt><dd>{{ graphStore.metadata?.source_label || graphStore.metadata?.repository_url || 'Indexed WRF source' }}</dd></div>
            <div><dt>Revision</dt><dd>{{ graphStore.metadata?.branch }} @ {{ shortCommit }}</dd></div>
            <div><dt>Indexed</dt><dd>{{ indexedAt }}</dd></div>
          </dl>
        </div>
      </header>

      <section class="start-grid">
        <div class="question-panel surface-panel">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Start with a question</p>
              <h2>What do you want to understand?</h2>
            </div>
            <span class="section-index">01</span>
          </div>

          <div class="question-list">
            <router-link
              v-for="item in questions"
              :key="item.title"
              :to="item.to"
              class="question-row"
            >
              <span class="question-code">{{ item.code }}</span>
              <span class="question-copy">
                <strong>{{ item.title }}</strong>
                <small>{{ item.description }}</small>
              </span>
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 6l4 4-4 4" /></svg>
            </router-link>
          </div>
        </div>

        <aside class="trace-panel surface-panel">
          <div class="trace-header">
            <div>
              <p class="eyebrow">Canonical trace</p>
              <h2><code>sf_surface_physics = 2</code></h2>
            </div>
            <span class="confidence exact">Source mapped</span>
          </div>

          <div class="trace-chain" aria-label="Configuration trace">
            <div class="trace-step">
              <span class="trace-type namelist">NML</span>
              <div><strong>Configuration value</strong><code>sf_surface_physics = 2</code></div>
            </div>
            <span class="trace-connector"></span>
            <div class="trace-step">
              <span class="trace-type registry">REG</span>
              <div><strong>Registry predicate</strong><code>package LSMSCHEME</code></div>
            </div>
            <span class="trace-connector"></span>
            <div class="trace-step">
              <span class="trace-type driver">DRV</span>
              <div><strong>Runtime dispatch</strong><code>surface_driver</code></div>
            </div>
            <span class="trace-connector"></span>
            <div class="trace-step">
              <span class="trace-type routine">CALL</span>
              <div><strong>Implementation branch</strong><code>CASE (LSMSCHEME)</code></div>
            </div>
          </div>

          <router-link to="/namelist?focus=sf_surface_physics&value=2" class="primary-action">
            Open the complete evidence trace
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 10h11M11 6l4 4-4 4" /></svg>
          </router-link>
          <p class="trace-note">The Registry mapping and dispatch calls are read from the indexed checkout, not a tutorial fixture.</p>
        </aside>
      </section>

      <section class="orientation-panel surface-panel">
        <div class="orientation-copy">
          <p class="eyebrow">Execution orientation</p>
          <h2>From executable entry to physics work</h2>
          <p>Use this compact path for orientation, then open a node to inspect exact callers and source lines.</p>
        </div>
        <div class="orientation-flow">
          <template v-for="(node, index) in orientationNodes" :key="node.id">
            <router-link :to="sourceLink(node)" class="orientation-node">
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
              <strong>{{ node.label }}</strong>
              <small>{{ node.data?.file || node.data?.path || node.type }}</small>
            </router-link>
            <span v-if="index < orientationNodes.length - 1" class="orientation-line"></span>
          </template>
        </div>
      </section>

      <section class="coverage-bar">
        <div class="coverage-intro">
          <p class="eyebrow">Index coverage</p>
          <p>What this snapshot can currently connect.</p>
        </div>
        <dl class="coverage-stats">
          <div><dt>{{ formatted(graphStore.stats?.namelist_options) }}</dt><dd>Namelist options</dd></div>
          <div><dt>{{ formatted(graphStore.stats?.registry_packages) }}</dt><dd>Registry packages</dd></div>
          <div><dt>{{ formatted(graphStore.stats?.state_variables) }}</dt><dd>State fields</dd></div>
          <div><dt>{{ formatted(graphStore.stats?.fortran_files_parsed) }}</dt><dd>Fortran files</dd></div>
        </dl>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useGraphStore } from '@/stores/graphStore'
import type { GraphNode } from '@/types/graph'

const graphStore = useGraphStore()
const sourceContextLabel = computed(() => graphStore.metadata?.source_mode === 'local'
  ? 'local source atlas'
  : 'versioned upstream atlas')

const questions = [
  { code: 'NML', title: 'What happens when I change a physics option?', description: 'Compare active and inactive dispatch branches.', to: '/namelist' },
  { code: 'TIME', title: 'Where am I inside a WRF timestep?', description: 'Follow integration stages and scheduled physics.', to: '/execution' },
  { code: 'FIELD', title: 'Where does a model field travel?', description: 'Trace Registry state into drivers and schemes.', to: '/variables' },
  { code: 'CODE', title: 'Who calls this routine?', description: 'Search symbols and inspect their local source context.', to: '/source' },
]

const shortCommit = computed(() => graphStore.metadata?.commit?.slice(0, 8) || 'unknown')
const indexedAt = computed(() => {
  const value = graphStore.metadata?.indexed_at
  if (!value) return 'unknown'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
})

const orientationIds = [
  'program:wrf',
  'subroutine:wrf_init',
  'subroutine:wrf_run',
  'subroutine:solve_em',
  'subroutine:first_rk_step_part1',
]

const orientationNodes = computed(() => orientationIds
  .map(id => graphStore.getNodeById(id))
  .filter((node): node is GraphNode => Boolean(node)))

const sourceLink = (node: GraphNode) => ({
  path: '/source',
  query: {
    file: node.data?.file || node.data?.path || '',
    line: String(node.data?.line || 1),
  },
})

const formatted = (value?: number) => new Intl.NumberFormat().format(value || 0)
</script>

<style scoped>
.overview-view { display: flex; width: 100%; max-width: 1460px; margin: 0 auto; flex-direction: column; gap: 22px; }
.loading-shell { display: flex; min-height: 60vh; align-items: center; justify-content: center; gap: 12px; color: var(--text-muted); }
.loading-line { width: 36px; height: 2px; overflow: hidden; background: var(--border-subtle); }
.loading-line::after { display: block; width: 50%; height: 100%; background: var(--accent-emerald); animation: loading 1.1s infinite ease-in-out; content: ''; }
@keyframes loading { from { transform: translateX(-110%); } to { transform: translateX(220%); } }

.page-intro { display: grid; grid-template-columns: minmax(0, 1fr) 360px; align-items: end; gap: 48px; padding: 14px 2px 8px; }
.page-intro h1 { max-width: 780px; margin-top: 9px; font-size: clamp(2.3rem, 4vw, 4.1rem); font-weight: 570; line-height: 1.02; letter-spacing: -0.052em; }
.intro-copy { max-width: 760px; margin-top: 19px; color: var(--text-secondary); font-size: 1rem; line-height: 1.7; }
.source-identity { padding-left: 22px; border-left: 1px solid var(--border-subtle); }
.identity-state { display: flex; align-items: center; gap: 8px; margin-bottom: 13px; color: var(--text-secondary); font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
.identity-state i { width: 7px; height: 7px; background: var(--accent-emerald); border-radius: 50%; box-shadow: 0 0 0 4px var(--accent-soft); }
.source-identity dl { display: flex; flex-direction: column; gap: 6px; }
.source-identity dl div { display: grid; grid-template-columns: 68px minmax(0, 1fr); gap: 10px; font-family: var(--font-mono); font-size: 0.66rem; }
.source-identity dt { color: var(--text-muted); }
.source-identity dd { overflow: hidden; color: var(--text-secondary); text-overflow: ellipsis; white-space: nowrap; }

.start-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(390px, 0.8fr); gap: 18px; }
.question-panel, .trace-panel { min-height: 455px; overflow: hidden; }
.section-heading { display: flex; align-items: flex-start; justify-content: space-between; padding: 24px 26px 20px; border-bottom: 1px solid var(--border-subtle); }
.section-heading h2, .trace-header h2, .orientation-copy h2 { margin-top: 7px; font-size: 1.15rem; }
.section-index { color: var(--border-strong); font-family: var(--font-mono); font-size: 0.74rem; }
.question-list { display: flex; flex-direction: column; }
.question-row { display: grid; min-height: 83px; grid-template-columns: 48px minmax(0, 1fr) 24px; align-items: center; gap: 16px; padding: 14px 25px; color: var(--text-primary); border-bottom: 1px solid var(--border-subtle); transition: background 140ms ease; }
.question-row:last-child { border-bottom: 0; }
.question-row:hover { background: var(--bg-surface-hover); }
.question-code { color: var(--accent-emerald); font-family: var(--font-mono); font-size: 0.68rem; font-weight: 650; letter-spacing: 0.04em; }
.question-copy { display: flex; flex-direction: column; gap: 4px; }
.question-copy strong { font-size: 0.88rem; font-weight: 580; }
.question-copy small { color: var(--text-muted); font-size: 0.76rem; }
.question-row svg, .primary-action svg { width: 17px; fill: none; stroke: var(--text-muted); stroke-linecap: round; stroke-width: 1.5; transition: transform 140ms ease; }
.question-row:hover svg, .primary-action:hover svg { transform: translateX(3px); stroke: currentColor; }

.trace-panel { display: flex; flex-direction: column; padding: 24px 26px; }
.trace-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.trace-header code { color: var(--text-primary); font-size: 0.98rem; }
.confidence { padding: 4px 7px; border: 1px solid var(--border-subtle); border-radius: 4px; font-family: var(--font-mono); font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.04em; }
.confidence.exact { background: var(--accent-soft); border-color: color-mix(in srgb, var(--accent-emerald) 30%, var(--border-subtle)); color: var(--accent-emerald); }
.trace-chain { display: flex; flex: 1; flex-direction: column; justify-content: center; padding: 22px 0; }
.trace-step { display: grid; grid-template-columns: 42px minmax(0, 1fr); align-items: center; gap: 12px; }
.trace-step > div { display: flex; flex-direction: column; }
.trace-step strong { font-size: 0.75rem; font-weight: 570; }
.trace-step code { margin-top: 2px; color: var(--text-muted); font-size: 0.67rem; }
.trace-type { display: grid; width: 38px; height: 26px; place-items: center; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; font-family: var(--font-mono); font-size: 0.59rem; font-weight: 650; }
.trace-type.namelist { color: var(--accent-amber); }.trace-type.registry { color: var(--accent-emerald); }.trace-type.driver { color: var(--accent-blue); }.trace-type.routine { color: var(--accent-purple); }
.trace-connector { width: 1px; height: 16px; margin: 3px 0 3px 19px; background: var(--border-strong); }
.primary-action { display: flex; height: 42px; align-items: center; justify-content: space-between; padding: 0 14px; background: var(--accent-emerald); border-radius: 5px; color: #08130f; font-size: 0.78rem; font-weight: 650; }
.primary-action svg { stroke: #08130f; }
.trace-note { margin-top: 11px; color: var(--text-muted); font-size: 0.66rem; line-height: 1.5; }

.orientation-panel { display: grid; grid-template-columns: 260px minmax(0, 1fr); align-items: center; gap: 34px; padding: 24px 26px; }
.orientation-copy p:last-child { margin-top: 8px; color: var(--text-muted); font-size: 0.72rem; line-height: 1.55; }
.orientation-flow { display: flex; min-width: 0; align-items: center; }
.orientation-node { display: flex; width: 150px; min-width: 0; flex-direction: column; gap: 2px; padding: 11px 12px; color: var(--text-primary); background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 5px; }
.orientation-node:hover { border-color: var(--border-strong); background: var(--bg-surface-hover); }
.orientation-node span { color: var(--accent-emerald); font-family: var(--font-mono); font-size: 0.57rem; }
.orientation-node strong { overflow: hidden; font-family: var(--font-mono); font-size: 0.67rem; font-weight: 550; text-overflow: ellipsis; white-space: nowrap; }
.orientation-node small { overflow: hidden; color: var(--text-muted); font-size: 0.58rem; text-overflow: ellipsis; white-space: nowrap; }
.orientation-line { height: 1px; min-width: 13px; flex: 1; background: var(--border-strong); }

.coverage-bar { display: grid; grid-template-columns: 1fr 2fr; align-items: center; padding: 16px 2px 0; }
.coverage-intro p:last-child { margin-top: 4px; color: var(--text-muted); font-size: 0.72rem; }
.coverage-stats { display: grid; grid-template-columns: repeat(4, 1fr); }
.coverage-stats div { padding-left: 22px; border-left: 1px solid var(--border-subtle); }
.coverage-stats dt { color: var(--text-primary); font-family: var(--font-mono); font-size: 1.05rem; }
.coverage-stats dd { margin-top: 2px; color: var(--text-muted); font-size: 0.66rem; }

@media (max-width: 1120px) {
  .page-intro { grid-template-columns: 1fr; gap: 22px; }
  .source-identity { padding-left: 0; border-left: 0; }
  .start-grid { grid-template-columns: 1fr; }
  .orientation-panel { grid-template-columns: 1fr; }
  .orientation-flow { overflow-x: auto; padding-bottom: 5px; }
  .orientation-node { flex: 0 0 150px; }
}

@media (max-width: 720px) {
  .page-intro h1 { font-size: 2.35rem; }
  .coverage-bar { grid-template-columns: 1fr; gap: 16px; }
  .coverage-stats { grid-template-columns: repeat(2, 1fr); gap: 16px 0; }
}
</style>
