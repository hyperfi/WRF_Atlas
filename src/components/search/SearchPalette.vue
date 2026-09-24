<template>
  <div v-if="isOpen" class="search-backdrop" @click.self="close">
    <section class="search-palette" role="dialog" aria-modal="true" aria-label="Search WRF Code Atlas">
      <div class="search-input-wrapper">
        <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="4.5"/><path d="m12 12 4 4"/></svg>
        <input ref="searchInput" v-model="query" type="search" class="search-input"
          :placeholder="scope === 'atlas' ? 'Search options, fields and routines' : 'Search the broader indexed codebase'"
          @keydown.esc="close" @keydown.down.prevent="moveSelection(1)"
          @keydown.up.prevent="moveSelection(-1)" @keydown.enter="selectCurrent" />
        <kbd>Esc</kbd>
      </div>

      <div class="search-scope" aria-label="Search source">
        <button :class="{ active: scope === 'atlas' }" @click="scope = 'atlas'">
          <span>Atlas evidence</span><small>WRF-aware</small>
        </button>
        <button :class="{ active: scope === 'graphify' }" @click="selectGraphify">
          <span>Broader codebase</span><small>Graphify</small>
        </button>
      </div>

      <div v-if="scope === 'graphify'" class="provenance-strip">
        <span class="provenance-mark">G</span>
        <p v-if="graphifyStore.available">
          Supplementary discovery index · {{ graphifyStore.metadata?.stats.entries.toLocaleString() }} symbols · {{ graphifyStore.metadata?.sourceLabel }}
          <em v-if="sourceMismatch">Different WRF commit from the selected Atlas snapshot</em>
          <em v-if="folderMismatch">This index may describe a different local folder. Reindex the selected folder before relying on its results.</em>
        </p>
        <p v-else-if="graphifyStore.loading">Loading the local Graphify index…</p>
        <p v-else>No sidecar index is available. {{ localDev ? 'Choose a WRF folder below to build one.' : 'Build one with the local Atlas; GitHub Pages cannot run local commands.' }}</p>
      </div>

      <div v-if="scope === 'graphify' && localDev" class="local-index-control">
        <template v-if="localSource.connected">
          <div class="local-index-heading"><strong>Index {{ localSource.folderName }}</strong><span>Local Atlas only</span></div>
          <p>The browser does not reveal a folder's full path to Python. Confirm the path below; Atlas checks files in it against the folder you selected before running Graphify.</p>
          <div class="local-index-actions">
            <input v-model="wrfPath" type="text" aria-label="Absolute path of selected WRF folder" placeholder="Absolute path to selected WRF folder" :disabled="indexRunning" />
            <button type="button" :disabled="indexRunning || !wrfPath.trim()" @click="runLocalIndex">{{ indexRunning ? 'Indexing…' : graphifyStore.available ? 'Reindex folder' : 'Build index' }}</button>
          </div>
          <p v-if="runStatus" class="index-status" role="status">{{ runStatus }}</p>
          <p v-if="runError" class="index-error" role="alert">{{ runError }}</p>
          <details v-if="runLog && runError"><summary>Indexer output</summary><pre>{{ runLog }}</pre></details>
        </template>
        <p v-else>Choose <strong>Local folder</strong> in the header first, then confirm its path so the local Atlas server can run Python.</p>
      </div>

      <div class="search-results">
        <div v-if="query.trim() && !results.length && !graphifyStore.loading" class="empty">
          No {{ scope === 'atlas' ? 'Atlas evidence' : 'Graphify discoveries' }} match “{{ query }}”.
        </div>
        <div v-else-if="!query.trim()" class="empty">
          <strong>{{ scope === 'atlas' ? 'Source-grounded Atlas search' : 'Supplementary code discovery' }}</strong>
          <span>{{ scope === 'atlas' ? 'Search configuration, Registry packages, routines and fields.' : 'Search symbols, paths and nearby relationships extracted by Graphify.' }}</span>
        </div>

        <button v-for="(result, index) in results" :key="result.id" class="result-item"
          :class="{ selected: selectedIndex === index }" @click="selectResult(result)"
          @mouseenter="selectedIndex = index">
          <span class="result-icon">{{ result.source === 'atlas' ? atlasGlyph(result.type) : 'G' }}</span>
          <span class="result-info">
            <span class="result-heading"><strong>{{ result.label }}</strong><i :class="result.source">{{ result.source === 'atlas' ? 'Atlas' : result.confidence }}</i></span>
            <span class="result-meta">{{ result.detail }}</span>
            <span v-if="result.context" class="result-context">{{ result.context }}</span>
          </span>
          <span class="result-arrow">↗</span>
        </button>
      </div>

      <footer><span><kbd>↑</kbd><kbd>↓</kbd> navigate</span><span><kbd>Enter</kbd> open</span><span>Graphify never overrides Atlas execution evidence.</span></footer>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import { useGraphifyStore } from '@/stores/graphifyStore'
