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
          Supplementary discovery index · {{ graphifyStore.metadata?.stats.entries.toLocaleString() }} symbols
          <em v-if="sourceMismatch">Different WRF commit from the selected Atlas snapshot</em>
        </p>
        <p v-else-if="graphifyStore.loading">Loading the local Graphify index…</p>
        <p v-else>No sidecar index is available. <code>npm run graphify:index</code> creates one locally.</p>
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
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import { useGraphifyStore } from '@/stores/graphifyStore'
import type { GraphNode, GraphifySearchEntry } from '@/types/graph'

type Scope = 'atlas' | 'graphify'
type Result = { id: string; label: string; type: string; source: Scope; detail: string; context?: string; confidence?: string; node?: GraphNode; graphify?: GraphifySearchEntry }

const props = defineProps<{ isOpen: boolean }>()
const emit = defineEmits(['close'])
const graphStore = useGraphStore()
const graphifyStore = useGraphifyStore()
const router = useRouter()
const query = ref('')
const scope = ref<Scope>('atlas')
const searchInput = ref<HTMLInputElement | null>(null)
const selectedIndex = ref(0)

const sourceMismatch = computed(() => Boolean(graphifyStore.metadata?.sourceCommit && graphStore.metadata?.commit && graphifyStore.metadata.sourceCommit !== graphStore.metadata.commit))
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
const selectGraphify = async () => { scope.value = 'graphify'; await graphifyStore.loadIndex() }
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
watch(() => props.isOpen, async open => { if (open) { if (scope.value === 'graphify') await graphifyStore.loadIndex(); nextTick(() => searchInput.value?.focus()) } })
</script>

<style scoped>
.search-backdrop { position: fixed; inset: 0; z-index: 1000; display: flex; justify-content: center; padding: 9vh 20px 20px; background: rgba(3, 8, 14, .66); backdrop-filter: blur(8px); }
.search-palette { width: min(720px, 100%); max-height: min(760px, 82vh); overflow: hidden; align-self: flex-start; background: color-mix(in srgb, var(--bg-raised) 97%, transparent); border: 1px solid var(--border-strong); border-radius: 10px; box-shadow: 0 28px 80px rgba(0, 0, 0, .48); }
.search-input-wrapper { display: flex; align-items: center; gap: 12px; min-height: 58px; padding: 0 18px; border-bottom: 1px solid var(--border-subtle); }.search-input-wrapper svg { width: 18px; fill: none; stroke: var(--text-muted); stroke-width: 1.5; }.search-input { min-width: 0; flex: 1; background: transparent; border: 0; outline: 0; color: var(--text-primary); font-size: .98rem; }kbd { padding: 2px 6px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-muted); font: .61rem var(--font-mono); }
.search-scope { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; padding: 10px 12px; border-bottom: 1px solid var(--border-subtle); }.search-scope button { display: flex; align-items: baseline; justify-content: space-between; padding: 9px 11px; background: transparent; border: 1px solid transparent; border-radius: 6px; color: var(--text-muted); cursor: pointer; }.search-scope button:hover { background: var(--bg-surface-hover); color: var(--text-secondary); }.search-scope button.active { background: var(--bg-inset); border-color: var(--border-strong); color: var(--text-primary); }.search-scope small { font: .58rem var(--font-mono); letter-spacing: .05em; text-transform: uppercase; }
.provenance-strip { display: flex; align-items: center; gap: 10px; padding: 9px 15px; background: color-mix(in srgb, var(--accent-amber) 6%, var(--bg-inset)); border-bottom: 1px solid var(--border-subtle); }.provenance-mark { display: grid; width: 23px; height: 23px; place-items: center; border: 1px solid color-mix(in srgb, var(--accent-amber) 50%, var(--border-subtle)); border-radius: 4px; color: var(--accent-amber); font: 650 .66rem var(--font-mono); }.provenance-strip p { margin: 0; color: var(--text-secondary); font-size: .66rem; line-height: 1.5; }.provenance-strip code { color: var(--text-primary); }.provenance-strip em { display: block; color: var(--accent-amber); font-style: normal; }
.search-results { min-height: 170px; max-height: 470px; overflow-y: auto; padding: 7px; }.empty { display: flex; min-height: 150px; align-items: center; justify-content: center; flex-direction: column; gap: 7px; color: var(--text-muted); font-size: .76rem; text-align: center; }.empty strong { color: var(--text-secondary); font-size: .84rem; }
.result-item { display: flex; width: 100%; align-items: center; gap: 12px; padding: 10px 11px; background: transparent; border: 1px solid transparent; border-radius: 7px; color: inherit; cursor: pointer; text-align: left; }.result-item:hover, .result-item.selected { background: var(--bg-surface-hover); border-color: var(--border-subtle); }.result-icon { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 5px; color: var(--text-secondary); font: 600 .58rem var(--font-mono); }.result-info { display: flex; min-width: 0; flex: 1; flex-direction: column; gap: 3px; }.result-heading { display: flex; align-items: center; gap: 8px; }.result-heading strong { overflow: hidden; color: var(--text-primary); font-size: .79rem; font-weight: 580; text-overflow: ellipsis; white-space: nowrap; }.result-heading i { padding: 2px 5px; border: 1px solid var(--border-subtle); border-radius: 3px; color: var(--text-muted); font: normal .5rem var(--font-mono); text-transform: uppercase; }.result-heading i.graphify { border-color: color-mix(in srgb, var(--accent-amber) 35%, var(--border-subtle)); color: var(--accent-amber); }.result-meta { overflow: hidden; color: var(--text-muted); font: .61rem var(--font-mono); text-overflow: ellipsis; white-space: nowrap; }.result-context { overflow: hidden; color: var(--text-secondary); font-size: .62rem; text-overflow: ellipsis; white-space: nowrap; }.result-arrow { color: var(--text-muted); font-size: .72rem; }
footer { display: flex; align-items: center; gap: 17px; padding: 9px 14px; border-top: 1px solid var(--border-subtle); color: var(--text-muted); font-size: .58rem; }footer span:last-child { margin-left: auto; }
@media (max-width: 620px) { .search-backdrop { padding: 4vh 8px; }.search-scope { grid-template-columns: 1fr; }footer span:last-child { display: none; } }
</style>