import { useLocalSourceStore } from '@/stores/localSourceStore'
import type { GraphNode, GraphifySearchEntry } from '@/types/graph'

type Scope = 'atlas' | 'graphify'
type Result = { id: string; label: string; type: string; source: Scope; detail: string; context?: string; confidence?: string; node?: GraphNode; graphify?: GraphifySearchEntry }

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['close'])
const graphStore = useGraphStore()
const graphifyStore = useGraphifyStore()
const localSource = useLocalSourceStore()
const localDev = import.meta.env.DEV
const router = useRouter()
const query = ref('')
const scope = ref<Scope>('atlas')
const searchInput = ref<HTMLInputElement | null>(null)
const selectedIndex = ref(0)
const wrfPath = ref('')
const runStatus = ref('')
const runError = ref('')
const runLog = ref('')
const indexRunning = ref(false)
let pollTimer: ReturnType<typeof setTimeout> | undefined
let loadedJobId = ''

const readRunnerStatus = async () => {
  if (!import.meta.env.DEV) return
  try {
    const response = await fetch('/api/graphify/status', { cache: 'no-store' })
    if (!response.ok) return
    const status = await response.json() as { id: string; state: string; message: string; log: string; configuredRoot: string }
    if (!wrfPath.value) wrfPath.value = status.configuredRoot
    indexRunning.value = status.state === 'running'
    if (status.state !== 'idle') {
      runStatus.value = status.message
      runLog.value = status.log
    }
    if (status.state === 'complete' && status.id !== loadedJobId) {
      await graphifyStore.loadIndex(true)
      loadedJobId = status.id
    }
    if (status.state === 'failed') runError.value = status.message
    if (indexRunning.value && props.isOpen && scope.value === 'graphify') pollTimer = setTimeout(readRunnerStatus, 1200)
  } catch {
    runError.value = 'The local index runner is unavailable. Start the Atlas with npm run dev.'
    indexRunning.value = false
  }
}

const digest = async (value: ArrayBuffer) => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', value))).map(byte => byte.toString(16).padStart(2, '0')).join('')

const runLocalIndex = async () => {
  if (!localSource.connected || indexRunning.value) return
  runError.value = ''
  runStatus.value = 'Checking the selected folder…'
  runLog.value = ''
  indexRunning.value = true
  try {
    const signatures: Record<string, string> = {}
    for (const file of ['main/wrf.F', 'Registry/Registry.EM_COMMON']) signatures[file] = await digest(await (await localSource.readFile(file)).arrayBuffer())
    const response = await fetch('/api/graphify/run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ root: wrfPath.value.trim(), folderName: localSource.folderName, signatures }),
    })
    const result = await response.json() as { error?: string; message?: string }
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`)
    runStatus.value = result.message || 'Indexing started.'
    pollTimer = setTimeout(readRunnerStatus, 1200)
  } catch (error) {
    runError.value = error instanceof Error ? error.message : 'Could not start the local index.'
    runStatus.value = ''
    indexRunning.value = false
  }
}

const sourceMismatch = computed(() => Boolean(graphifyStore.metadata?.sourceCommit && graphStore.metadata?.commit && graphifyStore.metadata.sourceCommit !== graphStore.metadata.commit))
const folderMismatch = computed(() => Boolean(localSource.connected && graphifyStore.metadata && graphifyStore.metadata.sourceLabel !== `WRF checkout ${localSource.folderName}`))
const results = computed<Result[]>(() => {
  if (!query.value.trim()) return []
  if (scope.value === 'atlas') return graphStore.searchNodes(query.value, 20).map(node => ({
    id: node.id, label: node.label, type: node.type, source: 'atlas', detail: formatType(node.type),
    context: node.data?.file ? `${node.data.file}${node.data.line ? `:${node.data.line}` : ''}` : undefined, node,
  }))
  return graphifyStore.search(query.value, 20).map(entry => ({
    id: entry.id, label: entry.label, type: entry.kind, source: 'graphify', confidence: entry.confidence,
    detail: `${entry.kind.replaceAll('_', ' ')} · ${entry.path}${entry.line ? `:${entry.line}` : ''}`,
    context: entry.relations[0], graphify: entry,
  }))
})

const close = () => { emit('close'); query.value = '' }
const selectGraphify = async () => { scope.value = 'graphify'; await Promise.all([graphifyStore.loadIndex(), readRunnerStatus()]) }
const moveSelection = (direction: number) => { if (results.value.length) selectedIndex.value = (selectedIndex.value + direction + results.value.length) % results.value.length }
const selectCurrent = () => { const result = results.value[selectedIndex.value]; if (result) selectResult(result) }
const selectResult = (result: Result) => {
  if (result.graphify) router.push({ path: '/source', query: { file: result.graphify.path, line: result.graphify.line || undefined, origin: 'graphify' } })
  else if (result.node?.type === 'physics_scheme' || result.node?.type === 'namelist_option') router.push('/physics')
  else if (result.node?.type === 'state_variable') router.push('/variables')
  else if (result.node?.data?.file) router.push({ path: '/source', query: { file: result.node.data.file, line: result.node.data.line || undefined } })
  else router.push('/source')
  close()
}
const atlasGlyph = (type: string) => ({ namelist_option: 'NL', physics_scheme: 'PH', state_variable: 'VAR', subroutine: 'F', module: 'MOD', source_file: 'SRC' }[type] || 'IDX')
const formatType = (type: string) => type.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase())
watch(query, () => { selectedIndex.value = 0 })
watch(scope, () => { selectedIndex.value = 0 })
watch(() => props.isOpen, async open => { if (open) { if (scope.value === 'graphify') await Promise.all([graphifyStore.loadIndex(), readRunnerStatus()]); nextTick(() => searchInput.value?.focus()) } else if (pollTimer) clearTimeout(pollTimer) })
onUnmounted(() => { if (pollTimer) clearTimeout(pollTimer) })
</script>

<style scoped>
.search-backdrop { position: fixed; inset: 0; z-index: 1000; display: flex; justify-content: center; padding: 9vh 20px 20px; background: rgba(3, 8, 14, .66); backdrop-filter: blur(8px); }
.search-palette { display: flex; flex-direction: column; width: min(720px, 100%); max-height: min(760px, 82vh); overflow: hidden; align-self: flex-start; background: color-mix(in srgb, var(--bg-raised) 97%, transparent); border: 1px solid var(--border-strong); border-radius: 10px; box-shadow: 0 28px 80px rgba(0, 0, 0, .48); }
.search-input-wrapper { display: flex; align-items: center; gap: 12px; min-height: 58px; padding: 0 18px; border-bottom: 1px solid var(--border-subtle); }.search-input-wrapper svg { width: 18px; fill: none; stroke: var(--text-muted); stroke-width: 1.5; }.search-input { min-width: 0; flex: 1; background: transparent; border: 0; outline: 0; color: var(--text-primary); font-size: .98rem; }kbd { padding: 2px 6px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-muted); font: .61rem var(--font-mono); }
.search-scope { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 10px 12px; border-bottom: 1px solid var(--border-subtle); }.search-scope button { display: flex; align-items: baseline; justify-content: space-between; padding: 9px 11px; background: transparent; border: 1px solid transparent; border-radius: 6px; color: var(--text-muted); cursor: pointer; }.search-scope button:hover { background: var(--bg-surface-hover); color: var(--text-secondary); }.search-scope button.active { background: var(--bg-inset); border-color: var(--border-strong); color: var(--text-primary); }.search-scope small { font: .58rem var(--font-mono); letter-spacing: .05em; text-transform: uppercase; }
.provenance-strip { display: flex; align-items: center; gap: 10px; padding: 9px 15px; background: color-mix(in srgb, var(--accent-amber) 6%, var(--bg-inset)); border-bottom: 1px solid var(--border-subtle); }.provenance-mark { display: grid; width: 23px; height: 23px; place-items: center; border: 1px solid color-mix(in srgb, var(--accent-amber) 50%, var(--border-subtle)); border-radius: 4px; color: var(--accent-amber); font: 650 .66rem var(--font-mono); }.provenance-strip p { margin: 0; color: var(--text-secondary); font-size: .66rem; line-height: 1.5; }.provenance-strip code { color: var(--text-primary); }.provenance-strip em { display: block; color: var(--accent-amber); font-style: normal; }
.local-index-control { max-height: 250px; overflow-y: auto; padding: 13px 16px; border-bottom: 1px solid var(--border-subtle); background: var(--bg-inset); }.local-index-control p { margin: 5px 0 0; color: var(--text-muted); font-size: .64rem; line-height: 1.5; }.local-index-heading { display: flex; justify-content: space-between; gap: 12px; color: var(--text-secondary); font-size: .72rem; }.local-index-heading span { color: var(--accent-emerald); font: .56rem var(--font-mono); text-transform: uppercase; }.local-index-actions { display: flex; gap: 8px; margin-top: 11px; }.local-index-actions input { min-width: 0; flex: 1; padding: 8px 10px; background: var(--bg-raised); border: 1px solid var(--border-strong); border-radius: 5px; color: var(--text-primary); font: .65rem var(--font-mono); }.local-index-actions button { padding: 8px 11px; background: var(--accent-soft); border: 1px solid var(--border-strong); border-radius: 5px; color: var(--text-primary); cursor: pointer; font-size: .64rem; white-space: nowrap; }.local-index-actions button:disabled { cursor: not-allowed; opacity: .55; }.local-index-control .index-status { color: var(--accent-emerald); }.local-index-control .index-error { color: var(--accent-amber); }.local-index-control details { margin-top: 7px; color: var(--text-muted); font-size: .61rem; }.local-index-control pre { overflow-x: auto; max-height: 110px; margin-top: 6px; white-space: pre-wrap; }
.search-results { min-height: 130px; max-height: 470px; overflow-y: auto; padding: 7px; }.empty { display: flex; min-height: 130px; align-items: center; justify-content: center; flex-direction: column; gap: 7px; color: var(--text-muted); font-size: .76rem; text-align: center; }.empty strong { color: var(--text-secondary); font-size: .84rem; }
.result-item { display: flex; width: 100%; align-items: center; gap: 12px; padding: 10px 11px; background: transparent; border: 1px solid transparent; border-radius: 7px; color: inherit; cursor: pointer; text-align: left; }.result-item:hover, .result-item.selected { background: var(--bg-surface-hover); border-color: var(--border-subtle); }.result-icon { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 5px; color: var(--text-secondary); font: 600 .58rem var(--font-mono); }.result-info { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 3px; }.result-heading { display: flex; align-items: center; gap: 8px; }.result-heading strong { overflow: hidden; color: var(--text-primary); font-size: .79rem; font-weight: 580; text-overflow: ellipsis; white-space: nowrap; }.result-heading i { padding: 2px 5px; border: 1px solid var(--border-subtle); border-radius: 3px; color: var(--text-muted); font: normal .5rem var(--font-mono); text-transform: uppercase; }.result-heading i.graphify { border-color: color-mix(in srgb, var(--accent-amber) 35%, var(--border-subtle)); color: var(--accent-amber); }.result-meta { overflow: hidden; color: var(--text-muted); font: .61rem var(--font-mono); text-overflow: ellipsis; white-space: nowrap; }.result-context { overflow: hidden; color: var(--text-secondary); font-size: .62rem; text-overflow: ellipsis; white-space: nowrap; }.result-arrow { color: var(--text-muted); font-size: .72rem; }
footer { display: flex; align-items: center; gap: 17px; padding: 9px 14px; border-top: 1px solid var(--border-subtle); color: var(--text-muted); font-size: .58rem; }footer span:last-child { margin-left: auto; }
@media (max-width: 620px) { .search-backdrop { padding: 4vh 8px; }.search-scope { grid-template-columns: 1fr; }footer span:last-child { display: none; } }
</style>
